# The server as a MQTT client

## Introduction

MQTT is the IoT message system used by the Megamicros server.
Messages are sent by the publishers on a particular topic to a broker.
Topics can be seen as communication channels.
Those messages can be viewed by some subscribers provided they are listening to the considered topics.
Publishers end subscribers are MQTT clients while the broker is the server.

The Megamicros broadcast server is both a *publisher* and a *subscriber* MQTT client.
As a *subscriber*, the server can get configuration parameters, and get start, stop and status job's commands.
As a *publisher*, the server sends internal states such as cpu occupency, internal temperature, job reports and IA alarms.

The server can also communicate by direct websocket data transfers.
Websockets allow bidirectionnal realtime data transfer, which MQTT system cannot do.
The server's objectif is threefold:

* 1) Acquiring the signals from antenna microphones, extracting informations from them and sending alarms;
* 2) Saving parts of signals with relevant informations and saving them by sending them through the net;
* 3) Getting realtime signals from the antenna such as audio channels, beamformed channels or spectrograms.

1) is only performed by using the MQTT system.
2) is made using a passive way.
The server saves data on the local disk and an external operator retreives them using the ssh tunnel.
In that case, all is governed by the MQTT channel.
3) is done by using the websocket channel. 1) and 3) cannot work together and it becomes obvious that the two communication ways MQTT and websocket should be implemented independently of each other.

## Publishing logs

Depending on the configuration file, the log messages of the server are sent both to the standard output stream and to the default log file. But upon success of the Megamicros server connection to a MQTT broker, log messages are also sent to this MQTT broker.

For this service, a Mqtt handler is defined and declared in the `mqtt-client.hpp` include file.  
Adding this handler to the log logger is performed like this:

```cpp
    // set the log level to "info":
    mmic::log.setLevel( "info" );

    // define a Mqtt Handler:
    mmic::MqttPubHandler log_mqtt_handler( 
        "tcp://parisparc.biimea.tech:1883",     // broker host
        "parisparc_mbs",                        // client id
        1,                                      // QOS
        "./persist",                            // peristance directory
        "log"                                   // topic name
    );

    // Add the Mqtt handler to the logger:
    mmic::log.setHandler( log_mqtt_handler );
```

After this declaration, the program is connected to the broker and all log messages are automaticaly sent to the broker under the topic `log`.



## Publishing events

## Architecture

A special thread is dedicaced to the MQTT subscriber service.
This thread is listening to the remote broker and report every message sent by the broker to the server.
It is implemented exactely as the websocket listening thread is.

## Bibliography

* [Paho MQTT c++ API](https://www.eclipse.org/paho/files/cppdoc/index.html)