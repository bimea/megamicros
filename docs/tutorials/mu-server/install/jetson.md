# Jetson Nano as mini-laptop

In this totorial we propose to install a Megamicros server on a [Jetson Nano 4Go model](https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit) computer (see [this page](https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-2gb-devkit) for the Jetson Nano 2Go model).

## Installing the OS

Download the Jetson Nano 2GB Developer Kit SD Card Image and write it to your SD micro card.
Follow the installation instruction.
Connect your mini-laptop to the router using a RJ45 ethernet cable. You should be able to open a ssh connection to your Jetson Nano from your laptop computer.

Update and upgrade the system:

```bash
    $ > sudo apt update
    $ > sudo apt upgrade
```

## Setting the run level 3 (muti-user)

The default run level on Jetson and Raspberry stations is usually set to 5 which is the graphic mode.
Since the graphic mode is useless, you can change it and set the defalt run level to 3 (multi-user target).

```bash
    $ > sudo systemctl get-default
    graphical.target
```

Before changing the default runlevel, check out the available targets:

```bash
    $ > sudo systemctl list-units --type=target
````

Issue the following command to change the default runlevel to runlevel 3 (nothing but a multi-user.target):

```bash
    $ > sudo systemctl set-default multi-user.target
```

Confirm the default runlevel:
```bash
    $ > sudo systemctl get-default
    multi-user.target
```

Reboot and check it out.

## Wifi

There is no wifi device on the Jetson Nano.
You can verify by printing the network devices list:

```bash
    $ > ls /sys/class/net
    docker0  dummy0  eth0  l4tbr0  lo  rndis0  usb0
```

The only way to have a wifi is to plug an usb wifi device.

## Usb

Connect the Megamicros device on the Jetson Nano usb port.
Your USB MegaMicro interface should appear in the list of available usb devices:

```bash
    $ > lsusb
    Bus 002 Device 002: ID fe27:ac03  
    Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
    Bus 001 Device 002: ID 1a40:0801 Terminus Technology Inc. 
    Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
```

You can see the MegaMicro device appeariog on bus ``002 Device 002`` with its ``fe27:ac03`` identifier.
Unfortunatly the Usb device is not accessible by users but only by root.
The most common way for giving usb rights to users is to create the foollowing file at ``/etc/udev/rules.d``:

```bash

    $ > vi /etc/udev/rules.d/99-megamicro-devices.rules
    # Floowing lines add access to MegaMicro devices:
    # Order is Mu32-usb2, Mu32-usb3, Mu256, Mu1024:
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac00", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac01", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac03", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac02", MODE="0666"
```

## Python

``Python 3.6`` is the default python version installed on the Jetson. 
Megamicros needs at least the 3.10 Python version.
For installing a newer version, follow the next steps.

The `software-properties-common` package gives you better control over your package manager by letting you add PPA (Personal Package Archive) repositories. 
It should be already installed. If not, install the supporting software with the command:

```bash
    sudo apt install software-properties-common
```

Deadsnakes is a PPA with newer releases than the default Ubuntu repositories. Add the PPA by entering the following:

```bash
    $ > sudo add-apt-repository ppa:deadsnakes/ppa
    $ > sudo apt update
```

Now you can start the installation of Python 3++ (say 3.10 in our example) with the command:

```bash
    $ > sudo apt install python3.10
    $ > python3 --version
    Python 3.6.9
```

You have now to change the default python version:

```bash
    $ > update-alternatives --install /usr/bin/python python /usr/bin/python2.7 1
    $ > sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.6 2
    $ > sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.10 3
```

Choosing the python version becomes interactiv with :

```bash
    $ > update-alternatives --config python
```

Install ``python3-pip`` and ``virtualenv``:

```bash
    $ > apt install curl
    $ > curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10
    $ > pip --version
    pip 23.0.1 from /usr/local/lib/python3.10/dist-packages/pip (python 3.10)
    $ > pip install virtualenv
```

Install development headers for building C extensions, the standard library (venv) module, the standard library (dbm.gnu) module and the standard library (tkinter) module:
  
```bash
    $ > sudo apt install -y python3.10-dev python3.10-venv python3.10-gdbm python3.10-tk
```

The following modules may be already installed. If not :

```bash
    $ > sudo apt install -y python3.10-distutils python3.10-lib2to3
```

The Cmake version is too old. The only way to uprage it is to clone de Cmake GitHub repository, compile from scratch , make and install:

```bash
    $ > sudo apt remove cmake
    $ > sudo apt install libssl-dev
    $ > git clone https://github.com/Kitware/CMake
    $ > cd CMake
    $ > ./bootstrap
    $ > make
    $ > make install
```


## Documentation

* [Getting Started with Jetson Nano 2GB Developer Kit](https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-2gb-devkit)
* [Jetson Nano 2GB Developer Kit User Guide](https://developer.nvidia.com/embedded/learn/jetson-nano-2gb-devkit-user-guide)


