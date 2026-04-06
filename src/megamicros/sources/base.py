# megamicros.sources.base.py
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
Base data source protocol and utilities.

This module defines the DataSource protocol that all data sources must implement
to be compatible with the Megamicros architecture.

Features:
    - DataSource protocol defining the interface
    - SourceState enum for lifecycle management  
    - Base utilities for all data sources
    
Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Iterator, Protocol, runtime_checkable
import numpy as np

from ..core.config import AcquisitionConfig, MemsArrayInfo


class SourceState(Enum):
    """Data source lifecycle states."""
    IDLE = auto()
    CONFIGURED = auto()
    RUNNING = auto()
    STOPPED = auto()
    ERROR = auto()


@runtime_checkable
class DataSource(Protocol):
    """
    Protocol defining the interface for data sources.
    
    All data sources (USB, H5, WebSocket, Random, etc.) must implement
    this interface to be compatible with the Megamicros architecture.
    
    The data source follows this lifecycle:
        IDLE → configure() → CONFIGURED → start() → RUNNING → stop() → STOPPED
        
    Usage pattern:
        source = SomeDataSource()
        source.configure(config)
        source.start()
        for frame in source:
            process(frame)
        source.wait()  # blocks until complete
        source.stop()
    """
    
    @property
    def state(self) -> SourceState:
        """Get current source state."""
        ...
    
    @property
    def info(self) -> MemsArrayInfo:
        """Get array information (positions, available channels, etc.)."""
        ...
    
    def configure(self, config: AcquisitionConfig) -> None:
        """
        Configure the data source.
        
        Args:
            config: Acquisition configuration
            
        Raises:
            ValueError: If configuration is invalid
        """
        ...
    
    def start(self) -> None:
        """
        Start data acquisition.
        
        Must be called after configure() and before iteration.
        Non-blocking - data flows asynchronously into queue.
        
        Raises:
            RuntimeError: If not configured or already running
        """
        ...
    
    def stop(self) -> None:
        """
        Stop data acquisition.
        
        Can be called during iteration to terminate early.
        """
        ...
    
    def wait(self) -> None:
        """
        Block until acquisition is complete.
        
        Should be called after iteration to ensure clean shutdown.
        """
        ...
    
    def __iter__(self) -> Iterator[np.ndarray]:
        """
        Iterate over data frames.
        
        Yields:
            np.ndarray: Frame data with shape (channels, samples)
            
        Note:
            Iteration empties the internal queue. Each frame is yielded once.
        """
        ...
    
    @property
    def queue_content(self) -> int:
        """Get current number of frames in the queue."""
        ...
    
    @property
    def transfert_lost(self) -> int:
        """Get number of frames lost due to queue overflow."""
        ...


class BaseDataSource(ABC):
    """
    Abstract base class providing common functionality for data sources.
    
    Subclasses must implement:
        - _do_configure()
        - _do_start()
        - _do_stop()
        - _generate_frames()
    """
    
    def __init__(self):
        self._state = SourceState.IDLE
        self._config: AcquisitionConfig | None = None
        self._info: MemsArrayInfo = MemsArrayInfo()
    
    @property
    def state(self) -> SourceState:
        return self._state
    
    @property
    def info(self) -> MemsArrayInfo:
        return self._info
    
    def configure(self, config: AcquisitionConfig) -> None:
        """Configure the source."""
        if self._state not in (SourceState.IDLE, SourceState.STOPPED):
            raise RuntimeError(f"Cannot configure in state {self._state}")
        
        self._config = config
        self._do_configure(config)
        self._state = SourceState.CONFIGURED
    
    def start(self) -> None:
        """Start acquisition."""
        if self._state != SourceState.CONFIGURED:
            raise RuntimeError(f"Cannot start in state {self._state}. Call configure() first.")
        
        self._do_start()
        self._state = SourceState.RUNNING
    
    def stop(self) -> None:
        """Stop acquisition."""
        if self._state == SourceState.RUNNING:
            self._do_stop()
            self._state = SourceState.STOPPED

    def selftest(self, duration=5) -> dict:
        """
        Perform a self-test acquisition to check if MEMS and analog channels are working and which of them are connected. 
        This is done by acquiring a short signal and analyzing the data to determine which channels have valid signals.
        
        Args:
            duration: Duration of the self-test acquisition in seconds (default: 5)
        
        Returns:
            dict: Self-test results containing information about active MEMS and analog channels.
        """
        if self._state != SourceState.IDLE:
            raise RuntimeError(f"Cannot perform self-test in state {self._state}. Must be in IDLE state.")
        
        return self._do_selftest(duration)
    
    @abstractmethod
    def _do_selftest(self, duration: int) -> dict:
        """Subclass-specific self-test logic."""
        pass

    @abstractmethod
    def _do_configure(self, config: AcquisitionConfig) -> None:
        """Subclass-specific configuration."""
        pass
    
    @abstractmethod
    def _do_start(self) -> None:
        """Subclass-specific start logic."""
        pass
    
    @abstractmethod
    def _do_stop(self) -> None:
        """Subclass-specific stop logic."""
        pass
    
    @abstractmethod
    def _generate_frames(self) -> Iterator[np.ndarray]:
        """Subclass-specific frame generation."""
        pass
    
    def wait(self) -> None:
        """
        Wait for acquisition to complete naturally.
        
        Automatically transitions from RUNNING to STOPPED state.
        Subclasses should override this to join threads etc.
        """
        self._do_wait()
        if self._state == SourceState.RUNNING:
            self._state = SourceState.STOPPED
    
    def _do_wait(self) -> None:
        """Subclass-specific wait logic (join threads, etc)."""
        pass
    
    def __iter__(self) -> Iterator[np.ndarray]:
        """
        Iterate over frames.
        
        Can be called on RUNNING sources (data still being generated)
        or STOPPED sources (reading remaining frames from queue).
        """
        if self._state not in (SourceState.RUNNING, SourceState.STOPPED):
            raise RuntimeError(f"Cannot iterate in state {self._state}. Call run() first.")
        
        yield from self._generate_frames()
    
    @property
    def queue_content(self) -> int:
        """Default: 0 (override in subclasses with queues)."""
        return 0
    
    @property
    def transfert_lost(self) -> int:
        """Default: 0 (override in subclasses with queues)."""
        return 0
