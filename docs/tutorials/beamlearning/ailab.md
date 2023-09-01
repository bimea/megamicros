# Ailab tools and Notebooks

*Megamicros-Ailab* provides tools and examples for making machine learning programs for microphones arrays.

* [Beamforming](beamforming/index.md)

## Installing the package

```bash
    $ > cd /your_project_path
    $ > virtualenv venv
    $ > source venv/bin/activate
    (venv) $ > pip install megamicros_ailab
```

## Starting with Notebooks 

### ``querying_metadata.ipynb``

This notebook explains the metadata access of a REST database *Aidb* for Megamicros.
The metadata access allows access to the signals in the database by providing useful information for their search.

### ``querying_audio.ipynb``

This notebook aims to understand how to connect and then extract data from a REST database *Aidb* to perform learning.

### ``using_librosa.ipynb``

Librosa is a python package for music and audio analysis. 
It provides the building blocks necessary to create music information retrieval systems.
This Notebook is intended to show how you can use the Librosa python library with Megamicros.