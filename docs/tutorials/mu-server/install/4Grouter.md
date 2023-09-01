# Install with a 4G router

You have a Magamicros antenna with its USB receiver and a mini-laptop that embeds the server.
This laptop should be connected to the internet by a wifi connection or an ethernet RJ45 cable to your 4G router.

## 4G configuring

One supposed you subscribed to an internet operator and you have an activated  SIM card.
The first thing you have to do is to remove the PIN number of your SIM card, unless your router is well equiped to deal with the SIM number handling.

You can remove the PIN number of your SIM card by using an ordinary smartphone.
On Android systems:

``` text
    Paramètres > Sécurité > Autres paramètres > Cryptage et références > Définir verouillage
```

Plug in your 4G router with the SIM card in it and connect to the router with a laptop computer.
Connect your mini-laptop to the router using a RJ45 ethernet cable.
The cable connection is mandatory the first time, unless your mini-laptop is already installed.

## The two-way ssh channel

Once the 4G server is installed and the server connected to the router by a local ethernet RJ45 cable or a wifi wireless connection, it can acces any host on the internet.
But the reverse is impossible: the computer is not accessible from the internet.
This is due to the closing of all input ports by the operator.

Here comes the **ssh channel** solution.

### ssh tunneling

Let's assume that the computer that integrates the broadcast server has the IP number `192.168.8.2`.
The ``192.168.8`` local network is hosted by the 4G router which provide the connection to the Internet network (The 4G router actes as a gateway).

It is now necessary to install an ssh server that could act as an output channel.
Of course, this server must be accessible to users from the internet.
The idea is to use ssh to build a channel between the Megamicros server (input) and the ssh server (output).
The end user would not connect to the Megamicros server but to the ssh server, and through it and the tunnel he would have access to the Megamicros server.

Let `hostssh.mydomain.com` be the internet name of the ssh server and `username` a login. In what follows, `megamicros` is a login on the Megamicro server.

It is obvious that the Megamicros server can connect to the host:

```bash
$ megamicros > ssh username@hostssh.mydomain.com
passwd:****
$ hostssh > ...
```

By adding the correct options one can build the channel:

```bash
$ megamicros > ssh username@hostssh.mydomain.com -N -R :8822:localhost:22
passwd:****
```

The optional -N says "don't execute a command" (helpful to prevent accidents caused by leaving remote shells laying around.).

The -R option specifies a remote SSH port forwarding.
This allows anyone on the ssh server to connect to TCP port 8080 on the ssh server.
The connection will then be tunneled back to the Megamicros server, which then makes a TCP connection to port 80 on localhost. Any other host name or IP address could be used instead of localhost to specify the host to connect to.

```bash
$ hostssh > ssh -p 8822 megamicros@localhost
passwd: ****
$ megamicros >
```

### More options for tunneling

The call that install the tunnel is a blocking call.
The -f option allows the ssh to run in the background.

```bash
$ megamicros > ssh username@hostssh.mydomain.com -N -f -R :8822:localhost:22
passwd:****
```

Setting the password may be problematic for security reasons.
The common solution is to generate a ssh-key and declare it in the ssh server.
The password will be no longer required and the tunnel right built:

```bash
    > megamicros > ssh-keygen 
    > megamicros > ssh-copy-id username@hostssh.mydomain.com
```

