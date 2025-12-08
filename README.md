# megamicros

Megamicros Mems array library

## Install

You can install *Megamicros* using the Phyton pip utility or from the GitHub repository.

### Using pip install

First create your virtual environnement, then install:

```bash
  > virtualenv venv
  > source venv/bin/activate
  (venv) > pip install megamicros
```

Upgrading:

```bash
  > pip install --upgrade megamicros
```

### Installing from the GitHub repository 

Clone the *Megamicros* GitHub repository:

```bash
  > cd path_to_project
  > git clone https://github.com/bimea/megamicros.git
```

Create a virtual environnement in the ``megamicros`` repository and install the Python libraries needed for *Megamicros* to work:

```bash
  > cd path_to_project/megamicros
  > virtualenv venv
  > source venv/bin/activate
  > pip install -r requirements.txt
```

## Issues with usb access

### On windows systems

Before using the megamicros python library you must install the *Zadig* usb driver. 

### On MacOs / Linux systems

In some Linux distributions, only the root user has access to the USB port, so the following message may appear:

```bash
    ...
    aborting:  LIBUSB_ERROR_ACCESS [-3]
```

The USB devices are probably not accessible to users (test under root should be ok).
You must then give user access to the usb port by creating a new device rules file:

```bash
    > sudo vi /etc/udev/rules.d/99-megamicros-devices.rules
    # Insert next lines which give access to the Megamicros devices (Mu32-usb2, Mu32-usb3, Mu256, Mu1024):
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac00", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac01", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac03", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac02", MODE="0666"
```

User should be also in the ``plugdev`` group. Check the group file:

```bash
    > vi /etc/group
    ...
    plugdev:x:46:user_account_login
    ...
```

If there is no entry with your user account (``user_account_login`` above), then add your user account in the ``plugdev`` group.
Unplugg and plugg your usb device. All should be fine.

!!! Note

    Don't forget that if you run your Python programs on a virtual machine, usb ports should be declared as accessible on your VM.


## Megamicros documentation

You can also consult the *Megamicros* project web page at [readthedoc.bimea.io](https://readthedoc.biimea.io).
