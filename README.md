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
  (venv) > pip install --index https://pypi.bimea.io megamicros
```

You may want to not write systematically the repository address. 
Always specifying the pypi url on the command line is a bit cumbersome. 
For pip command this can be done by setting the environment variable ``PIP_EXTRA_INDEX_URL`` in your .bashr/.profile/.zshrc/.zprofile:

```bash
  export PIP_EXTRA_INDEX_URL=https://pypi.bimea.io
```

or by adding the following lines to ~/.pip/pip.conf:

```bash
  [global] extra-index-url = https://pypi.bimea.io
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

Update your ``.bashrc/.zprofile/...`` by adding (or updating) the ``PYTHONPATH`` variable:

```bash
  > export PYTHONPATH=path_to_megamicros/megamicros/src
```

Create a virtual environnement in the ``megamicros`` repository and install the Python libraries needed for *Megamicros* to work:

```bash
  > cd path_to_project/megamicros
  > virtualenv venv
  > source venv/bin/activate
  > pip install -r requirements.txt
```

## Megamicros documentation

You have direct access to the documentation on the [GitHub repository web page](docs/index.md).
You can also consult the *Megamicros* project web page at [readthedoc.biimea.io](https://readthedoc.biimea.io).
Finally, you can install the Python *mkdocs* server and targeting the local web page it creates with your browser:

```bash
  cd path_to_project/megamicros
  > source venv/bin/activate
  (venv) > pip install mkdocs "mkdocstrings[python]" mkdocs-material plantuml_markdown
  (venv) > mkdocs serve
  [09:50:16] Serving on http://127.0.0.1:8000/
```

## Releases

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
