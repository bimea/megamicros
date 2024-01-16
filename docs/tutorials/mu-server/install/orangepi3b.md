# Orangepi 3B as mini-laptop

In this totorial we propose to install a Megamicros server on a [Orange Pi 3B 4Go model](http://www.orangepi.org/) computer.

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

Then add the new *megamicros* user ssh key to the Github Bimea account.

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
````

Issue the following command to change the default runlevel to runlevel 3 (nothing but a multi-user.target):

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

Identify the name of your wireless network interface:

```bash
    $ > ls /sys/class/net
    enp2s0 lo wlan0
```

The wireless network interface name is `wlan0`.
Depending on your Ubuntu system the wireless network interface name would be something like: *wlan0* or like *wlp1s0*.
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
                  "DISTALSENSE":
                      password: "BEKFMBW8TU"
              dhcp4: true
```

Apply the changes and connect to your wireless interface by executing the bellow command:

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
```

You can see the MegaMicro device appeariog on bus ``002 Device 002`` with its ``fe27:ac03`` identifier.
Unfortunatly the Usb device is not accessible by users but only by root.
The most common way for giving usb rights to users is to create the following file at ``/etc/udev/rules.d``:

```bash

    > vi /etc/udev/rules.d/99-megamicro-devices.rules
    # Floowing lines add access to MegaMicro devices:
    # Order is Mu32-usb2, Mu32-usb3, Mu256, Mu1024:
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac00", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac01", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac03", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac02", MODE="0666"
```

## Complementary tools

You can install tools for fan control:

```bash
    > apt install lm-sensors fancontrol read-edid i2c-tools
```

Check by looking at some sensor's values:

```bash
    > watch -n 2 sensors
```

## Python

`Python 3.10` is already installed. No need to upgrade.

`python3-pip` and `virtualenv` are not installed. Install them and check

```bash
    > apt install python3-pip virtualenv
    > pip --version
    > virtualenv --version
```

## System and C++ compiling tools

You have to install the c++ toolkit for building the *megamicros-server* program.

...

## Documentation

* [Organge Pi official site](http://www.orangepi.org/)
* [Overview](http://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/details/Orange-Pi-3B.html)
* [Official tools](https://drive.google.com/drive/folders/1wuc59jK3Dqlt3XBiRdzJ5FBV-66lwJhD)

