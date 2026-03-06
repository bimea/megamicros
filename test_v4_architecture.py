#!/usr/bin/env python3
"""
Test script for Megamicros v4.0.0 architecture.

Tests the new multi-source system without requiring hardware.
"""

import sys
import numpy as np

def test_random_source():
    """Test RandomDataSource."""
    print("Testing RandomDataSource...")
    
    from megamicros import Megamicros
    
    # Create antenna with random source (no hardware needed)
    antenna = Megamicros()
    
    # Check available channels
    print(f"  Available MEMS: {len(antenna.available_mems)}")
    assert len(antenna.available_mems) == 32
    
    # Run acquisition
    antenna.run(
        mems=[0, 1, 2, 3],
        sampling_frequency=44100,
        frame_length=1024,
        duration=0.1,  # 100ms
        datatype='int32'
    )
    
    # Iterate over frames
    frame_count = 0
    for frame in antenna:
        assert frame.shape == (4, 1024), f"Expected shape (4, 1024), got {frame.shape}"
        frame_count += 1
    
    antenna.wait()
    
    print(f"  ✓ Received {frame_count} frames")
    print(f"  ✓ Queue content: {antenna.queue_content}")
    print(f"  ✓ Frames lost: {antenna.transfert_lost}")
    print()


def test_configuration_objects():
    """Test new configuration system."""
    print("Testing configuration objects...")
    
    from megamicros import AcquisitionConfig, Megamicros
    
    # Create config object
    config = AcquisitionConfig(
        mems=[0, 1],
        sampling_frequency=50000,
        frame_length=512,
        duration=0.05,
        datatype='float32'
    )
    
    print(f"  Config: {config.total_frames} frames expected")
    assert config.total_samples == 2500  # 50000 * 0.05
    assert config.total_frames == 5  # ceil(2500 / 512)
    
    # Use config with antenna
    antenna = Megamicros()
    antenna.run(**config.__dict__)
    
    frame_count = sum(1 for _ in antenna)
    antenna.wait()
    
    print(f"  ✓ Received {frame_count} frames (expected {config.total_frames})")
    print()


def test_backward_compatibility():
    """Test v3.x API compatibility."""
    print("Testing backward compatibility...")
    
    from megamicros import Megamicros
    
    # v3.x style usage
    antenna = Megamicros()
    antenna.run(
        mems=[0, 1, 2, 3],
        sampling_frequency=44100,
        duration=0.05
    )
    
    for frame in antenna:
        pass
    
    antenna.wait()
    
    # v3.x properties
    assert antenna.sampling_frequency == 44100
    assert antenna.mems == [0, 1, 2, 3]
    assert antenna.datatype == 'int32'
    
    # v3.x infos dict
    infos = antenna.infos
    assert 'available_mems' in infos
    assert 'source_type' in infos
    assert infos['source_type'] == 'RandomDataSource'
    
    print(f"  ✓ v3.x API works correctly")
    print(f"  ✓ Source type: {infos['source_type']}")
    print()


def test_imports():
    """Test that all imports work."""
    print("Testing imports...")
    
    from megamicros import (
        Megamicros,
        MemsArray,
        AcquisitionConfig,
        UsbConfig,
        MemsArrayInfo,
        DataSource,
        UsbDataSource,
        H5DataSource,
        RandomDataSource,
        MuH5,
        log,
        MuException,
        __version__
    )
    
    print(f"  ✓ All imports successful")
    print(f"  ✓ Version: {__version__}")
    print()


def main():
    """Run all tests."""
    print("="*60)
    print("Megamicros v4.0.0 Architecture Tests")
    print("="*60)
    print()
    
    try:
        test_imports()
        test_random_source()
        test_configuration_objects()
        test_backward_compatibility()
        
        print("="*60)
        print("✓ All tests passed!")
        print("="*60)
        return 0
        
    except Exception as e:
        print()
        print("="*60)
        print(f"✗ Test failed: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
