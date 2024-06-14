# bmfcheck.py python program example for MegaMicros devices 
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

"""
Python interface to the app_bmfcheck application of the Megamicros IOT server

Megamicros documentation is available on https://readthedoc.bimea.io
"""

welcome_msg = '-'*20 + '\n' + 'bmfcheck  program\n \
Copyright (C) 2024  Bimea\n \
This program comes with ABSOLUTELY NO WARRANTY; for details see the source code\'.\n \
This is free software, and you are welcome to redistribute it\n \
under certain conditions; see the source code for details.\n' + '-'*20

import sys
sys.path.append( 'src' )

import argparse
import numpy as np
import matplotlib.pyplot as plt
import json
from mpl_toolkits.mplot3d import Axes3D
from IPython import display
from megamicros_tools.log import log
import megamicros_tools.mqtt as mqtt

from megamicros import __version__
from megamicros.apps import welcome_msg

DEFAULT_MQTT_HOST = 'mqtt.bimea.tech'
DEFAULT_MQTT_SUB_TOPIC = 'romille/mater/1/device/mu32/poc2-2/status'

def arg_parse() -> dict:

    parser = argparse.ArgumentParser()
    parser.add_argument( "-v", "--version", help=f"print version", action='store_true' )
    parser.add_argument( "--verbose", help=f"set verbose mode on" )
    parser.add_argument( "-H", "--host", help=f"MQTT host", action='store_true' )
    parser.add_argument( "-t", "--topic", help=f"MQTT subscrib topic", action='store_true' )

    args = parser.parse_args()

    if args.version:
        print( f"megamicros {__version__}" )
        exit(0)
    
    if args.verbose:
        log.setLevel( "INFO" if args.verbose=='INFO' else "WARNING" if args.verbose=='WARNING' else "ERROR" if args.verbose=='ERROR' else "OFF" )

    if args.host:
        host = args.host
    else:
        host = DEFAULT_MQTT_HOST

    if args.topic:
        topic = args.topic
    else:
        topic = DEFAULT_MQTT_SUB_TOPIC

    return { 'host': host, 'topic': topic }


def on_message( client, userdata, msg):
    
    message = json.loads( msg.payload.decode() )

    report = None
    if 'content' in message and 'report' in message['content']:
        report = json.loads( message['content'] )['report']
    else:
        return
    
    BFE = np.array( report['BFE'] )
    mems_position =np.array( report['mems_position'] )
    locations_position = np.array( report['locations_position'] )
    sampling_frequency = report['sampling_frequency']
    frame_length = report['frame_length']
    max_energy_index = report['max_energy_index']

    # print area locations and antenna 
    fig = plt.figure()
    ax = fig.add_subplot( 131, projection='3d' )
    ax.scatter( mems_position[:,0], mems_position[:,1], mems_position[:,2] )
    ax.scatter( locations_position[:,0], locations_position[:,1], locations_position[:,2] )
    ax = fig.add_subplot( 132, projection='3d' )

    ax.set_xlabel( 'X' )
    ax.set_ylabel( 'Y' )
    ax.scatter( mems_position[:,0], mems_position[:,1], mems_position[:,2], c=np.arange(32) )
    fig.show()
    car = input( 'Press any key to continue' )

    plt.figure()
    BFE = np.reshape( BFE, (50, 50) )
    plt.xlabel('width')
    plt.ylabel('height')
    plt.imshow( BFE, origin='lower', aspect='equal')
    plt.show()
    print(BFE)
    car = input( 'Press any key to continue' )



def main():
        
        args = arg_parse()
    
        print( welcome_msg )
    
        # Connect to MQTT broker
        client = mqtt.MqttClient( host=args['host'], name='bmfcheck' )
        if not client.is_connected():
            log.error( "Failed to connect to MQTT broker" )
            exit(1)
    
        # Subscribe to MQTT topic
        client.subscribe( args['topic'] )
        log.info( f"Subscribed to topic {args['topic']}" )

        # run callback function
        try:
            client.run( args['topic'], on_message )
        except KeyboardInterrupt:
            print( "\nExiting..." )
            exit(0)


if __name__ == "__main__":
    main()
