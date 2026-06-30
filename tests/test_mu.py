from megamicros import Megamicros
import numpy as np
from megamicros.log import log
import matplotlib
import os

log.setLevel("DEBUG")

antenna = Megamicros()

# Acquisition de 1 seconde
antenna.run(
    mems=list(range(4)),  # Tous les MEMS
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

# plot channel 0, 1, 2 and 3
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 6))
for i in range(4):
    plt.plot(signal[i, :], label=f'Channel {i}')
plt.xlabel('Sample')
plt.ylabel('Amplitude')
plt.title('Channels 0 to 3')
plt.legend()

backend = matplotlib.get_backend().lower()
if 'agg' in backend:
    output_file = 'channels_0_3.png'
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    print(f"Matplotlib backend '{matplotlib.get_backend()}' is non-interactive.")
    print(f"Figure saved to: {output_file}")
else:
    plt.show()


# wait for user input to close the program
input("Press Enter to exit...")