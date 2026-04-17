# megamicros.sources.usb.py
#
# ® Copyright 2024-2026 Bimea
# Author: bruno.gas@bimea.io
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
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

This data source interfaces with physical Megamicros USB devices (Mu32, Mu64, Mu128, Mu256, Mu1024)
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


# MegaMicro hardware commands
MU_CMD_RESET = b'\x00'
MU_CMD_INIT = b'\x01'
MU_CMD_START = b'\x02'
MU_CMD_STOP = b'\x03'
MU_CMD_COUNT = b'\x04'
MU_CMD_ACTIVE = b'\x05'
MU_CMD_PURGE = b'\x06'
MU_CMD_ABORT = b'\x08'      # Abort acquisition (allow to stop waiting for the trigger start)
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
MU_MEMS_SENSIBILITY = 3.54e-6; # (racine(2)/400 000 = 3,54µPa/digit)
MU_ANALOGS_SENSIBILITY = 0.33                       # Default analogs sensibility in V/digit (0.33 V/digit: 0x00FFFFFF on 24bits <-> 5.65Vcc)
TRANSFER_DATAWORDS_SIZE = 4

# Devices 
VENDOR_ID = 0xFE27

PRODUCT_MAP = {
    0xAC00: "Mu32-usb2 (legacy)",
    0xAC01: "Mu256",
    0xAC02: "Mu1024",
    0xAC03: "Mu32",
    0xAC04: "Mu64 (new)",
    0xAC05: "Mu128 (new)",
    0xAC06: "Mu256 (Haikus, new)",
    0xAC07: "Mu256 (Haikus - 48kHz, new)",
    0xAC08: "Mu512 (new)",
}

PRODUCT_IDS = list(PRODUCT_MAP.keys())

PRODUCT_MEMS = {
    0xAC00: 32,   # Mu32-usb2 (legacy)
    0xAC01: 256,  # Mu256
    0xAC02: 1024, # Mu1024
    0xAC03: 32,   # Mu32
    0xAC04: 64,   # Mu64 (new)
    0xAC05: 128,  # Mu128 (new)
    0xAC06: 256,  # Mu256 (Haikus, new)
    0xAC07: 256,  # Mu256 (Haikus - 48kHz, new)
    0xAC08: 512,  # Mu512 (new)
}

PRODUCT_ANALOGS = {
    0xAC00: 0,   # Mu32-usb2 (legacy)
    0xAC01: 4,   # Mu256
    0xAC02: 16,   # Mu1024
    0xAC03: 2,   # Mu32
    0xAC04: 2,   # Mu64 (new)
    0xAC05: 4,   # Mu128 (new)
    0xAC06: 4,   # Mu256 (Haikus, new)
    0xAC07: 4,   # Mu256 (Haikus - 48kHz, new)
    0xAC08: 8,   # Mu512 (new)
}

DEFAULT_CLOCK_DIVIDER_REFERENCE = 500000  # 500 kHz clock reference
DEFAULT_TRANSFER_TIMEOUT_MS = 1000  # 1 second transfer timeout (could be adjusted based on duration)
DEFAULT_SAMPLING_FREQUENCY_REFERENCE = 500000  # Default max sampling frequency x 10 (could be improved by auto-detecting from device or allowing user to specify)
DEFAULT_SELFTEST_DURATION = 1 # Duration of SELTEST in seconds (used for MEMS and analogs check)
DEFAULT_SELFTEST_SAMPLING_FREQUENCY = 50000 # Sampling frequency for SELFTEST (should be high enough to capture signals but not too high to avoid data loss during test)
DEFAULT_SELFTEST_FRAME_LENGTH = 1024 # Frame length for SELFTEST (should be long enough to analyze signals but not too long to avoid data loss during test)
DEFAULT_USB_QUEUE_TIMEOUT = 0.1 # Timeout for USB queue get operations (in seconds)
DEFAULT_USB_TRIGGER_TIMEOUT = 1 # Timeout for waiting trigger start in seconds

