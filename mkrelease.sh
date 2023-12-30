#! /bin/bash
# This script is used to create a new release of the package.
# It will create a new tag, update the version number, and push to PyPI.
# Usage: ./mkrelease.sh

python3 -m build --sdist
python3 -m build --wheel
python setup.py sdist upload -r biimea