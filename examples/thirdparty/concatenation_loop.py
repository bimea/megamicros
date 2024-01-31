import numpy as np
import matplotlib.pyplot as plt
from megamicros.log import log
from megamicros.core.h5 import MemsArrayH5

import IPython
from IPython.display import Audio, display
import time
import plotly.express as px

log.setLevel("INFO")
# log.setLevel("WARNING")

# Choose a file where some H5 files are stored
DIRECTORY = '/Users/brunogas/Documents/Data/'

# Choose a H5 file
FILENAME = DIRECTORY + 'mu5h-20220816-051126.h5' # 2m40 de silence puis écrasement jusqu'à 4min30 env.
print(FILENAME)

# Define the antenna
antenna = MemsArrayH5(filename=FILENAME)

print(f"Sampling frequency: {antenna.sampling_frequency}Hz")
print(f"Available MEMs number: {antenna.available_mems_number}")
print(f"Whether counter is available or not: {antenna.counter}")
print(f"{antenna.file_duration}s ({(antenna.file_duration/60):}min) of data in H5 file")

sample_rate = antenna.sampling_frequency
sample_rate


# Run antenna to download the file entirely

# Record start time
start_time = time.time()
formatted_start_time = time.strftime(" %H:%M:%S", time.localtime(start_time))
print(f"Start time: {formatted_start_time}")


antenna.run(
    mems = [6],
    duration=600,
    counter_skip = True,
    datatype='int32'
)

# Init a np.ndarray
signals2 = np.ndarray((0, antenna.channels_number))

# Get signals
for data in antenna:
#     print(f"Data shape: {data.shape}, Signals2 shape: {signals2.shape}")
    signals2 = np.concatenate((signals2, data), axis=0)
    
    # if the whole duration of the file has been added : stop the loop (if not, it re-starts from the beginning and keeps adding to the signals)
    if signals2.shape[0]>antenna.file_duration*antenna.sampling_frequency :
        signals2 = signals2[:int(antenna.file_duration*antenna.sampling_frequency)]
        print(f"The entire duration of the file has been processed, waiting for the antenna to finish running ...")
        break

# waiting for the end of the running thread is mandatory
antenna.wait()
print(f"exit from loop. Signal shape is: {np.shape(signals2)}")


# Record end time
end_time = time.time()
formatted_end_time = time.strftime("%H:%M:%S", time.localtime(end_time))
print(f"End time: {formatted_end_time}")

# Calculate elapsed time
elapsed_time = end_time - start_time

print(f"Elapsed time: {elapsed_time} seconds, ({elapsed_time/60} m.)")
print(f"Duration of the audio : {signals2.shape[0]/antenna.sampling_frequency}s.({round(signals2.shape[0]/antenna.sampling_frequency/60,1)}m.)")


# plot signals
time_axis = np.array(range(np.size(signals2,0)))/sample_rate
fig, axs = plt.subplots(antenna.channels_number)
fig.suptitle('Channels activity')

for s in range(antenna.channels_number):
    if antenna.channels_number > 1:
        axs[s].plot(time_axis/60, signals2[:len(time_axis), s])
        axs[s].set(xlabel='time in minutes', ylabel=f'channel {s}')
    else:
        axs.plot(time_axis/60, signals2[:len(time_axis), s])
        axs.set(xlabel='time in minutes', ylabel=f'channel {s}')

plt.show()

IPython.display.Audio(signals2[:,0], rate=sample_rate)