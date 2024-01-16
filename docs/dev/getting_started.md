# Getting started

## TO BE REVIZED

## Installing the development environment


Megamicros comes with several packages:

* Megamicros, the main Python package, which includes the Megamicros library
* Megamicros_aidb, a Python package dedicaded to the REST database application
* Megamicros_aiboard, a Python frontend for the AiDB application
* Megamicros_ailab, another Python package with notebooks for audio and AI applications
* Megamicros_cpp, a C++ package for using Megamicros receiver as a network remote device
* Megamicros_readthedoc, the documentation package

If you are interested in developping for one of these packages, clone the package:

```bash
    $ > git clone https://gitlabsu.sorbonne-universite.fr/megamicros/Megamicros_aidb
    $ > cd Megamicros_aidb
    $ > virtualenv venv
    $ > source venv/bin/activate
    $ > pip install other_needed_packages
```

Add the source path of the package in your ``PYTHONPATH`` environment variable:

```bash
    $ > export PYTHONPATH=/your_path_to_your_project/Megamicros_aidb/src
```

You are ready for working.

Suppose now that you want to work on more than one package.
You just have to clone all corresponding repositories in the same way.
Here is an example: working on *Megamicro* and *Megamicros_aidb* packages, while the other are considered as ok:

```bash
    $ > mkdir Megamicros_project     # the root project directory
    $ > cd Megamicros_project
    $ > git clone https://gitlabsu.sorbonne-universite.fr/megamicros/Megamicros
    $ > git clone https://gitlabsu.sorbonne-universite.fr/megamicros/Megamicros_aidb
    $ > virtualenv venv
    $ > source venv/bin/activate
    $ > pip install other_needed_packages
```

Note that the virtualenv has been installed in the root project directory, not in the respective packages directories as before.
This is for VSC to see all the packages you are working on with the same common python interpreter.

Don't forget that you have now to declare two paths in your ``PYTHONPATH`` environment variable:

```bash
    $ > export PYTHONPATH=/your_path_to_your_project/Megamicros/src:/your_path_to_your_project/Megamicros_aidb/src
```

Last but not least.
The Pylint server in VSC whill not work correctly as it will not see your workig packages.
Create a ``.vscode/settings.json`` file and insert the correct paths:

``` json
    {
        "python.analysis.extraPaths": [
            "./Megamicros/src",
            "./Megamicros_aidb/src",
        ]
    }
```

All should be working right now.

## Using Megamicros packages

For users that only want to use some Megamicros package(s), the simplest way is to use the python *pip* installer on the private Megamicros repository:

```bash
    $ > pip install --extra-index-url https://pypi.bimea.io megamicros megamicros_aidb
```

## Working on all packages with `megamicros.sh` batch file

A special tool has been created to help you upgrading your local repositories.
This method concerns managing all Megamicros packages. 
The tool is located in the [Megamicros repository](https://gitlabsu.sorbonne-universite.fr/megamicros/Megamicros/-/blob/main/megamicros.sh).

Here are the main commands using `source megamicros.sh -h`:

```bash
    Usage: source megamicros [options]
    -a : activate venv if ./venv exists, otherwise create one and activate
    -i : create a local venv and clone Megamicros repositories in the current directory
    -[s|p|P [-c commit]] : performs status|pull|push command on every repositories
    -v : verbose mode
    -h : this help
```

Installing full Megamicros packages:

```bash
    $ > mkdir your_directory            # create your local directory
    $ > cd your_directory               # move to your ditrectory and place there the megamicros.sh file 
    $ > source megamicros.sh install    # install python virtual env, activate it, clone repositories and install python modules 
```

Every time you need:

```bash
    $ > source megamicros.sh status     # git status on all local repositories  
    $ > source megamicros.sh pull       # git pull on all repositories
    $ > source megamicros.sh push       # git push on all repositories

```

## Documentation

* [How to Publish an Open-Source Python Package to PyPI](https://realpython.com/pypi-publish-python-package/)
* [Python packaging: layout ](https://realpython.com/python-application-layouts/)