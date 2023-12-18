# -*- coding: utf-8 -*-
# import required libraries
#%%###########################################################################
import h5py as h5
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as sig
import os
import matplotlib.dates as dates
import datetime
import wave
import struct

import matplotlib.animation as manimation
from scipy.optimize import curve_fit

# FFMpegWriter = manimation.writers['ffmpeg']
# metadata = dict(title='Movie', artist='Matplotlib',
#                 comment='Movie !')
# writer = FFMpegWriter(fps=10, metadata=metadata)


#%%###########################################################################
#import speech features and IA libraries
#import python_speech_features as sp
#import tensorflow as tf
#from tensorflow import set_random_seed
#from numpy.random import seed
#os.environ['KMP_DUPLICATE_LIB_OK']='True'

#%%###########################################################################
#Sensibilité : -26dBFS pour 104 dB soit 3.17 Pa
FS = 2**23
S = FS*10**(-26/20.) / 3.17
po = 20e-6
Fs = 10000
NumMicPlot = 1
plt.close('all')
datadir = './'
NbMems = 32
Fe = 10e3
Po = 20e-6    

# Physical parameters
Tc = 35 
c0 = np.sqrt( 1.4 * 287 *(Tc + 273) )

dfen = 1
Nfen = int(Fe/dfen)
Nfft = Nfen#int(Fe)
f = np.fft.rfftfreq(Nfft,1/Fe)

#%%###################################################################
## Affichage 
##################################################################
#intialisation des graphiques
plt.ion()
fig = plt.figure(1, clear = True, figsize=(10,5))

ax1 = fig.add_subplot(211)
lineCoh, = ax1.plot(f,np.zeros_like(f))
lineCohf, = ax1.plot(f,np.zeros_like(f))
lineFit, = ax1.plot(f,np.zeros_like(f))

ax1.set_xlim(0, np.max(f))
ax1.autoscale(enable=True, axis='y',    tight=None)
ax1.set_ylim(-1, 1)
ax1.grid()

Debut = 0
Duree = 900
Fin = Debut+Duree
MemsOff =[2,3,14,20,21,26,27]
MemsOn = [m for m in np.arange(32) if m not in MemsOff]
NbMems0 = NbMems
NbMems -= len(MemsOff)
nbd = int((NbMems**2-NbMems)/2)
d = np.zeros((NbMems,NbMems, Duree*dfen))
e = np.ones((NbMems,NbMems, Duree*dfen))

ax2 = fig.add_subplot(223)
ax3 = fig.add_subplot(224)
MapD = ax2.imshow(d[:,:,0])
MapC = ax3.imshow(e[:,:,0])
#ax2.grid()
fcb = 150
fch = 4000
band = np.logical_and(f>fcb, f<fch)
def Sinc(x, d):
    return np.sinc(2*f[band]*d/c0)
from scipy.signal import savgol_filter

#%%###################################################################
## Traitement données 
##################################################################
Seqs = []
h5Names = np.sort([fin for fin in os.listdir(datadir) if fin.endswith('h5')])
h5Files = [h5.File(datadir + h5Name, 'r') for h5Name in h5Names]
for h5f in h5Files :  
    Seqs = np.sort([int(s) for s in h5f['muh5'].keys()])
    Seqs = [str(i) for i in Seqs]
NbSeqs = len(Seqs[Debut:Fin])
print( 'Collected sequence number is: ' + str(NbSeqs) )
##################################################################
## Traitement des sequences et affichage du BF
##################################################################
print( 'Process sequences...' )
NumSec = 0

