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
    __sampling_mode: str
    __boxes: list
    
    def __init__( self ):
        self.__antennas_focal = []
        self.__sampling_mode = None
        self.__boxes = []


    def addAntenna(self, position: list | tuple | np.ndarray, focal_width: float, focal_depth: float ) -> None:
        """ Add an antenna in the room with its own focal dimensions

        Parameters
        ----------

        * position: list|tuple|np.ndarray
            The 3D position of the antenna in the room in meters
        * focal_width: float
            The width of the focal plan in meters
        * focal_depth: float
            The depth of the focal plan in meters
        """
        
        super().addAntenna( position )
        self.__antennas_focal.append( {
            'plan_width': focal_width, 
            'plan_depth': focal_depth, 
        } )


    def addBoxSampling( self, centers: list|tuple|np.ndarray, width: float, depth: float ) -> None:
        """ Generate a box sampling using centers of boxes as sampling points.
            This sampling can be added to an existing one.
        """
        self.__sampling_mode = 'box'

        if type(centers) is np.ndarray or type(centers) is tuple:
            centers = list( centers )

        self.__boxes = []
        for center in centers:
            self.__boxes.append( [center[0]*scale_width-half_width, center[1]*scale_length-half_length, width*scale_width, length*scale_length] )
