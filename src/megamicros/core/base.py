# core.base.py base class for MegaMicros receivers
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


"""Provide the base class of MEMs arrays.

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import numpy as np
from megamicros.log import log


DEFAULT_FRAME_LENGTH = 256
DEFAULT_SAMPLING_FREQUENCY = 50000


class MemsArray:
    """ MEMs array base class.

    The MemsArray class models the operation of an antenna composed of any number of microphones
    Les microphones de l'antenne sont obligatoireement numérotés de 0 à `available_mems_number`. 
    Certains peuvent ne pas être *actifs*. `mems_number` donne le nombre de microphnes actifs. 
    Les microphones sont définis par une position relative au centre de l'antenne. 
    Ces positions peuvent ne pas être connues. Il n'est alors pas possible de faire du filtrage spatial.

    Antenna microphones must be numbered from 0 to `available_mems_number`. 
    Some may not be *active*. `mems_number` gives the number of active microphones. 
    Microphones are defined by a position relative to the center of the antenna.
    Tese positions may not be known. In this case, spatial filtering is not possible.

    Attributes
    ----------
    __mems: tuple
        activated MEMs (from 0 to last-1)

    __available_mems: tuple
        actual MEMs (from 0 to last-1)

    __analogs: tuple
        actiovated analogs channels

    __available_analogs: tuple
        actual analogs channels

    __mems_position: np.ndarray
        MEMs 3D position relative to the antenna center 

    __sampling_frequency: float
        Sampling frequency

    __frame_length: int
        The output buffer length in signal samples number
    """

    # Antenna dimensions
    __mems: tuple = []
    __available_mems: tuple
    __analogs: tuple = []
    __available_analogs: tuple = []
    __mems_position: np.ndarray | None

    # Antenna properties
    __sampling_frequency: float = DEFAULT_SAMPLING_FREQUENCY

    # Output buffering
    __frame_length: int = DEFAULT_FRAME_LENGTH
    __it: int = 0

    @property
    def mems_number( self ) -> int:
        """ Get the active MEMs number """
        return len( self.__mems )
    
    @property
    def available_mems_number( self ) -> int:
        """ Get the available MEMs number """
        return len( self.__available_mems )

    @property
    def analogs_number( self ) -> int:
        """ Get the active analogs number """
        return len( self.__analogs )
    
    @property
    def available_analogs_number( self ) -> int:
        """ Get the available analogs number """
        return len( self.__available_analogs )
    
    @property
    def mems_position( self ) -> np.ndarray | None:
        """ Get the antenna mems positions
        
        Returns
        -------
            mems_position : np.ndarray | None
                array of 3D MEMs positions  
        """
        return self.__mems_position
    
    @property
    def frame_length( self ) -> int:
        """ Get the output frames length """
        return self.__frame_length

    
    @property
    def sampling_frequency( self ) -> float:
        """ Get the antenna current sampling frequency """
        return self.__sampling_frequency
    

    def __init__( self, available_mems_number:int|None=None, mems_position:np.ndarray|None=None, unit: str|None=None ):
        """Create an antenna object

        One of the two MEMs parameters (`available_mems_number` or `mems_position`) should be given. 

        Parameters:
        -----------
        available_mems_number : int | None
            The total number of MEMs composing the antenna
        mems_position : np.ndarray | None
            The positions of the MEMs relative to the center of the antenna
        unit : str | None
            The unit used for mems_position ("meters", "centimeters", "millimeters"), default is "meters"
        """

        if available_mems_number is None and mems_position is None:
            raise Exception( f"At least one of the two parameters `available_mems_number` or `mems_position` should be given" )
        elif mems_position is not None:
            self.__mems_position = mems_position
            self.__available_mems = [i for i in range( len( mems_position ) )]
        else:
            self.__mems_position = None
            self.__available_mems = [i for i in range( available_mems_number )]

    def setFrameLength( self, frame_length: int ):
        """ Set the output frame length in samples number 
        
        Parameters:
        -----------
        frame_length : int
            the frame length in samples number
        """

        self.__frame_length = frame_length


    def setSamplingFrequency( self, sampling_frequency: float ):
        """ Set the antenna sampling frequency
        
        Parameters:
        -----------
        sampling_frequency : float
            The sampling frequency (default is given by DEFAULT_SAMPLING_FREQUENCY)
        """

        self.__frame_length = sampling_frequency


    def setActiveMems( self, mems: tuple ):
        """ Activate mems

        Parameters:
        -----------
        mems : tuple
            list or tuple of mems number to activate
        """

        # Check if activated MEMs are available. Raise an exception if not
        if False in np.isin( mems, self.__available_mems ):
            mask = np.logical_not( np.isin( mems, self.__available_mems ) )
            raise Exception( f"Some activated microphones ({mems[mask]}) are not available on antenna.")

        self.__mems = mems


    def __iter__( self ):
        """ Init iterations over the antenna data """

        self.__it = 0
        return self

    def __next__( self ) -> np.ndarray :
        """ next iteration over the antenna data 

        Note that as MemsArray is a base class without any data inside, one can only return zeros filled data
        """

        self.__it += 1
        return np.zeros( ( self.mems_number, self.__frame_length ) )
