import sys
sys.path.append( '../src' )

import numpy as np
import argparse
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from queue import Empty
from megamicros_tools.log import log
from megamicros.core.mu import Megamicros

welcome_msg = '-'*20 + '\n' + 'db_audio program\n \
Copyright (C) 2023  Sorbonne University\n \
This program comes with ABSOLUTELY NO WARRANTY; for details see the source code\'.\n \
This is free software, and you are welcome to redistribute it\n \
under certain conditions; see the source code for details.\n' + '-'*20

DEFAULT_DURATION = 1
FRAME_LENGTH = 512
DEFAULT_MEMS_NUMBER = 1
DEFAULT_SAMPLING_FREQUENCY = 50000

def main():
    duration, mems_number, sampling_frequency = arg_parse()

    # Define an empty antenna
    antenna = Megamicros()

    # Set the 32 available MEMs
    mems = [i for i in range(mems_number)]
    antenna.setAvailableMems( mems )

    # init PyQtgraph
    win = pg.GraphicsLayoutWidget(show=True, title="Plotting database signals")
    win.resize(1000,600)
    win.setWindowTitle('Plotting database signals')
    pg.setConfigOptions(antialias=True)
    graph = win.addPlot(title="Microphones")
    graph.setYRange(-5,5, padding=0, update = False)
    curves = []
    for s in range( mems_number ):
        curves.append( graph.plot(pen='y' ) )

    # Set the Qt timer
    timer = QtCore.QTimer()
    timer.timeout.connect( lambda: plot_on_the_fly( antenna, curves ) )

    antenna.run( 
        mems=mems,						                        # activated mems
        duration=duration,
        sampling_frequency=sampling_frequency,					# sampling frequency
        counter = False,
        counter_skip=False, 
        status=False,
        buffer_length=FRAME_LENGTH,
        queue_maxsize=32,
        queue_size=1,
    )

    # Start and set the timer period in milliseconds
    timer.start( 5 )

    input( "Press [Return] key to stop...\n" )

    timer.stop()
    antenna.stop()
    antenna.wait()


def plot_on_the_fly( antenna: Megamicros, curves ):
    """ Get last queued signal and plot it

    Parameters
    ----------
    antenna: MemsArrayWS
        The remote antenna
    curves: 
        PyQtGraph curves
    """

    try:
        data = antenna.queue.get( block=True, timeout=1 )
    except Empty:
        return

    t = np.arange( np.size( data, 1 ) )/antenna.sampling_frequency
    for s in range( antenna.mems_number ):
        curves[s].setData( t, ( data[s,:] * antenna.sensibility ) + s - antenna.mems_number/2 )



def arg_parse() -> tuple:

    print( welcome_msg )

    parser = argparse.ArgumentParser()
    parser.add_argument( "-D", "--duration", help=f"set the duration. Default is {DEFAULT_DURATION}" )
    parser.add_argument( "-N", "--mems-number", help=f"activates MEMs from 0 to N-1. Default is {1}" )
    parser.add_argument( "-F", "--sampling-frequency", help=f"Sampling frequency. Default is {DEFAULT_SAMPLING_FREQUENCY} kHz" )

    args = parser.parse_args()

    duration = DEFAULT_DURATION
    mems_number = DEFAULT_MEMS_NUMBER
    sampling_frequency = DEFAULT_SAMPLING_FREQUENCY

    if args.mems_number:
        mems_number = int( args.mems_number )
        if mems_number <= 0:
            log.error( "The number of MEMs should be greater than 0." )
            sys.exit(1)
    if args.duration:
        duration = int( args.duration )
    if args.sampling_frequency:
        sampling_frequency = float( args.sampling_frequency )

    return duration, mems_number, sampling_frequency


if __name__ == "__main__":
	main()

