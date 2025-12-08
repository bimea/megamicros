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
Copyright (C) 2024-2025 Bimea\n \
This program comes with ABSOLUTELY NO WARRANTY; for details see the source code\'.\n \
This is free software, and you are welcome to redistribute it\n \
under certain conditions; see the source code for details.\n' + '-'*20 + '\n' + '\
MegaMicros documentation is available on https://readthedoc.bimea.io.\n' + '-'*20