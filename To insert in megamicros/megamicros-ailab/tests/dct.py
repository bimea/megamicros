import logging
import numpy as np
import scipy
import matplotlib.pyplot as plt

from megamicros_aidb.query.db import AidbSession
from megamicros.log import log
from megamicros_ailab.antenna import Antenna, Room, Mu32_Mems32_JetsonNano_0001
from megamicros_ailab.bmf import BeamformerDas2D

log.setLevel( logging.DEBUG )

# extrait une trame
offset = 10000
size = 512
sf = 10000

t = np.arange( size ) / sf

frame1 = np.cos( 2*np.pi*500*t )
frame2 = np.cos( 2*np.pi*500*t + 2*np.pi )

# calcul la DCT
dctframe1 = scipy.fftpack.dct( frame1, type=2 )
dctframe2 = scipy.fftpack.dct( frame2, type=2 )
f = np.arange( size ) * sf / size / 2

# Affiche
fig1, axes1 = plt.subplots(2, 1)

axes1[0].plot( t, frame1 )
axes1[1].plot( f, dctframe1, f, dctframe2 )

plt.show()