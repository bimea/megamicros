# megamicros.mqtt.py mqtt client handler for MegaMicros libraries
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
Megamicros documentation is available on https://readthedoc.bimea.io

!!! WARNING!!!
The MQTT client should be created and should connect to the broker outside the MqttHandler
In fact the client should be given as argument to the MqttHandler

!!! WARNING!!!


Release 2.0.0 of the Paho Python MQTT includes breaking changes; 
this means that code written for v1.x will not work without some (minimal) modifications. 
As v2.0.0 was only released a few days ago (11th Feb 2024) most examples, including the one you reference, will not work.
See bellow for the migration guide:
https://eclipse.dev/paho/files/paho.mqtt.python/html/migrations.html
https://github.com/eclipse/paho.mqtt.python/blob/master/docs/migrations.rst
so far the code bellow is working with the 1.6.1 version of the paho-mqtt library.
As such it breaks with the 2.0 version. In the mean time.
In the mean time we only changed the 'client = mqtt.Client(client_id)' to 'client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)'.
It seems enough to make the code work with the 2.0 version of the paho-mqtt library.

See: https://www.emqx.com/en/blog/how-to-use-mqtt-in-python 
"""

import paho.mqtt.client as mqtt
from .exception import MuException
from .log import log, logging

DEFAULT_BROKER_HOST = 'localhost'
DEFAULT_BROKER_PORT = 1883
DEFAULT_CLIENT_NAME = 'megamicros/unknown'
DEFAULT_TOPIC = 'megamicros/unknown/unknown/log'
DEFAULT_QOS = 1
DEFAULT_LEVEL = logging.NOTSET

MQTT_ERROR_0 = 'Connection successful'
MQTT_ERROR_1 = 'incorrect protocol version'
MQTT_ERROR_2 = 'invalid client identifier'
MQTT_ERROR_3 = 'server unavailable'
MQTT_ERROR_4 = 'bad username or password'
MQTT_ERROR_5 = 'not authorised'


class MqttClient :
    __client: mqtt.Client
    __connected: bool
    __host: str
    __port: int
    __name: str
    __onMessageCallback = None
    __onMessageCallbackUserdata = None


    def __init__( self, host=DEFAULT_BROKER_HOST, port=DEFAULT_BROKER_PORT, name=DEFAULT_CLIENT_NAME ) :
        self.__connected = False
        self.__host = host
        self.__port = port
        self.__name = name
        self.__onMessageCallback = None
        self.__onMessageCallbackUserdata = None

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                log.info( f" .Connected on MQTT broker")
            else:
                log.info( f" .Failed to connect to MQTT broker with return code: '{rc}'")
        
        try :
            self.__client = mqtt.Client( mqtt.CallbackAPIVersion.VERSION1, name )
            self.__client.user_data_set( self )
            self.__client.on_connect = on_connect
            self.__client.connect( host=host, port=port, keepalive=60, bind_address="" )
            self.__connected = True


        except Exception as e:
            log.error( f"MQTT broker connection failed: {e}" )
            raise

    def __del__( self ) :
        self.__client.disconnect()

    def is_connected( self ) -> bool : 
        return self.__connected

    def publish( self, message: str, topic: str, qos: int=1 ) :
        self.__client.publish( topic, message, qos, retain=False )

    def subscribe(self, topic: str, on_message=None, userdata=None):
        def on_message_default(client, userdata, msg):
            print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")

        self.__onMessageCallback = on_message if on_message is not None else self.__onMessageCallback
        self.__onMessageCallbackUserdata = userdata if userdata is not None else self.__onMessageCallbackUserdata

        self.__client.subscribe(topic)
        self.__client.on_message = on_message_default if self.__onMessageCallback is None else self.__onMessageCallback
        self.__client.user_data_set( self.__onMessageCallbackUserdata )

    def onMessage(self, callback, userdata=None):
        self.__onMessageCallback = callback
        self.__onMessageCallbackUserdata = userdata
        

    def run(self, topic: str, on_message=None, userdata=None ):
        self.subscribe( topic, on_message, userdata )
        self.__client.loop_forever()


class MqttPubHandler( logging.Handler ) :

    __client: MqttClient
    __topic: str
    __qos: int

    def __init__( self, client: MqttClient, topic=DEFAULT_TOPIC, qos=DEFAULT_QOS, level=DEFAULT_LEVEL ) :
        try :
            super().__init__( level )
            if not client.is_connected():
                raise MuException( 'Cannot init logging Handler: MQTT client is not connected' )
            self.__client = client
            self.__topic = topic
            self.__qos = qos

        except Exception as e:
            log.error( f"MQTT broker connection failed: {e}" )
            raise

    def getTopic( self ) -> str :
        return self.__topic


    def __del__(self) :
        self.__client = None


    def emit( self, record ) :
        message = record.getMessage()
        self.__client.publish( message=message, topic=self.__topic, qos=self.__qos )



