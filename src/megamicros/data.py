# megamicros.data.py python software for direct signal extracting from databse
#
# Copyright (c) 2023 Sorbonne Université
# Author: bruno.gas@sorbonne-universite.fr
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
MegaMicros documentation is available on https://readthedoc.biimea.io
git clone https://gitlabsu.sorbonne-universite.fr/megamicros/Megamicros.git
"""

import numpy as np
from megamicros.exception import MuException

DEFAULT_LIMIT_VALUE = 10
FILETYPE_H5 = 1
FILETYPE_MP4 = 2
FILETYPE_WAV = 3
FILETYPE_MUH5 = 4


# =============================================================================
# Data and Audio Data base classes
# =============================================================================

class MuData:
    """Base class for Megamicros data objects"""

# =============================================================================
# The MuAudio classe
# =============================================================================

class MuAudio( MuData ):
    """
    MuAudio data class for multi-channels audio objects
    """
    __label: str = ""
    __raw: np.array = np.array( [] )
    __sampling_frequency: int = 0
    __dtype: np.dtype = np.float32
    __frame_size: int = None
    __frame_number: int = 0
    __it: int = 0


    def __init__(
            self, audio_signal:np.ndarray|list|None=None,
            sampling_frequency: int|float=None,
            label:str="No label",
            frame_size = None,
            frame_number = 0
        ):
        if audio_signal is not None and sampling_frequency is None:
            raise MuException( "Cannot create MuAudio object without knowing its sampling frequency" )

        if audio_signal is None:
            self.__raw = np.array( [] )
            self.__sampling_frequency = 0
            self.__label = label
            frame_size = None
            frame_number = 0

        # Get signal as an array of only one signal
        elif type( audio_signal ) is list:
            self.__raw = np.array( [audio_signal] )
            self.__sampling_frequency = sampling_frequency
            self.__label = label
            if frame_size is None:
                self.__frame_size = self.__raw.size
                self.__frame_number = 1

            print( f"I'm a list of one signal with frame size = {self.__frame_size} and frame number = {self.__frame_number}")
        
        # Get signal as a ND array (signals number x signals size)
        else:
            self.__raw = audio_signal
            self.__sampling_frequency = sampling_frequency
            self.__label = label
            # set default frame size as the length of signals  
            if frame_size is None:
                self.__frame_size = np.shape(self.__raw)[1]
                self.__frame_number = 1
            else:
                self.__frame_number = int( np.shape(self.__raw)[1] / self.__frame_size )

            print( f"I'm a NDarray signal with frame size = {self.__frame_size} and frame number = {self.__frame_number}")


# =============================================================================
# Properties
# =============================================================================

    @property
    def label( self ):
        """The data label if any"""
        return self.__label

    @property
    def channels_number( self ):
        """The number of channels"""
        if len( np.shape( self.__raw ) ) == 1:
            return 1
        return np.shape( self.__raw )[0]

    @property
    def samples_number( self ):
        """The number of samples per channels"""
        if len( np.shape( self.__raw ) ) == 1:
            return len( self.__raw )
        else:
            return np.shape( self.__raw )[1]

    @property
    def sampling_frequency( self ):
        """Audio signal's sampling frequency."""
        return self.__sampling_frequency 

    @property
    def dtype( self ):
        """The numpy data type used to store audio signals"""
        return self.__dtype

# =============================================================================
# Iterator and bracket operator
# =============================================================================

    def __iter__( self ):
        self.__it = 0
        if self.__frame_number == 0:
            raise Exception( f"Cannot iterate: empty object with no frame to iterate on" ) 
        return self

    def __next__( self ) -> np.ndarray :
        if self.__it >= self.__frame_number:
            raise StopIteration
        
        offset = self.__it * self.__frame_size
        result = self.__raw[:,offset:offset+self.__frame_size]
        self.__it += 1
        return result

    def __getitem__( self, item: int ) -> np.ndarray :
        if item == -1:
            offset = self.__frame_number-1
        elif item < -1 or item >= self.__frame_number:
            raise IndexError( f"Index value ({item}) exceed the avalaible frames number (allowed values are between 0 and {self.__frame_number-1}) " )
        else:
            offset = item * self.__frame_size
        
        return self.__raw[:,offset:offset+self.__frame_size]
    
    def __call__( self ):
        return self.__raw


# =============================================================================
# Overloaded interface
# =============================================================================

    def __str__( self ):
        return f"{self.channels_number} X {self.samples_number} audio signals (sf={self.sampling_frequency} Hz)"

# =============================================================================
# Interface
# =============================================================================

    def channel( self, channel_number:int=0 ) -> np.array:
        """
        Get the audio signal which channel is given as input (np.array)

        ## Parameters
        * channel_number: the channel number
        """
        if channel_number >= self.channels_number:
            raise MuException( f"Array overflow: there is no channel {channel_number} in MuAUdio object" )

        return self.__raw[channel_number,:]

    def set_frame_size( self, frame_size: int ) -> None:
        """
        Set the frame size for cutting signal into frames of fixed length when iterating 
        The default frame size (if not set by user) is equal to the signal length 
        """
        if frame_size > np.shape(self.__raw)[1]:
            raise Exception( f"Cannot set frame_size: actual signal length ({np.shape(self.__raw)[1]}) is shorter than frame size ({frame_size}) " )

        self.__frame_size = frame_size
        self.__frame_number = int( np.shape(self.__raw)[1] / self.__frame_size )