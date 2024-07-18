# megamicros.tools.acoustics.location.py
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

""" Define Locator classes for location prediction using BFE signals

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from megamicros.log import log

class Locator:
    """ Predictor base class for localization prediction
    """
    __room_width: float
    __room_depth: float
    __room_height: float
    __antennas_position: list


    @property
    def room_width( self ) -> float:
        """ Get the room width in meters """
        return self.__room_width
    
    @property
    def room_depth( self ) -> float:
        """ Get the room depth in meters """
        return self.__room_depth

    @property
    def room_height( self ) -> float:
        """ Get the room height in meters """
        return self.__room_height


    def __init__( self, room_width: float, room_depth: float, room_height: float ) -> None:
        self.__room_width = room_width
        self.__room_depth = room_depth
        self.__room_height = room_height
        self.__antennas_position = []
        log.info( f'Localization Predictor object initialized on room {room_width} x {room_depth} x {room_height} meters' )

    def addAntenna( self, position: list|tuple|np.ndarray ) -> None:
        """ Add an antenna in the room
        """

        if type(position) is list:
            position = np.array( position )
        elif type(position) is tuple:
            position = np.array( list( position ) )
        
        self.__antennas_position.append( position )

        if position.shape[0] != 3:
            raise ValueError( f'Invalid antenna position: {position}. Should be a 3D position' )
        
        log.info( f'Antenna added in room at position: {position}' )


class Locator2D( Locator ):
    """ Predictor2D class for 2D localization prediction
    """

    __antennas_focal: list
    __sampling_mode: str
    __boxes: list
    
    def __init__( self, room_width: float, room_depth: float, room_height: float ) -> None:
        super().__init__( room_width, room_depth, room_height )
        self.__antennas_focal = []
        self.__sampling_mode = None
        self.__boxes = []
        log.info( 'Localization Predictor2D object initialized' )


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
        log.info( f'Antenna added in room with focal {focal_width} x {focal_depth} meters' )


    def addBoxSampling( self, centers: list|tuple|np.ndarray, width: float, depth: float ) -> None:
        """ Generate a box sampling using centers of boxes as sampling points.
            This sampling can be added to an existing one.
        """
        self.__sampling_mode = 'box'

        if type( centers ) is np.ndarray or type( centers ) is tuple:
            centers = list( centers )

        half_width = width / 2
        half_depth = depth / 2
        for center in centers:
            if type( center ) is not np.ndarray or center.shape[0] != 2:
                raise ValueError( f'Invalid center: {center}. Should be a 2D position in np.ndarray type' )
            
            self.__boxes.append( np.array( [
                center[0] - half_width, 
                center[1] - half_depth, 
                width, 
                depth
            ]) )

        log.info( f'{len( centers )} box sampling added with {len(centers)} boxes of {width} x {depth} meters' )


    def roomPlot( self ):
        """ Plot the room with antennas and sampling points
        """

        # Create the figure and the axes
        fig, ax = plt.subplots()
        xticks = np.linspace( 0, self.room_width, 10 )
        xticks_number = len( xticks )
        yticks = np.linspace( 0, self.room_depth, 10 )
        yticks_number = len( yticks )
        ax.set_xticks( xticks, labels=np.array( [i for i in range( xticks_number )] )*self.room_width//(xticks_number-1) )
        ax.set_yticks( yticks, labels=np.array( [i for i in range( yticks_number )] )*self.room_depth//(yticks_number-1) )

        # Force same unit size on both x and y axis
        ax.set_aspect('equal')

        # Add boxes if any
        if self.__sampling_mode == 'box':
            for box in self.__boxes:
                ax.add_patch( Rectangle( ( box[0], box[1] ), box[2], box[3], fill=False, edgecolor='red' ) )

        return ax