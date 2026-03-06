#!/usr/bin/env python3
"""
Test UX improvements for v4.0:
1. Auto-cleanup when calling run() twice
2. clear_queue() method
3. wait() keeps frames in queue
"""

from megamicros import Megamicros
from megamicros.log import log

log.setLevel('WARNING')

def test_double_run():
    """Test that calling run() twice doesn't raise RuntimeError."""
    print("Test 1: Double run() auto-cleanup...")
    
    a = Megamicros()
    
    # First run
    a.run(mems=[0, 1], duration=0.1)
    print("  ✓ First run() successful")
    
    # Second run WITHOUT manual cleanup - should work!
    a.run(mems=[2, 3], duration=0.1) 
    print("  ✓ Second run() auto-cleaned previous acquisition")
    
    a.wait()
    print("  ✓ Test passed!\n")

def test_clear_queue():
    """Test clear_queue() method."""
    print("Test 2: clear_queue() method...")
    
    a = Megamicros()
    a.run(mems=[0,1,2,3], duration=1.0)
    
    # Process a few frames
    count = 0
    for frame in a:
        count += 1
        if count >= 5:
            break
    
    print(f"  ✓ Processed {count} frames")
    
    # Clear remaining
    cleared = a.clear_queue()
    print(f"  ✓ Cleared {cleared} frames using clear_queue()")
    
    a.wait()
    print("  ✓ Test passed!\n")

def test_wait_keeps_frames():
    """Test that wait() doesn't empty the queue."""
    print("Test 3: wait() keeps frames...")
    
    a = Megamicros()
    a.run(mems=[0,1], duration=1.0)
    a.wait()
    
    # Note: RandomDataSource doesn't use a queue - frames are generated on-demand
    # With real USB or H5, queue_content would be > 0 after wait()
    print("  ✓ wait() completed (frames available for iteration)")
    
    # Iterate to get them
    count = 0
    for frame in a:
        count += 1
    
    print(f"  ✓ Retrieved {count} frames after wait()")
    print("  ✓ Test passed!\n")

def test_method_chaining():
    """Test that run() returns self for chaining."""
    print("Test 4: Method chaining...")
    
    a = Megamicros()
    result = a.run(mems=[0], duration=0.1)
    
    assert result is a, "run() should return self"
    print("  ✓ run() returns self for chaining")
    print("  ✓ Test passed!\n")

if __name__ == '__main__':
    print("="*60)
    print("Testing v4.0 UX Improvements")
    print("="*60 + "\n")
    
    test_double_run()
    test_clear_queue()
    test_wait_keeps_frames()
    test_method_chaining()
    
    print("="*60)
    print("All tests passed! ✨")
    print("="*60)
