# Server developpment

These pages are devoted to programmers who want to get knowledge about the server c++ program.

* [MQTT client](mqtt-client.md)

The server is built arround three threads:

* A thread devoted to webwocket messages listening;
* A thread devoted to mqtt messages listening;
* The main thread devoted to the Megamicros job's handling.

The two first threads read incoming messages and transform them as jobs to be executed by the third thread.
The way the jobs are executed by the job's execution thread may be different whether the job comes from the websocket remote client or the from mqtt remote broker.
Indeed MQTT messages do not require responses from the server while websocket do.
This is mainly because websocket protocol is a two-way communication protocol. 
As such, it serves as a channel between the server and the remote client which acts as a frontend.  
On the contrary, MQTT is a one-way protocol. The MQTT broker acts as a central system to connect the server with several remote clients which want to get services from the server. Those clients may send commands to the server and receive some final results of those commands, most often under the form of alerts or states of internal variables and sensors.

## Job scheduler operating principle

One important thing to know is that jobs using the antena cannot share the antena with others jobs.
This is because the USB cannot be shared - or at least USB sharing is not implemented.
As a consequence, jobs work in blocking mode. Actually they are queued up for execution one after the other.
Despite this, it is possible to run some actions while a job is running provided this action does not use the antenna Usb port.
Such actions are usefull form performing remote machine control for example.

Messages coming from the websocket stream or even from a topic the server has subscribed can then divided in actions commands and jobs command. Actions are directly executed when received while job are pushed in the job queue and executed once the antenna is free.

Finaly, the configuration file acts as a third input stream that can execute actions or send jobs to the queue.
Note that the configuration stream has priority over the websocket and MQTT streams.

Another important principle is that the server manages stateless jobs.
It means that the antenna configuration must be given at the same time as the job itself. 
If not, default parameters values will be used, but not the values left by previous jobs.

Another important point is about communicating. 
Actions and jobs can send data while they are running.
But communicating with the configuration file makes no sens.
So when the actions or jobs originate from the configuration file, output messages are lost. 
When actions or jobs originate from the MQTT topic to which the server is subsribed, output message are also lost.  
Only commands issued from the websocket stream can send messages over this same stream.
All of this is summarized by the dedicaced function *send_message()*. 
One exception is the subscription of the server to a MQTT topic for sending output messages from the actions and jobs. This subscription should be defined in the client request by setting the *mqttout* parameter to the desired MQTT broker topic.   

## Accessing the resource

Every job using the antenna locks the device during all the time it is using it.
But actions are executed in asynchronous mode. 
It means that if the device is not free, the action is stopped and a failure message is return to the client.
On the contrary, jobs are executed in a synchronous mode. 
It follows that before running, jobs are put in a wait state until the device is free. 


## Action commands

Here is the exhaustive list of built in commands twhich acts as actionsn, meaning that they do not require the Usb bus:

### ps

*Lists pending jobs and, where applicable, job in progress*.

* request form

```json
{
    "request": "ps", 
    "type": "status", 
    "message": ""
}
```

* response

```json
{
    "request": "ps", 
    "type": "response", 
    "response": [ 
        "job_name",            
        "job_name",            
    ], 
    "message": ""
}
```

## Jobs commands

### Selftest

*Performs a setest of the Megamicros device*.

Responses are always sent by the function running the job, not by the message handler.
In reality, the message handler has completed its task when the job runs. 
When writing the job handler function, you should therefore bear in mind that the connection may have been interrupted.




