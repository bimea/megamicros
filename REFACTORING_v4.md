# Megamicros v4.0.0 Refactoring Guide

## Overview

Version 4.0.0 introduces a major architectural refactoring while maintaining **full backward compatibility** with v3.x.

## Key Changes

### 1. Multi-Source Architecture

The new design separates **data acquisition** from **data sources**, enabling:

- **USB hardware** (production)
- **H5 file playback** (analysis)
- **WebSocket remote** (distributed arrays)
- **Random generator** (testing without hardware)

All sources implement the `DataSource` protocol, providing a unified interface.

### 2. Structure

```
src/megamicros/
├── core/
│   ├── base.py              # MemsArray (legacy base class)
│   ├── megamicros.py        # NEW: Main facade class
│   ├── config.py            # NEW: Configuration dataclasses
│   └── mu.py                # Legacy Megamicros implementation (v3.x)
├── sources/                 # NEW: Data source module
│   ├── __init__.py
│   ├── base.py             # DataSource protocol
│   ├── usb.py              # USB hardware source
│   ├── h5.py               # HDF5 file source
│   ├── random.py           # Random generator source
│   └── websocket.py        # WebSocket source (🚧 WIP)
├── acoustics/
├── usb.py                   # Low-level USB interface
├── muh5.py                  # Legacy H5 reader
└── ...
```

### 3. Usage Examples

#### Auto-Detection (v4.0)

```python
from megamicros import Megamicros

# Auto-detects USB or falls back to random
antenna = Megamicros()
antenna.run(mems=[0,1,2,3], sampling_frequency=50000, duration=10)

for frame in antenna:
    process(frame)

antenna.wait()
```

#### Explicit Sources (v4.0)

```python
# H5 file playback
antenna = Megamicros(filepath='recording.h5')

# Remote device
antenna = Megamicros(url='ws://antenna.local:8080')

# Force USB
antenna = Megamicros(usb=True)

# Random (testing)
antenna = Megamicros()  # No hardware → random
```

#### Configuration Objects (v4.0)

```python
from megamicros import Megamicros, AcquisitionConfig

config = AcquisitionConfig(
    mems=[0, 1, 2, 3],
    sampling_frequency=50000,
    frame_length=1024,
    duration=10,
    datatype='float32'
)

antenna = Megamicros()
antenna.run(**config.__dict__)
```

#### Backward Compatibility (v3.x still works)

```python
# All v3.x code works unchanged
from megamicros import Megamicros

antenna = Megamicros()
antenna.run(
    mems=[0,1,2,3],
    sampling_frequency=50000,
    duration=10,
    frame_length=1024
)

for data in antenna:
    process(data)

antenna.wait()
```

## Development Workflow

### Setup

```bash
# Create virtual environment
virtualenv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install in editable mode
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"
```

### Testing Without Hardware

```bash
# Run architecture tests
python test_v4_architecture.py

# Test specific source
python -c "
from megamicros import Megamicros
antenna = Megamicros()  # RandomDataSource
antenna.run(mems=[0,1,2,3], duration=1)
print(f'Frames: {sum(1 for _ in antenna)}')
antenna.wait()
"
```

### Adding a New Data Source

1. Create `sources/mysource.py`
2. Implement `DataSource` protocol:
   ```python
   from .base import BaseDataSource
   
   class MyDataSource(BaseDataSource):
       def _do_configure(self, config): ...
       def _do_start(self): ...
       def _do_stop(self): ...
       def _generate_frames(self): ...
   ```
3. Add to `sources/__init__.py`
4. Update `Megamicros._create_source()` factory

## Migration from v3.x

### No Changes Needed

Existing code continues to work:

```python
# v3.x code - still works in v4.0
antenna = Megamicros()
antenna.run(mems=antenna.available_mems, sampling_frequency=50000)
for data in antenna:
    process(data)
antenna.wait()
```

### Optional Modernization

You can progressively adopt v4.0 patterns:

```python
# Use explicit sources
antenna = Megamicros(filepath='data.h5')

# Use configuration objects
from megamicros import AcquisitionConfig
config = AcquisitionConfig(mems=[0,1,2,3], sampling_frequency=50000)
antenna.run(**config.__dict__)

# Leverage type hints
from megamicros import Megamicros, AcquisitionConfig

def process_antenna(antenna: Megamicros, config: AcquisitionConfig):
    antenna.run(**config.__dict__)
    ...
```

## Breaking Changes

**None** - v4.0.0 maintains full API compatibility with v3.x

However, Python 3.9+ is now required (was 3.7+).

## Roadmap

- [ ] Complete WebSocketDataSource implementation
- [ ] Add pytest test suite
- [ ] Add mypy type checking
- [ ] Improve USB error handling
- [ ] Add context manager support (`with antenna.run(...):`)
- [ ] Benchmark performance vs v3.x

## Questions?

- See `notebooks/` for usage examples
- Read `.github/copilot-instructions.md` for AI agent guidance
- Check `CHANGELOG` for detailed changes
