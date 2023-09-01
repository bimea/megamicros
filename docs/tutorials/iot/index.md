# Megamicros IoT

* [MQTT broker](mqtt-server.md)
* [Dashboards](boards.md)
* [MQTT c++ client](mqtt-cpp.md)
* [Station tracker](stracker.md)

MQTT is the IoT message system used by the Megamicros server.
Messages are sent by the *publishers* on a particular *topic* to a *broker*. 
*Topics* can be seen as communication channels.
Those messages can be viewed by some *subscribers* provided they are listening to the considered *topics*.
*Publishers* end *subscribers* are MQTT clients while the broker is the server.

Every message has to be associated to a *topic* and those *topics* are divided into *levels*. 
Some wild-cards exists as *+* and *#*.

*QoS* is the *Quality of Service* :

* QoS = 0 : the message is delivered *at most one* time. It means that there is no garanty of reception. The message can be lost;
* QoS = 1 : the message is delivered *at least one* time. There is a garanty of reception: the message will be repeted if needed;
* QoS = 2 : The mesasge is delivered *exactly once* time. Garanty of no loss: the message is saved. As a consequence the transmission is slower.

# Bibiography

* [Practical MQTT](http://www.steves-internet-guide.com/)