FPGA_TRIG_TIMEOUT = 30.0 # Timeout for waiting the first frame after trigger start in seconds (should be longer than FPGA timeout to allow acquisition to start)
SOURCE_TIMEOUT = 0.1 # Timeout for source frame retrieval (in seconds) - should be shorter than FPGA_TRIG_TIMEOUT to allow checking for halt request and stopping acquisition if needed

class UsbSourceException(MuException):
    """Exception for USB data source."""
    pass


class UsbDataSource(BaseDataSource):
    """
    USB hardware data source.
    
    Interfaces with physical Megamicros devices via USB for real-time acquisition.
    
    Args:
        usb_config: USB device configuration
        available_mems: Number of available MEMS (default: auto-detect) (not connected, nor activated - just available)
    """
    
    @staticmethod
    def detectMegamicrosDevice(vendor_id: int = 0xFE27) -> tuple[bool, int]:
        """Detect which Megamicros device is connected.
        
        Parameters
        ----------
        vendor_id: int
            The vendor ID to search for (default: 0xFE27)
        
        Returns
        -------
        tuple[bool, int]
            (device_found, product_id) where product_id is one of:
            0xAC00 (Mu32-usb2 legacy), 0xAC01 (Mu256), 0xAC02 (Mu1024), 
            0xAC03 (Mu32), 0xAC04 (Mu64)
            If not found, returns (False, 0xAC03) as default
        """
        # Try all known Megamicros product IDs        
        for product_id in PRODUCT_IDS:
            if Usb.checkDeviceByVendorProduct(vendor_id, product_id):
                return (True, product_id)
        
        # Not found - return default (Mu32)
        return (False, 0xAC03)

    def __init__(
        self,
        usb_config: UsbConfig | None = None,
        available_mems: int | None = None,
        available_analogs: int | None = None,
    ):
        super().__init__()
        
        self._usb_config = usb_config or UsbConfig()
        self._usb_device: Usb | None = None
        self._queue: queue.Queue = queue.Queue()  # Created once, reused across runs
        self._queue_size: int = 0  # Track configured size
        self._use_direct_transfer = True  # If False, use usb queue to get frames otherwise use direct transfer mode (faster, but no usb queue management)
        self._transfer_thread: Thread | None = None
        self._timer_thread: Thread | None = None
        self._halt_request = False
        self._frames_received = 0
        self._transfert_lost = 0
        self._waiting_for_trigger = False
        
        # Detect or set available MEMS
        if available_mems is None:
            available_mems = self._detect_device_mems()
        
        # Detect or set available Analogs
        if available_analogs is None:
            available_analogs = self._detect_device_analogs()
        
        # Info on Mems Array acoustics and geometry (positions not available for USB source)
        self._info = MemsArrayInfo(
            available_mems=list(range(available_mems)),
            available_analogs=list(range(available_analogs)),
            max_sampling_frequency=DEFAULT_SAMPLING_FREQUENCY_REFERENCE / 10,
            hardware = PRODUCT_MAP.get(self._usb_config.product_id, "Unknown Device"),
            description=f"USB Device {hex(self._usb_config.vendor_id)}:{hex(self._usb_config.product_id)}"
        )
        
        log.info(f"UsbDataSource initialized: {available_mems} MEMS available")
    
    def _detect_device_mems(self) -> int:
        """Detect number of MEMS from product ID."""
        return PRODUCT_MEMS.get(self._usb_config.product_id, 32)
    
    def _detect_device_analogs(self) -> int:
        """Detect number of Analogs from product ID."""
        return PRODUCT_ANALOGS.get(self._usb_config.product_id, 0)
    
    def _do_selftest(self, duration=DEFAULT_SELFTEST_DURATION) -> dict:
        """Perform a self-test acquisition to check if MEMS and analog channels are working and which of them are connected. 
        This is done by acquiring a short signal and analyzing the data to determine which channels have valid signals."""
    
        # Configure a short acquisition with all channels
        test_config = AcquisitionConfig(
            mems=self._info.available_mems,
            analogs=self._info.available_analogs,
            counter=[0], # Include counter channel to check if acquisition is working
            sampling_frequency=DEFAULT_SELFTEST_SAMPLING_FREQUENCY,  # Higher frequency for test
            frame_length=DEFAULT_SELFTEST_FRAME_LENGTH,  # Longer frames for better analysis
            duration=duration,  # Short duration
        )

        frames = []
        self.configure(test_config)
        self.start()
        
        # Collect frames until acquisition is complete
        for frame in self:
            frames.append(frame)

        # Wait for acquisition to complete
        self.wait()
        self.stop()

        frames_number = len(frames)
        channels_number = test_config.channels_number

        # Concatenate frames to analyze signals (shape: channels x total_samples)
        signal = np.concatenate(frames, axis=1)
        log.info(f"SELFTEST acquired signal shape: {signal.shape}")

        counter = signal[0, :]
        mems_signals = signal[1:1+len(self._info.available_mems), :]
        analog_signals = signal[1+len(self._info.available_mems):, :]
        
        mems_signals = mems_signals.astype(np.float32) * MU_MEMS_SENSIBILITY
        analogs_signals = analog_signals.astype(np.float32) * MU_ANALOGS_SENSIBILITY

        mems_power = np.mean(mems_signals**2, axis=1)
        analogs_power = np.mean(analog_signals**2, axis=1)

        mems_actives = np.where( mems_power > 0, 1, 0 )
        analogs_actives = np.where( analogs_power > 1e-10 , 1, 0 )

        # get indexes of connected mems and analogs
        connected_mems =  np.where( mems_actives > 0 )[0].tolist()
        connected_analogs =  np.where( analogs_actives > 0 )[0].tolist()

        log.info( f"Autotest results:" )
        log.info( f"  ✓ recording time is: {duration} seconds" )
        log.info( f"  ✓ Received {frames_number * channels_number * 4} data bytes: {frames_number} frames on {channels_number } channels")
        log.info( f"  ✓ detected {sum(mems_actives)} active MEMs: {connected_mems}" )
        log.info( f"  ✓ detected {sum(analogs_actives)} active analogs: {connected_analogs}" )
        log.info( f"  ✓ detected counter channel with values from {counter[0]} to {counter[-1]}" )
        log.info( f"  ✓ estimated data lost: {counter[-1] - counter[0] + 1 - frames_number * DEFAULT_SELFTEST_FRAME_LENGTH} samples" )
        log.info( f"Selftest endded successfully" )

        return {
            "connected_mems": connected_mems,
            "connected_analogs": connected_analogs,
            "counters": counter,
            "mems_power": mems_power,
            "analogs_power": analogs_power,
        }
        

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
            except Exception as e:
                raise UsbSourceException(f"Failed to open USB device: {e}")
        
        # Validate channels
        for mems in config.mems:
            if mems not in self._info.available_mems:
                raise ValueError(f"MEMS {mems} not available")
        
        # Configure USB buffers
        n_channels = config.channels_number
        buffer_size = config.frame_length * n_channels * TRANSFER_DATAWORDS_SIZE
        self._usb_device.setBuffersNumber(self._usb_config.buffers_number)
        self._usb_device.setBufferSize(buffer_size)
        self._use_direct_transfer = config.use_direct_transfer
        
        log.info(f"USB configured: {buffer_size} bytes/frame, {n_channels} channels, "
                 f"{self._usb_config.buffers_number} buffers")
        
        # Send FPGA commands
        try:
            log.debug("Sending RESET+PURGE command")
            self._send_reset()
            
            log.debug(f"Sending sampling frequency: {config.sampling_frequency} Hz")
            self._send_sampling_frequency(config.sampling_frequency)
            
            log.debug(f"Sending active channels: {config.mems}")
            self._send_active_channels(config.mems, config.analogs, config.counter, config.status)
            
            log.debug(f"Sending datatype: {config.datatype}")
            self._send_datatype(config.datatype)
            
            # CRITICAL: For asyncBulkTransfer (streaming mode), always send 0
            # The timer controls the duration, not the FPGA sample counter
            log.debug("Sending sample count: 0 (streaming mode)")
            self._send_sample_count(0)

            # Wait for MEMS powering
            time.sleep( config.time_activation/1000 )
                
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
        self._waiting_for_trigger = False

        # NOTE: transfert_lost is NOT reset - cumulative counter
        
        log.debug(f"UsbDataSource configured: {len(config.mems)} MEMS, "
                 f"{config.sampling_frequency}Hz, {config.frame_length} samples/frame")
    
    def _do_start(self) -> None:
        """Start USB acquisition using native async bulk transfer. This is a non-blocking call."""
        if self._config is None or self._usb_device is None:
            raise RuntimeError("Source not configured")
        log.info("Starting USB acquisition...")

        # Send start command to FPGA
        self._send_start(self._config.trigger_start, self._config.trigger_start_mode)
 
        self._usb_device._Usb__transfer_timeout = DEFAULT_TRANSFER_TIMEOUT_MS
        log.debug(f"USB transfer timeout set to {DEFAULT_TRANSFER_TIMEOUT_MS}ms")
        
        # Uses libusb's native async transfers with callbacks
        log.info(f"Starting native USB async bulk transfer (duration={self._config.duration}s, expected frames={self._config.total_frames})")
        try:
            if self._use_direct_transfer:
                self._usb_device.setTransfertCallback(self._consume_usb_transfert)
            self._usb_device.asyncBulkTransfer(self._config.duration)
        except Exception as e:
            raise UsbSourceException(f"Failed to start async bulk transfer: {e}")
        
        # Start thread to consume data from USB queue in usb queue mode (non-direct transfer)
        """
        Note: In asyncBulkTransfer mode and direct transfer mode OFF, data is received in the USB callback and put in the internal USB queue.
            We start a separate thread to consume this queue, convert to frames and put in our own queue.
            This allows us to decouple USB data reception from frame processing, and handle queue timeouts and halting more gracefully.
        """
        if not self._use_direct_transfer:
            self._transfer_thread = Thread(
                target=self._consume_usb_queue,
                name="UsbQueueConsumer",
                daemon=True
            )
            self._transfer_thread.start()

        # Start timer thread if duration is limited and trig mode on soft
        if self._config.trigger_start == "soft":
            if self._config.duration > 0 and self._timer_thread is None:
                self._timer_thread = Thread(
                    target=self._timer_worker,
                    name="RandomTimerThread",
                    daemon=True
                )
            self._timer_thread.start()

        # in triggered mode, the timer thread is started after receiving the first frame to ensure accurate timing based on actual acquisition start after trigger, 
        # so we don't start it here. Instead we set a flag to indicate that we're waiting for the trigger, 
        # and the timer thread will be started in the _consume_usb_transfert callback when we receive the first frame after trigger start
        else:
            self._waiting_for_trigger = True

        
    def _timer_worker(self) -> None:
        """Timer thread to stop generation after specified duration."""
        if self._config is None or self._config.duration <= 0:
            return
        
        time.sleep(self._config.duration)

        log.debug(f"USBDataSource: duration limit reached ({self._config.duration}s)")
        
        # Send FPGA STOP command
        if self._config.trigger_stop == "soft":
            self._send_stop()
            if not self._halt_request:
                log.debug(f"Halt requested")
                self._halt_request = True
        else:
            # In hard trigger stop mode, we rely on the trigger to stop acquisition, 
            # so we don't stop USB transfer here to allow remaining frames to be received until trigger stop is detected in the callback
            # Trigger stop detection is done by checking the queue timeouts in the _consume_usb_transfert callback, 
            # and if we detect a timeout after halt_request is set, we know that the trigger stop has been reached and we can stop the USB transfer and end acquisition
            log.debug("Stopping acquisition from timer thread (hard trigger stop mode, waiting for trigger stop)...")
            self._send_stop(trigger_stop=self._config.trigger_stop, trigger_stop_mode=self._config.trigger_stop_mode)
            return  

        # Stop USB async transfer
        if self._usb_device is None:
            raise RuntimeError("USB device lost during acquisition")

        try:
            log.debug("Stopping USB async transfer from timer thread...")
            self._usb_device.asyncBulkTransferStop()
        except Exception as e:
            log.warning(f"Error stopping USB transfer from timer thread: {e}")
            pass

    def _do_abort(self):
        """Send the ABORT command to FPGA to stop acquisition immediately (without waiting for trigger start if triggered acquisition)."""
        if self._config is None or self._usb_device is None:
            raise RuntimeError("Source not configured")
        log.info("Aborting USB acquisition...")
        
        # send ABORT command to FPGA
        self._send_abort()

        # Stop USB acquisition and release resources
        self._do_stop()

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
        
        # Wait for consumer thread if using USB queue mode (non-direct transfer)
        if not self._use_direct_transfer:
            if self._transfer_thread and self._transfer_thread.is_alive():
                self._transfer_thread.join(timeout=2.0)
        
        # Close USB device
        if self._usb_device:
            try:
                log.info("Stopping USB device and releasing resources...")
                self._usb_device.close()
                self._usb_device = None
            except Exception as e:
                log.warning(f"Error releasing USB device during stop: {e}")
                pass

        log.debug(f"UsbDataSource stopped: {self._frames_received} frames received, "
                 f"{self._transfert_lost} frames lost")
    
    def _consume_usb_transfert(self, data: bytes) -> None:
        """Callback that is called when a new USB transfer is received, converts to frames and insert into our queue."""
        if self._config is None or self._usb_device is None:
            return
        
        frame_length = self._config.frame_length
        n_channels = self._config.channels_number
        transfer_size = frame_length * n_channels * TRANSFER_DATAWORDS_SIZE

        if len(data) != transfer_size:
            log.debug(f"Incorrect frame size: got {len(data)}, expected {transfer_size}. Skipping frame.")
            self._transfert_lost += 1
            return
        
        # Convert to numpy array
        frame = self._bytes_to_frame(data, n_channels, frame_length)

        # Put in the queue (drop oldest if full)
        if self._queue.maxsize > 0 and self._queue.qsize() >= self._queue.maxsize:
            try:
                self._queue.get_nowait()
                self._transfert_lost += 1
            except queue.Empty:
                pass
        
        self._queue.put(frame)

        # Start the timer thread after receiving the first frame to ensure accurate timing based on actual acquisition start
        if self._waiting_for_trigger:
            if self._config.duration > 0 and self._timer_thread is None:
                self._timer_thread = Thread(
                    target=self._timer_worker,
                    name="RandomTimerThread",
                    daemon=True
                )
                self._timer_thread.start()
            self._waiting_for_trigger = False
            log.debug("Timer thread started after receiving first frame (triggered acquisition)")
    
        self._frames_received += 1

    def _consume_usb_queue(self) -> None:
        """Consumer thread that reads from USB internal queue, converts to frames and insert into our queue."""
        if self._config is None or self._usb_device is None:
            return
        
        frame_length = self._config.frame_length
        n_channels = self._config.channels_number
        transfer_size = frame_length * n_channels * TRANSFER_DATAWORDS_SIZE
        
        log.debug(f"Queue consumer started: expecting {transfer_size} bytes per frame")
        
        # Access USB internal queue and transfer flag
        usb_queue = self._usb_device._Usb__queue
        
        try:
            # Loop while USB transfer is active OR queue has data
            while not self._halt_request:
                # Check if USB transfer is still running
                usb_active = self._usb_device._Usb__bulk_transfer_on
                
                try:
                    # Get raw bytes from USB queue
                    if self._waiting_for_trigger:
                        # Longer timeout for first frame to allow acquisition to start
                        # This timeout value is set to 1s to allow checking USB active flag and halting if needed
                        log.debug(f"Waiting for first frame from USB queue after trigger start with timeout {DEFAULT_USB_TRIGGER_TIMEOUT}s...")
                        data = usb_queue.get(timeout=DEFAULT_USB_TRIGGER_TIMEOUT)

                        # Start the timer thread after receiving the first frame to ensure accurate timing based on actual acquisition start
                        if self._config.duration > 0 and self._timer_thread is None:
                            self._timer_thread = Thread(
                                target=self._timer_worker,
                                name="RandomTimerThread",
                                daemon=True
                            )
                            self._timer_thread.start()
                        self._waiting_for_trigger = False
                        log.debug("Timer thread started after receiving first frame (triggered acquisition)")
                    else:
                        # Short timeout for subsequent frames to allow checking USB active flag and halting if needed
                        data = usb_queue.get(timeout=DEFAULT_USB_QUEUE_TIMEOUT)

                    if data is None or len(data) == 0:
                        continue
                    
                    # Verify size
                    if len(data) != transfer_size:
                        log.debug(f"Incorrect frame size: got {len(data)}, expected {transfer_size}. Skipping frame.")
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
        
        log.debug(f"Queue consumer stopped: {self._frames_received} frames received. _halt_request={self._halt_request}, _transfer_on={self._usb_device._Usb__bulk_transfer_on if self._usb_device else 'N/A'}    ")
    
    
    def _bytes_to_frame(self, data: bytes, n_channels: int, frame_length: int) -> np.ndarray:
        """Convert raw bytes to numpy frame."""
        if self._config is None:
            raise RuntimeError("Source not configured")
        
        # Convert bytes to int32/float32 array according the configured datatype
        if self._config.datatype == 'int32':
            arr = np.frombuffer(data, dtype=np.int32)
        elif self._config.datatype == 'float32':
            arr = np.frombuffer(data, dtype=np.float32)
        else:
            raise ValueError(f"Unsupported datatype: {self._config.datatype}")

        # arr = np.frombuffer(data, dtype=dtype, count=n_channels * frame_length)

        # Reshape to (channels, samples)
        frame = arr.reshape((n_channels, frame_length), order='F')
        
        # Convert to float if needed
        '''
        if self._config.datatype == 'float32':
            frame = frame.astype(np.float32)
            # Apply sensibility to MEMS channels
            mems_offset = 1 if self._config.counter else 0
            n_mems = len(self._config.mems)
            if n_mems > 0:
                frame[mems_offset:mems_offset+n_mems, :] *= self._config.sensibility
        '''
        
        return frame
    
    def _generate_frames(self) -> Iterator[np.ndarray]:
        """Yield frames from queue."""
        if self._config is None:
            raise RuntimeError("Source not configured")

        if self._queue.qsize() == 0 and self._state != SourceState.RUNNING:
            log.warning("Iteration called but source not running and queue is empty.")
            return

        # Continue yielding frames until queue is empty or timeout
        while True:
            try:
                # frame = self._queue.get(timeout=timeout_sec)
                if self._waiting_for_trigger:
                    # For triggered acquisitions, wait longer for the first frame to allow acquisition to start after trigger
                    log.debug(f"(USB Source) Waiting for trigger start with timeout {self._config.timeout}s...")
                    if self._config.timeout > 0:
                        # Longer timeout for first frame defined by config
                        frame = self._queue.get(timeout=self._config.timeout)
                    else:
                        # No limit timeout for first frame if config timeout is 0 or negative
                        frame = self._queue.get()
                else:
                    # Shorter timeout for subsequent frames to allow checking for halt request and stopping acquisition if needed
                    frame = self._queue.get(timeout=SOURCE_TIMEOUT)

                '''
                # Already done weather by...
                if self._waiting_for_trigger:
                    log.debug("First frame received after trigger start, acquisition started")
                    self._waiting_for_trigger = False
                '''
                yield frame

            except queue.Empty:
                # No more frames available within timeout
                if self._waiting_for_trigger:
                    log.debug("User timeout for trigger waiting reached")
                    # In triggered mode, if we reach the timeout while waiting for the first frame, 
                    # it means that the trigger was not received or acquisition did not start properly, so we stop the acquisition to avoid hanging indefinitely
                    # send ABORT command to FPGA
                    if not self._halt_request:
                        self._halt_request = True

                    # Send FPGA ABORT command
                    self._send_abort()
                    self._send_stop()

                    # Stop USB async transfer
                    if self._usb_device is None:
                        raise RuntimeError("USB device lost during acquisition")

                    try:
                        log.debug("Stopping USB async transfer from source thread...")
                        self._usb_device.asyncBulkTransferStop()
                    except Exception as e:
                        log.debug(f"Error stopping USB transfer from source thread: {e}")
                        pass

                elif self._config.trigger_stop != "soft":
                    log.debug("User timeout for hard trigger stop reached - assuming trigger stop reached and stopping acquisition")
                    # In hard trigger stop mode, if we reach the timeout while waiting for frames after trigger, 
                    # it means that the trigger stop may have been received so that acquisition has likely stopped (no more frames), 
                    # so we stop the acquisition
                    self._send_abort()
                    self._send_stop()

                    # Stop USB async transfer
                    if self._usb_device is None:
                        raise RuntimeError("USB device lost during acquisition")

                    try:
                        log.debug("Stopping USB async transfer from source thread...")
                        self._usb_device.asyncBulkTransferStop()
                    except Exception as e:
                        log.debug(f"Error stopping USB transfer from source thread: {e}")
                        pass 

                else:
                    log.debug("No more frames available in queue (source stopped or timeout reached)")
                break


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
        log.info("RESET and PURGE commands sent to FPGA")

    def _send_start(self, trigger_start: str = "soft", trigger_mode: str = "rising") -> None:
        """Send START command to FPGA."""
        if not self._usb_device:
            return
        switcher_trigger_start = {
            "soft": 0x00,
            "trig1": 0x01,
            "trig2": 0x02
        }
        switcher_trigger_mode = {
            "rising": 0x00,
            "falling": 0x40,
            "high": 0x80,
            "low": 0xC0
        }
        trig_opt = switcher_trigger_start.get(trigger_start, 0x00)        
        trig_mode_opt = switcher_trigger_mode.get(trigger_mode, 0x00)

        if trigger_start not in switcher_trigger_start:
            log.warning(f"Invalid trigger start option: {trigger_start}. Defaulting to 'soft'.")
        if trigger_mode not in switcher_trigger_mode:
            log.warning(f"Invalid trigger mode option: {trigger_mode}. Defaulting to 'rising'.")

        buf = create_string_buffer(2)
        buf[0] = MU_CMD_START
        buf[1] = 0x00 + trig_opt + trig_mode_opt
        self._usb_device.ctrlWrite(MU_CMD_FPGA_1, buf)
        
        log.info(f"START command sent to FPGA (trigger: {trigger_start}, mode: {trigger_mode if trigger_start != 'soft' else 'N/A'})")
    
    def _send_stop(self, trigger_stop: str = "soft", trigger_stop_mode: str = "rising") -> None:
        """Send STOP command to FPGA and wait for remaining data."""
        if not self._usb_device:
            return
        
        switcher_trigger_stop = {
            "soft": 0x00,
            "trig1": 0x01,
            "trig2": 0x02
        }
        switcher_trigger_stop_mode = {
            "rising": 0x00,
            "falling": 0x40,
            "high": 0x80,
            "low": 0xC0
        }
        if trigger_stop not in switcher_trigger_stop:
            log.warning(f"Invalid trigger stop option: {trigger_stop}. Defaulting to 'soft'.")
        if trigger_stop_mode not in switcher_trigger_stop_mode:
            log.warning(f"Invalid trigger stop mode option: {trigger_stop_mode}. Defaulting to 'rising'.")

        trig_opt = switcher_trigger_stop.get(trigger_stop, 0x00)        
        trig_mode_opt = switcher_trigger_stop_mode.get(trigger_stop_mode, 0x00)

        buf = create_string_buffer(2)
        buf[0] = MU_CMD_STOP
        buf[1] = 0x00 + trig_opt + trig_mode_opt
        self._usb_device.ctrlWrite(MU_CMD_FPGA_1, buf)
        log.info(f"STOP command sent to FPGA (trigger: {trigger_stop}, mode: {trigger_stop_mode if trigger_stop != 'soft' else 'N/A'})")
    
    def _send_abort(self) -> None:
        """Send ABORT command to FPGA to stop waiting for the trigger start."""
        if not self._usb_device:
            return
        buf = create_string_buffer(1)
        buf[0] = MU_CMD_ABORT
        self._usb_device.ctrlWrite(MU_CMD_FPGA_1, buf)
        log.info("ABORT command sent to FPGA")

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
        log.info(f"Sampling frequency {freq}Hz sent as clockdiv {clockdiv} (nearest activated frequency is {DEFAULT_CLOCK_DIVIDER_REFERENCE // (clockdiv + 1)}Hz)")
    
    def _send_active_channels(self, mems: list[int], analogs: list[int], counter: list[int], status: bool) -> None:
        """Send active channels configuration."""
        buf = create_string_buffer(4)
        buf[0] = MU_CMD_ACTIVE		
        buf[1] = 0x00

        # Activate MEMS channels
        available_mems_number = len(self._info.available_mems)
        pluggable_mems_beams = available_mems_number // MU_BEAM_MEMS_NUMBER
        map_mems = [0 for _ in range( pluggable_mems_beams )]
        for mic in mems:
            mic_index = mic % MU_BEAM_MEMS_NUMBER
            beam_index = int(mic / MU_BEAM_MEMS_NUMBER)
            if beam_index >= pluggable_mems_beams:
                raise UsbSourceException( 'microphone index [%d] is out of range (should be less than %d)' % ( mic,  pluggable_mems_beams * MU_BEAM_MEMS_NUMBER ) )
            map_mems[beam_index] += ( 0x01 << mic_index )
    
        for beam in range( pluggable_mems_beams ):
            if map_mems[beam] != 0:
                buf[2] = beam
                buf[3] = map_mems[beam]				
                self._usb_device.ctrlWrite(MU_CMD_FPGA_3, buf)

        # Activate analogs channels, status and counter in a single command (bitmask)
        buf[0] = MU_CMD_ACTIVE		# command
        buf[1] = 0x00				# module
        buf[2] = 0xFF				# counter, status and analogic channels

        map_csa = 0x00
        if len( analogs ) > 0:
            for anl_index in analogs:
                map_csa += ( 0x01 << anl_index ) 

        if status:
            map_csa += ( 0x01 << 6 )

        if len(counter) > 0:
            if available_mems_number <= 256:
                # There is only one counter channel on 32 to 256 devices, so we can use bit 7 of the same byte
                map_csa += ( 0x01 << 7 )
            else:
                raise UsbSourceException("Counter channel not yet supported on USB devices over 256 MEMS (contact support if you need this feature)")
            
        buf[3] = map_csa
        self._usb_device.ctrlWrite( MU_CMD_FPGA_3, buf )
        log.info(f"Active channels sent to FPGA: MEMS={len(mems)}, Analogs={len(analogs)}, Counter={len(counter)}, Status={status}")

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
        log.info( f"Datatype sent to FPGA: {datatype}")
    
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
        log.info(f"Sample count sent to FPGA: {count} (streaming mode if 0)")
    
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

        # Timer thread is daemon, it will exit on its own if still running
        self._timer_thread = None  
    
    @property
    def queue_content(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    @property
    def transfert_lost(self) -> int:
        """Get number of lost frames."""
        return self._transfert_lost
    
    @property 
    def mems_sensibility(self) -> float:
        """Get MEMS sensibility in Pa/digit."""
        return MU_MEMS_SENSIBILITY

    def __del__(self):
        """Cleanup USB resources."""
        self.cleanup()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup even on exceptions."""
        self.cleanup()
        return False  # Don't suppress exceptions

    def cleanup(self):
        """
        Explicit cleanup method.
        
        Stops acquisition, releases USB device, and closes connection.
        Safe to call multiple times.
        """
        # Stop acquisition if running (it will also release USB device)
        if self._state == SourceState.RUNNING:
            try:
                self.stop()
            except:
                pass
        
            return
        
        # Else release USB device
        if self._usb_device:
            try:
                self._usb_device.close()
                log.info("USB device released and closed")
            except Exception as e:
                log.warning(f"Error during cleanup: {e}")


    def __iter__(self) -> Iterator[np.ndarray]:
        """
        Iterate over frames.
        
        Can be called on RUNNING sources (data still being generated)
        or STOPPED sources (reading remaining frames from queue).
        """
        if self._state not in (SourceState.RUNNING, SourceState.STOPPED):
            raise RuntimeError(f"Cannot iterate in state {self._state}. Call run() first.")
        
        yield from self._generate_frames()
