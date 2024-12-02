import numpy as np
import matplotlib.pyplot as plt
import pyroomacoustics as pra
from IPython import display
from megamicros_ailab.antenna import Antenna, Mu32_Mems32_JetsonNano_0001
from megamicros_ailab.room import arrange_2D
from megamicros_ailab.bmf import BeamformerDas2D
from megamicros_aidb.query.db import AidbSession
from megamicros.data import MuAudio
from megamicros.log import log
from megamicros.audio import play

FRAME_LENGTH = 512
ROOM_SIZE = (10, 12, 2.2)
ANTENNA_POSITION = (2.5, 4.5, 2.18)
#SOURCE_POSITION = (1, 1.5, 0.5)
SOURCE_POSITION = (8, 1, 0.5)
SIGNAL_FREQUENCY = 2000
ECHO = False

#SIGNAL = 'synthesis' 
SIGNAL = 'guitar'

log.setLevel( 'INFO' )

# Generate signal
if SIGNAL == 'synthesis' :
    SAMPLING_FREQUENCY = 10000
    ff = SIGNAL_FREQUENCY
    N = 2048
    signal = np.cos(2*np.pi*ff*np.arange(N)/SAMPLING_FREQUENCY)
elif SIGNAL == 'guitar' :
    from scipy.io import wavfile
    SAMPLING_FREQUENCY = 16000
    _, signal = wavfile.read("./guitar_16k.wav")
else:
    exit()

# Play original sound
print( np.shape(signal) )
print( type(signal[0]) )
play( signal, fs=SAMPLING_FREQUENCY )

# Build the room
rt60_tgt = 0.3  # seconds
room_dim = ROOM_SIZE  # meters

if ECHO:
    e_absorption, max_order = pra.inverse_sabine(rt60_tgt, room_dim)
    room = pra.ShoeBox(
        room_dim, 
        fs=SAMPLING_FREQUENCY, 
        materials=pra.Material( e_absorption ), 
        max_order=max_order,
        use_rand_ism = True, 
        max_rand_disp = 0.05
    )
else:
    room = pra.ShoeBox(
        room_dim, 
        fs=SAMPLING_FREQUENCY
    )

# Build the antenna
antenna_square: Antenna = Mu32_Mems32_JetsonNano_0001

# Locate the antenna in the room
room.add_microphone_array( antenna_square.antenna( ANTENNA_POSITION ).T )

# Compute antenna response
source_position = SOURCE_POSITION
room.add_source( source_position, signal=signal, delay=1.3 )

fig, ax = room.plot()
ax.set_xlim([-1, ROOM_SIZE[0]+1])
ax.set_ylim([-1, ROOM_SIZE[1]+1]);
ax.set_zlim([-1, ROOM_SIZE[2]+2]);

room.simulate()

# Space quantization
sq_x = 1
sq_y = 1
nx: int = int( ROOM_SIZE[0] * sq_x )
ny: int = int( ROOM_SIZE[1] * sq_y )
ground_elevation = 0.20
space_q = arrange_2D( ROOM_SIZE, sq_x=sq_x, sq_y=sq_y, ground_elevation=ground_elevation )
space_q_2D = np.reshape( space_q, (nx, ny, 3) )

# Create beamformer
bmf: BeamformerDas2D = BeamformerDas2D( antenna_square, space_q, ANTENNA_POSITION, SAMPLING_FREQUENCY, FRAME_LENGTH )

#fig2, ax2 = plt.subplots()
#ax2.imshow( np.reshape( bmf.D[:,31], (nx, ny) ) )

# Compute beamformed antenna output
antenna_output: MuAudio = MuAudio( room.mic_array.signals, SAMPLING_FREQUENCY )
antenna_output.set_frame_size( FRAME_LENGTH )
BF: np.ndarray = np.zeros( (len(space_q),) )
E = []
mx = 0
for idx, sig in enumerate( antenna_output ):
    bf = bmf.beamform( sig )
    if np.amax( bf ) > mx:
        mx = np.amax( bf )
    img = np.reshape( bf, (nx, ny) )
    
    E.append( np.sum(bf) )
    BF += bf

    plt.figure(1); plt.clf()
    plt.imshow( img )
    plt.pause(0.05)

print( f"max = {mx}")

# Mean energy per space location (spatial filter)
fig3, ax3 = plt.subplots(1, 1)
ax3.plot( BF )

# Energy through time
fig4, ax4 = plt.subplots()
ax4.plot( E )

plt.show()


input('Tapez une touche...')