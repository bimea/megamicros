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
  (venv) > pip install --index https://pypi.biimea.io megamicros
```

You may want to not write systematically the repository address. 
Always specifying the pypi url on the command line is a bit cumbersome. 
For pip command this can be done by setting the environment variable ``PIP_EXTRA_INDEX_URL`` in your .bashr/.profile/.zshrc/.zprofile:

```bash
  export PIP_EXTRA_INDEX_URL=https://pypi.biimea.io
```

or by adding the following lines to ~/.pip/pip.conf:

```bash
  [global] extra-index-url = https://pypi.biimea.io
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

# Releases

## 2.0.31

* Change the DB_PROCESSING_DELAY_RATE value needed for realtime simulation from 3/10 to 2/10
