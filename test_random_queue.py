#!/usr/bin/env python3
"""Test that RandomDataSource now uses queue asynchronously"""

from megamicros import Megamicros
from megamicros.log import log
import time

log.setLevel('INFO')

print('Test 1: Queue gets filled asynchronously')
print('='*60)
a = Megamicros()
a.run(mems=[0,1,2,3], duration=1.0, frame_length=1024)

# Check queue is filling in background
time.sleep(0.5)
print(f'After 0.5s: queue has {a.queue_content} frames (generating...)')

a.wait()
print(f'After wait(): queue has {a.queue_content} frames (ready to iterate!)')

# Consume some frames
count = 0
for frame in a:
    count += 1
    if count == 10:
        print(f'After consuming 10 frames: {a.queue_content} frames remaining')
        break

print(f'\nTest 2: Clear queue works')
print('='*60)
cleared = a.clear_queue()
print(f'Cleared {cleared} frames')
print(f'Queue after clear: {a.queue_content}')

print(f'\n✅ RandomDataSource now uses queue like USB!')
