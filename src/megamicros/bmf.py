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
    __mems_position: np.ndarray | None          = None  # 3D MEMs positions from the antenna center
    __space_quantization: np.ndarray | None     = None  # locations number per meters (space frequency)
    __space_size: np.ndarray | None             = None
    __sampling_frequency: float | None          = None
    __fft_win_size: int | None                  = None

    # for internal purpose
    __freq_number: int                                  # spectral bands number
    __loc_number: int                                   # Total space locations number
    __locations: np.ndarray | None              = None

    def setMemsPosition( self, mems_position: np.ndarray ) -> None:

        if np.shape( mems_position )[1] != 3:
            raise MuBmfException( f"bad dimensions ({np.shape( mems_position )}). Mems positions should be a 3D data array (shape=(mems_number, 3))" )
        
        log.info( f' .Set beamformer on a {np.shape( mems_position )[0]} MEMs antenna' )

        self.__mems_position = mems_position


    def setSamplingFrequency( self, sr: float ) -> None:
        
        log.info( f' .Set beamformer sampling rate on {sr} Hz' )
        self.__sampling_frequency = sr


    def setFftWindowSize( self, ws: int ) -> None:
        
        log.info( f' .Set beamformer FFT window size to {ws} samples' )
        self.__fft_win_size = ws


    def setSpaceQuantization( self, sq: np.ndarray | tuple ) -> None:
        
        if type( sq ) is tuple or type( sq ) is list:
            if len( sq ) != 3:
                raise MuBmfException( f"Incorrect quantization dimensions ({len( sq )}). Should be 3 (sq_x, sq_y, sq_z)" )
            else:
                self.__space_quantization = np.array( [sq] )
        elif np.shape( sq ) != (1,3):
            raise MuBmfException( f"Incorrect array dimensions ({np.shape( sq )}). Should be (1, 3)" )
        else:
            self.__space_quantization = sq
            
        log.info( f' .Set beamformer space quantization to {sq} locations/meter' )


    def setSpaceSize( self, ss: np.ndarray|tuple ) -> None:
        """ Set the beamformer working space dimensions 
        
        Note that the working space has nothing to do with the room space. 
        The working space is the area where the beamformer perfoms the source localization.
        Its definition is relative to the antenna center. 
        Use the `Beamformer.moveAntenna()` method to stop centering of the working space.
        """
        
        if type( ss ) is tuple or type( ss ) is list:
            if len( ss ) != 3:
                raise MuBmfException( f"Incorrect space dimensions ({len( ss )}). Should be 3 (dx, dy, dz)" )
            else:
                self.__space_size = np.array( [ss] )
        elif np.shape( ss ) != (1,3):
            raise MuBmfException( f"Incorrect array dimensions ({np.shape( ss )}). Should be (1, 3)" )
        else:
            self.__space_size = ss
            
        log.info( f' .Set beamformer space size to {ss} meters' )
        
        
    def getLocations( self ) -> np.ndarray:
        """ Get the locations matrix
        
        The locations matrix is a 3D array of 3D points coverring the beamformer working space
        """

        if self.__locations is None:
            raise MuBmfException( f"No locations found. The beamformer seems not initialized. Please use the `Beamformer.init()` method before." )

        return self.__locations 


    def getLocationsNumber( self ) -> tuple:
        """ Get the locations number among x, y and z axis
        
        The locations matrix is a 3D array of 3D points coverring the beamformer working space
        """

        if self.__locations is None:
            raise MuBmfException( f"No locations found. The beamformer seems not initialized. Please use the `Beamformer.init()` method before." )

        # locations number
        loc_number_x = int( self.__space_size[0,0] * self.__space_quantization[0,0] )
        loc_number_y = int( self.__space_size[0,1] * self.__space_quantization[0,1] )
        loc_number_z = int( self.__space_size[0,2] * self.__space_quantization[0,2] )

        return [loc_number_x, loc_number_y, loc_number_z] 


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

        log.info( f' .[Ready]' )
        return result


    def init( self ) -> None:
        
        """ Init beamformer. All parameters should be set before 
        
        Check antenna parameters, then build the distance matrix
        """

        # check for parameters
        if not self._check():
            raise MuBmfException( f'Some parameters are not set. Cannot perform beamforming' )

        # time axis in seconds
        t = np.arange( self.__fft_win_size )/self.__sampling_frequency

        # frequency axis in Hz
        f = np.fft.rfftfreq( self.__fft_win_size, 1/self.__sampling_frequency )

        # frequencies number
        self.__freq_number = np.fft.rfftfreq( self.__fft_win_size, 1/self.__sampling_frequency ).size

        # space size
        dimx = self.__space_size[0,0]
        dimy = self.__space_size[0,1]
        dimz = self.__space_size[0,2]

        # locations number
        loc_number_x = int( dimx * self.__space_quantization[0,0] )
        loc_number_y = int( dimy * self.__space_quantization[0,1] )
        loc_number_z = int( dimz * self.__space_quantization[0,2] )

        self.__loc_number = loc_number_x * loc_number_y * loc_number_z

        # width, depth, height quantizations in meters
        dx: float = 1/self.__space_quantization[0,0]
        dy: float = 1/self.__space_quantization[0,1]
        dz: float = 1/self.__space_quantization[0,2]

        # microphones number
        mems_number = np.shape( self.__mems_position )[0]

        # print info
        log.info( f" .Beamformer2D Initilization:" )
        log.info( f"  > Found antenna with {mems_number} MEMs microphones" )
        log.info( f"  > FFT window size is {self.__fft_win_size} samples" )
        log.info( f"  > Time range: [0, {t[-1]}] s" )
        log.info( f"  > Frequency range: [0, {f[-1]}] Hz ({self.__freq_number} beams)" )
        log.info( f"  > Space quantization: {self.__space_quantization} locations/meter" )
        log.info( f"  > Found {self.__loc_number} locations ({loc_number_x} x {loc_number_y} x {loc_number_z})")
        log.info( f"  > Space quantum size is ({dx:.2f} x {dy:.2f} x {dz:.2f}) meters")

        # Build the locations 3D (centered) coordinates
        self.__locations = np.ndarray( ( loc_number_x*loc_number_y*loc_number_z, 3 ) )
        for x in range( loc_number_x ):
            for y in range( loc_number_y):
                for z in range( loc_number_z):
                    i = x * loc_number_y * loc_number_z + y * loc_number_z + z
                    self.__locations[i] = np.array( [x*dx+dx/2-dimx/2, y*dy+dy/2-dimy/2, z*dz+dz/2-dimz/2] )
        
        # Init distance matrix
        log.info( f" .Build distances matrix D ({self.__loc_number} x {mems_number})" ) 
        self._D = np.ndarray( (self.__loc_number, mems_number), dtype=float )
        for s in range( self.__loc_number ):
            for m in range( mems_number ):
                self._D[s, m] = np.linalg.norm( np.array( self.__mems_position[m] ) - self.__locations[s] )

        # Allocate and build the H complex transfer function matrix (preformed channels)
        log.info( f" .Build preformed channels matrix H ({self.__freq_number} x {self.__loc_number} x {mems_number})" ) 
        self._H = np.outer( f, self._D ).reshape( self.__freq_number, self.__loc_number, mems_number )/SOUND_SPEED
        self._H = np.exp( 1j*2*np.pi*self._H ) 
        


