# megamicros.muh5.py H5 file handler for MegaMicros libraries
#
# Copyright (c) 2023 Sorbonne Université
# Author: bruno.gas@sorbonne-universite.fr
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Megamicros documentation is available on https://readthedoc.bimea.io
"""

import numpy as np
import h5py

from .log import log, logging
from .core.mu import MU_MEMS_SENSIBILITY

class MuH5:
    
    @property
    def sampling_frequency( self ):
        return self.__sampling_frequency

    @property
    def mems_number( self ):
        return self.__mems_number
    
    @property
    def available_mems( self ):
        return self.__available_mems

    @property
    def channels_number( self ):
        return self.__channels_number

    @property
    def duration( self ):
        return self.__duration

    @property
    def status( self ) -> bool:
        return self.__status
    
    @property
    def samples_number( self ):
        return self.__samples_number
    
    @property
    def info( self ):
        return self.__info
    
    @property
    def video_available( self ) -> bool:
        return self.__video_available
    
    @property 
    def info_video( self ):
        return self.__info_video
    
    @property
    def video_adaptive_fps( self ) -> bool:
        return self.__adaptive_fps
    
    @property
    def video_max_fps( self ) -> float:
        return self.__max_fps
    
    @property
    def video_dataset_count( self ) -> int:
        return self.__video_dataset_count

    @property
    def video_frame_count( self ) -> int:
        return self.__video_frame_count
    

    def __init__( self, filename:str ):

        """ open h5 file and get informations from """
        self.__filename = filename
        with h5py.File( filename, 'r' ) as f:

            """ Control whether H5 file is a MuH5 file """
            if not f['muh5']:
                raise Exception( f"{filename} seems not to be a MuH5 file: unrecognized format" )

            """ get fil informations """
            group = f['muh5']
            self.__info = dict( zip( group.attrs.keys(), group.attrs.values() ) )
            self.__sampling_frequency = self.__info['sampling_frequency']
            self.__available_mems = list( self.__info['mems'] )
            self.__mems_number = len( self.__available_mems )
            self.__available_analogs = list( self.__info['analogs'] )
            self.__analogs_number = len( self.__available_analogs )
            self.__duration = self.__info['duration']
            self.__counter = self.__info['counter'] and not self.__info['counter_skip']
            self.__status = True if 'status' in self.__info and self.__info['status'] else False
            self.__channels_number = self.__mems_number + self.__analogs_number + ( 1 if self.__counter else 0 ) + ( 1 if self.__status else 0 )
            self.__dataset_length = self.__info['dataset_length']
            self.__dataset_number = self.__info['dataset_number']
            self.__samples_number = self.__dataset_number * self.__dataset_length

            # Explore the first dataset to check data integrity and get data type
            dataset = f['muh5/0/sig']
            data = np.array( dataset[:] )
            if data.shape[0] != self.__channels_number or data.shape[1] != self.__dataset_length:
                raise Exception( f"Data integrity error: dataset shape {data.shape} does not match expected shape ({self.__channels_number}, {self.__dataset_length})" )

            # Check if muh5/video group exists
            self.__video_available = False
            if 'video' not in f['muh5']:
                self.__video_available = False
            else:
                self.__video_available = True

                # get video group attributes:
                video_group = f['muh5/video']
                self.__info_video = dict( zip( video_group.attrs.keys(), video_group.attrs.values() ) )
                self.__adaptive_fps = self.__info_video['adaptive_fps']
                self.__max_fps = self.__info_video['max_fps']
                self.__video_dataset_count = self.__info_video['video_dataset_count']
                self.__video_frame_count = self.__info_video['video_frame_count']

                # Explore the first dataset to check video data integrity
                # Check video dataset existance
                if '0' not in f['muh5/video']:
                    raise Exception( f"Video data integrity error: video dataset 0 not found in muh5/video group " )
                else:
                    log.info( f" .This muh5 file contains a video: {self.__video_frame_count} frames found" )

            log.info( f" .Created MuH5 object from {filename} file " )

    def get_video_frames( self, start_frame: int=0, end_frame: int=-1 ) -> np.ndarray:
        """
        Extract video from file

        Returns
        -------
        * video (np.ndarray): array of shape ( frame_count, height, width, channels ) containing video frames
        """

        if not self.__video_available:
            raise Exception( "No video available in this MuH5 file" )

        if end_frame == -1:
            end_frame = self.__video_frame_count - 1

        if start_frame < 0 or end_frame >= self.__video_frame_count or start_frame > end_frame:
            raise Exception( f"Frame index out of bounds: start_frame={start_frame}, end_frame={end_frame}, video_frame_count={self.__video_frame_count}" )

        video_frames = []

        with h5py.File( self.__filename, 'r' ) as f:
            # Get frames from start_frame to end_frame
            frame_index = 0
            for dataset_index in range( self.__video_dataset_count ):
                dataset = f['muh5/video/' + str( dataset_index ) + '/img']
                dataset_frame_number = dataset.shape[0]
                if frame_index + dataset_frame_number - 1 < start_frame:
                    # Skip this dataset
                    frame_index += dataset_frame_number
                    continue
                if frame_index > end_frame:
                    # All requested frames have been extracted
                    break
                # Extract frames from this dataset
                data = np.array( dataset[:] )
                
                # Get the range of frames to extract from this dataset
                dataset_start_frame = max( 0, start_frame - frame_index )
                dataset_end_frame = min( dataset_frame_number - 1, end_frame - frame_index )

                for index in range( dataset_start_frame, dataset_end_frame + 1 ):
                    video_frames.append( data[index,:,:,:] )
                    frame_index += 1

        video_array = np.array( video_frames )

        return video_array

    def get_signal( self, channels: list, mems_sensibility:float=MU_MEMS_SENSIBILITY ) -> np.ndarray:
        """
        Extract signal from file

        Parameters
        ----------
        * channels (list<int>): list of channels to extract
        * mems_sensibility: mems semsibility factor. if 0, the original signal is returned as it is (int32), otherwise as float32
        """

        """ build the mask from the channels list given as argument """
        mask = [ True if channel in channels else False for channel in range(self.channels_number) ]

        sound = np.zeros( ( len( channels ), self.__samples_number ), dtype=np.int32 )

        with h5py.File( self.__filename, 'r' ) as f:
            offset = 0
            for dataset_index in range( self.__dataset_number ):
                dataset = f['muh5/' + str( dataset_index ) + '/sig']
                sound[:,offset:offset+self.__dataset_length] = np.array( dataset[:] )[mask,:]
                offset += self.__dataset_length

        """ product with mems sensibility factor if one is given """
        if mems_sensibility is not None or mems_sensibility != 0:
            first_mems = 1 if self.__counter else 0
            last_mems = first_mems + self.__mems_number - 1
            mask = [ True if channel >= first_mems and channel <= last_mems else False for channel in channels ]
            sound = sound.astype( np.float32 )
            sound[mask,:] = sound[mask,:] * mems_sensibility

        return sound

    def get_one_channel_signal( self, channel_number, mems_sensibility:float=MU_MEMS_SENSIBILITY  ) -> np.ndarray:
        """
        Get only one channel signal whose channel number is given as argument
        """
        if channel_number >= self.channels_number:
            raise Exception( f"Index overflow: cannt extract channel [{channel_number}] from MuH5 with only [{self.channels_number}] channels " )

        return self.get_signal( [channel_number], mems_sensibility=mems_sensibility )

    def get_all_channels_signal( self, mems_sensibility:float=MU_MEMS_SENSIBILITY  ) -> np.ndarray:
        """
        Get all channels signal
        """        

        return self.get_signal( [i for i in range( self.__channels_number )], mems_sensibility=mems_sensibility )