# db_slave.py python program example for MegaMicros antenna
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
Run a remote antenna as a slave client for getting and hearing signals

MegaMicros documentation is available on https://readthedoc.biimea.io
"""

welcome_msg = '-'*20 + '\n' + 'db_audio program\n \
Copyright (C) 2023  Sorbonne University\n \
This program comes with ABSOLUTELY NO WARRANTY; for details see the source code\'.\n \
This is free software, and you are welcome to redistribute it\n \
under certain conditions; see the source code for details.\n' + '-'*20


import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
import pyaudio
import queue

from megamicros.log import log
from megamicros.core.ws import MemsArrayWS


MEMS = (2, 4)					# the two Mu32 antenna microphones used
DURATION = 0					# Time recording in seconds. 0 means infinite acquisition loop: use Ctrl C for stopping
DEFAULT_HOST = 'localhost'      # server host  
DEFAULT_PORT = 9002               # server port
FRAME_LENGTH = 256					# Number of stereo samples per block.


log.setLevel( "INFO" )

def arg_parse() -> tuple:

    parser = argparse.ArgumentParser()
    parser.add_argument( "-n", "--host", help=f"set the server network host name or ip address. Default is {DEFAULT_HOST}" )
    parser.add_argument( "-p", "--port", help=f"set the server listening port. Default is {DEFAULT_PORT}" )
    parser.add_argument( "-D", "--duration", help=f"set the duration. Default is {DURATION}" )

    args = parser.parse_args()

    host = DEFAULT_HOST
    port = DEFAULT_PORT
    duration = DURATION

    if args.host:
        host = args.host
    if args.port:
        port = int( args.port )
    if args.duration:
        duration = int( args.duration )

    return host, port, duration


def main():

    host, port, duration = arg_parse()

    print( welcome_msg )

    try:

        # Define the antenna
        antenna = MemsArrayWS( host, port=port )

        # 2 seconds run, getting signals from MEMs 1 and 2
        antenna.run(
            mems = [1, 2],
            duration=2,
            buffer_length=512,
            signal_q_size = 0,
            job='listen'
        )

        # Init a np.ndarray
        signals = np.ndarray( (0, antenna.channels_number ) )

        # Get signals
        for data in antenna:
            signals = np.concatenate( ( signals, data ), axis=0 )

        # waiting for the end of the running thread is mandatory
        antenna.wait()
        print( f"exit from loop. Signal shape is: {np.shape( signals )}" )


        # plot signals
        time = np.array( range( np.size(signals,0) ) )/antenna.sampling_frequency
        fig, axs = plt.subplots( antenna.channels_number )
        fig.suptitle('Channels activity')	
        for s in range( antenna.channels_number ):
            axs[s].plot( time, signals[:,s] )
            axs[s].set( xlabel='time in seconds', ylabel='channel %d' % s )

        plt.show()


    except Exception as e:
        print( f"error ({type(e).__name__}): {e}" )
    except:
        print( 'Unexpected exception: ', sys.exc_info()[0] )



if __name__ == "__main__":
	main()
