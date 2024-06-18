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
DEFAULT_MQTT_SUB_TOPIC = 'romille/mater/1/device/mu32/poc2-1/status'

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
    
    if report['app'] == 'bmfcheck':

        BFE = np.array( report['BFE'] )
        mems_position =np.array( report['mems_position'] )
        locations_position = np.array( report['locations_position'] )
        n_x = report['n_width']
        n_y = report['n_depth']
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
        BFE = np.reshape( BFE, (n_x, n_y) )
        plt.xlabel('width')
        plt.ylabel('height')
        plt.imshow( BFE, origin='lower', aspect='equal')
        plt.show()
        print(BFE)
        car = input( 'Press any key to continue' )

    elif report['app'] == 'bmfsim':

        # Load P1-2 data
        data = np.load( 'P2.npy' )
        print( 'P2=', data)

        # Get data from server
        BFE = np.array( report['BFE'] )
        max_energy_index = report['max_energy_index']
        mems_number = report['mems_number']
        mems_position =np.array( report['mems_position'] )
        locations_position = np.array( report['locations_position'] )
        width = report['width']
        depth = report['depth']
        n_x = report['n_width']
        n_y = report['n_depth']
        sampling_frequency = report['sampling_frequency']
        frame_length = report['frame_length']
        source_position = np.array( report['source_position'] )
        source_frequency = np.array( report['source_frequency'] )
        D = np.array( report['D'] )

        # show antenna and locations
        fig = plt.figure()

        # print antenna
        ax = fig.add_subplot( 121, projection='3d' )
        ax.set_xlabel( 'Width' )
        ax.set_ylabel( 'Depth' )
        ax.scatter( mems_position[:,0], mems_position[:,1], mems_position[:,2], c=np.arange(32) )

        # print locations
        ax = fig.add_subplot( 122, projection='3d' )
        ax.set_aspect('equal')
        ax.scatter( mems_position[:,0], mems_position[:,1], mems_position[:,2], c=np.arange(32) )
        ax.scatter( locations_position[:,0], locations_position[:,1], locations_position[:,2], 'ob' )
        ax.set_xlabel( 'Width' )
        ax.set_ylabel( 'Depth' )
        fig.show()
        #input( 'Press any key to continue' )

        # Print BFE
        fig2 = plt.figure()
        ax = fig2.add_subplot(111)
        BFEimg = np.reshape(BFE, (n_y, n_x) )
        BFE_max_index = np.argmax( BFE )
        BFE_max_position = locations_position[BFE_max_index,:]
        XM = BFE_max_position[0]
        YM = BFE_max_position[1]
        print( 'Source position:', source_position)
        print( 'BFE_max_index=', BFE_max_index)
        print( 'BFE_max_position=', BFE_max_position)
        Xsource = source_position[0]
        Ysource = source_position[1]
        xs = np.arange( -width/2, +width/2, width/n_x )
        ys = np.arange( -depth/2, +depth/2, depth/n_y )
        ax.imshow( BFEimg, extent=[ xs[0], xs[-1], ys[-1], ys[0] ], cmap='Greys_r', origin='upper')
        ax.contourf( BFEimg, 20, extent=[ xs[0], xs[-1], ys[-1], ys[0] ], cmap='Greys_r', origin='upper' )
        ax.contour( BFEimg, 20, extent=[ xs[0], xs[-1], ys[-1], ys[0] ], origin='upper' )
        ax.scatter( XM, YM, c='r' )
        ax.scatter( Xsource, Ysource, c='y' )
        ax.grid( True )
        ax.set_aspect('equal')
        ax.set_xlabel( 'x [m]' )
        ax.set_ylabel( 'y [m]' )
        ax.invert_yaxis()
        fig2.show()

        # Print matrix distances
        #fig3 = plt.figure()
        #print( "D=", D)
        #print( "D.shape=", np.shape(D) )
        #print( "Distance min: ", np.min( D ) )
        #print( "Distance max: ", np.max( D ) )
        #plt.pcolormesh( D )
        #fig3.show()

        input( 'Press any key to continue' )




        """
        # print BFE indexes
        fig2 = plt.figure()
        plt.xlabel('location index')
        plt.ylabel('prediction index')
        plt.plot( BFE_index )
        fig2.show()
        #input( 'Press any key to continue' )

        # print signals
        t = np.array( [i for i in range( frame_length )] ) * 1000 / sampling_frequency
        fig3 = plt.figure(3)
        plt.plot( t, channel_1_signal, t, channel_2_signal )
        fig3.show()
        #input( 'Press any key to continue' )

        fig4 = plt.figure()
        #for i in range( len( BFE ) ):
        #    BFEdisplay = np.reshape( np.array( BFE[i] ), (n_x, n_y) )
        #    plt.imshow( BFEdisplay, origin='lower', aspect='equal')
        #    plt.draw()  # Mettez à jour la figure
        #    plt.pause(0.001)  # Pause nécessaire pour permettre la mise à jour de la figure
        #    input('Press any key to continue')
        #    plt.clf()  # Effacez la figure pour le prochain affichage


        BFEshow = np.reshape( BFE, (n_x, n_y) )
        plt.xlabel('width')
        plt.ylabel('height')
        plt.imshow( BFEshow, origin='lower', aspect='equal')
        #plt.pcolormesh( BFEshow )
        plt.draw()  # Mettez à jour la figure
        plt.pause(0.001)  # Pause nécessaire pour permettre la mise à jour de la figure
        #print(BFEshow)
        #input( 'Press any key to continue' )

        max_index_BFE = np.argmax( BFE )
        max_index_BFE_location = locations_position[max_index_BFE,:]
        min_index_BFE = np.argmin( BFE )
        min_index_BFE_location = locations_position[min_index_BFE,:]

        fig5 = plt.figure()

        plt.scatter( locations_position[:,0], locations_position[:,1] )
        plt.scatter( mems_position[:24,0], mems_position[:24,1], c=np.arange(24) )
        plt.scatter( source_position[0], source_position[1], c='r' )
        plt.scatter( max_index_BFE_location[0], max_index_BFE_location[1], c='g' )
        plt.scatter( min_index_BFE_location[0], min_index_BFE_location[1], c='y' )
        plt.xlabel('width')
        plt.ylabel('height')
        fig5.show()

        print( 'max PFE=', max_index_BFE_location, ', value=', BFE[max_index_BFE] )
        print( 'min PFE=', min_index_BFE_location, ', value=', BFE[min_index_BFE])
        print( 'BFEshow=', BFEshow)

        fig6 = plt.figure()
        plt.title( 'BFE at x=n_x/2' )
        plt.plot( BFEshow[int(n_x/2),:] )
        fig6.show()

        print( 'mems_position=', mems_position )

        # Plot FFT module
        fig7 = plt.figure()
        channel_number = 5
        fft_module = fftchannels[channel_number]
        plt.title( 'FFT module on channels' )
        n_f = len(fft_module)
        f = np.array( [i for i in range( n_f )] ) * sampling_frequency / n_f / 2
        plt.plot( f, np.array( fft_module ) )
        fig7.show()

        input( 'Press any key to continue' )
        """

        plt.close( 'all' )


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

