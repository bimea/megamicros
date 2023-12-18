import numpy as np
from IPython import display
from megamicros_aidb.query.db import AidbSession
from megamicros.data import MuAudio
from megamicros.log import log
from megamicros.core_base import MU_MEMS_SENSIBILITY

log.setLevel( "INFO" )

FRAME_LENGTH = 1024
SAMPLING_FREQUENCY = 10000
CUTOFF_FREQUENCY = 2500

LABEL_SOW_FEEDING_CALL = 18
LABEL_PIGLET_SQUEALS = 15
LABEL_ROOM_NOISE = 29

# choose your label:
LABEL_ID = LABEL_SOW_FEEDING_CALL

# Choose your file
with AidbSession(
    dbhost='http://dbwelfare.biimea.io/',
    login='ailab',
    email='bruno.gas@biimea.com',
    password='#T;uZnQ5UJ_JC~&' ) as session:   
    numsig = 0
    
    LblIds = [16, 18, 18, 18, 8, 1, 3, 3, 5, 5, 15, 15]
    FileIds =[7135, 8692, 8692, 7135, 7135, 5838, 7839, 7355, 7075, 6859, 6830, 8146 ]
    channels = list( np.arange( 32 ) + 1 )
    NbSmpls = len(LblIds)
    Transits = np.zeros_like(LblIds)
    for ii in range(12) :
        labelings_file = session.load_labelings( label_id=LblIds[ii] )
        signals = session.load_labelized( sourcefile_id=FileIds[ii], label_id=LblIds[ii], limit=100, channels=channels )
        signal = signals[0]
        if ii :        
            Mems = np.hstack((Mems,signal()))
        else : 
            Mems = signal()
        Transits[ii] = Mems.shape[1]

        

#%%
import matplotlib.pyplot as plt        
plt.plot(Mems[0,:])
np.save('ScenarBruno.npy', Mems)    
np.save('TransitsBruno.npy', Transits)    

# %%
