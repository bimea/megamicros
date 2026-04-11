# megamicros.core.config.py
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
Configuration dataclasses for Megamicros library.

This module provides typed configuration objects used throughout the library
to ensure type safety and clear interfaces.

Features:
    - AcquisitionConfig: Configuration for data acquisition
    - UsbConfig: USB device configuration
    - BeamformerConfig: Beamforming parameters
    
Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
import numpy as np

# Type aliases
DataType = Literal['int32', 'float32']


@dataclass
class AcquisitionConfig:
    """
    Configuration for data acquisition.
    
    Attributes:
        mems: List of active MEMS channels (default: empty)
        analogs: List of active analog channels (default: empty)
        sampling_frequency: Sampling rate in Hz
        frame_length: Number of samples per frame
        duration: Acquisition duration in seconds (0 = infinite)
        datatype: Data type for samples ('int32' or 'float32')
        counter: List of active counters (default [0] for single counter)
        use_direct_transfer: Whether to use direct USB transfer mode (bypassing USB queue)
        skip_counter: Skip counter in iteration output
        queue_size: Maximum queue size (0 = unlimited)
        timeout: Timeout in seconds before stopping acquisition if no data is received
        sensibility: MEMS sensitivity factor (Pa/digit)
        time_activation: Delay before starting acquisition in ms (200ms: skip the transiant state)
        trigger_start: Trigger start mode ('soft', 'trig1', 'trig2')
        trigger_start_mode: Trigger mode for external/USB trigger ('rising', 'falling', 'high', 'low')
        trigger_stop: Trigger stop mode ('soft', 'trig1', 'trig2')
        trigger_stop_mode: Trigger mode for external/USB stop trigger ('rising', 'falling', 'high', 'low')
    """
    
    mems: Optional[list[int]] = None
    analogs: Optional[list[int]] = None
    sampling_frequency: int = 44100
    frame_length: int = 1024
    duration: float = 0
    datatype: DataType = 'int32'
    counter: Optional[list[int]] = field(default_factory=lambda: [0])
    use_direct_transfer: bool = False
    status: bool = False
    skip_counter: bool = False
    queue_size: int = 0
    timeout: float = 1.0
    sensibility: float = 3.54e-6
    time_activation: int = 0
    trigger_start: Literal['soft', 'trig1', 'trig2'] = 'soft'
    trigger_start_mode: Literal['rising', 'falling', 'high', 'low'] = 'rising'
    trigger_stop: Literal['soft', 'trig1', 'trig2'] = 'soft'
    trigger_stop_mode: Literal['rising', 'falling', 'high', 'low'] = 'rising'
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.mems is None:
            self.mems = []
        if self.analogs is None:
            self.analogs = []
        
        if self.sampling_frequency <= 0:
            raise ValueError("sampling_frequency must be positive")
        if self.frame_length <= 0:
            raise ValueError("frame_length must be positive")
        if self.duration < 0:
            raise ValueError("duration must be non-negative")
        
        # Validate counter for compability with legacy API (bool)
        if isinstance(self.counter, bool):
            self.counter = [0] if self.counter else []
        elif self.counter is None:
            self.counter = []
        elif isinstance(self.counter, list):
            if not all(isinstance(c, int) for c in self.counter):
                raise ValueError("counter list must contain integers")
        else:
            raise ValueError("counter must be a list of integers, a boolean, or None")
        
        # Validate trigger options
        valid_trigger_starts = {'soft', 'trig1', 'trig2'}
        valid_trigger_start_modes = {'rising', 'falling', 'high', 'low'}
        if self.trigger_start not in valid_trigger_starts:
            raise ValueError(f"trigger_start must be one of {valid_trigger_starts}")
        if self.trigger_start_mode not in valid_trigger_start_modes:
            raise ValueError(f"trigger_start_mode must be one of {valid_trigger_start_modes}")

        valid_trigger_stops = {'soft', 'trig1', 'trig2'}
        valid_trigger_stop_modes = {'rising', 'falling', 'high', 'low'}
        if self.trigger_stop not in valid_trigger_stops:
            raise ValueError(f"trigger_stop must be one of {valid_trigger_stops}")
        if self.trigger_stop_mode not in valid_trigger_stop_modes:
            raise ValueError(f"trigger_stop_mode must be one of {valid_trigger_stop_modes}")
        
    @property
    def active_mems(self) -> list[int]:
        """Get a copy of active MEMS channels."""
        return list(self.mems)
    
    @property
    def active_analogs(self) -> list[int]:
        """Get a copy of active analog channels."""
        return list(self.analogs)
    
    @property
    def active_counters(self) -> list[int]:
        """Get a copy of active counters."""
        return list(self.counter)

    @property
    def mems_number(self) -> int:
        """Get the number of active MEMS channels."""
        return len(self.mems)

    @property
    def analogs_number(self) -> int:
        """Get the number of active analog channels."""
        return len(self.analogs)

    @property
    def counters_number(self) -> int:
        """Get the number of active counters."""
        return len(self.counter)

    @property
    def channels_number(self) -> int:
        """Get the total number of active channels."""
        status_channels = 1 if self.status else 0
        return self.mems_number + self.analogs_number + self.counters_number + status_channels

    @property
    def total_samples(self) -> int:
        """Calculate total number of samples for acquisition."""
        if self.duration == 0:
            return 0  # Infinite
        return int(self.sampling_frequency * self.duration)
    
    @property
    def total_frames(self) -> int:
        """Calculate total number of frames for acquisition."""
        if self.duration == 0:
            return 0  # Infinite
        total = self.total_samples
        return (total + self.frame_length - 1) // self.frame_length


