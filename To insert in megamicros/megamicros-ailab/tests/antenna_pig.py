import numpy as np
import matplotlib.pyplot as plt
import pyroomacoustics as pra
from IPython import display
from megamicros_ailab.antenna import Antenna, BmfAntenna, Mu32_Mems32_JetsonNano_0001
from megamicros_ailab.room import arrange_2D
from megamicros_aidb.query.db import AidbSession
from megamicros.data import MuAudio
from megamicros.log import log
from megamicros.audio import play
from megamicros.core_base import MU_MEMS_SENSIBILITY

"""
Merging video and sound, see: https://stackoverflow.com/questions/11779490/how-to-add-a-new-audio-not-mixing-into-a-video-using-ffmpeg

Salle M10: 11.80m x 17m x 2,05m.  40 places (4 x 10)
Taille approximative des box: 2,5m x 1,7m 
Largeur des couloirs: 0,9m
"""
FRAME_LENGTH = 1024
ROOM_SIZE = (8.40, 10.20, 2.05)          # 4 box + 1 couloir + 4 box + 4 box   
ANTENNA_POSITION = (2.95, 5.1, 2.03)    # au centre du couloir face aux cases 432, 433, 434, 435 et 422, 424, 426 et 428
SAMPLING_FREQUENCY = 10000
LABEL_ID = 18
log.setLevel( 'INFO' )


import os
import wave 
from scipy.io import wavfile

def generate_video( img, rate: float, sound, sampling_frequency ):

    # Create video from images 
    for i, img in enumerate( imgs ):
        plt.imshow( img )
        plt.savefig( f"./tmp/file{i:02d}.png" )

    # write video
    cmd = f"cd ./tmp && ffmpeg -r {rate} -i file%02d.png -vcodec mpeg4 -y video.mp4"
    error = os.system( cmd )
    if error:
        print( "failed to write video part..." )
    else:
        print( "video saved")

    # Save sound
    wavfile.write ( f"./tmp/audio.wav", sampling_frequency, sound )
    print( "audio saved")

    # merge video and sound
    cmd = f"cd ./tmp && ffmpeg -i video.mp4 -i audio.wav -map 0:v -map 1:a -c:v copy -shortest movie.mp4"
    error = os.system( cmd )
    if error:
        print( "failed to write movie..." )
    else:
        print( "movie saved")

# Get signal
with AidbSession(
    dbhost='http://dbwelfare.biimea.io/',
    login='ailab',
    email='bruno.gas@biimea.com',
    password='#T;uZnQ5UJ_JC~&' ) as session:
        domains = session.load_domains()
        labels = session.load_labels( domain_id=1 )
        for label in labels:
            print( f" > [{label['code']}: {label['name']}] -> {label['id']}")
        label_id = int( input( 'Choisir un label: ') )
        labelings_file = session.load_labelings( label_id=label_id )
        print( f"Etiquettages trouvés:" )
        for labeling_file in labelings_file:
            print( f" > [{labeling_file['sourcefile_id']}: {labeling_file['sourcefile_filename']}]")

        sourcefile_id = int( input( 'Numéro identificateur du fichier à sélectionner:' ) )
        #limit = int( input( 'Nombre limite d\'exemples à charger: ') )
        limit = 100
        channels = list( np.arange( 32 ) + 1 )
        #signals = session.load_labelized( label_id=LABEL_ID, limit=limit, tags_id=5, channels=channels )
        signals = session.load_labelized( sourcefile_id=sourcefile_id, label_id=label_id, limit=limit, channels=channels )

print( f"{len(signals)} section audio récupérées: " )
for idx, aud in enumerate( signals ):
    print( f"Audio[{idx}]: {aud} -> label={aud.label}, channels number: {aud.channels_number} ({aud.samples_number} samples)")


# Build the antenna
antenna_square: Antenna = Mu32_Mems32_JetsonNano_0001

# Space quantization
sq_x = 4
sq_y = 4
nx: int = int( ROOM_SIZE[0] * sq_x )
ny: int = int( ROOM_SIZE[1] * sq_y )
ground_elevation = 0.20
space_q = arrange_2D( ROOM_SIZE, sq_x=sq_x, sq_y=sq_y, ground_elevation=ground_elevation )
space_q_2D = np.reshape( space_q, (nx, ny, 3) )

# Space quantization (2)
ROOM_SIZE = (7, 10, 2.2)
ANTENNA_POSITION = (2.5, 5, 2.18)
sq_x = 4
sq_y = 4
nx: int = int( ROOM_SIZE[0] * sq_x )
ny: int = int( ROOM_SIZE[1] * sq_y )
ground_elevation = 0.20
space_q = arrange_2D( ROOM_SIZE, sq_x=sq_x, sq_y=sq_y, ground_elevation=ground_elevation )
space_q_2D = np.reshape( space_q, (nx, ny, 3) )

# Create antenna with beamformer
bmf_antenna: BmfAntenna = BmfAntenna( 
    mems = Mu32_Mems32_JetsonNano_0001.mems(),
    position = ANTENNA_POSITION,
    frame_length = FRAME_LENGTH,
    space_q = space_q,
    sampling_frequency = SAMPLING_FREQUENCY
)

#xticks = np.arange(0, ROOM_SIZE[0], 1)
#yticks = np.arange(0, ROOM_SIZE[1], 1)

while True:
    selected = input( f"Choisir un signal (0 à {len(signals)-1}): " )
    if selected == 'q' or selected == 'Q':
        break
    else:
        selected = int(selected)
    
    antenna_output: MuAudio = signals[selected]

    # Play original sound
    left = np.array( antenna_output.channel(0) )
    right = np.array( antenna_output.channel(1) )
    sound = np.array( [left, right] )
    sound = sound.astype( np.float32 ).T

    play( sound, fs=SAMPLING_FREQUENCY )

    # Compute beamformed antenna output
    BF: np.ndarray = np.zeros( (len(space_q),) )
    E = []
    imgs = []
    antenna_output.set_frame_size( FRAME_LENGTH )
    for idx, sig in enumerate( antenna_output ):
        bf = bmf_antenna.beamform( sig ) 

        img = np.reshape( bf, (nx, ny) )
        imgs.append(img)
        E.append( np.sum(bf) )
        BF += bf

        #plt.figure(1); plt.clf()
        ##plt.imshow( img, vmin=0, vmax=1.27 )
        #plt.imshow( img )
        #plt.pause(0.050)

    generate_video( imgs, rate=SAMPLING_FREQUENCY/FRAME_LENGTH, sound=sound, sampling_frequency=SAMPLING_FREQUENCY )

    fig2, ax2 = plt.subplots(1, 1)
    ax2.plot( BF )

    fig3, ax3 = plt.subplots()
    ax3.imshow( np.reshape( BF, (nx, ny) ) )
    #ax3.set_xticks(yticks)
    #ax3.set_yticks(xticks)

    fig5, ax5 = plt.subplots()
    ax5.plot(E)

    plt.show()


plt.close('all')
