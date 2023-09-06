# megamicros.bmf.py
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

"""Define beamformer classes for beamforming

Usage
-----
import megamicros.bmf

Attributes
----------

__mems_position: np.ndarray()
    3D MEMs positions from the antenna center
    
__sampling_frequency: float
    Sampling frequency

__space_quantization: float
    locations number per meters (space frequency)

__window_size: int
    samples number for FFT estimation

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import numpy as np
from megamicros.log import log
from megamicros.exception import MuException

SOUND_SPEED = 340.29

class MuBmfException( MuException ):
    """ Exception for beamformers """
    pass


class Beamformer:
    """ Base class for beamformers"""

    # bmf properties
    __mems_position: np.ndarray         = None  # 3D MEMs positions from the antenna center
    __space_quantization: np.ndarray    = None  # locations number per meters (space frequency)
    __space_size: np.ndarray            = None
    __sampling_frequency: float         = None
    __fft_win_size: int                 = None

    # for internal purpose
    __freq_number: int                  # spectral bands number
    __loc_number: int                   # Total space locations number


    def setMemsPosition( self, mems_position: np.ndarray ) -> None:

        mems_number, dim = np.shape( mems_position )
        if dim != 3:
            raise MuBmfException( f"bad dimensions ({mems_number}, {dim}). Mems positions should be a 3D data array (shape=(mems_number, 3))" )
        
        log.info( f' .Set beamformer on a {mems_number} MEMs antenna' )

        self.__mems_position = mems_position


    def setSamplingFrequency( self, sr: float ) -> None:
        
        log.info( f' .Set beamformer sampling rate on {sr} Hz' )
        self.__sampling_frequency = sr


    def setFftWindowSize( self, ws: int ) -> None:
        
        log.info( f' .Set beamformer FFT window size to {ws} samples' )
        self.__fft_win_size = ws


    def setSpaceQuantization( self, sq: np.ndarray | tuple ) -> None:
        
        dim = len( sq )
        if dim != 3:
            raise MuBmfException( f"Incorrect array or tuple dimensions ({dim}). Should be 3 (sq_x, sq_y, sq_z)" ) 

        log.info( f' .Set beamformer space quantization to {sq} locations/meter' )
        self.__space_quantization = sq


    def setSpaceSize( self, ss: np.ndarray|tuple ) -> None:
        
        dim = len( ss )
        if dim != 3:
            raise MuBmfException( f"Incorrect space dimensions ({dim}). Should be 3 (dx, dy, dz)" ) 

        log.info( f' .Set beamformer space size to {ss}' )
        self.__space_size = np.array( ss )


    def __init__( self, mems_position: np.ndarray|None=None, sampling_frequency: float|None=None, window_size:int|None=None, space_quantization:float|None=None, space_size:float|None=None ):

        if mems_position is not None:
            self.setMemsPosition( mems_position )
        if sampling_frequency is not None:
            self.setSamplingFrequency( sampling_frequency )
        if window_size is not None:
            self.setFftWindowSize( window_size )
        if space_quantization is not None:
            self.setSpaceQuantization( space_quantization )
        if space_size is not None:
            self.setSpaceSize( space_size )

    def _check( self ) -> bool:

        log.info( f' .Checking beamformer parameters...' )
        result: bool = True
        if self.__mems_position is None:
            log.info( f' > MEMs position should be set.' )
            result = False
        if self.__space_quantization is None:
            log.info( f' > Space quantization should be set.' )
            result = False
        if self.__space_size is None:
            log.info( f' > Space size should be set.' )
            result = False
        if self.__sampling_frequency is None:
            log.info( f' > Sampling should be set.' )
            result = False
        if self.__fft_win_size is None:
            log.info( f' > FFT window size not set.' )
            result = False

        log.info( f' .[Ready]]' )
        return result


    def init( self ) -> None:
        
        """ Init beamformer. All parameters should be set before """

        # check for parameters
        if not self._check():
            raise MuBmfException( f'Some parameters are not set. Cannot perform beamforming' )

        # time axis in seconds
        t = np.arange( self.__fft_win_size )/self.__sampling_frequency

        # frequency axis in Hz
        f = np.fft.rfftfreq( self.__fft_win_size, 1/self.__sampling_frequency )

        # frequencies number
        self.__freq_number = np.fft.rfftfreq( self.__fft_win_size, 1/self.__sampling_frequency ).size

        # locations number
        __loc_number_x = self.__space_size[0,0]
        __loc_number_y = self.__space_size[0,1]
        self.__loc_number = __loc_number_x * __loc_number_y

        # print info
        log.info( f" .Beamformer2D Initilization:" )
        log.info( f"  > Found antenna with {np.shape( self.__mems_position )[1]} MEMs microphones" )
        log.info( f"  > FFT window size is {self.__fft_win_size} samples" )
        log.info( f"  > Time range: [0, {t[-1]}] s" )
        log.info( f"  > Frequency range: [0, {f[-1]}] Hz ({self.__freq_number} beams)" )
        log.info( f"  > Space quantization: {self.__space_quantization} locations/meter" )
        log.info( f"  > Locations number: {self.__loc_number}" )



        


