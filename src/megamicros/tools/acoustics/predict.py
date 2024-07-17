# megamicros.tools.acoustics.predict.py
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

""" Define Predictor classes for localization prediction

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import numpy as np

class Predictor:
    """ Predictor base class for localization prediction
    """
    __room_width: float
    __room_depth: float
    __room_height: float
    __antennas_position: list

    def __init__( self, room_width: float, room_depth: float, room_height: float ) -> None:
        self.__room_width = room_width
        self.__room_depth = room_depth
        self.__room_height = room_height
        self.__antennas_positions = []

    def addAntenna( self, position: list|tuple|np.ndarray ) -> None:
        """ Add an antenna in the room
        """

        if type(position) is list:
            self.__antennas_position.append( np.array( position ) )
        elif type(position) is tuple:
            self.__antennas_position.append( np.array( list( position ) ) )
        else:
            self.__antennas_position.append( position )


class Predictor2D( Predictor ):
    """ Predictor2D class for 2D localization prediction
    """

    __antennas_focal: list
    
    def __init__():
        pass

    def addAntenna(self, position: list | tuple | np.ndarray, focal_width: float, focal_depth: float, focal_width_sampling: float, focal_depth_sampling: float ) -> None:
        super().addAntenna( position )
        self.__antennas_focal.append( {
            'plan_width': focal_width, 
            'plan_depth': focal_depth, 
            'plan_width_sampling': focal_width_sampling, 
            'plan_depth_samplin': focal_depth_sampling
        } )
