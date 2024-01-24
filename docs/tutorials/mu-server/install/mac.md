# MacOS installation

In this totorial we propose to install a Megamicros server on a [MacOs apple system](https://apple.com).
This installation is intended for developers.  
If you whish to use the server only, you can install *Megamicros* bimary packages.

## Installing programming tools

Many of the libraries which are needed for *megamicros* to work are installed using *homebrew*. 
So you have first to install [homebrew](https://brew.sh/) if not already done.

Then:

```bash
    > brew update
    > brew upgrade
```

Install the `lsusb` utilitary :

```bash
    > brew install lsusb
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
If `python3-pip` and `virtualenv` are not installed. Install them.


## System and C++ compiling tools

It is supposed that *gcc*  is already installed. 
In addition to *gcc*, you have to install the *cmake* utility:

```bash
    >brew install cmake
```

All libraries needed by *Megamicros* should be installed from now:

* `openssl`: for crypted networking with OpenSSL
* `libusb`: for USB programing
* `hdf5`: for data saving in H5 format
* `websocketpp`: for websocket communications
* `fftw`: for computing the discrete Fourier transform (DFT) in one or more dimensions
* `libpaho-mqtt`: for MQTT protocol programing (IOT)
* `nlohmann-json`: for json programming

```bash
    > brew install openssl libusb hdf5 websocketpp fftw libpaho-mqtt nlohmann-json
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

Test with the following command:

```bash
    > megamicros-server -h
```

## Documentation

* [Ubuntu official site](https://ubuntu.com)
* [homebrew](https://brew.sh/)

