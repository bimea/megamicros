# megamicros.core.megamicros.py
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
Megamicros main class - v4.0.0 refactored architecture.

This module provides the main Megamicros class, which is a facade over
different data sources (USB, H5, WebSocket, Random).

Features:
    - Automatic source detection based on parameters
    - Unified interface for all data sources
    - Backward compatible with v3.x API
    - Modern Python patterns (dataclasses, protocols, type hints)
    
Examples:
    USB hardware::

        from megamicros import Megamicros
        
        antenna = Megamicros()  # Auto-detects USB
        antenna.run(
            mems=[0, 1, 2, 3],
            sampling_frequency=50000,
            duration=10,
            frame_length=1024
        )
        
        for frame in antenna:
            process(frame)
        
        antenna.wait()
    
    H5 file playback::

        antenna = Megamicros(filepath='recording.h5')
        antenna.run(mems=[0, 1, 2, 3], frame_length=1024)
        
        for frame in antenna:
            process(frame)
    
    Random generator (testing)::

        antenna = Megamicros()  # Falls back to random if no USB
        antenna.run(mems=[0, 1, 2, 3], duration=5)
        
        for frame in antenna:
            assert frame.shape == (4, 1024)
    
Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""

from typing import Optional, Iterator
from pathlib import Path
import numpy as np

from .base import MemsArray
from .config import AcquisitionConfig, UsbConfig, MemsArrayInfo
from ..sources import DataSource, UsbDataSource, H5DataSource, RandomDataSource
from ..sources.websocket import WebSocketDataSource
from ..usb import Usb
from ..log import log
from ..exception import MuException


class MegamicrosException(MuException):
    """Exception for Megamicros class."""
    pass


