#! /bin/bash
# This script is used to create a new release of the package.
# It will create a new tag, update the version number, and push to PyPI.
# Usage: ./mkrelease.sh

PACKAGE_NAME="megamicros"
# Remove previous build artifacts
rm -rf dist
rm -rf build
rm -rf $PACKAGE_NAME.egg-info

# Update the version number in the package
# Note that `sed` command syntax differs between macOS and Linux
VERSION=$(cd src && python -c "import $PACKAGE_NAME; print($PACKAGE_NAME.__version__)" | awk -F. '{print $1"."$2"."$3+1}')
echo "Updating package version to $VERSION" 
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/__version__=.*/__version__='$VERSION'/" src/$PACKAGE_NAME/__init__.py
else
    sed -i "s/__version__=.*/__version__='$VERSION'/" src/$PACKAGE_NAME/__init__.py
fi

#!/bin/bash
# Update the VERSION file:
echo "$VERSION" > VERSION

# Create a new git tag
git tag -a "v$VERSION" -m "Release version $VERSION"
git push origin "v$VERSION"

# Build the package and upload to PyPI
#!/bin/bash
set -e
# Ensure the required tools are installed
if ! command -v python3 &> /dev/null || ! command -v twine &> /dev/null; then
    echo "Required tools are not installed. Please install Python 3, Twine, and Build."
   # exit 1
fi

# Create the distribution files
python3 -m build --sdist
python3 -m build --wheel
python setup.py sdist bdist_wheel
twine upload -r bimea dist/*

# Clean up build artifacts
rm -rf dist
rm -rf build
rm -rf $PACKAGE_NAME.egg-info
echo "Release version $VERSION created and uploaded to PyPI."
# Update the version number in the package
echo "Version updated to $VERSION."
# Update the version number in the package
echo "New release created: v$VERSION"





#! /bin/bash
# This script is used to create a new release of the package.
# It will create a new tag, update the version number, and push to PyPI.
# Usage: ./mkrelease.sh

# python3 -m build --sdist
# python3 -m build --wheel
# python setup.py sdist upload -r bimea

# Build and upload to Conda
# conda-build my_package
# anaconda upload /path/to/your/package.tar.bz2