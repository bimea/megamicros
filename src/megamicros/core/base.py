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
    __mems_position: np.ndarray

    @property
    def mems_number( self ) -> int:
        """ Get the MEMs number """
        return len( self.__mems_position )
    
    @property
    def mems_position( self ) -> np.ndarray:
        """ Get the antenna mems positions
        
        Returns
        -------
            mems_position : np.ndarray
                array of 3D MEMs positions  
        """
        return self.__mems_position