class Megamicros(MemsArray):
    """
    Main Megamicros MEMS array class.
    
    This class provides a unified interface for MEMS microphone arrays,
    automatically selecting the appropriate data source based on initialization
    parameters.
    
    Source Selection Logic:
        1. If filepath provided → H5DataSource
        2. If url provided started with ws:// or wss:// → WebSocketDataSource
        3. If usb=True or USB device detected → UsbDataSource
        4. Otherwise → RandomDataSource (fallback for testing)
    
    Args:
        usb: Force USB source (default: None = auto-detect)
        filepath: Path to H5 file for playback
        url: WebSocket URL for remote device
        source: Explicit DataSource instance (advanced usage)
        vendor_id: USB vendor ID
        product_id: USB product ID
        **kwargs: Additional configuration options
    """
    
    def __init__(
        self,
        usb: Optional[bool] = None,
        filepath: Optional[str | Path] = None,
        url: Optional[str] = None,
        source: Optional[DataSource] = None,
        vendor_id: int = 0xFE27,
        product_id: int = 0xAC03,
        **kwargs
    ):
        # Don't call super().__init__() - we're replacing the base class pattern
        
        # Source selection
        if source is not None:
            # Explicit source injection (for testing/advanced usage)
            self._source = source
            log.info(f"Megamicros initialized with explicit source: {type(source).__name__}")
        else:
            self._source = self._create_source(
                usb, filepath, url, vendor_id, product_id, **kwargs
            )
        
        # Current configuration
        self._config: Optional[AcquisitionConfig] = None
        
        # Legacy compatibility properties
        self._running = False
        
        log.debug(f"Megamicros instance created with {type(self._source).__name__}")
    
    def _create_source(
        self,
        usb: Optional[bool],
        filepath: Optional[str | Path],
        url: Optional[str],
        vendor_id: int,
        product_id: int,
        **kwargs
    ) -> DataSource:
        """
        Factory method to create appropriate data source.
        
        Priority order:
        1. H5 file (if filepath provided)
        2. WebSocket (if url provided)
        3. USB (if usb=True or device detected)
        4. Random (fallback)
        """
        
        # 1. H5 file source
        if filepath is not None:
            log.info(f"Creating H5DataSource from {filepath}")
            return H5DataSource(filepath)
        
        # 2. WebSocket source
        if url is not None:
            log.info(f"Creating WebSocketDataSource for {url}")
            return WebSocketDataSource(url)
        
        # 3. USB source
        if usb is True or (usb is None and self._usb_device_detected(vendor_id, product_id)):
            log.info(f"Creating UsbDataSource ({hex(vendor_id)}:{hex(product_id)})")
            usb_config = UsbConfig(vendor_id=vendor_id, product_id=product_id)
            return UsbDataSource(usb_config)
        
        # 4. Random fallback
        log.warning("No hardware or file specified - using RandomDataSource for testing")
        return RandomDataSource(seed=kwargs.get('seed'))
    
    @staticmethod
    def _usb_device_detected(vendor_id: int, product_id: int) -> bool:
        """Check if USB device is available."""
        try:
            return Usb.checkDeviceByVendorProduct(vendor_id, product_id)
        except:
            return False
    
    # Public API - Backward compatible with v3.x
    
    def run(
        self,
        mems: Optional[list[int]] = None,
        analogs: Optional[list[int]] = None,
        sampling_frequency: int = 44100,
        frame_length: int = 1024,
        duration: float = 0,
        datatype: str = 'int32',
        counter: bool = False,
        skip_counter: bool = False,
        queue_size: int = 0,
        queue_timeout: int = 1000,
        sensibility: float = 3.54e-6,
        **kwargs
    ) -> 'Megamicros':
        """
        Start data acquisition.
        
        Non-blocking method that starts asynchronous data collection.
        Use iteration to retrieve frames and wait() to ensure completion.
        
        Args:
            mems: List of active MEMS channels (default: all available)
            analogs: List of active analog channels (default: none)
            sampling_frequency: Sampling rate in Hz
            frame_length: Samples per frame
            duration: Acquisition duration in seconds (0 = infinite)
            datatype: 'int32' or 'float32'
            counter: Include counter channel
            skip_counter: Skip counter in output
            queue_size: Max queue size (0 = unlimited)
            queue_timeout: Queue timeout in ms
            sensibility: MEMS sensitivity (Pa/digit)
            
        Returns:
            self (for method chaining)
        """
        
        # Auto-cleanup if already running (better UX)
        if self._running:
            log.debug("Previous acquisition still running - stopping automatically")
            self.wait()
        
        # Use available MEMS if not specified
        if mems is None:
            mems = self.available_mems
        
        # Create configuration
        self._config = AcquisitionConfig(
            mems=mems,
            analogs=analogs or [],
            sampling_frequency=sampling_frequency,
            frame_length=frame_length,
            duration=duration,
            datatype=datatype,
            counter=counter,
            skip_counter=skip_counter,
            queue_size=queue_size,
            queue_timeout=queue_timeout,
            sensibility=sensibility,
        )
        
        # Configure and start source
        self._source.configure(self._config)
        self._source.start()
        self._running = True
        
        log.info(f"Acquisition started: {len(mems)} MEMS, {sampling_frequency}Hz, "
                f"{duration}s duration, {frame_length} samples/frame")
        
        return self
    
    def wait(self) -> None:
        """
        Block until acquisition is complete.
        
        Must be called after run() to ensure proper cleanup,
        especially when not iterating over all frames.
        """
        self._source.wait()
        self._running = False
        log.debug("Acquisition complete")
    
    def clear_queue(self) -> int:
        """
        Clear all frames from the queue without processing them.
        
        Returns:
            Number of frames that were discarded
        """
        count = 0
        for _ in self:
            count += 1
        log.debug(f"Cleared {count} frames from queue")
        return count
    
    def stop(self) -> None:
        """
        Stop acquisition prematurely.
        
        Can be called during iteration to terminate early.
        """
        self._source.stop()
        self._running = False
        log.debug("Acquisition stopped by user")
    
    def __iter__(self) -> Iterator[np.ndarray]:
        """
        Iterate over data frames.
        
        Can be called:
        - During acquisition (while running) for real-time processing
        - After wait() to retrieve buffered frames from queue
        
        Yields:
            np.ndarray: Frame data with shape (channels, samples)
            
        Note:
            Each frame is yielded once. Iteration empties the queue.
        """
        # Allow iteration on stopped source if queue has content
        if not self._running and self.queue_content == 0:
            log.warning("Iteration called but source not running and queue is empty. Call run() first.")
            return
        
        yield from self._source
    
    # Properties - Backward compatible
    
    @property
    def available_mems(self) -> list[int]:
        """Get list of available MEMS channels."""
        return self._source.info.available_mems
    
    @property
    def available_analogs(self) -> list[int]:
        """Get list of available analog channels."""
        return self._source.info.available_analogs
    
    @property
    def mems(self) -> list[int]:
        """Get active MEMS channels."""
        return self._config.mems if self._config else []
    
    @property
    def analogs(self) -> list[int]:
        """Get active analog channels."""
        return self._config.analogs if self._config else []
    
    @property
    def sampling_frequency(self) -> int:
        """Get sampling frequency."""
        return self._config.sampling_frequency if self._config else 44100
    
    @property
    def frame_length(self) -> int:
        """Get frame length."""
        return self._config.frame_length if self._config else 1024
    
    @property
    def duration(self) -> float:
        """Get acquisition duration."""
        return self._config.duration if self._config else 0
    
    @property
    def datatype(self) -> str:
        """Get datatype."""
        return self._config.datatype if self._config else 'int32'
    
    @property
    def counter(self) -> bool:
        """Get counter flag."""
        return self._config.counter if self._config else False
    
    @property
    def running(self) -> bool:
        """Check if acquisition is running."""
        return self._running
    
    @property
    def queue_content(self) -> int:
        """Get current queue size."""
        return self._source.queue_content
    
    @property
    def transfert_lost(self) -> int:
        """Get number of lost frames."""
        return self._source.transfert_lost
    
    @property
    def infos(self) -> dict:
        """Get antenna information as dictionary (legacy v3.x API)."""
        return {
            'available_mems': self.available_mems,
            'available_analogs': self.available_analogs,
            'mems': self.mems,
            'sampling_frequency': self.sampling_frequency,
            'frame_length': self.frame_length,
            'duration': self.duration,
            'datatype': self.datatype,
            'source_type': type(self._source).__name__,
            'running': self.running,
        }
    
    # Legacy compatibility methods
    
    def setActiveMems(self, mems: list[int]) -> None:
        """Set active MEMS (legacy v3.x API) - prefer using run(mems=...)."""
        log.warning("setActiveMems() is deprecated. Use run(mems=[...]) instead.")
        if self._config:
            self._config.mems = mems
    
    def setDuration(self, duration: float) -> None:
        """Set duration (legacy v3.x API) - prefer using run(duration=...)."""
        log.warning("setDuration() is deprecated. Use run(duration=...) instead.")
        if self._config:
            self._config.duration = duration
