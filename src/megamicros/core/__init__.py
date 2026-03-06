# megamicros.core
#
# ® Copyright 2024-2026 Bimea
# Author: bruno.gas@bimea.io
#
# Core module for Megamicros library.

from .base import MemsArray
from .megamicros import Megamicros
from .config import AcquisitionConfig, UsbConfig, MemsArrayInfo

__all__ = [
    'MemsArray',
    'Megamicros',
    'AcquisitionConfig',
    'UsbConfig',
    'MemsArrayInfo',
]