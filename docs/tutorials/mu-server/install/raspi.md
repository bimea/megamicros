# Standalone on Raspberry Pi


## Raspberry Pi installation


* First install the Raspberry Pi OS following Raspberrypi recommandations. 
* Updgrade de system:

```bash
    $ > sudo apt update                             # update/check repositories
    $ > sudo apt list --upgradable                  # See what should be upgraded
    $ > sudo apt full-upgrade                       # Run a full upgrade
    $ > sudo apt autoremove                         # Remove unused old packages
    $ > sudo apt autoclean                          
```

Give usb rights to users by creating the following file at ``/etc/udev/rules.d``:

```bash
    $ > vi /etc/udev/rules.d/99-megamicro-devices.rules
    # Floowing lines add access to MegaMicro devices:
    # Order is Mu32-usb2, Mu32-usb3, Mu256:
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac00", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac01", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac03", MODE="0666"
```

* Plug the Megamicro device in the usb port and see if the interface appears:

```bash
    $ > lsusb
    Bus 002 Device 002: ID fe27:ac03 DALEMBE Mµ
    Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
    Bus 001 Device 002: ID 2109:3431 VIA Labs, Inc. Hub
    Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
```
Yes it is. All seems going right but some libraries may still missing.

* The ``libcblas.so`` lib:

```bash
    $ > sudo apt install libatlas-base-dev
```

* The ``libhdf5_serial`` for H5 files:

```bash
    $ > sudo apt install -y libhdf5-dev
```

### Python >3.9 install


On 2022 july first, ``Python 3.9`` is the default python version installed with the Raspberry Pi OS. 
The only way to install the latest Python version on Raspberry Pi OS is to download it from the official website and install it from sources.
However Python 3.9 version is enough for running Megamicro software.

### Building a virtual environment


If the ``virtualenv`` programm does not exist on your OS, you can use the ``python`` command to create it:

```bash
    $ > cd your_local_directory_path
    $ > python -m venv venv
```

This should create the local ``venv`` environment. Activate it :

```bash
    $ > source venv/bin/activate
    (venv) $ > 
```

Then install the last Mu32 library:

```bash
    (venv) $ > pip install mu32
```

And run the MegaMicro autotest program:

```bash
    (venv) $ > mu32-autotest
```