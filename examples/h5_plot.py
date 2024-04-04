# h5_plot.py python program example for MegaMicros antenna
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
Run a H5 antenna and plot data using matplotlib
MegaMicros documentation is available on https://readthedoc.bimea.io
"""

welcome_msg = '-'*20 + '\n' + 'h5_plot program\n \
Copyright (C) 2023  Sorbonne University\n \
This program comes with ABSOLUTELY NO WARRANTY; for details see the source code\'.\n \
This is free software, and you are welcome to redistribute it\n \
under certain conditions; see the source code for details.\n' + '-'*20

import sys
sys.path.append( '../src' )

import numpy as np
import argparse
import matplotlib.pyplot as plt
from megamicros_tools.log import log
from megamicros.core.h5 import MemsArrayH5

log.setLevel( "INFO" )


DEFAULT_DURATION = 1					# Time recording in seconds. 0 means infinite acquisition loop: use Ctrl C for stopping
DEFAULT_FILENAME = "test.h5"

def main():

    filename, duration = arg_parse()

    # Define the antenna
    try:
        antenna_h5 = MemsArrayH5( 
            filename=filename,
        )
    except Exception as e:
        print( f"Failed: {e}" )
    
    print( f"Sampling frequency: {antenna_h5.sampling_frequency}Hz" )
    print( f"Channels number: {antenna_h5.mems_number}" )
    print( f"Available MEMs number: {antenna_h5.available_mems_number}" )
    print( f"Available MEMs: {antenna_h5.available_mems}" )
    print( f"Whether counter is available or not: {antenna_h5.counter}" )
    print( f"Dataset(s) number: " + str(antenna_h5.dataset_number) )

    # Choose MEMS to plot
    MEMS = antenna_h5.available_mems

    # Init a np.ndarray
    signals = np.ndarray( (0, len(MEMS) ) )

    # Run the H5 antenna
    antenna_h5.run( 
        duration=1, 
        mems = MEMS,
        real_time=False,
    )

    # Get signals
    for data in antenna_h5:
        signals = np.concatenate( ( signals, data ), axis=0 )

    # waiting for the end of the running thread is mandatory
    antenna_h5.wait()
    print( f"exit from loop. Signal shape is: {np.shape( signals )}" )

    # plot signals
    time = np.array( range( np.size(signals,0) ) )/antenna_h5.sampling_frequency
    #time = np.array( range( 1000 ) )/antenna_h5.sampling_frequency
    fig, axs = plt.subplots( antenna_h5.channels_number )
    fig.suptitle('Channels activity')	
    for s in range( antenna_h5.channels_number ):
        axs[s].plot( time, signals[:len(time),s] )
        axs[s].set( xlabel='time in seconds', ylabel='channel %d' % s )

    plt.show()



def arg_parse() -> tuple:

    print( welcome_msg )

    parser = argparse.ArgumentParser()
    parser.add_argument( "-F", "--filename", help=f"H5 filename. Default is {DEFAULT_FILENAME}" )
    parser.add_argument( "-D", "--duration", help=f"set the duration. Default is {DEFAULT_DURATION}" )

    args = parser.parse_args()

    filename = DEFAULT_FILENAME
    duration = DEFAULT_DURATION

    if args.filename:
        host = args.filename
    if args.duration:
        duration = int( args.duration )

    return filename, duration


if __name__ == "__main__":
	main()