With the previous command, users have to be logged on the "local machine", i.e the ssh server, to initiate a connection on the tunnel. But this is not mandatory.
Provided the user has access to the ssh server, he can initiate a connection from the host is is connected (ùserhost` in the following example):

```bash
$ userhost > ssh -p 8822 megamicros@hostssh.mydomain.com
```

If the ssh server host is hosted on a local network behind a private router, you may have to configure the ports routing on the gateway server.
Supposing incomming ssh connections on port 4022 are redirected to the 22 port of the ``host`` the Megamicros server would have to initiate the ssh connection like:

```bash
$ megamicros > ssh username@hostssh.mydomain.com -N -f -R :8822:localhost:22  -p 4022
```

The same gateway should be configured so as to redirect 8822 incomming connections to the ssh server on the same 8822 port.

### Robustness with autossh

autossh is a program to start a copy of ssh and monitor it, restarting it as necessary should it die or stop passing traffic:

```bash
$ megamicros > autossh -M 9042 username@hostssh.mydomain.com -N -f -R :8822:localhost:22  -p 4022
```

The option -M 9042 specifies the base monitoring port to use.
This port and the port immediately above it (9043) should not be used.


### Forwarding other ports

ssh server makes possible to forward other port than its own port 22.
Megamicros uses to send data through the 9000 port.
One can set a second tunnel to allow external users to receive the Megamicros data :

```bash
$ megamicros > autossh -M 9942 username@hostssh.mydomain.com -N -f -R :8822:localhost:9000  -p 4022
```

The port 22 is replaced by the port 9000.  
The control port 9042 is replaced by the port 9942.
With such tunnekls, users can connect to the Megamicros server by using the ssh port 22 and send/receive data by the port 9000.

### Installing the ssh server in a docker container

Dockerfile example:

```yaml
FROM       ubuntu:20.04
MAINTAINER bruno.gas@sorbonne-universite.fr

RUN apt-get update

RUN apt-get install -y openssh-server
RUN mkdir /var/run/sshd

RUN echo 'root:root' |chpasswd

RUN sed -ri 's/^#?PermitRootLogin\s+.*/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -ri 's/UsePAM yes/#UsePAM yes/g' /etc/ssh/sshd_config

RUN mkdir /root/.ssh

RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

EXPOSE 22

CMD    ["/usr/sbin/sshd", "-D"]
```

docker-compose.yaml entry example:

```yaml
version: '3.8'

services:
    ssh4g:
        build: ssh4g/.
        container_name: ssh4g
        restart: unless-stopped
        ports:
          - "4022:22"
```


## Services

The ssh tunnels and the server must be run automatically.
Services are the ideal tool for this.

In what follows we define a service which starts the megamicros server once.

```bash
    $ > vi /etc/systemd/system/megamicros-server.service
    #/etc/systemd/system/megamicros-server.service
    [Unit]
    Description=Megamicros Parisparc server

    [Service]
    Type=oneshot

    User=megamicros
    WorkingDirectory=/home/megamicros/Megamicros/Megamicros_cpp/build
    ExecStart=/home/megamicros/Megamicros/Megamicros_cpp/build/apps/mu-server/src/mu-server
    ExecStop=/bin/kill -9 $MAINPID

    [Install]
    WantedBy=multi-user.target
```

Let us install, start and then control the service:

```bash
    $ > systemctl daemon-reload
    $ > systemctl start megamicros-server.service
    $ > systemctl status megamicros-server.service
```

If all seems going right, then you can enable the service:

```bash
    $ > systemctl enable megamicros-server.service
```

Concerning log messages, the serv ice daemon redirect them to the syslog file.
In case the megamicros server failed you can have a look at it:

```bash
    $ > cat /var/log/syslog
```

## Data streaming with 4G routers and bandwidth

The question is how 4G routers are relevant and efficient for data transmission, when the acoustic data from antennas is so voluminous.

Assuming a sampling frequency of 22 kHz and a 32-channel antenna, the total byte rate per second can be calculated as follows:

$$
    N = 32 \times 4 \times 22000 \times = 2,6856 Mo/s
$$

Supposing a recording time interval of 11 hours per day, then:

$$
    N = 32 \times 4 \times 22000 \times 3600 \times 11 = 103,85 Go/day
$$

Per month with 22 open days:

$$
    N = 32 \times 4 \times 22000 \times 3600 \times 11 \times 22 = 2,23 To/month
$$


## Documentation

* [Antennes 4G: comparatif et guide d'achat](https://routeur-5g.fr/antenne-4g/)
* [Tunneling SSH](https://www.it-connect.fr/chapitres/tunneling-ssh/?utm_content=cmp-true)
* [SSH Tunneling: Examples, Command, Server Config](https://www.ssh.com/academy/ssh/tunneling-example)

# Laste versions

## Dockerfile

```yaml
FROM       ubuntu:20.04
MAINTAINER bruno.gas@distalsense.com

RUN apt-get update

RUN apt-get install -y openssh-server
RUN mkdir /var/run/sshd

RUN echo 'root:root' |chpasswd

RUN sed -ri 's/^#?PermitRootLogin\s+.*/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -ri 's/UsePAM yes/#UsePAM yes/g' /etc/ssh/sshd_config
RUN sed -ri 's/^#?GatewayPorts no/GatewayPorts yes/' /etc/ssh/sshd_config

RUN mkdir /root/.ssh

RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

EXPOSE 22
EXPOSE 9002
EXPOSE 2200
EXPOSE 2201 

VOLUME /root/.ssh

CMD    ["/usr/sbin/sshd", "-D"]
```

## Docker compose

```yaml
    ...
    ssh4g:
        build: ssh4g/.
        container_name: ssh4g
        restart: unless-stopped
        ports:
          - "4022:22"
          - "9002:9002"
          - "2200:2200"
          - "2201:2201"
        volumes:
          - /usr/share/docker/DATA/ssh4g/.ssh:/root/.ssh
        environment:
          - TZ=Europe/Paris
          - DEBIAN_FRONTEND=noninteractive
```

## Clés ssh

Clés présentes dans ``/root/.ssh/authorized_keys`` (``-rw------- 1 root root``)

```bash
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCqmUSB3A3ilp/kx4t92Y+W7btaYP7ESTQZ5apg5Dr7BTxCBwxYw2dDu0v75ACziF5OBDnLuaQwdKMmqV/4BCv4m2xhG4MFNwnL39KapjWvpFW+A2aiA5SUS1+2SwPTAf/jF74Qw0yflY2I5EzjoQYELvxpzCuBfUdin9prDAmugD3RZCg3HsH+UpqdPYwgnpjBcpc5t/hH+6PQmUiCk//HcZlhSGYHWl1z/JCF/+wq5sWdhV1f1ZF7VuFLFj1iAOq0moLoKURPkeIKhrybNfgzQqyce3GfgouwAgzZfUeIihKFM/QxbR1W8B+evY98HZmT12shCIwZHTQIW2JapHLVcUIZsBHilfsluXSSp6pcFP479uSS0Nr7r7cMuhzLXZE5L89HsFnHMF775pEY58tpSZBbQ1LwUaCYwe8fxHniKozqm1oVyWljMFxOA8P3zR+lF7rOBebhjA26Mbxf3Xm45pg+MhV91jbbho2gyhKuzBlo/Qaoho/Ue+0gKM4vC4k= megamicros@parisparc
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDPg+5p+I+PQjC+gMUESGnFRRcG2qAH4+6PNM93IRqJybzyOsbbw6KOqaNKelyp4CiQ1Lf9HcSu5zNOYQC6SmwNdc0c6opft2tyPCa8+K8llGoXoENK0cdKJnA6MVOXxdr9MvaNwEJ6/XgKJDpKUHGzTMzZT6gRsO7/T4gl2c7aXQIAB3LrDL/axNnfUs1LNDfZhQia/i5MYTZ3hvHV3I8A5fzOGyBxCjVrlx7QzUEyLq3bVVxDG0YGiQ1U2kvq4ZuHI1e/Pimf+iJVjDOWCjxssWIkxZtj7Puu/mWiE4tS6uqKJdH+sfOjWEhAbjSiWaMxPVfb30dcxs5KM5w+6665 megamicros@parisparc2
```
