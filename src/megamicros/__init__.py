# megamicros.__init__.py
#
# ® Copyright 2024-2026 Bimea
# Author: bruno.gas@bimea.io
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
from importlib.metadata import version

def _get_version():
    try:
        # Try to read from VERSION file (for development)
        version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'VERSION')
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                return f.read().strip()
    except:
        pass
    
    try:
        # Try to get version from installed package (for installed package)
        return version('megamicros')
    except:
        pass
    
    # Fallback version
    return "unknown"

__version__ = _get_version()

welcome_msg = '-'*20 + '\n' + 'Megamicros python library\n \
Copyright (C) 2024-2026 Bimea\n \
This program comes with ABSOLUTELY NO WARRANTY; for details see the source code\'.\n \
This is free software, and you are welcome to redistribute it\n \
under certain conditions; see the source code for details.\n' + '-'*20 + '\n' + '\
MegaMicros documentation is available on https://readthedoc.bimea.io.\n' + '-'*20

# Utilities
from .log import log
from .exception import MuException

__all__ = [
    # Main classes
    
    # Configuration
    
    # Data sources
    
    # Legacy
    
    # Utilities
    'log',
    'MuException',
    '__version__',
]