# querying_audio.py. Python software notebook for Megamicros
#
# Copyright (c) 2023 Sorbonne Université
# Author: bruno.gas@sorbonne-universite.fr
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Notebook on querying audio data from Megamicros audio database.

Note that following libraries should be installed before using this script
* numpy
* requests
"""

import logging
import numpy as np
import matplotlib.pyplot as plt
from megamicros_aidb.query.db import AidbSession
from megamicros.log import log


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
    channels = [0,1,2,3,4,5,6,7]
    audio = session.load_labelized( label_id=LABEL_ID, limit=limit, tags_id=5, channels=channels )
    print( f"{len(audio)} section audio récupérées: " )
    for idx, aud in enumerate( audio ):
        print( f"Audio[{idx}]: {aud}")


#signal = audio[1].channel(0)
#t = np.arange( signal.size )
#fig, ax = plt.subplots()
#ax.plot( t, signal )
#plt.show()

from megamicros_ailab import display as mu_display

#mu_display.plot_muaudio( audio[0], [0,2,3] )
#mu_display.specgram_muaudio( audio[0], [0,2,3] )



s1 = audio[0].channel(1)
s2 = audio[0].channel(6)
N = audio[0].samples_number
sf = audio[0].sampling_frequency
t = np.arange( N ) / sf

fig1, axes1 = plt.subplots(1, 1)
offset = 10000
size = 512
axes1.plot(t, s1, t, s2)
#axes[1].plot(t[offset:offset+size], s1[offset:offset+size], t[offset:offset+size], s2[offset:offset+size])


# Frequential 
fig2, axes2 = plt.subplots(3, 1)

# extract a frame 
ss1 = s1[offset:offset+size]
N1 = len(ss1)/2 + 1

# frequencies axis
f = np.arange( N1 ) * sf / N1 /2

# compute RFFT and RFFT module
ssf1 = np.fft.rfft( ss1 )
SSF1 = abs( ssf1 )

# plot module
axes2[0].plot(f, SSF1 )
axes2[1].plot(f, ssf1.real )
axes2[2].plot(f, ssf1.imag )

plt.show()

input( 'Tapez une touche...' )