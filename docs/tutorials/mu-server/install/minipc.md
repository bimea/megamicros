# Mini-PC installation

In this tutorial we propose to install a Megamicros server on a *Otazak* mini PC with Intel processor type.
Otazak systems are mini computers running on linux that can serve as MegaMicro server like Jetson or Raspberry.

## Computer installation

Follow the guideline given by the computer manufacturer. For Ortazak systems:

* Download a linux system iso image like [Ubuntu server](https://ubuntu.com/download/server)
* Install [balenaEtcher](http://www.balena.io/etcher) and flash the OS iso image to USB drive 
* Plug the usb drive on the Otazak system, reboot while pressing the F7 key to boot on the USB drive.
* Complete the OS installation
  
## Network configuration

Network configuration is automatic provided you have a ... server on your local network

### Configuring wifi network from command line

* Identify the name of your wireless network interface:

```bash
    $ > ls /sys/class/net
    enp2s0 lo wlp1s0
```

Depending on your Ubuntu system the wireless network interface name would be something like: ``wlan0`` or like in this case it is ``wlp1s0``.

* Navigate to the `/etc/netplan` directory and edit the wifi configuration file:

```bash
    $ > cd /etc/netplan
    $ > vi 00-installer-config-wifi.yaml
    network:
        ethernets:
            eth0:
                dhcp4: true
                optional: true
        version: 2
        wifis:
            wlp1s0:
                optional: true
                access-points:
                    "SSID-NAME-HERE":
                        password: "PASSWORD-HERE"
                dhcp4: true
```

* Apply the changes and connect to your wireless interface by executing the bellow command:
  
```bash
    $ > sudo netplan apply
```

Alternatively, if you run into some issues execute:

```bash
    $ > sudo netplan --debug apply
```

If all went well you would be able to see your wireless adapter connected to the wireless network by executing the ip command: 

```bash
    $ > ip a
```

## Update/upgrade

```bash
    $ > sudo apt update
    $ > sudo apt full-upgrade
    $ > sudo spt autoremove
    $ > sudo apt autoclean
```

## USB for MegaMicro users

Plug a Mu32 device on your USB interface and check it:

```bash
    $ > lsusb
    Bus 002 Device 003: ID 0bc2:2344 Seagate RSS LLC Portable
    Bus 002 Device 004: ID fe27:ac03 DALEMBE Mµ
    Bus 002 Device 002: ID 05e3:0626 Genesys Logic, Inc. USB3.1 Hub
    Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
    Bus 001 Device 007: ID 8087:0a2a Intel Corp. Bluetooth wireless interface
    Bus 001 Device 005: ID 0bda:0129 Realtek Semiconductor Corp. RTS5129 Card Reader Controller
    Bus 001 Device 008: ID 046d:0892 Logitech, Inc. C920 HD Pro Webcam
    Bus 001 Device 004: ID 05e3:0610 Genesys Logic, Inc. Hub
    Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
```

One can see the MegaMicro device ``fe27:ac03``, also the webcam device ``046d:0892`` end the Seagate portable hard disk ``0bc2:2344``. 

Make accessible usb interface to users :

```bash
    $ > sudo vi /etc/udev/rules.d/99-megamicro-devices.rules
    # Insert next lines which give access to the MegaMicro devices (Mu32-usb2, Mu32-usb3, Mu256):
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac00", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac01", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac03", MODE="0666"
```

Don't forget to unplug/plug the Megamicro usb cable.

## Complementary tools

You can install tools for fan control:

```bash
    $ > apt install lm-sensors fancontrol read-edid i2c-tools
```

Here is a command for watching sensor's values:

```bash
    $ > watch -n 2 sensors
```

## Python 3.10 installation

On Ubuntu 22.04 version Python3.10 is already installed. Ortherwize see previous sections.
If ``virtualenv`` is not installed:

```bash
    $ > sudo apt install python3-virtualenv 
```

## Open CV installation

With the Ubuntu server some libraries used by Open CV may be not installed. Complete the by installing them:

```bash 
    $ > sudo apt install python3-opencv
```

## MegaMicro installation

Follow the Mu32 documention:

```bash
    $ > git clone git@github.com:distalsense/Mu32.git
```

Install a virtual environment and the appropriate libraries:

```bash
    $ > cd Mu32
    $ > virtualenv venv
    $ > source venv/bin/activate
    $ > pip install libusb1 numpy matplotlib sounddevice h5py scipy websockets opencv-python
```

Add the ``Mu32``lib in your ``PYTHONPATH``:

```bash
    $ > vi /home/your_home_dir/.bashrc
    PYTHONPATH=$PYTHONPATH:/home/gas/Mu32/src       # add this line
```

Test the MegaMicro by checking usb:

```bash
    $ > python src/mu32/apps/mu32usbcheck.py
```





## Documentation



