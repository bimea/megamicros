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
from ctypes import create_string_buffer
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
MU_CMD_PURGE = b'\x06'
MU_CMD_DATATYPE = b'\x09'
MU_CMD_FX3_RESET = 0xC0
MU_CMD_FX3_PH = 0xC4

# FPGA command wrappers
MU_CMD_FPGA_0 = 0xB0  # Send a 0 byte command to FPGA
MU_CMD_FPGA_1 = 0xB1  # Send a 1 byte command to FPGA
MU_CMD_FPGA_2 = 0xB2  # Send a 2 byte command to FPGA
MU_CMD_FPGA_3 = 0xB3  # Send a 3 byte command to FPGA
MU_CMD_FPGA_4 = 0xB4  # Send a 4 byte command to FPGA

# Hardware codes
MU_CODE_DATATYPE_INT32 = b'\x00'
MU_CODE_DATATYPE_FLOAT32 = b'\x01'

# Hardware properties
MU_BEAM_MEMS_NUMBER = 8
MU_MEMS_QUANTIZATION = 23
MU_MEMS_AMPLITUDE = 2**MU_MEMS_QUANTIZATION
TRANSFER_DATAWORDS_SIZE = 4
DEFAULT_CLOCK_DIVIDER_REFERENCE = 500000  # 500 kHz clock reference


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
            0xAC00: 32,   # Mu32-usb2 (legacy)
            0xAC01: 256,  # Mu256
            0xAC02: 1024, # Mu1024
            0xAC03: 32,   # Mu32
            0xAC04: 64,   # Mu64 (new)
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
                    bus_address=self._usb_config.bus_address,
                    endpoint_in=self._usb_config.endpoint_in
                )
                self._usb_device.claim()
            except Exception as e:
                raise UsbSourceException(f"Failed to open USB device: {e}")
        
        # Validate channels
        for mems in config.mems:
            if mems not in self._info.available_mems:
                raise ValueError(f"MEMS {mems} not available")
        
        # Configure USB buffers
        n_channels = len(config.active_channels)
        buffer_size = config.frame_length * n_channels * TRANSFER_DATAWORDS_SIZE
        self._usb_device.setBuffersNumber(self._usb_config.buffers_number)
        self._usb_device.setBufferSize(buffer_size)
        
        log.info(f"USB configured: {buffer_size} bytes/frame, {n_channels} channels, "
                 f"{self._usb_config.buffers_number} buffers")
        
        # Send FPGA commands
        try:
            log.debug("Sending RESET+PURGE command")
            self._send_reset()
            
            log.debug(f"Sending sampling frequency: {config.sampling_frequency} Hz")
            self._send_sampling_frequency(config.sampling_frequency)
            
            log.debug(f"Sending active channels: {config.mems}")
            self._send_active_channels(config.mems, config.analogs, config.counter)
            
            log.debug(f"Sending datatype: {config.datatype}")
            self._send_datatype(config.datatype)
            
            # CRITICAL: For asyncBulkTransfer (streaming mode), always send 0
            # The timer controls the duration, not the FPGA sample counter
            log.debug("Sending sample count: 0 (streaming mode)")
            self._send_sample_count(0)
                
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
        """Start USB acquisition using native async bulk transfer."""
        if self._config is None or self._usb_device is None:
            raise RuntimeError("Source not configured")
        
        # Send start command to FPGA
        log.info("Sending START command to FPGA")
        self._send_start()
        
        # Configure STOP callback to send FPGA STOP command when timer expires
        self._usb_device.setOnStopCallback(self._send_stop)
        
        # CRITICAL: Set transfer timeout much longer than duration
        # This prevents individual transfers from timing out before the global timer expires
        transfer_timeout_ms = max(self._config.duration * 2000, 5000)  # 2x duration or 5s min
        self._usb_device._Usb__transfer_timeout = transfer_timeout_ms
        log.debug(f"USB transfer timeout set to {transfer_timeout_ms}ms")
        
        # Use native asyncBulkTransfer from v3 (tested and working)
        # This uses libusb's native async transfers with callbacks
        log.info(f"Starting native USB async bulk transfer (duration={self._config.duration}s)")
        try:
            self._usb_device.asyncBulkTransfer(self._config.duration)
        except Exception as e:
            raise UsbSourceException(f"Failed to start async bulk transfer: {e}")
        
        # Start thread to consume data from USB queue
        self._transfer_thread = Thread(
            target=self._consume_usb_queue,
            name="UsbQueueConsumer",
            daemon=True
        )
        self._transfer_thread.start()
        
        log.info(f"USB acquisition started (duration={self._config.duration}s, "
                f"expected frames={self._config.total_frames})")
    
    def _do_stop(self) -> None:
        """Stop USB acquisition."""
        self._halt_request = True
        
        # Set flag to stop USB async transfer
        # Note: asyncBulkTransferStop() is not implemented, so we set the internal flag
        if self._usb_device:
            try:
                # Access private flag to stop transfer loop
                self._usb_device._Usb__bulk_transfer_on = False
            except:
                pass
        
        # Wait for consumer thread
        if self._transfer_thread and self._transfer_thread.is_alive():
            self._transfer_thread.join(timeout=2.0)
        
        log.debug(f"UsbDataSource stopped: {self._frames_received} frames received, "
                 f"{self._transfert_lost} frames lost")
    
    def _consume_usb_queue(self) -> None:
        """Consumer thread that reads from USB internal queue and converts to frames."""
        if self._config is None or self._usb_device is None:
            return
        
        frame_length = self._config.frame_length
        n_channels = len(self._config.active_channels)
        transfer_size = frame_length * n_channels * TRANSFER_DATAWORDS_SIZE
        
        log.debug(f"Queue consumer started: expecting {transfer_size} bytes per frame")
        
        # Access USB internal queue and transfer flag
        usb_queue = self._usb_device._Usb__queue
        queue_timeout = self._config.queue_timeout / 1000.0
        
        try:
            # Loop while USB transfer is active OR queue has data
            while not self._halt_request:
                # Check if USB transfer is still running
                usb_active = self._usb_device._Usb__bulk_transfer_on
                
                try:
                    # Get raw bytes from USB queue
                    data = usb_queue.get(timeout=queue_timeout)
                    
                    if data is None or len(data) == 0:
                        continue
                    
                    # Verify size
                    if len(data) != transfer_size:
                        log.warning(f"Incorrect frame size: got {len(data)}, expected {transfer_size}")
                        continue
                    
                    # Convert to numpy array
                    frame = self._bytes_to_frame(data, n_channels, frame_length)
                    
                    # Put in our queue (drop oldest if full)
                    if self._queue.maxsize > 0 and self._queue.qsize() >= self._queue.maxsize:
                        try:
                            self._queue.get_nowait()
                            self._transfert_lost += 1
                        except queue.Empty:
                            pass
                    
                    self._queue.put(frame)
                    self._frames_received += 1
                    
                except queue.Empty:
                    # Timeout waiting for data
                    # If USB transfer is done AND queue is empty, we're finished
                    if not self._usb_device._Usb__bulk_transfer_on:
                        log.debug("USB transfer complete and queue empty, stopping consumer")
                        break
                    # Otherwise keep waiting for data
                    log.debug(f"Queue timeout (USB still active: {usb_active})")
                    continue
                    
                except Exception as e:
                    log.error(f"Error consuming USB queue: {e}")
                    break
                    
        except Exception as e:
            log.error(f"Fatal error in queue consumer: {e}")
        
        log.debug(f"Queue consumer stopped: {self._frames_received} frames received")
    
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
        
        log.debug(f"Transfer worker started: reading {transfer_size} bytes per frame")
        
        try:
            while not self._halt_request and self._state == SourceState.RUNNING:
                try:
                    # Read bulk data
                    data = self._usb_device.bulkRead(
                        size=transfer_size,
                        timeout=self._usb_config.transfer_timeout
                    )
                    
                    if data is None or len(data) == 0:
                        log.warning("Received empty data from USB")
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
                    
                except Exception as read_error:
                    # Log but continue on individual read errors
                    error_msg = str(read_error)
                    if "TIMEOUT" in error_msg or "timeout" in error_msg.lower():
                        log.debug(f"USB read timeout (normal at end of acquisition)")
                        break  # Timeout usually means end of data
                    else:
                        log.warning(f"USB read error: {read_error}")
                        # Continue trying to read unless it's a critical error
                        if "PIPE" in error_msg or "NO_DEVICE" in error_msg:
                            break
                    
        except Exception as e:
            log.error(f"USB transfer thread fatal error: {e}")
            self._halt_request = True
        
        log.debug(f"Transfer worker stopped: {self._frames_received} frames received")
    
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
        """Send RESET and PURGE commands to FPGA (clear FIFO)."""
        if not self._usb_device:
            return
        # RESET command
        buf = create_string_buffer(1)
        buf[0] = MU_CMD_RESET
        self._usb_device.ctrlWrite(MU_CMD_FPGA_0, buf)
        # PURGE command (clear FIFO)
        buf[0] = MU_CMD_PURGE
        self._usb_device.ctrlWrite(MU_CMD_FPGA_0, buf)
    
    def _send_start(self) -> None:
        """Send START command to FPGA."""
        if not self._usb_device:
            return
        buf = create_string_buffer(2)
        buf[0] = MU_CMD_START
        buf[1] = 0x00
        self._usb_device.ctrlWrite(MU_CMD_FPGA_1, buf)
    
    def _send_stop(self) -> None:
        """Send STOP command to FPGA and wait for remaining data."""
        if not self._usb_device:
            return
        buf = create_string_buffer(2)
        buf[0] = MU_CMD_STOP
        buf[1] = 0x00
        self._usb_device.ctrlWrite(MU_CMD_FPGA_1, buf)
        log.info("STOP command sent to FPGA")
        
        # Wait a bit for last USB data to arrive from FPGA FIFO
        import time
        time.sleep(0.2)  # 200ms should be enough for last frames
        log.debug("Waited 200ms for remaining FPGA data")
    
    def _send_sampling_frequency(self, freq: int) -> None:
        """Send sampling frequency as clockdiv to FPGA."""
        if not self._usb_device:
            return
        # Convert frequency to clockdiv
        clockdiv = (DEFAULT_CLOCK_DIVIDER_REFERENCE // freq) - 1
        buf = create_string_buffer(2)
        buf[0] = MU_CMD_INIT
        buf[1] = clockdiv & 0xFF
        self._usb_device.ctrlWrite(MU_CMD_FPGA_1, buf)
    
    def _send_active_channels(self, mems: list[int], analogs: list[int], counter: bool) -> None:
        """Send active channels configuration."""
        # TODO: Implement channel activation FPGA command
        pass
    
    def _send_datatype(self, datatype: str) -> None:
        """Send datatype configuration to FPGA."""
        if not self._usb_device:
            return
        buf = create_string_buffer(2)
        buf[0] = MU_CMD_DATATYPE
        if datatype == 'int32':
            buf[1] = MU_CODE_DATATYPE_INT32
        else:
            buf[1] = MU_CODE_DATATYPE_FLOAT32
        self._usb_device.ctrlWrite(MU_CMD_FPGA_1, buf)
    
    def _send_sample_count(self, count: int) -> None:
        """Send expected sample count to FPGA."""
        if not self._usb_device:
            return
        buf = create_string_buffer(5)
        buf[0] = MU_CMD_COUNT
        buf[1] = bytes((count & 0x000000FF,))
        buf[2] = bytes(((count & 0x0000FF00) >> 8,))
        buf[3] = bytes(((count & 0x00FF0000) >> 16,))
        buf[4] = bytes(((count & 0xFF000000) >> 24,))
        self._usb_device.ctrlWrite(MU_CMD_FPGA_4, buf)
    
    def _do_wait(self) -> None:
        """Wait for acquisition to complete."""
        if self._usb_device:
            try:
                # Wait for native async bulk transfer to complete
                self._usb_device.asyncBulkTransferWait()
            except Exception as e:
                log.warning(f"Error waiting for USB transfer: {e}")
        
        # Wait for queue consumer thread
        if self._transfer_thread:
            self._transfer_thread.join(timeout=5.0)
    
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
