# megamicros.core.config.py
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
        mems: List of active MEMS channels (default: all available)
        analogs: List of active analog channels (default: empty)
        sampling_frequency: Sampling rate in Hz
        frame_length: Number of samples per frame
        duration: Acquisition duration in seconds (0 = infinite)
        datatype: Data type for samples ('int32' or 'float32')
        counter: Include counter channel in output
        skip_counter: Skip counter in iteration output
        queue_size: Maximum queue size (0 = unlimited)
        queue_timeout: Queue timeout in milliseconds
        sensibility: MEMS sensitivity factor (Pa/digit)
    """
    
    mems: Optional[list[int]] = None
    analogs: Optional[list[int]] = None
    sampling_frequency: int = 44100
    frame_length: int = 1024
    duration: float = 0
    datatype: DataType = 'int32'
    counter: bool = False
    skip_counter: bool = False
    queue_size: int = 0
    queue_timeout: int = 1000
    sensibility: float = 3.54e-6
    
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
    
    @property
    def active_channels(self) -> list[int]:
        """Get all active channels (MEMS + analogs + counter if enabled)."""
        channels = list(self.mems) + list(self.analogs)
        if self.counter:
            channels = [0] + channels  # Counter as first channel
        return channels
    
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
        available_analogs: List of available analog channels
        description: Optional description of the array
    """
    
    positions: Optional[np.ndarray] = None
    available_mems: list[int] = field(default_factory=lambda: list(range(32)))
    available_analogs: list[int] = field(default_factory=list)
    description: str = ""
    
    def __post_init__(self):
        """Validate positions array."""
        if self.positions is not None:
            if self.positions.ndim != 2 or self.positions.shape[1] != 3:
                raise ValueError("positions must be a (N, 3) numpy array")
            if self.positions.shape[0] != len(self.available_mems):
                raise ValueError("positions length must match available_mems length")
