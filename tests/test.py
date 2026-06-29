from megamicros import Megamicros
import numpy as np
from megamicros.log import log

log.setLevel("DEBUG")

antenna = Megamicros()

# Acquisition de 1 seconde
antenna.run(
    mems=list(range(32)),  # Tous les MEMS
    sampling_frequency=50000,
    duration=1,
    frame_length=1024
)

antenna.wait()

print(f"Queue content before: {antenna.queue_content}")

# Stocker toutes les données
all_frames = []
for frame in antenna:
    all_frames.append(frame)

print(f"Retrieved frames {len(all_frames)}")
print(f"Queue content after: {antenna.queue_content}")

# Concaténer
signal = np.concatenate(all_frames, axis=1)
print(f"Signal complet : {signal.shape}")

# Affiche le compteur en voie 0:
print(f"Compteur en voie 0 : {signal[0, :]}")
