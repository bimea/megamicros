

# Using the Megamicros broadcast server

## Configuration

Before doing any thing, you should focuse on the server configuration.
Configuration can be done only once. It allows you to adapt the server to your needs.
There is no default configuration file. 
By starting the server from your current directory without any configuration file, the server creates one.
You can then adapt it to your needs.
Also you can take an already existant configuration file by using the `-c` option: 

```bash
    $ > cd your_directory
    $ > mbs-server -c your_config_file.json
```

If you have not, the default configuration file will be created with the default name `mbs-server.json` in your current directory.

Here is an example of configuration thst could be used:

??? Example "Example: a simple json configuration file for the MBS server"

    ```json
    {
        "config": {
            "filename": "mbs-server.json"
        },
        "logging": {
            "file": "mbs-server.log",
            "level": "info"
        },
        "messages": [
            {
                "request": "selftest"
            }
        ],
        "mqtt": {
            "broker": "parisparc.biimea.tech",
            "client_id": "megamicros/mbs-server/server_name",
            "persist": "./persist",
            "subscribe": {
                "qos": [
                    1
                ],
                "topics": [
                    "megamicros/mbs-server/server_name/command"
                ]
            },
            "logging": {
                "topic": "megamicros/mbs-server/server_name/log",
                "qos": 1
            }
        },
        "websocket": {
            "port": 9002,
            "reuse_addr": false
        }
    }
    ```

You can see many topics as *config*, *logging*, etc.

### Logging

This configuration topic is for adjusting the logging system. You can set many different log levels:

* *debug*: the debug mode with maximum informations printed while the server is running;
* *info*: all conventional informations are printed;
* *warning*: only warning are displayed o the log system;
* *error*: only error messages are reported
* *critical*: only critical messages are reported.

The `file` entry decides for the log filename. 

### MQTT

MQTT is the IoT procol used by the Megamicros server to communicate. 
The server subscribes to the topics mentionned in the config file with the desired *quality of service (qos)*.
The command which are sent on this topic are then executed by the server using a dedicaced job queue.

More over, the server can publish in two ways:

* by publishing its regular activity and its state
* by publishing log messages according the log level previously mentionned

Here are the two entries for publishing both activities, status and log.
Note that if not mentionned, those reporting activities won't be realized and no MQTT publishing will be performed by the server:

```json
{
    "mqtt": {
        "status":{
            "topic": "megamicros/mbs-server/server_name/status",
            "qos": 1,
        },
        "logging": {
            "topic": "megamicros/mbs-server/server_name/log",
            "qos": 1,
        },
    },
}
```

### Websocket

The server can perform realtime data exchange using the websocket protocol. 
To do that, you have to set the *websocket* entry in the configuration file by specifying the listening port.
The default port is set to 9002.


### Tasks execution at startup

You can put some commands in the configuration file that will be executed every time the server starts. 
An example of such commands could be a *seltest* command for controling available mems on the connected antena. 
Syntaxe of these commands is very similar to the original commands syntaxe when using the MQTT or the webspcket streams.


## Testing the Megamicros server

Once the Megamicros Broadcast Server is installed and running, you can run tests to make sure everything is working properly.
The best way to do that is to write a python program as those given in the `Megamicros/examples` directory.

Here is a very simple program getting antenna parameters:

??? Example "Example: performing a self-test"

    ```python
    # see the example/mu32ws_selftest.py python program
    
    import numpy as np
    from megamicros.core_ws import Megamicros, MegamicrosWS

    mu32ws = MegamicrosWS( remote_host=host, remote_port=port )
    mu32ws.selftest()

    print( f"System type is: {Megamicros.System(mu32ws.system)}" )
    print( f"Sampling frequency: {mu32ws.sampling_frequency} Hz" )
    print( f"Available mems: {mu32ws.available_mems}" )
    print( f"Activated mems: {mu32ws.mems}" )
    ```

    Results:

    ```bash
    System type is: Mu32
    Sampling frequency: 50000.0 Hz
    Available mems: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
    Activated mems: []
    ```

The self-test procedure is a one-second procedure that starts the Megamicros receiver in recording mode to generate data and calculate measurements on it.
The current receiver parameters are then saved in the server memory. 
All subsequent calls to request the receiver settings are only a readout of the stored settings.
It is obvious that you should require for a self-test before requiring parameters.







## Connecting to H5 audio sources

Getting H5 audio source may be performed following two ways: 
* getting H5 signals from a remote Megamicros database;
* getting H5 signals from files stored on the server file system.  










