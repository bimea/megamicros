# megamicros

Megamicros Mems array library

## Install

You can install *Megamicros* using the Phyton pip utility or from the GitHub repository.

### Using pip install

*Megamicros* is stored in a private PyPi repository so that you have to mention it. 
First create your virtual environnement, then install:

```bash
  > virtualenv venv
  > source venv/bin/activate
  (venv) > pip install --upgrade --extra-index-url https://repository.bimea.io/api-pypi megamicros
```

You may want to not write systematically the repository address. 
Always specifying the pypi url on the command line is a bit cumbersome. 
For pip command this can be done by setting the environment variable ``PIP_EXTRA_INDEX_URL`` in your .bashr/.profile/.zshrc/.zprofile:

```bash
  export PIP_EXTRA_INDEX_URL=https://pypi.bimea.io/api-pypi
```

or by adding the following lines to ~/.pip/pip.conf:

```bash
  [global] extra-index-url = https://pypi.bimea.io/api-pypi
```

Installing *megamicros* becomes as simple as:

```bash
  > pip install megamicros
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

### Issues with usb access

It may appears that usb tools are not installed (such as the ``lsusb`` command).
Then install the following package:

```bash
    > sudo apt install -y usbutils
```

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

## Releases

### 3.0.2

* Add Data classes for signal and video
* Define the default sensibilitu of analogs to 0.33 (see megaicros.core.mu)

### 3.0.1

* Add the sgcal diffuse antenna calibration of Charles Vanwynsberghe(see: https://github.com/cvanwynsberghe/sgcal-jasa).
* Add the `ParisParcGeoCalibDiffuse` Notebook as example of geocalibrating using `calibrate.py` and `covariancegpu.py` on the Sorbonne University Innovation City construction site (to be revized).

### 3.0.0

New major release

* Usb interface Refactoring

### 2.1.30-2.1.34

The next minor release (2.2) is comming soon.
The core of megamicros will not change but most of the tools will be reorganized

* Update the release making process
* Import mqtt and muh5 from the ol library megamicros_tools

### 2.1.29

* Minor updates on megamicros.mu

### 2.1.13-2.1.28

* Prepare the next major release
* Transform megamicros_tools package in megamicros.tools sub package
* Major updates in tools/acoustics/location.py
* Add BFE on limited frequency bandwith
* Add getBFE function in core/h5 to get BFE data from MµH5 files
* fix bug in tools/signal.py: `megamicros.exception` instead of `import exception`.

### 2.1.12

* Fix `get()` method error when getting signals from H5 file

### 2.1.11

* Fix the issue of H5 file bad recording

### 2.1.10

* Add system_type property to Mµ antenna systems

### 2.1.5 - 2.1.9

* Fix compatibility problems with libusb (Zadig) under windows

### 2.1.3 - 2.1.4

* Add the `megamicros` program

### 2.1.1 - 2.1.2

* Minor modifications

### 2.1.0

* Remove the aidb application from the package in favor of the megamicros-aidb new package
* Remove the aiboard application from the package in favor of the megamicros-aiboard new package
* megamicros-tools becomes a dependency of megamicros
* Remove log, mqtt, muh5, exception, previously moved in megamicros-tools
  * Please use in your code `from megamicros_tools.log import log` instead of `from megamicros.log import log`
  * Same with `exception`, `mqtt` and `muh5`.

### 2.0.75

* Remove docs form this repository. Documentation is now available on its on repository (megamicros-doc)

### 2.0.74

* Add 'real_time' option in MesmArrayH5 for playing H5 files
* There is still a bug to fix wen 'real_time=True': the delay which is imposed for real time respect leads to problem in the queue management

### 2.0.72 to 2.0.73

* Add download of H5 files as wav files du dbAi

### 2.0.71

* Add the megamicros base library for Megamicros device monitoring

### 2.0.70

* Fix bug in dataset concerning bad reshape when samples are shorter than split size

### 2.0.56 to 2.0.69

* Update aidb dataset by adding instance storing
* Update aiboard to work fine with the nexw dataset

### 2.0.55

* fix the download error in dataset samples duration

### 2.0.54

* update http address for aiboard

### 2.0.53

* ailab/sataset updated for data split and temporal zero padding

### 2.0.48, 2.0.49, 2.0.50, 2.0.51, 2.0.51, 2.0.52

* New Dataset view and serializer for AiDB

### 2.0.47

### 2.0.46

* Fix dataset error for entry removing in AiDB

### 2.0.45

* Fix error made by the default limit=20 for label downloading

### 2.0.44

* Create torch dataset for AiDB signals

### 2.0.43

* Add dbchantier database to megamicros-aiboard program configuration

### 2.0.42

* Compute power in decibels  on database signals

### 2.0.41

* Add the `fft` datatype for getting fft signals from the Megamicros broadcast server using the `run` method

### 2.0.40

* Add database endpoint for extracting samples (sourcefile/samples) and the library tools that comes with 

### 2.0.39

* Add direct signal samples extraction from AI database 

### 2.0.38

* Fix bug `TypeError: MemsArray.setAvailableAnalogs() got an unexpected keyword argument 'available_analogs_number'` in db.py

### 2.0.37

* Fix bug `TypeError: MemsArray.setAvailableMems() got an unexpected keyword argument 'available_mems_number'` in db.py

### 2.0.36

* Some updates

### 2.0.35

* Fix bug in H5 files reading

### 2.0.34

* Corrections in MemsArrayWS for using methods `settings()` and `selftest()` as *async* methods

### 2.0.33

### 2.0.32

* Before correcting DB_PROCESSING_DELAY_RATE issue, skip the realtime process

### 2.0.31

* Change the DB_PROCESSING_DELAY_RATE value needed for realtime simulation from 3/10 to 2/10

## Pypi

```bash
# Installer les outils nécessaires
pip install --upgrade build twine
```

Créez aussi un compte sur <https://test.pypi.org> pour tester d'abord.

Créez un fichier `~/.pypirc` :

```bash
[pypi]
username = __token__
password = pypi-YOUR_API_TOKEN_HERE

