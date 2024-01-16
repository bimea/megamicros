# Getting started

You can install the Megamicros library in two different ways:

* From the python pip installer utility
* By cloning the project's GitHub repository

## Pip install

As usual, you need to create a virtual environment, then install the Megamicros library.
The Megamicros library is no longer public, so you need to install it from `pypi.bimea.io` remote private repository:

```bash
    > cd your_path
    > virtualenv venv
    > source venv/bin/activate
    (venv) > pip install --extra-index-url http://pypi.bimea.io megamicros
```

All necessary dependencies are also installed. But others must be installed manually:

* libusb for usb communication
* hdf5 for H5 files
* alsa drivers for linux systems
* open-cv

Full installation details are given below.

## Install from GitHub repository

This is the second way to install Megamicros.
You can create a local copy of the official *Megamicros* repository:

* by going to the Github repository site ``https://github.com/bimea/megamicros`` and downloading the .zip image of the repository,
* by creating the repository on the command line:

```bash
    > cd your_path
    > git clone https://github.com/bimea/megamicros.git   # https mode
    > git clone git@github.com:bimea/megamicros.git       # ssh mode 
```

Then install all the dependencies from the `requirements.txt` file located in the Megamicros respository root directory :

```bash
    > cd your_path
    > virtualenv venv
    > source venv/bin/activate
    > cd megamicros
    > pip install -r requirements.txt
```

## About *libusb1*

