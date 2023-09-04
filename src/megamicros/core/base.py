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
    """

    __mems: tuple
    __available_mems: tuple
    __analogs: tuple
    __available_analogs: tuple
    __mems_position: np.ndarray | None

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
    
    def __init__( self, available_mems_number:int|None=None, mems_position:np.ndarray|None=None ):
        """Create an antenna object

        One of the two MEMs parameters should be given. 

        Parameters:
        -----------
        available_mems_number : int | None
            The total number of MEMs composing the antenna
        mems_position = np.ndarray | None
            The positions of the MEMs relative to the center of the antenna
        """

        if available_mems_number is None and mems_position is None:
            raise Exception( f"At least one of the two parameters `available_mems_number` or `mems_position` should be given" )
        elif mems_position is None:
            self.__mems_position = None
            self.__available_mems = [i for i in available_mems_number]
        else:
            self.__mems_position = mems_position
            self.__available_mems = [i for i in len( mems_position )]
