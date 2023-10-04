# db_audio.py python program example for MegaMicro Mu32 receiver 
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
Run an antenna for getting and hearing signals comming from a database 

MegaMicros documentation is available on https://readthedoc.biimea.io

See the programm help: 
    > db_audio -h

See http://people.csail.mit.edu/hubert/pyaudio/  
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
from megamicros.core.db import MemsArrayDB


MEMS = (2, 4)					# the two Mu32 antenna microphones used
DURATION = 0					# Time recording in seconds. 0 means infinite acquisition loop: use Ctrl C for stopping
DEFAULT_HOST = 'http://dbwelfare.biimea.io/'      # server host  
DEFAULT_PORT = 80               # server port
FRAME_LENGTH = 256					# Number of stereo samples per block.
OUTPUT_DEVICE = 2               # audio device
MEMS_NUMBER = len( MEMS )
SAMPLE_WIDTH = 4
CLOCKDIV = 9	           	    # this is the max frequency
SAMPLING_FREQUENCY = 500000 / (CLOCKDIV+1)

LOGIN = 'ailab'
EMAIL = 'bruno.gas@biimea.com'
PASSWORD = '#T;uZnQ5UJ_JC~&'
FILE_ID = 1

log.setLevel( "DEBUG" )

def arg_parse() -> tuple:

    parser = argparse.ArgumentParser()
    parser.add_argument( "-n", "--host", help=f"set the server network host name or ip address. Default is {DEFAULT_HOST}" )
    parser.add_argument( "-p", "--port", help=f"set the server listening port. Default is {DEFAULT_PORT}" )
    parser.add_argument( "-D", "--duration", help=f"set the duration. Default is {DURATION}" )
    parser.add_argument( "-c", "--clockdiv", help=f"set sampling frequency from the clockdiv given value (sf=500000/(1+clockdiv)))" )

    args = parser.parse_args()

    host = DEFAULT_HOST
    port = DEFAULT_PORT
    duration = DURATION
    clockdiv = CLOCKDIV

    if args.host:
        host = args.host
    if args.port:
        port = int( args.port )
    if args.duration:
        duration = int( args.duration )
    if args.clockdiv:
        device = int( args.clockdiv )

    return host, port, duration, clockdiv


def main():

    host, port, duration, clockdiv = arg_parse()

    print( welcome_msg )

    try:
        # Instantiate Mu32ws and initialize Mu32 with host and port of remote server
        antenna = MemsArrayDB( dbhost=host, dbport=port, login=LOGIN, email=EMAIL, password=PASSWORD, file_id=FILE_ID )

        # Start running the remote Megamicros system
        antenna.run( 
            mems=MEMS,
            duration=duration,
            frame_length=FRAME_LENGTH,
            counter_skip = True,
            signal_q_size=0
        )
        
        # Instantiate PyAudio and initialize PortAudio system resources (1)
        p = pyaudio.PyAudio()

        # Open stream
        stream = p.open(
            format = pyaudio.paFloat32,
            channels = MEMS_NUMBER,
            rate = int( antenna.sampling_frequency ),
            output=True,
            frames_per_buffer=FRAME_LENGTH,
        )

        # input-output loop
        # Frames are extracted from the queue and sent to the audio output stream
        # Since we use the blocking mode rather than the callback mode, there is a minimum latency that cannot be avoided (at least equal to the frame duration).
        # ALl this stands provided the queue is not limited (signal_q_size=0).
        # Use [Ctrl][C] to stop the loop
        transfers_counter = 0
        try:
            while( True ):
                # get megamicro antenna frame from queue
                try:
                    data = antenna.signal_q.get( timeout=1 )
                except queue.Empty:
                    continue

                # change frame buffer into numpy array of int32
                data = np.frombuffer( data, dtype=np.int32 )

                # reshape MEMs signals column wise ( samples number X mems_number )
                data = np.reshape( data, ( antenna.frame_length, antenna.mems_number ) ).T

                # convert into float and normalize with MEMs sensibility
                data = ( data.astype( np.float32 ).T * antenna.sensibility )

                # write into audio stream
                stream.write( data, num_frames=FRAME_LENGTH )
                transfers_counter += 1

        except KeyboardInterrupt:
            print( f"Interrupt !" )
        except Exception as e:
            print( f"Quitting loop: {e}" )


        # Close stream and release PortAudio system resources (5)
        stream.close()            
        p.terminate()

        antenna.stop()
        antenna.wait()


    except Exception as e:
        print( 'error:', e )
    except:
        print( 'Unexpected error:', sys.exc_info()[0] )



if __name__ == "__main__":
	main()
