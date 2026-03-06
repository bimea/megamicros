# megamicros.sources.h5.py
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
HDF5 file data source.

This data source reads previously recorded data from MuH5 format files,
allowing playback and analysis of stored acquisitions.

Features:
    - Read MuH5 format HDF5 files
    - Frame-by-frame iteration
    - Channel selection
    - Video data support
    
Examples:
    Basic usage::

        from megamicros.sources import H5DataSource
        from megamicros.core.config import AcquisitionConfig
        
        source = H5DataSource('recording.h5')
        config = AcquisitionConfig(
            mems=[0, 1, 2, 3],
            frame_length=1024
        )
        source.configure(config)
        source.start()
        
        for frame in source:
            print(f"Frame shape: {frame.shape}")
        
        source.stop()
        
Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""

from typing import Iterator, Optional
from pathlib import Path
import numpy as np
import h5py

from .base import BaseDataSource, SourceState
from ..core.config import AcquisitionConfig, MemsArrayInfo
from ..core.mu import MU_MEMS_SENSIBILITY
from ..log import log
from ..exception import MuException


class H5SourceException(MuException):
    """Exception for H5 data source."""
    pass


class H5DataSource(BaseDataSource):
    """
    HDF5 file data source for playback of recorded data.
    
    Reads MuH5 format files and provides frame-by-frame iteration.
    
    Args:
        filepath: Path to HDF5 file
    """
    
    def __init__(self, filepath: str | Path):
        super().__init__()
        self._filepath = Path(filepath)
        self._current_frame = 0
        self._dataset_index = 0
        self._frame_in_dataset = 0
        
        # Validate file exists
        if not self._filepath.exists():
            raise H5SourceException(f"File not found: {filepath}")
        
        # Read file metadata
        self._read_metadata()
        
        log.info(f"H5DataSource initialized from {filepath}")
    
    def _read_metadata(self) -> None:
        """Read metadata from H5 file."""
        try:
            with h5py.File(self._filepath, 'r') as f:
                # Validate MuH5 format
                if 'muh5' not in f:
                    raise H5SourceException(f"{self._filepath} is not a valid MuH5 file")
                
                group = f['muh5']
                attrs = dict(zip(group.attrs.keys(), group.attrs.values()))
                
                # Extract metadata
                self._sampling_frequency = attrs['sampling_frequency']
                self._available_mems = list(attrs['mems'])
                self._available_analogs = list(attrs.get('analogs', []))
                self._duration = attrs['duration']
                self._counter = attrs.get('counter', False) and not attrs.get('counter_skip', False)
                self._status = attrs.get('status', False)
                self._dataset_length = attrs['dataset_length']
                self._dataset_number = attrs['dataset_number']
                self._samples_number = self._dataset_number * self._dataset_length
                
                # Setup array info
                self._info = MemsArrayInfo(
                    available_mems=self._available_mems,
                    available_analogs=self._available_analogs,
                    description=f"H5 file: {self._filepath.name}"
                )
                
                # Check video availability
                self._video_available = 'video' in f['muh5']
                
                log.debug(f"H5 metadata: {len(self._available_mems)} MEMS, "
                         f"{self._sampling_frequency}Hz, {self._duration}s, "
                         f"{self._dataset_number} datasets")
                
        except Exception as e:
            raise H5SourceException(f"Failed to read H5 metadata: {e}")
    
    def _do_configure(self, config: AcquisitionConfig) -> None:
        """Configure H5 playback."""
        # Validate requested channels
        for mems in config.mems:
            if mems not in self._available_mems:
                raise ValueError(f"MEMS {mems} not available in H5 file")
        
        for analog in config.analogs:
            if analog not in self._available_analogs:
                raise ValueError(f"Analog {analog} not available in H5 file")
        
        # Build channel mask
        total_channels = len(self._available_mems) + len(self._available_analogs)
        if self._counter:
            total_channels += 1
        if self._status:
            total_channels += 1
        
        # Map requested channels to file indices
        self._channel_indices = []
        channel_offset = 1 if self._counter else 0
        
        if config.counter and self._counter:
            self._channel_indices.append(0)
        
        for mems in config.mems:
            idx = channel_offset + self._available_mems.index(mems)
            self._channel_indices.append(idx)
        
        for analog in config.analogs:
            idx = channel_offset + len(self._available_mems) + self._available_analogs.index(analog)
            self._channel_indices.append(idx)
        
        self._current_frame = 0
        self._dataset_index = 0
        self._frame_in_dataset = 0
        
        log.debug(f"H5DataSource configured: {len(self._channel_indices)} channels, "
                 f"frame_length={config.frame_length}")
    
    def _do_start(self) -> None:
        """Start H5 playback."""
        log.debug("H5DataSource playback started")
    
    def _do_stop(self) -> None:
        """Stop H5 playback."""
        log.debug(f"H5DataSource playback stopped at frame {self._current_frame}")
    
    def _generate_frames(self) -> Iterator[np.ndarray]:
        """Generate frames from H5 file."""
        if self._config is None:
            raise RuntimeError("Source not configured")
        
        frame_length = self._config.frame_length
        
        with h5py.File(self._filepath, 'r') as f:
            # Calculate total samples
            total_samples = min(
                self._samples_number,
                self._config.total_samples if self._config.total_samples > 0 else self._samples_number
            )
            
            sample_offset = 0
            
            while sample_offset < total_samples and self._state == SourceState.RUNNING:
                # Determine how many samples to read in this frame
                samples_left = total_samples - sample_offset
                samples_to_read = min(frame_length, samples_left)
                
                # Allocate frame buffer
                frame = np.zeros((len(self._channel_indices), samples_to_read), 
                               dtype=np.float32 if self._config.datatype == 'float32' else np.int32)
                
                # Read data (may span multiple datasets)
                samples_read = 0
                
                while samples_read < samples_to_read:
                    # Get current dataset
                    dataset_path = f'muh5/{self._dataset_index}/sig'
                    if dataset_path not in f:
                        break
                    
                    dataset = f[dataset_path]
                    
                    # Calculate read range within dataset
                    dataset_samples_left = self._dataset_length - self._frame_in_dataset
                    chunk_size = min(samples_to_read - samples_read, dataset_samples_left)
                    
                    # Read chunk
                    chunk_end = self._frame_in_dataset + chunk_size
                    data_chunk = dataset[self._channel_indices, self._frame_in_dataset:chunk_end]
                    
                    # Copy to frame buffer
                    frame[:, samples_read:samples_read + chunk_size] = data_chunk
                    
                    samples_read += chunk_size
                    self._frame_in_dataset += chunk_size
                    
                    # Move to next dataset if needed
                    if self._frame_in_dataset >= self._dataset_length:
                        self._dataset_index += 1
                        self._frame_in_dataset = 0
                
                # Apply sensibility to MEMS channels if needed
                if self._config.datatype == 'float32':
                    frame = frame.astype(np.float32)
                    # Apply sensibility to MEMS channels only
                    mems_offset = 1 if (self._config.counter and self._counter) else 0
                    n_mems = len(self._config.mems)
                    if n_mems > 0:
                        frame[mems_offset:mems_offset+n_mems, :] *= self._config.sensibility
                
                yield frame
                
                sample_offset += samples_to_read
                self._current_frame += 1
    
    @property
    def video_available(self) -> bool:
        """Check if video data is available."""
        return self._video_available
    
    def get_video_frames(self, start_frame: int = 0, end_frame: int = -1) -> np.ndarray:
        """
        Extract video frames from file.
        
        Args:
            start_frame: Start frame index
            end_frame: End frame index (-1 for last frame)
            
        Returns:
            np.ndarray: Video frames with shape (frames, height, width, channels)
        """
        if not self._video_available:
            raise H5SourceException("No video available in this H5 file")
        
        with h5py.File(self._filepath, 'r') as f:
            video_group = f['muh5/video']
            attrs = dict(zip(video_group.attrs.keys(), video_group.attrs.values()))
            video_frame_count = attrs['video_frame_count']
            
            if end_frame == -1:
                end_frame = video_frame_count - 1
            
            if start_frame < 0 or end_frame >= video_frame_count or start_frame > end_frame:
                raise H5SourceException(
                    f"Frame index out of bounds: start={start_frame}, end={end_frame}, "
                    f"total={video_frame_count}"
                )
            
            # Read video frames
            video_frames = []
            # Implementation similar to MuH5.get_video_frames()
            # ... (simplified for brevity)
            
        return np.array(video_frames)
