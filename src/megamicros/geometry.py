# megamicros.tools.geometry.py python software for data processing
#
# ® Copyright 2024-2025 Bimea
# Author: bruno.gas@bimea.io
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


"""
This module provides a set of tools for defining antenna geometries.

Features:
    - Create circular antenna arrays
    - Create rectangular antenna arrays
    - Generate 3D coordinates for antenna elements
    
Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""

import numpy as np


def circle( points_number: int, radius: float, height: float, angle_offset: float, clockwise: bool ) -> list:
    """ Create a circle of MEMs positions

    Parameters
    ----------
    points_number : int
        The number of MEMs positions
    radius : float
        The radius of the circle
    height : float
        The height of the antenna
    angle_offset : float
        The angle offset in radians
    clockwise : bool
        The MEMs positions direction

    Returns
    -------
    mems_positions : list
        The MEMs positions list
    """

    mems_positions = [ [0, 0, 0] for i in range( points_number ) ]

    direction = -1. if clockwise else 1.
    for i in range( points_number ):
        angle = direction * ( 2 * np.pi * i / points_number + angle_offset ) + np.pi / 2
        x = radius * np.cos( angle )
        y = radius * np.sin( angle )
        z = height
        mems_positions[i] = [x, y, z]

    return mems_positions

def horizontalPlan( width: float, depth: float, height: float, n_width: int, n_depth: int ) -> list:
    """ Create a horizontal plan of locations

    Parameters
    ----------
    width : float
        The width of the plan
    depth : float
        The depth of the plan
    height : float
        The height of the plan
    n_width : int
        The number of MEMs positions in width
    n_depth : int
        The number of MEMs positions in depth

    Returns
    -------
    locations : list
        The locations list
    """

    locations = [ [0, 0, 0] for i in range( n_width * n_depth ) ]

    step_width = width / n_width
    step_depth = depth / n_depth

    for i in range( n_depth ):
        for j in range( n_width ):
            x = j * step_width - width/2
            y = i * step_depth - depth/2
            z = height
            locations[i*n_width + j] = [x, y, z]

    return locations
