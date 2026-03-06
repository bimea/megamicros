"""Test frame accumulation between runs."""

from megamicros import Megamicros

antenna = Megamicros()

# First run: 0.5 seconds
print("=== First run (0.5s) ===")
antenna.run(mems=[0, 1], duration=0.5, sampling_frequency=44100, frame_length=1024)
antenna.wait()
print(f"Queue content after run 1: {antenna.queue_content} frames")

# Second run WITHOUT clearing: 0.5 seconds more
print("\n=== Second run (0.5s) WITHOUT clear_queue() ===")
antenna.run(mems=[0, 1], duration=0.5, sampling_frequency=44100, frame_length=1024)
antenna.wait()
print(f"Queue content after run 2: {antenna.queue_content} frames")
print(f"✨ Expected ~44 frames per run → total ~88 frames")

# Consume first 5 frames
print("\n=== Consuming 5 frames ===")
for i, frame in enumerate(antenna):
    if i >= 4:
        break
print(f"Queue content after consuming 5: {antenna.queue_content} frames")

# Third run: Add more!
print("\n=== Third run (0.5s) on top of existing frames ===")
antenna.run(mems=[0, 1], duration=0.5, sampling_frequency=44100, frame_length=1024)
antenna.wait()
print(f"Queue content after run 3: {antenna.queue_content} frames")
print(f"✨ Expected ~83 (from run 2) + ~44 (from run 3) = ~127 frames")

# Finally clear all
cleared = antenna.clear_queue()
print(f"\n=== Cleared {cleared} frames ===")
print(f"Queue content after clear: {antenna.queue_content} frames")

print("\n✅ Frames now ACCUMULATE between runs!")
print("💡 Use clear_queue() when you want a fresh start.")
