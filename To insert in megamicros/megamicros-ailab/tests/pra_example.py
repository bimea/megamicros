import numpy as np
import matplotlib.pyplot as plt
import pyroomacoustics as pra
from scipy.io import wavfile
from megamicros_aidb.query.db import AidbSession
from megamicros.log import log
from megamicros_ailab.antenna import Antenna, Room, Mu32_Mems32_JetsonNano_0001

# see https://pyroomacoustics.readthedocs.io/en/pypi-release/pyroomacoustics.room.html

#SAMPLING_FREQUENCY = 10000
SAMPLING_FREQUENCY = 16000

with AidbSession(
    dbhost='http://dbwelfare.biimea.io/',
    login='ailab',
    email='bruno.gas@biimea.com',
    password='#T;uZnQ5UJ_JC~&' ) as session:
    domains = session.load_domains()
    labels = session.load_labels( domain_id=1 )

    LABEL_ID = 15
    limit = 2
    channels = list( np.arange( 32 ) + 1 )
    audio = session.load_labelized( label_id=LABEL_ID, limit=limit, tags_id=5, channels=channels )


print( f"{len(audio)} section audio récupérées: " )
for idx, aud in enumerate( audio ):
    print( f"Audio[{idx}]: {aud} -> label={aud.label}, channels number: {aud.channels_number} ({aud.samples_number} samples)")

signal = audio[0][0]


# The desired reverberation time and dimensions of the room
rt60_tgt = 0.3  # seconds
room_dim = [10, 7.5, 3.5]  # meters

# We invert Sabine's formula to obtain the parameters for the ISM simulator
e_absorption, max_order = pra.inverse_sabine(rt60_tgt, room_dim)

# Create the room
room = pra.ShoeBox(
    room_dim, fs=SAMPLING_FREQUENCY, materials=pra.Material(e_absorption), max_order=max_order,
    use_rand_ism = True, max_rand_disp = 0.05
)

#from scipy.io import wavfile
fs, signal_wav = wavfile.read("guitar_16k.wav")

# place the source in the room
#room.add_source([2.5, 3.73, 1.76], signal=signal, delay=1.3)
room.add_source([2.5, 3.73, 1.76], signal=signal_wav, delay=1.3)


# get the antenna
antenna_square: Antenna = Mu32_Mems32_JetsonNano_0001
ant = antenna_square.antenna

# OR: define the locations of the microphones
mic_locs = np.c_[
    [6.3, 4.87, 1.2], [6.3, 4.93, 1.2],  # mic 1  # mic 2
]

# finally place the array in the room
#room.add_microphone_array( np.array( antenna_square.antenna ).T )
room.add_microphone_array( mic_locs )


# Run the simulation (this will also build the RIR automatically)
room.simulate()

# plot signal at microphone 1
plt.plot(room.mic_array.signals[1,:])

plt.show()