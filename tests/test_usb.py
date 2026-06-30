import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from megamicros.sources import UsbDataSource
from megamicros.core.config import AcquisitionConfig, UsbConfig
from megamicros.log import log

log.setLevel("INFO")

usb_config = UsbConfig(vendor_id=0xFE27, product_id=0xAC01)
source = UsbDataSource(usb_config)
        
config = AcquisitionConfig(
    mems=[0, 1, 2, 3],
    sampling_frequency=50000,
    frame_length=1024,
    duration=1.0,
    counter=True
)
source.configure(config)

all_frames = []
source.start()
        
# Stocker toutes les données
for frame in source:
    all_frames.append(frame)

source.wait()
source.stop()

print(f"Retrieved frames {len(all_frames)}")
print(f"Queue content after: {source.queue_content}")

# Concaténer
signal = np.concatenate(all_frames, axis=1)
print(f"Signal complet : {signal.shape}")

# Affiche le compteur en voie 0:
print(f"Compteur en voie 0 : {signal[0, :]}")

# Mems channels
print(f"MMEMS en voie 1 : {signal[1, :10]}")
print(f"MMEMS en voie 2 : {signal[2, :10]}")
print(f"MMEMS en voie 3 : {signal[3, :10]}")
print(f"MMEMS en voie 4 : {signal[4, :10]}")

plt.figure(figsize=(10, 6))
for i in range(5):
    plt.plot(signal[i, :], label=f'Channel {i}')
plt.xlabel('Sample')
plt.ylabel('Amplitude')
plt.title('Channels 0 to 4')
plt.legend()

backend = matplotlib.get_backend().lower()
if 'agg' in backend:
    output_file = 'channels_0_4.png'
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    print(f"Matplotlib backend '{matplotlib.get_backend()}' is non-interactive.")
    print(f"Figure saved to: {output_file}")
else:
    plt.show()


# wait for user input to close the program
input("Press Enter to exit...")
