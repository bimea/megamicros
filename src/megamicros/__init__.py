import os
try:
    from importlib.metadata import version
except ImportError:
    # Fallback for Python < 3.8
    from importlib_metadata import version

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


# v4.0.0 Modern API
from .core.megamicros import Megamicros
from .core.config import AcquisitionConfig, UsbConfig, MemsArrayInfo
from .sources import DataSource, UsbDataSource, H5DataSource, RandomDataSource

# Legacy v3.x compatibility
from .core.base import MemsArray
from .muh5 import MuH5

# Utilities
from .log import log
from .exception import MuException

__all__ = [
    # Main classes
    'Megamicros',
    'MemsArray',
    
    # Configuration
    'AcquisitionConfig',
    'UsbConfig',
    'MemsArrayInfo',
    
    # Data sources
    'DataSource',
    'UsbDataSource',
    'H5DataSource',
    'RandomDataSource',
    
    # Legacy
    'MuH5',
    
    # Utilities
    'log',
    'MuException',
    '__version__',
]