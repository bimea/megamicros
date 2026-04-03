# megamicros.sources
#
# ® Copyright 2024-2026 Bimea
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

"""
Data sources module for Megamicros library.

This module provides various data source implementations that can provide
data frames to the Megamicros antenna objects.

Available sources:
    - UsbDataSource: Hardware USB device
    - H5DataSource: HDF5 file playback
    - WebSocketDataSource: Remote device over WebSocket
    - RandomDataSource: Random signal generator (for testing)
    
Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""

from .base import DataSource
#from .random import RandomDataSource
from .usb import UsbDataSource
#from .h5 import H5DataSource

__all__ = [
    'DataSource',
    'UsbDataSource',
    'H5DataSource',
    'RandomDataSource',
]
