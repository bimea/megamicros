# Megamicros_tools.acoustics.antenna.py
#
# Copyright (c) 2024 Bimea
# Author: bruno.gas@bimea.io
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

""" Provide antenna definitions

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.bimea.io
"""

import numpy as np
from scipy.spatial.distance import cdist
from megamicros.log import log
from megamicros.exception import MuException


"""
Declare the square antenna of 32 mems used for the Mosellerie and Le Prehaut POCs 

vue de dessus


                  (back)
      24  25  26  27  28  29  30  31

                    F3
     --x---x---x---x---x---x---x---x--
7    x(0) (1) (...)              (0) x    16
     |                               | 
6    x                           (1) x    17
     |                               |
5    x                         (...) x    18
     |                               |
4    x                               x    19
  F0 |                               |  F2
3    x                               x    20
     |                               |
2    x (...)                         x    21
     |                               |
1    x (1)                           x    22
     |                               |
0    x (0)              (...) (1) (0)x    23
     --x---x---x---x---x---x---x---x--
  (0,0)             F1

       15  14  13  12  11  10  9   8              
                    !
                    !
                    !
              vers la porte (front)

MEMs numbering:
F0: 0,1,2,3,4,5,6,7
F1: 8, 9, 10, 11, 12, 13, 14, 15
F2: 16, 17, 18, 19, 20, 21, 22, 23
F3: 24, 25, 26, 27, 28, 29, 30, 31
"""


Mu32_Mems32_JetsonNano_0001 = {
    "name": "Mu32_Mems32_JetsonNano_0001",
    "mems": list( np.array( [
        [0, 3.82, 0], [0, 9.82, 0], [0, 15.82, 0], [0,  21.82, 0], [0,  27.82, 0], [0, 33.82, 0], [0, 39.82, 0], [0, 45.82, 0],
        [45.81, 0, 0], [39.81, 0, 0], [33.81, 0, 0], [27.81, 0, 0], [21.81, 0, 0], [15.81, 0, 0], [9.81, 0, 0] , [3.81, 0, 0],
        [49.63, 45.82, 0], [49.63, 39.82, 0], [49.63, 33.82, 0], [49.63,  27.82, 0], [49.63,  21.82, 0], [49.63, 15.82, 0], [49.63, 9.82, 0], [49.63, 3.82, 0],
        [3.81, 49.63, 0], [9.81, 49.63, 0], [15.81, 49.63, 0], [21.81, 49.63, 0], [27.81, 49.63, 0], [33.81, 49.63, 0], [39.81, 49.63, 0], [45.81, 49.63, 0]
    ] )/100 - 0.25 ),
    "comment": "Square antenna dimensions used in Lepreau experiments",
    "unit": "m",
}


def gen_circular( radius: float, mems_number: int, center: np.ndarray=[0,0,0], plane: str="XY" ):
    """ Generate a circular antenna

    Parameters
    ----------
    radius: float
        The radius of the circular antenna
    mems_number: int
        The number of MEMs in the circular antenna
    center: np.ndarray
        The center of the circular antenna
    plane: str
        The plane of the circular antenna. Default is "XY"

    Returns
    -------
    circular_antenna: dict
        The circular antenna
    """
    if plane == "XY":
        angle = np.linspace( 0, 2*np.pi, mems_number, endpoint=False )
        circular_antenna = {
            "name": "circular_antenna",
            "mems": list( np.array( [ center[0] + radius * np.cos( angle ), center[1] + radius * np.sin( angle ), np.zeros( mems_number ) ] ).T ),
            "comment": "Circular antenna",
            "unit": "m",
        }
    else:
        raise MuException( "The plane is not yet implemented" )
    
    return circular_antenna


def gen_helicoidal( radius: float, mems_number: int, center: np.ndarray=[0,0,0], laps: float=2, plane: str="XY" ):
    """ Generate a helicoidal antenna

    Parameters
    ----------
    radius: float
        The radius of the helicoidal antenna
    mems_number: int
        The number of MEMs in the helicoidal antenna
    center: np.ndarray
        The center of the helicoidal antenna
    laps: float
        NUmber of laps to be completed. Default is 2
    plane: str
        The plane of the helicoidal antenna. Default is "XY"

    Returns
    -------
    helicoidal_antenna: dict
        The helicoidal antenna
    """
    if plane == "XY":
        angle = np.linspace( 0, 2*np.pi*laps, mems_number, endpoint=False )
        radius = np.linspace( 0, radius, mems_number, endpoint=False )
        helicoidal_antenna = {
            "name": "helicoidal_antenna",
            "mems": list( np.array( [ center[0] + radius * np.cos( angle ), center[1] + radius * np.sin( angle ), np.zeros( mems_number ) ] ).T ),
            "comment": "Helicoidal antenna",
            "unit": "m",
        }
    else:
        raise MuException( "The plane is not yet implemented" )
    
    return helicoidal_antenna




"""
antenna= {'positions': np.array(
[[-0.2261063,  -0.2217998,   0.        ],
[-0.2231343,  -0.16230868,  0.        ],
[-0.23502814,  0.01106646,  0.        ],
[-0.23505722,  0.07143718,  0.        ],
[-0.23869585,  0.13492614,  0.        ],
[-0.241065,    0.19720244,  0.        ],
[-0.20675762,  0.23860315,  0.        ],
[-0.14724884,  0.23868911,  0.        ],
[-0.08815056,  0.23800337,  0.        ],
[-0.02524838,  0.23605316,  0.        ],
[ 0.03711273,  0.23184893,  0.        ],
[ 0.09778664,  0.22929929,  0.        ],
[ 0.20982932,  0.21545461,  0.        ],
[ 0.25022585,  0.17556075,  0.        ],
[ 0.24945468,  0.11548598,  0.        ],
[ 0.2482488,   0.05719138,  0.        ],
[ 0.25352816,  0.00069583,  0.        ],
[ 0.25355045, -0.17305451,  0.        ],
[ 0.26728441, -0.23428049,  0.        ],
[ 0.23313417, -0.27617064,  0.        ],
[ 0.16906521, -0.27623144,  0.        ],
[-0.01177931, -0.2639107,   0.        ],
[-0.0767392,  -0.26609785,  0.        ],
[-0.13061677, -0.26229372,  0.        ],
[-0.18359293, -0.25536996,  0.        ]] ),
'mems':[0,1,4,5,6,7,8,9,10,11,12,13,15,16,17,18,19,22,23,24,25,28,29,30,31],
'available_mems': [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31]
}
np.save( 'Antenna-square-JetsonNano-0001.npy', antenna )
"""

