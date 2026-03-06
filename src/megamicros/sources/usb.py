# megamicros.sources.usb.py
#
# ® Copyright 2024-2026 Bimea
# Author: bruno.gas@bimea.io
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
USB hardware data source.

This data source interfaces with physical Megamicros USB devices (Mu32, Mu256, Mu1024)
for real-time data acquisition from MEMS microphone arrays.

Features:
    - Direct USB communication with hardware
    - Multi-threaded asynchronous transfers
    - Thread-safe queue management
    - FPGA command interface
    - Support for int32 and float32 datatypes
    
Examples:
    Basic usage::

        from megamicros.sources import UsbDataSource
        from megamicros.core.config import AcquisitionConfig, UsbConfig
        
        usb_config = UsbConfig(vendor_id=0xFE27, product_id=0xAC03)
        source = UsbDataSource(usb_config)
        
        config = AcquisitionConfig(
            mems=[0, 1, 2, 3],
            sampling_frequency=50000,
            frame_length=1024,
            duration=10.0
        )
        source.configure(config)
        source.start()
        
        for frame in source:
            print(f"Frame: {frame.shape}")
        
        source.wait()
        source.stop()
        
Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""

from typing import Iterator
from threading import Thread
import time
import queue
import numpy as np

from .base import BaseDataSource, SourceState
from ..core.config import AcquisitionConfig, UsbConfig, MemsArrayInfo
from ..usb import Usb
from ..log import log
from ..exception import MuException


# MegaMicro hardware commands (from core/mu.py)
MU_CMD_RESET = b'\x00'
MU_CMD_INIT = b'\x01'
MU_CMD_START = b'\x02'
MU_CMD_STOP = b'\x03'
MU_CMD_COUNT = b'\x04'
MU_CMD_ACTIVE = b'\x05'
MU_CMD_DATATYPE = b'\x09'
MU_CMD_FX3_RESET = 0xC0
MU_CMD_FX3_PH = 0xC4

# Hardware codes
MU_CODE_DATATYPE_INT32 = b'\x00'
MU_CODE_DATATYPE_FLOAT32 = b'\x01'

# Hardware properties
MU_BEAM_MEMS_NUMBER = 8
MU_MEMS_QUANTIZATION = 23
MU_MEMS_AMPLITUDE = 2**MU_MEMS_QUANTIZATION
TRANSFER_DATAWORDS_SIZE = 4


class UsbSourceException(MuException):
    """Exception for USB data source."""
    pass