jj = 0
Max = 0
Sxy = np.zeros((Nfft//2+1, int((NbMems**2-NbMems)/2)), dtype='complex128')
Sxx = np.zeros((Nfft//2+1, int((NbMems**2-NbMems)/2)))
Syy = np.zeros((Nfft//2+1, int((NbMems**2-NbMems)/2)))

for Seq in Seqs[Debut:Fin]:
# Pour chaque séquence d'une seconde:       
    Mems = h5f['muh5'][Seq]['sig'][:].T/S
    Mems = Mems[:,1:]
    Mems = Mems[:,MemsOn]

    print( '\n processing sequence '  + str(int(NumSec)) + '/' + str(NbSeqs)  )
    NumSec += 1
    for ii in range(dfen):
        # pour chaque trame de 100ms:
        p=0    
        prand = np.random.randint(nbd)
        Npmod = 0
        Spec = np.fft.rfft(Mems[ii*Nfen + np.arange(Nfen),:], n=Nfft, axis=0)+1e-12
        for n in range(NbMems) : 
            e[n, n, jj] = 0            
            for m in range(n+1, NbMems):
                
                Sxy[:, p] += np.conj(Spec[:, n]) * Spec[:, m] + 1e-12
                Sxx[:, p] += np.abs(Spec[:, n])**2 + 1e-12
                Syy[:, p] += np.abs(Spec[:, m])**2 + 1e-12
                Coh = np.real(Sxy[:,p])/np.sqrt(Sxx[:,p]*Syy[:,p])
                
                popt, pcov = curve_fit(f=Sinc, xdata = f[band], ydata = Coh[band], maxfev = 15000, bounds = (0.05, 1))
                perr = np.sqrt(np.diag(pcov))
                
                if jj>=2 and e[n,m, jj-1] >= perr[0]:
                    e[n,m, jj] = perr[0]
                    e[m,n, jj] = perr[0]
                    d[n,m, jj] = popt[0]
                    d[m,n, jj] = popt[0]         
                    Npmod += 1           
                else : 
                    e[n,m, jj] = e[n,m, jj-1]
                    e[m,n, jj] = e[n,m, jj-1]
                    d[n,m, jj] = d[n,m, jj-1]
                    d[m,n, jj] = d[n,m, jj-1]
                    Sxy[:, p] -= np.conj(Spec[:, n]) * Spec[:, m] + 1e-12
                    Sxx[:, p] -= np.abs(Spec[:, n])**2 + 1e-12
                    Syy[:, p] -= np.abs(Spec[:, m])**2 + 1e-12
                    Coh = np.real(Sxy[:,p])/np.sqrt(Sxx[:,p]*Syy[:,p])
                step = 'Snapshot : {0:3d}  - Paire {1:2d}-{2:2d} - d (cm) = {3:5.1f} - err = {4:.1e}'.format(jj,n,m, d[n,m, jj]*100,  e[n,m, jj])
                #print('\r'+step, end='')
                
                if p==prand : 
                    ttl1 = 'Snapshot : {0:3d}  - Paire {1:2d}-{2:2d} - d (cm) = {3:5.1f} - err = {4:.1e}'.format(jj,n,m,  d[n,m, jj]*100,  e[n,m, jj])
                    lineCoh.set_ydata(Coh)
                    ax1.title.set_text(ttl1)
                    #lineCohf.set_ydata(Cohf)
                    lineFit.set_ydata(Sinc(f[band], d[n, m, jj]))     
                    lineFit.set_xdata(f[band])     
                    
                #    ax1.set_ylim(np.min(Coh), np.max(Coh))
                    plt.draw()
                    plt.pause(0.001)
                p+=1

        ax2.clear()
        MapD = ax2.imshow(d[:,:,jj])
        ax2.set_title('Npmod = '+ str(Npmod))
        plt.draw()
        plt.pause(0.001)
        
        ax3.clear()
        MapC = ax3.imshow(e[:,:,jj])

        #MapD.set_data(d[:,:,jj]) 
        #print(d[:,:,jj])                               
        #fig.canvas.draw()
        #fig.canvas.flush_events() 
        plt.draw()
        plt.pause(0.001)
                   
        np.save('d_last.npy',d)
        jj+=1
            
            


#     cl.close()
#     wo.close()
#     wsound.close()
#     print(str(detect_n) + ' détections opérées')
    
#     os.system('ffmpeg -y -i anim.mp4 -i sound.wav -c:v copy -c:a aac -strict experimental ' + prfx +'_'+ str(Debut) + '_' + str(Fin) + 'b.mp4')

