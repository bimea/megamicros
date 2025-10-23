# megamicros.acoustics.location.py
#
# ® Copyright 2023-2025 Bimea
# Author: bruno.gas@bimea.io
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
from ..log import log

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
    
    @property
    def antennas_position( self ) -> list:
        """ Get the antenna positions as a list of np.array 3D positions """
        return self.__antennas_position


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

    def removeAntennas(self) -> None:
        """ Remove all antennas
        """
        self.__antennas_position = []
        log.info( 'All antennas removed' )  


class Locator2D( Locator ):
    """ Predictor2D class for 2D localization prediction
    """

    __antennas_focal: list
    __sampling_mode: str
    __boxes: list               # [center_x, center_y, width, depth, lower_left_x, lower_left_y, upper_right_x, upper_right_y]
    
    def __init__( self, room_width: float, room_depth: float, room_height: float ) -> None:
        super().__init__( room_width, room_depth, room_height )
        self.__antennas_focal = []
        self.__sampling_mode = None
        self.__boxes = []
        log.info( 'Localization Predictor2D object initialized' )

    @property
    def antennas_focal( self ) -> list:
        """ Get the antenna positions as a list of np.array 3D positions """
        return self.__antennas_focal
    
    @property
    def boxes( self ) -> list:
        """ Get the boxes positions as a list of np.array 2D positions """
        return self.__boxes

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
        if len( self.__antennas_focal ) > 0:
            raise ValueError( f'Sorry, multiple antennas is not implemented yet' )

        super().addAntenna( position )
        self.__antennas_focal.append( {
            'plan_width': focal_width, 
            'plan_depth': focal_depth, 
        } )
        log.info( f'Antenna added in room with focal {focal_width} x {focal_depth} meters' )


    def removeAntennas(self) -> None:
        """ Remove all antennas
        """
        super().removeAntennas()
        self.__antennas_focal = []
        log.info( 'All antennas focal properties removed' )
    
    def addBoxSampling( self, n_x: int, n_y: int, c_x: float, c_y: float, width: float, depth: float ) -> None:
        """ Generate a box sampling using centers of boxes as sampling points.
        This sampling can be added to an existing one.

        Parameters
        ----------
        * n_x: int
            The number of boxes in x
        * n_y: int
            The number of boxes in y
        * c_x: float
            The center of the first box in x
        * c_y: float
            The center of the first box in y
        * width: float
            The width of the boxes in meters
        * depth: float
            The depth of the boxes in meters
        """
        self.__sampling_mode = 'box'

        half_width = width / 2
        half_depth = depth / 2
        for i in range( n_x ):
            for j in range( n_y ):
                self.__boxes.append( np.array( [
                    c_x + i*width, c_y + j*depth, 
                    width, depth, 
                    c_x + i*width - half_width, c_y + j*depth - half_depth, c_x + i*width + half_width, c_y + j*depth + half_depth
                ]) )

        log.info( f'Box sampling added with {n_x}x{n_y} boxes of {width} x {depth} meters' )

    def getLocationsNumber( self ):
        """ Get the number of locations in the sampling
        """
        if self.__sampling_mode == 'box':
            return len( self.__boxes )
        else:
            log.warning( f'Sampling mode {self.__sampling_mode} undefined. Cannot get the number of locations' )
            return 0
        
    def locateFromBFE( self, BFE: np.ndarray, sampling_x: int, sampling_y: int ) -> np.ndarray:
        """ Locate a source from BFE signals
        Parameters
        ----------
        BFE : np.ndarray
            The BFE signals
        sampling_x : int
            The number of sampling points in x
        sampling_y : int
            The number of sampling points in y
        """

        # Get the maximum value and max indice of BFE:
        max_value = np.max( BFE )
        max_indice = np.argmax( BFE )

        # Get corresponding BFE grid coordinates (on the antenna focal plan) of the maximum value
        x_focal = max_indice % sampling_x
        y_focal = max_indice // sampling_x

        # Get the corresponding position in metric space depending on the antenna focal covering 
        delta_focal_width = self.__antennas_focal[0]['plan_width'] / sampling_x
        delta_focal_depth = self.__antennas_focal[0]['plan_depth'] / sampling_y
        x = self.antennas_position[0][0] - self.__antennas_focal[0]['plan_width']/2 + x_focal * delta_focal_width + delta_focal_width/2
        y = self.antennas_position[0][1] - self.__antennas_focal[0]['plan_depth']/2 + y_focal * delta_focal_depth + delta_focal_depth/2

        # Find the first box containing the point
        box_index = -2
        if self.__sampling_mode == 'box':
            for index, box in enumerate( self.__boxes ):
                if x >= box[4] and x <= box[6] and y >= box[5] and y <= box[7]:
                    box_index = index
                    break
        else:
            log.warning( f'Sampling mode {self.__sampling_mode} undefined. Cannot locate the source' )

        return box_index


    def roomPlot( self, room_view: bool=False, ax: plt.Axes=None ) -> plt.Axes:
        """ Plot the room with antennas and sampling points
        """

        # Create the figure and the axes if not provided
        if ax is None:
            _, ax = plt.subplots()

        xticks = np.linspace( 0, self.room_width, 10 )
        xticks_number = len( xticks )
        yticks = np.linspace( 0, self.room_depth, 10 )
        yticks_number = len( yticks )
        ax.set_xticks( xticks, labels=np.array( [i for i in range( xticks_number )] )*self.room_width//(xticks_number-1) )
        ax.set_yticks( yticks, labels=np.array( [i for i in range( yticks_number )] )*self.room_depth//(yticks_number-1) )

        # Force same unit size on both x and y axis and add the room if requested
        ax.set_aspect('equal')
        if room_view:
            ax.add_patch( Rectangle( ( 0, 0 ), self.room_width, self.room_depth, fill=False, edgecolor='blue' ) )

        # Add antennas if any
        for a in range( len( self.antennas_position ) ):
            ax.add_patch( Rectangle( 
                ( self.antennas_position[a][0]-self.antennas_focal[a]['plan_width']/2, self.antennas_position[a][1]-self.antennas_focal[a]['plan_depth']/2 ),
                self.antennas_focal[a]['plan_width'], self.antennas_focal[a]['plan_depth'], fill=True, edgecolor='lightgrey', facecolor='lightgrey'
            ) )
            ax.scatter( self.antennas_position[a][0], self.antennas_position[a][1], color='orange', marker='^' )

        # Add boxes if any
        if self.__sampling_mode == 'box':
            for box in self.__boxes:
                ax.add_patch( Rectangle( ( box[4], box[5] ), box[2], box[3], fill=False, edgecolor='red' ) )
                
        return ax
    
    def locationsDisplay( self, locations: list | tuple, ax: plt.Axes=None ) -> plt.Axes:
        """
        Display the predicted locations on an horizontal activity bar
        """

        size_x = len( locations )
        size_y = self.getLocationsNumber()
        image = np.zeros( ( size_y, size_x ) )
        dx = 5
        dy = 20

        # Create the figure and the axes
        if ax is None:
            ax = plt.subplots()
        xticks = np.linspace( 0, len( locations ) * dx, 10 )
        xticks_number = len( xticks )
        yticks = np.linspace( 0, self.getLocationsNumber() * dy, self.getLocationsNumber() )
        yticks_number = len( yticks )
        ax.set_xticks( xticks, labels=np.array( [i for i in range( xticks_number )] )*len( locations )//(xticks_number-1) )
        ax.set_yticks( yticks, labels=np.array( [i for i in range( yticks_number )] ) )

        # Set a blue rectangle for the frame
        ax.add_patch( Rectangle( ( 0, 0 ), size_x * dx, size_y * dy, fill=False, edgecolor='blue' ) )
        
        # Add separation lines
        for j in range( size_y ):
            ax.axhline(y=j*dy, color='grey', linestyle='--', linewidth=0.5)

        # Draw the locations
        for i in range( size_x ):
            if locations[i] >= 0:
                # print( f'Location {i} at {locations[i]}, Rectangle = ', ( i*dx, locations[i]*dy ), dx, dy )
                ax.add_patch( Rectangle( 
                    ( i*dx, locations[i]*dy ), dx, dy, 
                    fill=True, 
                    edgecolor='red', 
                    facecolor='red'
                ) )
        
        return ax