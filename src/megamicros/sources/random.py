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

**v4.0**: Now uses queue + thread to simulate realistic asynchronous behavior,
matching USB/H5 data sources for consistent API testing.

Features:
    - Generates normally distributed random samples
    - Asynchronous generation with queue (like real hardware)
    - Respects all acquisition parameters
    - Deterministic if seed is provided
    - Optional timing simulation for realistic tests
    
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
        
        # Frames are generated asynchronously in background thread
        for frame in source:
            print(f"Frame shape: {frame.shape}")
        
        source.wait()
        
Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""

from typing import Iterator, Optional
import numpy as np
import queue
import time
from threading import Thread

from .base import BaseDataSource, SourceState
from ..core.config import AcquisitionConfig, MemsArrayInfo
from ..log import log


class RandomDataSource(BaseDataSource):
    """
    Random signal generator for testing and development.
    
    **v4.0**: Uses queue + thread to simulate realistic asynchronous behavior.
    This makes it functionally equivalent to USB/H5 sources for testing.
    
    Generates frames of random data with specified characteristics.
    Useful as fallback when no real hardware is available.
    
    Args:
        seed: Random seed for reproducibility (default: None for random)
        amplitude: Signal amplitude scaling factor (default: 1.0)
        available_mems: Number of available MEMS channels (default: 32)
        available_analogs: Number of available analog channels (default: 0)
        simulate_timing: If True, adds realistic delays between frames (default: False)
    """
    
    def __init__(
        self,
        seed: Optional[int] = None,
        amplitude: float = 1.0,
        available_mems: int = 32,
        available_analogs: int = 0,
        simulate_timing: bool = False,
    ):
        super().__init__()
        self._seed = seed
        self._amplitude = amplitude
        self._simulate_timing = simulate_timing
        self._rng = np.random.default_rng(seed)
        self._frame_count = 0
        
        # Queue for asynchronous generation (like USB)
        self._queue: queue.Queue = queue.Queue()
        self._generator_thread: Thread | None = None
        self._halt_request = False
        self._timer_thread: Thread | None = None
        
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
        self._halt_request = False
        
        # NOTE: Queue is NOT cleared - frames accumulate between runs!
        # Use Megamicros.clear_queue() to manually discard frames if needed.
        
        log.debug(f"RandomDataSource configured: {len(config.active_channels)} channels, "
                  f"{config.frame_length} samples/frame, {config.duration}s duration")
    
    def _do_start(self) -> None:
        """Start random generation in background thread."""
        if self._config is None:
            raise RuntimeError("Source not configured")
        
        # Start generator thread (analogous to USB transfer thread)
        self._generator_thread = Thread(
            target=self._generator_worker,
            name="RandomGeneratorThread",
            daemon=True
        )
        self._generator_thread.start()
        
        # Start timer thread if duration is limited
        if self._config.duration > 0:
            self._timer_thread = Thread(
                target=self._timer_worker,
                name="RandomTimerThread",
                daemon=True
            )
            self._timer_thread.start()
        
        log.debug("RandomDataSource started (asynchronous generation)")
    
    def _do_stop(self) -> None:
        """Stop random generation."""
        self._halt_request = True
        
        # Wait for threads
        if self._generator_thread and self._generator_thread.is_alive():
            self._generator_thread.join(timeout=2.0)
        
        if self._timer_thread and self._timer_thread.is_alive():
            self._timer_thread.join(timeout=1.0)
        
        log.debug(f"RandomDataSource stopped after {self._frame_count} frames")
    
    def _do_wait(self) -> None:
        """Wait for generation threads to complete."""
        if self._generator_thread:
            self._generator_thread.join()
        if self._timer_thread:
            self._timer_thread.join()
    
    def _generator_worker(self) -> None:
        """
        Background thread that generates frames and fills the queue.
        
        This simulates the asynchronous behavior of USB transfers.
        """
        if self._config is None:
            return
        
        total_frames = self._config.total_frames
        channels = self._config.active_channels
        n_channels = len(channels)
        frame_length = self._config.frame_length
        
        # Calculate frame period for timing simulation
        frame_period = frame_length / self._config.sampling_frequency if self._simulate_timing else 0
        
        # Generate frames
        frame_index = 0
        max_frames = total_frames if total_frames > 0 else float('inf')
        
        while frame_index < max_frames and not self._halt_request:
            # Generate frame
            frame = self._generate_single_frame(n_channels, frame_length)
            
            # Put in queue (blocks if queue is full, like real USB)
            try:
                self._queue.put(frame, timeout=1.0)
                self._frame_count += 1
                frame_index += 1
                
                # Simulate realistic timing if requested
                if self._simulate_timing and frame_period > 0:
                    time.sleep(frame_period)
                    
            except queue.Full:
                log.warning("RandomDataSource: queue full, frame dropped")
                break
        
        log.debug(f"RandomDataSource generator thread finished ({self._frame_count} frames)")
    
    def _timer_worker(self) -> None:
        """Timer thread to stop generation after specified duration."""
        if self._config is None or self._config.duration <= 0:
            return
        
        time.sleep(self._config.duration)
        
        if not self._halt_request:
            log.debug(f"RandomDataSource: duration limit reached ({self._config.duration}s)")
            self._halt_request = True
    
    def _generate_frames(self) -> Iterator[np.ndarray]:
        """
        Read frames from queue (generated by background thread).
        
        This matches the USB/H5 behavior: frames are retrieved from
        a queue that was filled asynchronously.
        """
        timeout = self._config.queue_timeout / 1000.0 if self._config else 1.0
        
        while True:
            try:
                frame = self._queue.get(timeout=timeout)
                yield frame
            except queue.Empty:
                # Queue empty and generation stopped
                if self._halt_request or not self._generator_thread.is_alive():
                    break
                # Timeout but still generating - keep waiting
                continue
    
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
    
    @property
    def queue_content(self) -> int:
        """Get current number of frames in the queue."""
        return self._queue.qsize()
    
    @property
    def transfert_lost(self) -> int:
        """Get number of frames lost due to queue overflow."""
        # RandomDataSource doesn't drop frames (infinite queue)
        return 0
    
    def reset_seed(self, seed: Optional[int] = None) -> None:
        """
        Reset random number generator with new seed.
        
        Args:
            seed: New seed (None for random)
        """
        self._seed = seed
        self._rng = np.random.default_rng(seed)
        log.debug(f"RandomDataSource seed reset to {seed}")