class UsbDataSource(BaseDataSource):
    """
    USB hardware data source.
    
    Interfaces with physical Megamicros devices via USB for real-time acquisition.
    
    Args:
        usb_config: USB device configuration
        available_mems: Number of available MEMS (default: auto-detect)
    """
    
    def __init__(
        self,
        usb_config: UsbConfig | None = None,
        available_mems: int | None = None,
    ):
        super().__init__()
        
        self._usb_config = usb_config or UsbConfig()
        self._usb_device: Usb | None = None
        self._queue: queue.Queue = queue.Queue()  # Created once, reused across runs
        self._queue_size: int = 0  # Track configured size
        self._transfer_thread: Thread | None = None
        self._timer_thread: Thread | None = None
        self._halt_request = False
        self._frames_received = 0
        self._transfert_lost = 0
        
        # Detect or set available MEMS
        if available_mems is None:
            available_mems = self._detect_device_mems()
        
        self._info = MemsArrayInfo(
            available_mems=list(range(available_mems)),
            description=f"USB Device {hex(self._usb_config.vendor_id)}:{hex(self._usb_config.product_id)}"
        )
        
        log.info(f"UsbDataSource initialized: {available_mems} MEMS available")
    
    def _detect_device_mems(self) -> int:
        """Detect number of MEMS from product ID."""
        product_map = {
            0xAC00: 32,   # Mu32-usb2
            0xAC01: 32,   # Mu32-usb3
            0xAC02: 256,  # Mu256
            0xAC03: 1024, # Mu1024
        }
        return product_map.get(self._usb_config.product_id, 32)
    
    def _do_configure(self, config: AcquisitionConfig) -> None:
        """Configure USB device."""
        # Open USB device
        if self._usb_device is None:
            self._usb_device = Usb()
            try:
                self._usb_device.open(
                    vendor_id=self._usb_config.vendor_id,
                    product_id=self._usb_config.product_id,
                    endpoint_in=self._usb_config.endpoint_in
                )
                self._usb_device.claim(interface=self._usb_config.interface)
            except Exception as e:
                raise UsbSourceException(f"Failed to open USB device: {e}")
        
        # Validate channels
        for mems in config.mems:
            if mems not in self._info.available_mems:
                raise ValueError(f"MEMS {mems} not available")
        
        # Send FPGA commands
        try:
            self._send_reset()
            self._send_sampling_frequency(config.sampling_frequency)
            self._send_active_channels(config.mems, config.analogs, config.counter)
            self._send_datatype(config.datatype)
            
            if config.duration > 0:
                total_samples = int(config.sampling_frequency * config.duration)
                self._send_sample_count(total_samples)
                
        except Exception as e:
            raise UsbSourceException(f"Failed to configure device: {e}")
        
        # Setup queue (recreate only if size changed)
        if config.queue_size != self._queue_size:
            old_size = self._queue_size
            self._queue = queue.Queue(maxsize=config.queue_size)
            self._queue_size = config.queue_size
            if old_size > 0:  # Not first configuration
                log.warning(f"Queue size changed ({old_size}→{config.queue_size}) - previous frames lost")
        # NOTE: If queue_size unchanged, queue is preserved (frames accumulate)!
        
        self._halt_request = False
        self._frames_received = 0
        # NOTE: transfert_lost is NOT reset - cumulative counter
        
        log.debug(f"UsbDataSource configured: {len(config.mems)} MEMS, "
                 f"{config.sampling_frequency}Hz, {config.frame_length} samples/frame")
    
    def _do_start(self) -> None:
        """Start USB acquisition."""
        if self._config is None or self._usb_device is None:
            raise RuntimeError("Source not configured")
        
        # Start transfer thread
        self._transfer_thread = Thread(
            target=self._transfer_worker,
            name="UsbTransferThread",
            daemon=True
        )
        self._transfer_thread.start()
        
        # Start timer thread if duration is limited
        if self._config.duration > 0:
            self._timer_thread = Thread(
                target=self._timer_worker,
                name="UsbTimerThread",
                daemon=True
            )
            self._timer_thread.start()
        
        # Send start command
        self._send_start()
        
        log.debug("UsbDataSource acquisition started")
    
    def _do_stop(self) -> None:
        """Stop USB acquisition."""
        self._halt_request = True
        
        # Send stop command
        if self._usb_device:
            try:
                self._send_stop()
            except:
                pass
        
        # Wait for threads
        if self._transfer_thread and self._transfer_thread.is_alive():
            self._transfer_thread.join(timeout=2.0)
        
        if self._timer_thread and self._timer_thread.is_alive():
            self._timer_thread.join(timeout=1.0)
        
        log.debug(f"UsbDataSource stopped: {self._frames_received} frames received, "
                 f"{self._transfert_lost} frames lost")
    
    def _generate_frames(self) -> Iterator[np.ndarray]:
        """Yield frames from queue."""
        if self._config is None:
            raise RuntimeError("Source not configured")
        
        timeout_sec = self._config.queue_timeout / 1000.0
        
        while self._state == SourceState.RUNNING:
            try:
                frame = self._queue.get(timeout=timeout_sec)
                yield frame
            except queue.Empty:
                # Check if acquisition is complete
                if self._halt_request or (self._transfer_thread and not self._transfer_thread.is_alive()):
                    break
    
    def _transfer_worker(self) -> None:
        """Worker thread for USB bulk transfers."""
        if self._config is None or self._usb_device is None:
            return
        
        frame_length = self._config.frame_length
        n_channels = len(self._config.active_channels)
        transfer_size = frame_length * n_channels * TRANSFER_DATAWORDS_SIZE
        
        try:
            while not self._halt_request and self._state == SourceState.RUNNING:
                # Read bulk data
                data = self._usb_device.bulkRead(
                    size=transfer_size,
                    timeout=self._usb_config.transfer_timeout
                )
                
                if data is None:
                    continue
                
                # Convert to numpy array
                frame = self._bytes_to_frame(data, n_channels, frame_length)
                
                # Put in queue (drop oldest if full)
                if self._queue.maxsize > 0 and self._queue.qsize() >= self._queue.maxsize:
                    try:
                        self._queue.get_nowait()
                        self._transfert_lost += 1
                    except queue.Empty:
                        pass
                
                self._queue.put(frame)
                self._frames_received += 1
                
        except Exception as e:
            log.error(f"USB transfer error: {e}")
            self._halt_request = True
    
    def _timer_worker(self) -> None:
        """Worker thread for duration timer."""
        if self._config is None or self._config.duration == 0:
            return
        
        time.sleep(self._config.duration)
        self._halt_request = True
        log.debug(f"Timer expired after {self._config.duration}s")
    
    def _bytes_to_frame(self, data: bytes, n_channels: int, frame_length: int) -> np.ndarray:
        """Convert raw bytes to numpy frame."""
        if self._config is None:
            raise RuntimeError("Source not configured")
        
        # Convert bytes to int32 array
        arr = np.frombuffer(data, dtype=np.int32)
        
        # Reshape to (channels, samples)
        frame = arr.reshape((n_channels, frame_length), order='F')
        
        # Convert to float if needed
        if self._config.datatype == 'float32':
            frame = frame.astype(np.float32)
            # Apply sensibility to MEMS channels
            mems_offset = 1 if self._config.counter else 0
            n_mems = len(self._config.mems)
            if n_mems > 0:
                frame[mems_offset:mems_offset+n_mems, :] *= self._config.sensibility
        
        return frame
    
    # FPGA command methods
    def _send_reset(self) -> None:
        """Send reset command."""
        if self._usb_device:
            self._usb_device.controlWrite(MU_CMD_RESET)
    
    def _send_start(self) -> None:
        """Send start command."""
        if self._usb_device:
            self._usb_device.controlWrite(MU_CMD_START)
    
    def _send_stop(self) -> None:
        """Send stop command."""
        if self._usb_device:
            self._usb_device.controlWrite(MU_CMD_STOP)
    
    def _send_sampling_frequency(self, freq: int) -> None:
        """Send sampling frequency."""
        if self._usb_device:
            freq_bytes = freq.to_bytes(4, byteorder='little')
            self._usb_device.controlWrite(MU_CMD_INIT, freq_bytes)
    
    def _send_active_channels(self, mems: list[int], analogs: list[int], counter: bool) -> None:
        """Send active channels configuration."""
        # TODO: Implement channel activation FPGA command
        pass
    
    def _send_datatype(self, datatype: str) -> None:
        """Send datatype configuration."""
        if self._usb_device:
            code = MU_CODE_DATATYPE_INT32 if datatype == 'int32' else MU_CODE_DATATYPE_FLOAT32
            self._usb_device.controlWrite(MU_CMD_DATATYPE, code)
    
    def _send_sample_count(self, count: int) -> None:
        """Send expected sample count."""
        if self._usb_device:
            count_bytes = count.to_bytes(4, byteorder='little')
            self._usb_device.controlWrite(MU_CMD_COUNT, count_bytes)
    
    def _do_wait(self) -> None:
        """Wait for acquisition threads to complete."""
        if self._transfer_thread:
            self._transfer_thread.join()
        if self._timer_thread:
            self._timer_thread.join()
    
    @property
    def queue_content(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    @property
    def transfert_lost(self) -> int:
        """Get number of lost frames."""
        return self._transfert_lost
    
    def __del__(self):
        """Cleanup USB resources."""
        if self._usb_device:
            try:
                self._usb_device.release()
                self._usb_device.close()
            except:
                pass