[testpypi]
username = __token__
password = pypi-YOUR_TEST_API_TOKEN_HERE
```

Remarque : Il est recommandé d'utiliser des tokens API plutôt que votre mot de passe. Générez-les depuis votre compte PyPI dans : Account Settings → API tokens.

### Builder le package

```bash
# Depuis la racine de votre projet
python -m build
```

Cela créera deux fichiers dans le dossier dist/ :

* `megamicros-X.X.X.tar.gz` (source distribution)
* `megamicros-X.X.X-py3-none-any.whl` (wheel distribution)

(Optionnel) Tester sur TestPyPI d'abord

```bash
# Upload sur TestPyPI
python -m twine upload --repository testpypi dist/*

# Tester l'installation
pip install --index-url https://test.pypi.org/simple/ megamicros
```

Uploader sur PyPI officiel

```bash
# Vérifier les distributions
python -m twine check dist/*

# Upload sur PyPI
python -m twine upload dist/*
```

Vérifier

Après l'upload, votre package sera disponible à :

https://pypi.org/project/megamicros/
Et installable via :

```bash
pip install megamicros
```

Points importants à vérifier avant l'upload

1. Version unique : Assurez-vous que le numéro de version dans VERSION n'a jamais été uploadé
2. README.md : Doit être bien formaté (sera affiché sur PyPI)
3. Licence : Vérifiez que votre licence GPL est correctement spécifiée
4. Nom du package : "megamicros" doit être disponible sur PyPI (vérifiez d'abord)

Workflow recommandé pour les mises à jour futures

```bash
# 1. Mettre à jour VERSION
echo "3.0.2" > VERSION

# 2. Nettoyer les anciens builds
rm -rf dist/ build/ src/megamicros.egg-info/

# 3. Builder
python -m build

# 4. Vérifier
python -m twine check dist/*

# 5. Uploader
python -m twine upload dist/*
```

Note : Une fois un package uploadé avec une version donnée, vous ne pouvez plus modifier ou re-uploader cette version. Vous devez incrémenter le numéro de version pour chaque nouveau upload.

Token (bimea-token):

pypi-AgEIcHlwaS5vcmcCJGI0N2E3YmUzLTQ5MTctNGNjOS1iMjdkLWQ1MmUxNjdlMjI0YwACKlszLCI4MjBlZjBkMi04MGM4LTQ3MzAtODNlNS0wODRhYzg2NjQyYmIiXQAABiBi9AFbwpQiJ4hSEsOWQ6rlf1g7x9OQ1LQcIt8KQgQP5Q
