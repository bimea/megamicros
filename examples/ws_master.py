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

    # Define the antenna
    try:
        antenna = MemsArrayWS( host, port=port )
    except Exception as e:
        print( f"Failed: {e}" )


    # Perform an antenna settings
    antenna.settings()

    # Print some results
    print( f"Available mems: {antenna.available_mems}" )
    print( f"Available analogs: {antenna.available_analogs}" )
    print( f"Default sampling freequency: {antenna.sampling_frequency} Hz" )

    # Perform an antenna selftest
    antenna.selftest()

    # getting some antenna settings
    print( f"Available mems: {antenna.available_mems}" )
    print( f"Available analogs: {antenna.available_analogs}" )
    print( f"Default sampling freequency: {antenna.sampling_frequency} Hz" )

    # Run the master
    antenna.run(
        mems = [0, 1, 2, 3, 4, 5, 6, 7],
        duration=0,
        frame_length=512,
        signal_q_size=0,
        sampling_frequency=10000,
        job='master', 
    )

    antenna.wait()

    # Here you can run a listener...


if __name__ == "__main__":
	main()

