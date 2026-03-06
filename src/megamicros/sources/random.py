# megamicros.sources.random.py
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
Random signal generator data source.

This data source generates random signals for testing and development purposes.
Useful when no hardware is available or for unit tests.

Features:
    - Generates normally distributed random samples
    - Respects all acquisition parameters
    - Deterministic if seed is provided
    - No external dependencies
    
Examples:
    Basic usage::

        from megamicros.sources import RandomDataSource
        from megamicros.core.config import AcquisitionConfig
        
        source = RandomDataSource(seed=42)
        config = AcquisitionConfig(
            mems=[0, 1, 2, 3],
            sampling_frequency=44100,
            frame_length=1024,
            duration=1.0
        )
        source.configure(config)
        source.start()
        
        for frame in source:
            print(f"Frame shape: {frame.shape}")
        
        source.wait()
        source.stop()
        
Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""

from typing import Iterator, Optional
import numpy as np

from .base import BaseDataSource, SourceState
from ..core.config import AcquisitionConfig, MemsArrayInfo
from ..log import log


class RandomDataSource(BaseDataSource):
    """
    Random signal generator for testing and development.
    
    Generates frames of random data with specified characteristics.
    Useful as fallback when no real hardware is available.
    
    Args:
        seed: Random seed for reproducibility (default: None for random)
        amplitude: Signal amplitude scaling factor (default: 1.0)
        available_mems: Number of available MEMS channels (default: 32)
        available_analogs: Number of available analog channels (default: 0)
    """
    
    def __init__(
        self,
        seed: Optional[int] = None,
        amplitude: float = 1.0,
        available_mems: int = 32,
        available_analogs: int = 0,
    ):
        super().__init__()
        self._seed = seed
        self._amplitude = amplitude
        self._rng = np.random.default_rng(seed)
        self._frame_count = 0
        
        # Configure available channels
        self._info = MemsArrayInfo(
            available_mems=list(range(available_mems)),
            available_analogs=list(range(available_analogs)),
            description="Random signal generator (testing/development)"
        )
        
        log.info(f"RandomDataSource initialized (seed={seed}, amplitude={amplitude})")
    
    def _do_configure(self, config: AcquisitionConfig) -> None:
        """Configure random generator."""
        # Validate requested channels are available
        for mems in config.mems:
            if mems not in self._info.available_mems:
                raise ValueError(f"MEMS {mems} not available")
        
        for analog in config.analogs:
            if analog not in self._info.available_analogs:
                raise ValueError(f"Analog {analog} not available")
        
        self._frame_count = 0
        log.debug(f"RandomDataSource configured: {len(config.active_channels)} channels, "
                  f"{config.frame_length} samples/frame, {config.duration}s duration")
    
    def _do_start(self) -> None:
        """Start random generation."""
        log.debug("RandomDataSource started")
    
    def _do_stop(self) -> None:
        """Stop random generation."""
        log.debug(f"RandomDataSource stopped after {self._frame_count} frames")
    
    def _generate_frames(self) -> Iterator[np.ndarray]:
        """Generate random frames."""
        if self._config is None:
            raise RuntimeError("Source not configured")
        
        total_frames = self._config.total_frames
        channels = self._config.active_channels
        n_channels = len(channels)
        frame_length = self._config.frame_length
        
        # If duration is 0, generate infinite frames
        if total_frames == 0:
            log.warning("RandomDataSource: infinite duration - will generate frames indefinitely")
            while self._state == SourceState.RUNNING:
                yield self._generate_single_frame(n_channels, frame_length)
                self._frame_count += 1
        else:
            for i in range(total_frames):
                if self._state != SourceState.RUNNING:
                    break
                yield self._generate_single_frame(n_channels, frame_length)
                self._frame_count += 1
    
    def _generate_single_frame(self, n_channels: int, frame_length: int) -> np.ndarray:
        """Generate a single random frame."""
        # Generate random data based on datatype
        if self._config.datatype == 'int32':
            # Simulate 24-bit quantization
            max_val = 2**23
            frame = self._rng.normal(0, self._amplitude * max_val * 0.1, 
                                    size=(n_channels, frame_length))
            frame = np.clip(frame, -max_val, max_val-1).astype(np.int32)
        else:  # float32
            frame = self._rng.normal(0, self._amplitude, 
                                    size=(n_channels, frame_length)).astype(np.float32)
        
        # Add counter if requested
        if self._config.counter and not self._config.skip_counter:
            frame[0, :] = self._frame_count  # Counter channel
        
        return frame
    
    def reset_seed(self, seed: Optional[int] = None) -> None:
        """
        Reset random number generator with new seed.
        
        Args:
            seed: New seed (None for random)
        """
        self._seed = seed
        self._rng = np.random.default_rng(seed)
        log.debug(f"RandomDataSource seed reset to {seed}")
