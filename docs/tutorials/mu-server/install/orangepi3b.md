# Orangepi 3B as mini-laptop

In this totorial we propose to install a Megamicros server on a [Orange Pi 3B 4Go model](http://www.orangepi.org/) computer.
This installation is intended for developers.  
If you whish to use the server only, you can install binaries.

## Installing the OS

Download the Orange Pi 3B SD Card Image and write it to your SD micro card.
Follow the installation instruction.
Connect your mini-laptop to the router using a RJ45 ethernet cable. You should be able to open a ssh connection to your Jetson Nano from your laptop computer.

Update and upgrade the system:

```bash
    > sudo apt update
    > sudo apt upgrade
```

## Default account and megamicros account creating

* Login: orangepi
* Passwd: orangepi

Create a *megamicros* sudoer account and generate its *ssh-key*:

```bash
  > sudo adduser megamicros
  > sudo usermod -aG sudo megamicros
  > exit
  > ssh megamicros@orangepi3b
  > ssh-keygen
  > sudo -i                   # Test the sudo -i command allowed for sudoers
```

Then add the new *megamicros* user ssh key to your Github Bimea account.

## Run level 3 (muti-user)

The default run level on Orange Pi stations is usually set to 5 which is the graphic mode.
Since the graphic mode is useless, you can change it and set the default run level to 3 (multi-user target).
The multi-user target is more appropriate for running a megamicros server.

```bash
    > sudo systemctl get-default
    graphical.target
```

Before changing the default runlevel, check out the available targets:

```bash
    > sudo systemctl list-units --type=target
```

Issue the following command to change the default runlevel to runlevel 3 :

```bash
    > sudo systemctl set-default multi-user.target
    Created symlink /etc/systemd/system/default.target → /lib/systemd/system/multi-user.target.
```

Confirm the default runlevel:

```bash
    $ > sudo systemctl get-default
    multi-user.target
```

Reboot and check it out.

## Wifi

Enabling the Wifi is not mandatory. 
Identify the name of your wireless network interface:

```bash
    $ > ls /sys/class/net
    enp2s0 lo wlan0
```

Depending on your Ubuntu system the wireless network interface name would be something like: *wlan0* or like *wlp1s0*.
In our case, the wireless network interface name is `wlan0`.
Navigate to the /etc/netplan directory and edit the wifi configuration file and set the network name interface:

```bash
    network:
        ethernets:
            eth0:
                dhcp4: true
                optional: true
        version: 2
        wifis:
            wlan0:
                optional: true
                access-points:
                    "YOUR_NETWORK_NAME_HERE":
                        password: "THE_WIFI_PASSWORD_HERE"
                dhcp4: true
```

Apply the changes and connect to your wireless interface by executing the command bellow:

```bash
  > sudo netplan apply
```

Check that the wifi interface is working:

```bash
  > ip a
```

## Usb

Connect the Megamicros device on the Orange Pi usb3 port.
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

    Don't forget that if you run your programs on a virtual machine, the USB ports should be declared as accessible on your VM.


## Complementary tools

You can install tools for fan control (not mandatory):

```bash
    > apt install lm-sensors fancontrol read-edid i2c-tools
```

Check by looking at some sensor's values:

```bash
    > watch -n 2 sensors
    Every 2.0s: sensors                                                                                                                            orangepi3b: Sun Jan 21 14:14:45 2024

    soc_thermal-virtual-0
    Adapter: Virtual device
    temp1:        +41.2°C  (crit = +115.0°C)

    gpu_thermal-virtual-0
    Adapter: Virtual device
    temp1:        +41.9°C
```

## Python

`Python 3.10` is already installed. No need to upgrade.
If `python3-pip` and `virtualenv` are not installed. Install them and check:

```bash
    > apt install python3-pip virtualenv
    > pip --version
    > virtualenv --version
```

Your Orange Pi 3B device is now ready.
Next steps are devoted to c++ tools installation. 

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
* `nlohmann-json3-dev`: for json programming

```bash
    > apt install -y \
        libssl-dev \
        libhdf5-dev \
        libusb-1.0-0 libusb-1.0-0-dev \
        libpaho-mqtt1.3 libpaho-mqtt-dev \
        libfftw3-3 libfftw3-bin libfftw3-dev \
        nlohmann-json3-dev
```

There is no debian package for the `paho_mqtt_c++` C++ wrapper to the `libpaho-mqtt` C library.
Therefore it is compiled within the `megamicro` package.

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

* [Organge Pi official site](http://www.orangepi.org/)
* [Overview](http://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/details/Orange-Pi-3B.html)
* [Official tools](https://drive.google.com/drive/folders/1wuc59jK3Dqlt3XBiRdzJ5FBV-66lwJhD)

