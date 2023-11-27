# ws_graph.py python program example for MegaMicros antenna
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

"""
Run a remote antenna and plot data using PyQtGraph
MegaMicros documentation is available on https://readthedoc.biimea.io
"""

welcome_msg = '-'*20 + '\n' + 'db_audio program\n \
Copyright (C) 2023  Sorbonne University\n \
This program comes with ABSOLUTELY NO WARRANTY; for details see the source code\'.\n \
This is free software, and you are welcome to redistribute it\n \
under certain conditions; see the source code for details.\n' + '-'*20

import numpy as np
import queue
import argparse
import matplotlib.pyplot as plt
from megamicros.log import log
from megamicros.core.ws import MemsArrayWS
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

log.setLevel( "INFO" )


MEMS = (2, 4)					# the two Mu32 antenna microphones used
DEFAULT_DURATION = 0					# Time recording in seconds. 0 means infinite acquisition loop: use Ctrl C for stopping
DEFAULT_HOST = 'localhost'      # server host  
DEFAULT_HOST = 'parisparc.biimea.tech'      # server host  
DEFAULT_PORT = 9002               # server port
FRAME_LENGTH = 512					# Number of stereo samples per block.


def main():

    host, port, duration = arg_parse()

    # Define the antenna
    try:
        antenna = MemsArrayWS( host=host, port=port )
    except Exception as e:
        print( f"Failed: {e}" )


    # init PyQtgraph
    win = pg.GraphicsLayoutWidget(show=True, title="Plotting database signals")
    win.resize(1000,600)
    win.setWindowTitle('Plotting database signals')
    pg.setConfigOptions(antialias=True)
    graph = win.addPlot(title="Microphones")
    graph.setYRange(-5,5, padding=0, update = False)
    curves = []
    for s in range( len( MEMS ) ):
        curves.append( graph.plot(pen='y' ) )

    # Set the Qt timer
    timer = QtCore.QTimer()
    timer.timeout.connect( lambda: plot_on_the_fly( antenna, curves ) )

    antenna.run( 
        mems=MEMS,									# activated mems
        duration=duration,
        sampling_frequency=20000,					# sampling frequency
        buffer_length=FRAME_LENGTH,
        signal_q_size=0,
        counter = False
    )

    # Start and set the timer period in milliseconds
    timer.start( 1 )

    input( "Press [Return] key to stop...\n" )

    timer.stop()
    antenna.wait()




def plot_on_the_fly( antenna, curves ):
    """ Get last queued signal and plot it

    Parameters
    ----------
    antenna: MemsArrayWS
        The remote antenna
    curves: 
        PyQtGraph curves
    """

    try:
        data = antenna.signal_q.get( timeout=1 )
    except queue.Empty:
        return

    t = np.arange( np.size( data, 1 ) )/antenna.sampling_frequency
    for s in range( antenna.mems_number ):
        curves[s].setData( t, ( data[s,:] * antenna.sensibility ) + s - antenna.mems_number/2 )


def arg_parse() -> tuple:

    print( welcome_msg )

    parser = argparse.ArgumentParser()
    parser.add_argument( "-n", "--host", help=f"set the server network host name or ip address. Default is {DEFAULT_HOST}" )
    parser.add_argument( "-p", "--port", help=f"set the server listening port. Default is {DEFAULT_PORT}" )
    parser.add_argument( "-D", "--duration", help=f"set the duration. Default is {DEFAULT_DURATION}" )

    args = parser.parse_args()

    host = DEFAULT_HOST
    port = DEFAULT_PORT
    duration = DEFAULT_DURATION

    if args.host:
        host = args.host
    if args.port:
        port = int( args.port )
    if args.duration:
        duration = int( args.duration )

    return host, port, duration


if __name__ == "__main__":
	main()