*Megamicros* uses USB port to communicate with the antenna.
As such you should have installed the *libusb* library on your computer before using it.
Please see on the [libusb web site](https://github.com/libusb/libusb/wiki) how to install it on your own platform (linux, MacOs or windows).

### On linux systems

On linux systems it may arrives that an error message occurs such as ``so library not found``. 
Ususally this library is automatically installed. If not:  

```bash
    > sudo apt install -y libusb-1.0-0/stable 
    > sudo apt install -y libusb-1.0-0-dev/stable   # comment: dev lib is not mandatory 
```

It may also appears that usb tools are not installed (such as the ``lsusb`` command). 
Then install the following package:

```bash
    > sudo apt install -y usbutils
```

Don't forget that if you run your Python programs on a VM machine, usb ports should be delared as accessible on your VM.

In some Linux distributions, only the root user has access to the USB port, so the following message may appear:

```bash
    ...
    aborting:  LIBUSB_ERROR_ACCESS [-3]
```

If you try the same command as root and the error disappears: the USB devices are probably not accessible to users.
You can give user access to the usb port by creating a new device rules file:

```bash
    > sudo vi /etc/udev/rules.d/99-megamicros-devices.rules
    # Insert next lines which give access to the Megamicros devices (Mu32-usb2, Mu32-usb3, Mu256, Mu1024):
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac00", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac01", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac03", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac02", MODE="0666"
```

User should be also in the ``plugdev`` group. Tcheck the group file:

```bash
    > vi /etc/group
    ...
    plugdev:x:46:user_account_login
    ...
```

If there is no entry with your user account (``user_account_login`` above), then add your user account in the ``plugdev`` group.
Unplugg and plugg your usb device. All should be fine.

### On Mac systems

First you should have Homebrew installed on tour Mac (see [Homebrew](https://brew.sh)).
If not:

```bash
    > sudo /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Copy/paste and run next command to make brew command available inside the Terminal:

```bash
    > echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
```

Install the libusb library:

```bash
    > brew install libusb
```

## About *h5py*

*h5py* is the Python library needed for working with H5 files.
As for *libusb1* the c library should be installed.
If not:

```bash
    > apt install libhdf5-dev              # H5 library
```

### On Mac Os systems

Using brew:

```bash
    > brew install hdf5
```

## About *pyaudio*

*Pyaudio* is the audio library used by Megamicros for playing audio files.

### With Mac systems

No problems noted.

### With Linux systems

On Linux systems, problems may arise. 
At first you should have installed the PortAudio libraries:

```bash
    > apt install libasound-dev portaudio19-dev libportaudio2 libportaudiocpp0 python3-pyaudio 
    > apt install alsa-utils
```

In the event of a problem, check that the audio card(s) are correctly installed.

```bash
    > sudo arecord -l
```

Also be sure to add the user to the audio group:

```bash
    > sudo usermod -a -G audio user_account
```






## Verifications

Please, plugg in your Megamicros usb cable and test your usb device:

```bash
    > lsusb
    Bus 003 Device 002: ID fe27:ac03 DALEMBE Mµ
    Bus 003 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
    Bus 002 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
    Bus 001 Device 002: ID 0627:0001 Adomax Technology Co., Ltd QEMU USB Tablet
    Bus 001 Device 001: ID 1d6b:0001 Linux Foundation 1.1 root hub
```

You should see the fe27:ac03 vendor/product numbers correponding to the MegaMicro usb device (above the first line).
Then try the usbcheck program of the Mu32 python package acoording the two following ways:

```bash
    > python src/mu32/apps/mu32usbcheck.py        # from the Mu32 git repository
    > mu32-usbcheck                               # if you have installed de Mu32 python package
    --------------------
    Mu32 usb check program
    Copyright (C) 2022  DistalSense
    This program comes with ABSOLUTELY NO WARRANTY; for details see the source code.
    This is free software, and you are welcome to redistribute it
    under certain conditions; see the source code for details.
    --------------------
    2022-05-21 10:28:49,659 [INFO]:  .Checking usb devices...
    Found following devices:
    --------------------
    .ID fe27:ac03  Bus 003->1 Device 3
    .ID 1d6b:0003  Bus 003 Device 1
    .ID 1d6b:0002  Bus 002 Device 1
    .ID 0627:0001  Bus 001->1 Device 2
    .ID 1d6b:0001  Bus 001 Device 1
    --------------------
    Found MegaMicro device fe27:ac03
    Gain handle on USB device fe27:ac03
    --------------------
    Found following device fe27:ac03 characteristics :
    .Bus number: 3
    .Ports number: 1
    .Device address: 3 (0003)
    .Device name: M?
    .Manufacturer: DALEMBE
    .Serial number: None
    .Device speed:  [SUPER SPEED] (The device is operating at high speed (480MBit/s))
    --------------------
    2022-05-21 10:28:49,663 [INFO]: --------------------
    2022-05-21 10:28:49,663 [INFO]: MegaMicro: end
```






## Test your installation -- TO BE REVIZED


Connect the microphones antenna to the Mu32 box then the Mu32 box to your computer via the USB 3.0 link.
The indicator light on the box lights up, showing the power supply to the acquisition system via the USB link.
If the indicator does not come on, refer to the section :ref:`install:Installing Mu32`.

Execute the self-test program ``mu32autotest``:

```bash
	$ > mu32-autotest
```

This program tests the presence of the microphones on your antenna.
It tells you the number of microphones found and their respective numbers.
If something goes wrong, please visite the autotest help page :ref:`help:Autotest`.

The simplest of the test programs is the *run* program.
The ``run.py`` program performs acquisition with any number of microphones and plots the resulting signals.
Connect a 8 microphone antenna to one of the ethernet port of your acquisition unit.
Connect the Mu32 receiver to your computer USB port and launch the program:

```bash
	$ > mu32-run
```

You should see a multiplot graph showing one second of microphones signal:

.. image:: images/mu32run-1.jpg
   :width: 400
   :align: center
   :alt: multiplot graph of 8 microphones signals during one second

Another test programm is the programm *play*. 
Connect an 8 microphone antenna to the first ethernet port of your acquisition unit.
Connect a headset to the audio output port of your computer and launch the program:

```bash
	$ > mu32-play
```

This program selects microphones 0 and 7 of your antenna.
You should hear your sound environment through the headphones.
Note that the default audio output device value is 2. If it doesn't works for you, try to get your own device by typing:

```bash
	$ > python -m sounddevice
```

Try again using the ``--device`` option:

```bash
	$ > mu32-play --device <your_device_number>
```
Next is the DOA example program. ``mu32doa`` let you test your Mu32 antenna as a Direction Of Arrival detector using beamforming algorithm:

```bash
	$ > mu32-doa
```

Once the programm is started, press any key and have a look to the polar bar graph while moving somme sound source in front of your antenna.
The program runs on eight microphones. But you can upgrade it for more microphones by changing the programm (see the examples section for that).

.. image:: images/mu32doa-1.jpg
   :width: 600
   :align: center
   :alt: DOA graph for a 8 microphones antenna

## Installing from repository


Go to the ``mu32/src`` directory, start python, then run the test programs:

```bash
	$ > cd mu32/src
	$ > python
	>>> import mu32.examples.mu32autotest as autotest
	>>> autotest.main()
	...
	>>> import mu32.examples.mu32play as play
	>>> play.main()
```

You can proceed in a more direct way by calling the python programs:

```bash
	$ > cd /path_to_repository_dir/mu32/src
	$ > python mu32/examples/mu32play.py
```

But you should have added the mu32 module in the Python path before:

```bash
	export PYTHONPATH=$PYTHONPATH:/path_to_repository_dir/mu32/src
```

Your system is ready for use.

