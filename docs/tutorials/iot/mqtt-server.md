# MQTT broker

The Megamicros server can be used as a "IoT system" providing you can connect it to a running MQTT server.
*Mosquitto* is a MQTT server that can be installed on a linux system:

```bash
    $ > sudo apt-get update
    $ > sudo apt-get install mosquitto
```

## Mosquitto as docker image

Edit this `docker-compose.yml` file:

```yaml
version: '3.8'

services:
    ...
    mosquitto:
      image: eclipse-mosquitto
      container_name: mosquitto
      restart: unless-stopped
      volumes:
          - /usr/share/docker/DATA/mosquitto/config:/mosquitto/config
          - /usr/share/docker/DATA/mosquitto/data:/mosquitto/data
          - /usr/share/docker/DATA/mosquitto/log:/mosquitto/log
      ports:
          - 1883:1883
          - 9101:9001
```

Edit the configuration file:

```bash
    $ > vi /usr/share/docker/DATA/mosquitto/config/mosquitto.conf
    persistence true
    persistence_location /mosquitto/data/
    log_dest file /mosquitto/log/mosquitto.log

    allow_anonymous true
```

Then pull the image:

```bash
    $ > docker-compose up mosquitto
```

If all seems going right, quit and start :

```bash
    [Ctrl][c]
    $ > docker-compose start mosquitto
```

## Testing

There is no `bash` or `csh` shell in the Mosquitto docker image. Use instead the `ash` shell:

```bash
    $ > docker exec -it mosquitto ash
    / # 
```

Inside the docker image you can test the subscrib and publish commands:
In the current shell, subscribe to the `test_topic` topic:

```bash
    / # mosquitto_sub -h localhost -t test_topic
```

Then open another shell and publish a message on the `test_topic` topic:

```bash
    / # mosquitto_pub -h localhost -t test_topic -m "Hello World!"
```

You should see the message appearing on the previous shell.

Now we need to perform the same test from outside the docker image.
Install the *mosquitto-clients* package on the server hosting the container. 
For linux Ubuntu systems:

```bash
    $ > sudo apt-add-repository ppa:mosquitto-dev/mosquitto-ppa
    $ > sudo apt-get update
    $ > sudo apt-get install mosquitto-clients
```

You may prefere using the snap system:

```bash
    $ > sudo snap install mosquitto
```

In that last case, both clients and server are installed and after install the server is running.
Just to avoid having two servers running on the same host, you should stop the snap mosquitto broker:

```bash
    $ > sudo snap stop mosquitto
```
Last but not least, add the following line to the congiguration file, otherwise you will get an `Error: The connection was lost` message:

```bash
    $ > vi /usr/share/docker/DATA/mosquitto/config/mosquitto.conf
    ...
    listener 1883 0.0.0.0
```

From a MacOS system, use brew installer:

```bash
    $ > brew install mosquitto
```

A default configuration file is provided. Here is its location on Mac M1/M2 systems:

```bash
    $ > vi /opt/homebrew/etc/mosquitto/mosquitto.conf
    $ > brew services restart mosquitto
```

Since there i no need of the MQTT broker, you can stop it:

```bash
    $ > sudo brew services stop mosquitto
```

Try now to subscribe and publish from the host without forgetting the port:

```bash
    $ >  mosquitto_sub -h localhost -p 1883 -t test_topic
```

Then open another shell and publish a message on the `test_topic` topic:

```bash
    $ > mosquitto_pub -h localhost -p 1883 -t test_topic -m "Hello World!"
```

And now perform the same test from an external laptop on the web (we suppose the server host name is `parisparc.biimea.tech` and you have mosquitto/clients installed on your external laptop):


```bash
    $ >  mosquitto_sub -h parisparc.biimea.tech -p 1883 -t test_topic
```

Open another shell and try:

```bash
    $ > mosquitto_pub -h parisparc.biimea.tech -p 1883 -t test_topic -m "Hello World!"
```

Your MQTT is now running.


* [Mosquitto homepage](https://mosquitto.org/)
* [Mosquitto docker image](https://hub.docker.com/_/eclipse-mosquitto)
* [MQTT clients](https://www.eclipse.org/paho/)



