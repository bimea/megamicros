# Linux station

In this totorial we propose to install a Megamicros server on a [Ubuntu 22.04 Linux desktop or server](https://ubuntu.com/#download).
This installation is intended for developers.  
If you whish to use the server only, you can install *Megamicros* bimary packages.

## Installing the OS

OS is supposed installed. You have root acces to your desktop using *ssh* and network is running.
Update and upgrade the system:

```bash
    > sudo apt update
    > sudo apt upgrade
```

## Usb

Connect the Megamicros device on one of your USB port.
Your USB MegaMicro interface should appear in the list of available usb devices:

```bash
    > lsusb
    Bus 008 Device 002: ID fe27:ac03 DALEMBE Mµ
    Bus 008 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
    Bus 007 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
    Bus 006 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
    ...
```

You can see the MegaMicro device appeariog on bus ``002 Device 002`` with its ``fe27:ac03`` identifier.
Unfortunatly the Usb device is not accessible by users but only by root.
The most common way for giving usb rights to users is to create the following file at ``/etc/udev/rules.d``:

```bash

    > vi /etc/udev/rules.d/99-megamicro-devices.rules
    # Following lines add access to MegaMicro devices:
    # Order is Mu32-usb2, Mu32-usb3, Mu256 and Mu1024:
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac00", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac01", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac03", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac02", MODE="0666"
```

??? Warning

    Don't forget that if your desktop/server is a virtual machine, the USB ports should be declared as accessible on your VM.


## Python

`Python >= 3.10` is supposed installed.
If `python3-pip` and `virtualenv` are not installed. Install them and check:

```bash
    > apt install python3-pip virtualenv
    > pip --version
    > virtualenv --version
```

## System and C++ compiling tools

It is supposed that *gcc*  is already installed. 
In addition to *gcc*, you have to install the *cmake* utility:

```bash
    > apt install cmake
```

All libraries needed by *Megamicros* should be installed from now:

* `libssl-dev`: for crypted networking with OpenSSL
* `libhdh5-dev`: for data saving in H5 format
* `libusb-1.0`: for USB programing
* `libfftw3-3`: for computing the discrete Fourier transform (DFT) in one or more dimensions
* `libpaho-mqtt`: for MQTT protocol programing (IOT)
* `libwebsocketpp-dev`: for websocket communications
* `nlohmann-json3-dev`: for json programming

```bash
    > apt install -y \
        libssl-dev \
        libhdf5-dev \
        libusb-1.0-0 libusb-1.0-0-dev \
        libpaho-mqtt1.3 libpaho-mqtt-dev \
        libfftw3-3 libfftw3-bin libfftw3-dev \
        libwebsocketpp-dev \
        nlohmann-json3-dev
```

There is no debian package for the `paho_mqtt_c++` C++ wrapper to the `libpaho-mqtt` C library.
Therefore it is compiled within the `megamicros` package.

Now your system is up to date. You can install *megamicros-server*.


## Installing Megamicros-server

Clone the megamicros-server github repository. 
Make the `build` directory inside the `megamicros-server` directory and run *cmake*:

```bash
    > git clone git@github.com:bimea/megamicros-server.git
    > cd megamicros-server
    > mkdir build && cd build
    > cmake ..
    > make
    > make install
```

## Documentation

* [Ubuntu official site](https://ubuntu.com)

