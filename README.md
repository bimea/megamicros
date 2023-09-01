# megamicros

Megamicros Mems array library

## Installing from the Pypi megamicros repository using pip

Install with pip from your virtual environment:

```bash
  > virtualenv venv
  > source venv/bin/activate
  (venv) > pip install --index https://pypi.biimea.io
```

## Installing from the GitHub repository 

```bash
  > cd path_to_project
  > git clone https://github.com/bimea/megamicros.git
  > cd megamicros
  > virtualenv venv
  > source venv/bin/activate
  > pip install -r requirements.txt
```

Update your ``.bashrc/.zprofile/...`` by adding (or updating) the ``PYTHONPATH`` variable:

```bash
  > export PYTHONPATH=path_to_megamicros/megamicros/src
```

## Megamicros documentation

* [Direct access from the git repository](docs/index.md)
* Using the *mkdocs* server: this method requires the GitHub installation:
```bash
  > cd path_to_project/megamicros
  > source venv/bin/activate
  (venv) > pip install mkdocs "mkdocstrings[python]" mkdocs-material plantuml_markdown
  (venv) > mkdocs serve 
``` 
