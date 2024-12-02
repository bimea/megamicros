# mu5h-20220720-132930.h5: cri truie douleur en nombre ! (antenne carré)-

import logging
import numpy as np
import scipy
import matplotlib.pyplot as plt

from megamicros_aidb.query.db import AidbSession
from megamicros.log import log
from megamicros_ailab.antenna import Antenna, Room, Mu32_Mems32_JetsonNano_0001
from megamicros_ailab.bmf import BeamformerDas2D

log.setLevel( logging.DEBUG )


with AidbSession(
    dbhost='http://dbwelfare.biimea.io/',
    login='admin',
    email='bruno.gas@biimea.com',
    password='htr4807' ) as session:
    domains = session.load_domains()
    labels = session.load_labels( domain_id=1 )

    LABEL_ID = 15
    limit = 2
    channels = list( np.arange( 32 ) + 1 )
    audio = session.load_labelized( label_id=LABEL_ID, limit=limit, tags_id=5, channels=channels )


print( f"{len(audio)} section audio récupérées: " )
for idx, aud in enumerate( audio ):
    print( f"Audio[{idx}]: {aud} -> label={aud.label}, channels number: {aud.channels_number} ({aud.samples_number} samples)")


#room = Room( dim=(10, 12, 2.2) )
antenna_square: Antenna = Mu32_Mems32_JetsonNano_0001
print( antenna_square.antenna() )
print( antenna_square.antenna()[0] )
print( antenna_square.antenna()[1] )
print( 'antenna at position (1,1,0): ', antenna_square.antenna( (1,1,0) ) )

print( 'mems[5]=', antenna_square.mems(5) )
print( 'mems[5] antenna = (1,1)=', antenna_square.mems(5, (1,1,0)) )

exit()

antenna_square.set_position( 5, 6, 2 )

print( "Mems number=", antenna_square.mems_number )
print( "Antenna position=", antenna_square.position )
#print( "Mems=", antenna_square.antenna )
print( "room size=", room )

frame_size = 512
bmf: BeamformerDas2D = BeamformerDas2D( 
    antenna=antenna_square, 
    room=room, 
    position=antenna_square.position, 
    sampling_rate=10000, 
    space_sampling_rate=(2,2,0), 
    frame_size=frame_size 
)

audio[0].set_frame_size( frame_size )
plt.show()

fig1, axes1 = plt.subplots(2, 1)

for idx, signal in enumerate( audio[0] ):
    BF = bmf.beamform( signal )
    img = np.reshape( BF, (20, 24) )

    axes1[0].plot( BF )
    plt.imshow( img )

    input( "next..." )