@dataclass
class UsbConfig:
    """
    USB device configuration.
    
    Attributes:
        vendor_id: USB vendor ID
        product_id: USB product ID
        bus_address: USB bus address (interface number)
        interface: USB interface number
        endpoint_in: USB input endpoint
        buffers_number: Number of USB transfer buffers
        transfer_timeout: USB transfer timeout in ms
        write_timeout: USB write timeout in ms
    """
    
    vendor_id: int = 0xFE27
    product_id: int = 0xAC03
    bus_address: int = 0x00
    interface: int = 0x00
    endpoint_in: int = 0x81
    buffers_number: int = 8
    transfer_timeout: int = 1000
    write_timeout: int = 1000


@dataclass
class MemsArrayInfo:
    """
    Information about a MEMS array geometry.
    
    Attributes:
        positions: 3D positions of MEMS in meters, shape (N, 3)
        available_mems: List of available MEMS indices
        available_analogs: List of available analog indices
        max_sampling_frequency: Maximum supported sampling frequency in Hz (if known)
        hardware: Optional hardware identifier or description
        description: Optional description of the array
    """
    
    positions: Optional[np.ndarray] = None
    available_mems: list[int] = field(default_factory=lambda: list(range(32)))
    available_analogs: list[int] = field(default_factory=list)
    max_sampling_frequency: Optional[float] = None
    hardware: Optional[str] = None
    description: str = ""
    
    def __post_init__(self):
        """Validate positions array."""
        if self.positions is not None:
            if self.positions.ndim != 2 or self.positions.shape[1] != 3:
                raise ValueError("positions must be a (N, 3) numpy array")
            if self.positions.shape[0] != len(self.available_mems):
                raise ValueError("positions length must match available_mems length")
            
    def __str__(self):
        # Only show first MEMS number and count for large arrays
        if len(self.available_mems) == 0:
            mems_display = "[]"
        elif len(self.available_mems) == 1:
            mems_display = f"[{self.available_mems[0]}]"
        else:
            mems_display = f"[{self.available_mems[0]}, ...] ({len(self.available_mems)} total)"
        return f"MemsArrayInfo(description='{self.description}', hardware='{self.hardware}', available_mems={mems_display})"
