# Megamicros Packaging

Packaging is the process of creating a Megamicros Python package versioned for pip.
Since the project has to be saved in a repository, one has first to create the GitHub Megamicros repository:

* Create the `bimea` free organization under GitHub
* Create the `megamicros` repository
* Add the `tmp/` line in the python model `.gitignore` file`
* Declare your ssh-key for direct cloning/pulling/pushing
* Clone the repository in your local project directory:

```bash
    > cd your_path
    > git clone git@github.com:bimea/megamicros.git
```

The local copy is now ready and one can add the Python project structure:

```bash
    megamicros/
    ├── LICENSE
    ├── CHANGELOG
    ├── pyproject.toml
    ├── README.md
    ├── VERSION
    ├── MANIFEST.in
    ├── src/
    │   └── megamicros/
    │       ├── __init__.py
    │       ├── log.py
    │       ├── core/
    │           ├── __init__.py
    │           └── base.py
    └── tests/
```

A module is a file containing Python definitions and statements.
The file name is the module name with the suffix `.py` appended.

Packages are a way of structuring Python’s module namespace by using “dotted module names”.
The `core` directory is a first package name.
The `__init__.py` files are required to make Python treat directories containing the file as packages.
`__init__.py` can just be an empty file, but it can also execute initialization code for the package or set the `__all__` variable.
Packages can be structured into subpackages using sub directories.

`tests/` is a placeholder for test files. Leave it empty for now.

## Packaging the project

Before you can build wheels and sdists for the project, you’ll need to install the build package:

```bash
    > pip install build
```

Then set the version number of your build in the text file `VERSION`.
Create a source distribution (which is unbuilt):

```bash
    > python3 -m build --sdist
```

and a build distribution:

```bash
    > python3 -m build --wheel
```

The build process creates an `__init__.py` file in the package directory with some inputs like `__version__` copied from the `VERSION` previously defined file.
Don't forget to set the good version number in the `VERSION` text file before making the package.
If a `./build` directory exists from a previous built, delete it before building your new package version.

## Testing

Test your built package: create a new directory with a new virtual environment and try *pip install*:

```bash
    > mkdir test && cd test && virtualenv venv
    > source venv/bin/activate
    > pip install your_path/megamicros
```

Don't forget to push the project new version in the repository:

```bash
    > mkdir test && cd test && virtualenv venv
    > source venv/bin/activate
    > cd your_path/megamicros
    > git add .
    > git commit -m "initial push"
    > git push
```

## Publishing

If you intend to use the public *PyPi* reprository, create an account on ``https://pypi.org`` and upload your distributions:

```bash
    > pip install twine
    > twine upload dist/*
```

When using a private repository as ``pypi.biimea.io``, set the ``.pypirc`` configuration file in your home directory. In the following example, two entries are set: the official python repository and your private repository:

```rc
[distutils]
index-servers =
pypi
biimea

[pypi]
username:<your_pypi_username>
password:<your_pypi_passwd>

[biimea]
repository: https://pypi.biimea.io
username: <some_username>
password: <some_passwd>
```

Then from within the directory of the python-project you wish to upload, issue this command:

```bash
    > python setup.py sdist upload -r biimea
```

See the [Python private repository](python_repos.md) section for building a private repository.

## Documentation

* [Packaging for python repository with pip](https://packaging.python.org/tutorials/packaging-projects/)
* [Packaging and distributing projects](https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/)
* [Setuptools Quickstart](https://setuptools.pypa.io/en/latest/userguide/quickstart.html)
* [Command Line Scripts](https://python-packaging.readthedocs.io/en/latest/command-line-scripts.html)
* [Build your first pip Package](https://dzone.com/articles/executable-package-pip-install)
* [Identification des versions](https://www.python.org/dev/peps/pep-0440/)
* [Classifiers](https://pypi.org/classifiers/)
* [Building Hybrid Python/C++ Packages](https://python.plainenglish.io/building-hybrid-python-c-packages-8985fa1c5b1d)
