# Megamicros AI Coding Agent Instructions

## Project Overview
**Megamicros** is a Python library for controlling and processing data from MEMS microphone arrays (32 to 1024 microphones). It interfaces with custom USB hardware (Mu32, Mu256, Mu1024) and provides beamforming algorithms for acoustic source localization.

**Current version**: 3.0.6 (tracked in `VERSION` file at repository root)

## Architecture Layers

### 1. Hardware Layer (`usb.py`)
- **USB communication** via `libusb1` with custom hardware
- **Vendor/Product IDs**: `0xFE27` / `0xAC00-0xAC03` (Mu32-usb2/3, Mu256, Mu1024)
- **FPGA commands** via control writes (e.g., `MU_CMD_START`, `MU_CMD_INIT`)
- **Thread-safe Queue** for asynchronous bulk transfers (default 8 buffers)
- **Platform-specific USB rules**: Linux requires udev rules in `/etc/udev/rules.d/99-megamicros-devices.rules`

### 2. Core Layer (`core/`)
- **`base.py`**: `MemsArray` abstract base class
  - Manages active/available MEMS, sampling frequency, frame length, duration
  - Non-blocking `run()` + blocking `wait()` pattern for real-time processing
  - Embeds custom `Queue` that drops oldest frames when full (not standard blocking behavior)
- **`mu.py`**: `Megamicros` concrete implementation
  - Hardware commands: `MU_CMD_RESET`, `MU_CMD_ACTIVE`, `MU_CMD_DATATYPE`
  - 24-bit signed quantization (`MU_MEMS_QUANTIZATION = 23`)
  - Default sensibility: `3.54e-6 Pa/digit` (`MU_MEMS_SENSIBILITY`)
  - Supports `int32` and `float32` datatypes

### 3. Data Persistence (`muh5.py`)
- **HDF5 format** for signal/video storage via `h5py`
- **Structure**: `/muh5` group with attrs (sampling_frequency, mems, analogs, etc.)
- **Read-only interface**: `MuH5` class for loading recorded data
- **Video support**: adaptive FPS, frame counts, multi-dataset

### 4. Acoustics Layer (`acoustics/`)
- **`bmf.py`**: Beamforming algorithms
  - `BeamformerFDAS`: Frequency Domain Delay-and-Sum
  - Methods: `'full'`, `'max'`, `'mean'`, `'gauss'`, `'omp'`
  - Requires 3D MEMS positions (numpy arrays, meters) and 3D target locations
- **`omp.py`**: Orthogonal Matching Pursuit for source localization
- **`sgcal_*.py`**: Geometric calibration tools (Charles Vanwynsberghe's method)

### 5. Utilities
- **`geometry.py`**: Antenna geometries (`circle()`, `horizontalPlan()`)
- **`mqtt.py`**: MQTT client for remote logging/control
- **`log.py`**: Centralized logging (colored console + file `./megamicros.log`)
- **`exception.py`**: Base `MuException` class

## Critical Conventions

### Naming Patterns
- **`Mu` prefix**: Megamicros-specific (e.g., `MuException`, `MuH5`, `Megamicros`)
- **MEMS vs Analogs**: Distinguish microphones (`mems`) from analog inputs (`analogs`)
- **Available vs Active**: `available_mems` (hardware capability) vs `active_mems` (current configuration)

### Data Structures
- **Positions**: Always 3D numpy arrays `shape=(N, 3)` in meters (absolute coordinates)
- **Frames**: Numpy arrays `shape=(channels, samples)` where channels include counter if enabled
- **Queue iteration**: Use `for data in antenna:` to consume frames (empties queue)

### Versioning
- **Single source of truth**: `VERSION` file at root (plain text, e.g., `3.0.6`)
- **Dynamic import**: `__init__.py` reads `VERSION` file or falls back to `importlib.metadata.version()`
- **Release workflow**: `mkrelease.sh` auto-increments patch version, tags git, builds and uploads to PyPI

### Hardware Specifics
- **Counter channel**: Optional first channel for frame counting (toggle via `counter=True`)
- **Transfer size**: Always 4 bytes per sample (`TRANSFER_DATAWORDS_SIZE = 4`) regardless of int32/float32
- **FPGA reset sequence**: `MU_CMD_FX3_RESET` → `MU_CMD_FX3_PH` for hard reset

## Development Workflows

### Environment Setup
```bash
virtualenv venv
source venv/bin/activate  # or `venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
```

### Build & Install
```bash
pip install -e ./  # Editable install from pyproject.toml
```

### Release Process
```bash
./mkrelease.sh  # Auto-increments version, creates git tag, pushes to PyPI
```

### Testing Pattern (from notebooks)
```python
from megamicros.log import log
from megamicros.core.mu import Megamicros

log.setLevel("INFO")  # Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

antenna = Megamicros()
antenna.run(
    mems=antenna.available_mems,
    sampling_frequency=50000,
    duration=10,
    frame_length=1024,
    datatype='int32'
)

# Real-time processing (iterate before wait)
for data in antenna:
    process(data)  # Non-blocking iteration
antenna.wait()  # Always call to join threads
```

## Key Files & Entry Points
- **Core classes**: [src/megamicros/core/base.py](src/megamicros/core/base.py), [src/megamicros/core/mu.py](src/megamicros/core/mu.py)
- **USB interface**: [src/megamicros/usb.py](src/megamicros/usb.py)
- **Beamforming**: [src/megamicros/acoustics/bmf.py](src/megamicros/acoustics/bmf.py)
- **CLI scripts**: `megamicros` and `megamicros-version` (defined in `pyproject.toml`)
- **Examples**: [notebooks/](notebooks/) (01-06 numbered tutorials)

## Common Pitfalls
1. **Forgetting `wait()`**: Non-blocking `run()` requires explicit `wait()` or threads leak
2. **Queue timeout**: Default 1s timeout adds to total acquisition time (e.g., 1s acq + 1s timeout = 2s)
3. **USB permissions**: Linux users must configure udev rules (see README)
4. **Position units**: Always meters, not mm (antenna diagrams may show mm for readability)
5. **Datatype confusion**: FPGA always sends 32-bit words; `int32` is raw ADC, `float32` is pre-scaled

## External Dependencies
- **Core**: `numpy`, `scipy`, `h5py`, `libusb1`, `matplotlib`, `imageio`
- **Optional**: `pyroomacoustics` (for advanced simulations)
- **Build system**: `setuptools>=42`, `wheel`, `cmake_build_extension`

## Documentation & Support
- **Main docs**: https://readthedoc.bimea.io
- **Repository**: https://github.com/bimea/megamicros
- **Author**: Bruno Gas <bruno.gas@bimea.io>
- **License**: MIT

---

**For v4.0.0 Refactoring**: This is v3.x. Major architectural changes should branch from `main` as `feature/4.0.0-refactor`.