## Generate synthesis signals


# Accessing the resource

The server performs **jobs** execution and **actions** execution.  
Jobs are supposed to use the antenna. As a consequence, they lock the device during all the time they are using it.
It follows that before running, jobs are put in a wait state until the device is free.
On the contrary, actions do not use the antenna. They don't lock the device. 
Actions are executed *on the fly* without waiting for jobs or actions terminaison.

## Web socket commands

Websocket system is the main way to send actions and jobs to a remote server. 
The two-ways communicating process allows sending and receiving informations about the active job.

### Run

The *run* command is the one that starts the full execution of the Megamicros device to get the raw signals from the antenna.
To succeed, this order needs the receiver to be free.
The values of some parameters can be added to the command. 
If this is not the case, the default values will be used by the server.

``` json
{
    "request": "run",
    "settings": {
        "mems": {0, 1, 2, 3, 4, 5, 6, 7},
        "duration": 5
    },
    "origin": "..."
}
```

* `request`: the job
* `settings`: an optionnal dictionnary with Meagmicros command settings 
* `origin`: if set to `background`, replace the `websocket` origin by the `system` origin, turning the command in the background execution mode 

If no error occures, the server send a positive message before sending the binary data :

``` json
{
    "request": "run",
    "type": "status",
    "response": "ok",
    "message": "",
}
```

When executing in the `backgound` mode, jobs stop the websocket connection, meaning that communication is no more available.

### H5Run

The *H5Run* command is a *Run* command without any data emission to the client. Instead data are saved in a local HDF5 file.
Idealy the command should be run in `background` origin mode. 

``` json
{
    "request": "h5run",
    "settings": {
        "mems": {0, 1, 2, 3, 4, 5, 6, 7},
        "duration": 5,
        ...
    },
    "origin": "background"
}
```

On success:

``` json
{
    "request": "h5run",
    "type": "status",
    "response": "ok",
    "message": "Job executed in background mode",
}
```


# Annexes (to be reviewed)

## Getting receiver parameters 

```python
{
    "request": "parameters",
}
```

The parameters are the set of values that characterize the operation of the Megamicros receiver. 
At boot, the server performs a self-test and retrieves the parameter values.
Those values are stored in memory and sent to client on request.

??? Example "Example: quering parameters value in python"

    ``` python
    await websocket.send( json.dumps( {'request': 'parameters'} ) )
    response = json.loads( await websocket.recv() )
    if response['request'] == 'parameters' and response['type'] == 'response':
        print( f"Receiver parameters values are: {response['response]}" )
    else:
        raise Exception( f"Failed to get parameters from server: {response['message']}" ) 
    ```


## Megamicros receiver Self-test

``` json
{
    "request": "selftest",
}

```

The self-test procedure is a one-second procedure that starts the Megamicros receiver in recording mode to generate data and calculate measurements on it.
The current receiver parameters are then saved in the server memory. 
All subsequent calls to request the receiver settings are only a readout of the stored settings.
It is obvious that you should require for a self-test before requiring parameters.

??? Example "Exemple: requiring self-test"

    ``` python
    await websocket.send( json.dumps( {'request': 'selftest'} ) )
    response = json.loads( await websocket.recv() )
    if response['request'] == 'selftest' and response['type'] == 'status' and response['response'] == 'ok':
        print( "Received positive answer to self-test request" )
    else:
        raise Exception( f"Failed to start self-test: {response['message']}" ) 
    ```

!!! Failure "Failure: receiver busy"

    You cannot start any self-test if the receiver is busy i.e. doing something else at the same time.

During the self-test, the receiver is blocked, which means that no other request can succeed.
Similarly, if you request a self-test while another self-test is running (or any other task requiring the receiver), your request will fail.

There are two solutions to solve this problem.
The first one is to make a request as above.
The second one is to set a time limit: the server waits for the recipient to reach it until the time limit has passed:

``` json
{
    "request": "selftest", "timeout": 1
}
```
Where the `timeout` is the time limit in seconds. If the time limit is exceeded, the client receives an error response with a timeout code:

``` json
{
    "request": "selftest",
    "type": "status",
    "response": "error",
    "message": "timeout occured",
    "code": 54                          # code value example
}
```

## Running the remote receiver


## Stop

``` json
{
    "request": "stop",
    "id": "123456789",
}
```
The *stop* command allows you to decide to stop a running process initiated by a [**run**](run.md) command before its normal end.
You cannot stop a process without providing the identifier that was given when it was started.