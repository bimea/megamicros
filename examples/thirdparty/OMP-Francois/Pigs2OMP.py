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
import omp
import matplotlib.animation as manimation

# FFMpegWriter = manimation.writers['ffmpeg']
# metadata = dict(title='Movie', artist='Matplotlib',
#                 comment='Movie !')
# writer = FFMpegWriter(fps=10, metadata=metadata)



#%%###########################################################################
#Sensibilité : -26dBFS pour 104 dB soit 3.17 Pa
FS = 2**23
S = FS*10**(-26/20.) / 3.17
po = 20e-6
Fs = 10000
NumMicPlot = 1
plt.close('all')
datadir = './'
datadir = '/Users/brunogas/Data/muh5/'

#%%##################################################################
print('Initialisation BeamForming')
#StdBF###########################################################################
NbMems = 32
Fe = 10e3
Po = 20e-6    

# Physical parameters
c0 = 343
rho0 = 1.2

# Topographic parameters
Lx = 10
Ly = 8
Lz = 2.2

Rm = np.load('Xm_Cohrmds.npy').T
Ym = Rm[0,:]
Xm = Rm[1,:]
Zm = np.ones((1,32))*Lz
Rm = np.vstack((Rm, Zm))

nx = 6
ny = 6
xs = np.linspace(-Lx/2+Lx/12, Lx/2-Lx/12, nx)
ys = np.linspace(-Ly/2+Ly/5, Ly/2-Ly/5, ny)
#nx, ny= len(xs), len(ys)
[Xs, Ys] = np.meshgrid(xs,ys)
Xs = Xs.flatten()
Ys = Ys.flatten()
Zs = np.zeros_like(Xs)
Rs = np.array([Xs, Ys, Zs])
Rms = np.linalg.norm(Rs[:,np.newaxis,:]-Rm[:,:,np.newaxis], axis = 0)
ns = nx*ny
dfen = 10
nfft = int(Fe/dfen)
f = np.fft.rfftfreq(nfft,1/Fe)

G = np.outer(f,Rms).reshape(f.shape[0],Rms.shape[0], Rms.shape[1])/c0
G = np.exp(1j*2*np.pi*G)


#%%###################################################################
## Affichage 
##################################################################
#intialisation des graphiques
plt.ion()
fig = plt.figure(1, clear = True, figsize=(20,10))

ax1 = fig.add_subplot(421)
ax1.scatter(Xm,Ym, c=np.arange(32))
ax1.set_xlim(-1, 1)
ax1.set_ylim(-1, 1)
ax1.set_aspect('equal')
ax1.grid()

dyndB = 12
ax2 = fig.add_subplot(422)
Map = ax2.imshow(np.zeros((ny,nx)), vmin=70, vmax = 120,extent = [-5,5, -4,4])
ax2.scatter(Rm[0],Rm[1], facecolors='none', edgecolors='grey', s=0.5)
ax2.set_aspect('equal')
ax2.set_title('BF Bande')
ax2.grid()
ax2.set_xticks([-5,-1.666,1.666, 5,5])
ax2.set_yticks([-4,-0.8,0.8,4])

ax5 = fig.add_subplot(412)
line, = ax5.plot([],[])
ax5.set_xlim([0,100])
ax5.axis('off')


ax3 = fig.add_subplot(413)
Chr = np.zeros((8,1000))
Mop = ax3.pcolormesh(Chr, vmin=90, vmax = 120)

ax3.set_title('Chronogram')
ax3.grid()
ax3.set_ylim([0,8]) 
ax3.set_yticks(list(np.arange(1,4))+list(np.arange(5,9)))
labels = ['Box '+str(i) for i in range(1,7)]
labels = np.insert(labels, 3,'')
ax3.set_yticklabels(labels)

ax4 = fig.add_subplot(414)
Lpline, = ax4.plot(np.arange(1000),np.zeros(1000,))
ax4.set_title('Lpgram')
ax4.set_xlim([0,1000])

#%%###################################################################
## Traitement données 
##################################################################
Prefix = ['Pigs2']
Seqs = []
for prfx in Prefix :
    print( 'Starting with prefix sequence: ' + prfx )
    h5Names = np.sort([fin for fin in os.listdir(datadir) if fin.endswith('h5')])
    h5Files = [h5.File(datadir + h5Name, 'r') for h5Name in h5Names]
    for h5f in h5Files :  
        fig.suptitle(h5f)
        Seqs = np.sort([int(s) for s in h5f['muh5'].keys() if s.isnumeric()])
        Seqs = [str(i) for i in Seqs]
    NbSeqs = len(Seqs)
    print( 'Collected sequence number is: ' + str(NbSeqs) )

##################################################################
## Traitement des sequences et affichage du BF
##################################################################
    Debut = 0
    Duree = 900                                                                                                 
    Fin = Debut+Duree
    energy_threshold = 0.01

    print( 'Process sequences...' )
    print( 'Opening file ' + prfx + '-FiltreFV.wav, channels: ' + str(ns) + ', samplewidth: 4, framerate: ' + str(Fs) )
    
    wo = wave.open(prfx+'-FiltreFV.wav', 'wb')
    wo.setnchannels(ns)
    wo.setsampwidth(4)
    wo.setframerate(Fe)
    jj = 0
#     with writer.saving(fig, "anim.mp4", 100):
    NumSec = 100
    Max = 0
    BFF = np.zeros(8)
    LpdB = np.zeros(1000)
    Signal = np.empty(1000*1000)
    for Seq in Seqs[Debut:Fin]:
    # Pour chaque séquence d'une seconde:   
        # without counter, replace by -->>> Mems = h5f['muh5'][Seq]['sig'][:].T/S    
        Mems = h5f['muh5'][Seq]['sig'][1:].T/S
        print( 'processing sequence ' + prfx + ' - ' + str(int(NumSec)) + '/' + str(NbSeqs)  + ', Seq: ' + str(Seq) )
        ax3.set_title('sequence ' + prfx + ' - ' + str(int(NumSec)) + '/' + str(NbSeqs))
        NumSec += 1
        for ii in range(dfen):
            # pour chaque trame de 100ms:
            Sigs = Mems[ii*int(Fe/dfen) + np.arange(int(Fe/dfen)),:]    
            Spec = np.fft.rfft(Sigs, axis=0)
            SpecG = Spec[:, :, None]*G
            BFSpec = np.sum(SpecG,1)/NbMems
            BFSig = np.fft.irfft(BFSpec, axis = 0)
            BF = np.std(BFSig,axis = 0)            

            OMPfo = np.zeros((nx,ny))
            ifo  = np.argmax(np.mean(np.abs(Spec), axis=1)) 
            Dico = G[ifo,:,:]
            result = omp.omp(Dico, Spec[ifo,:], maxit = 1)
            OMPfo = result.coef+1e-12 #.reshape(nx,ny)

            BF[Ys==0] = 0
            # BFF[0:4] = (BF[0:4]+BF[4:8])/2            
            # BFF[8:12] =(BF[12:16]+BF[16:20])/2
            
            OMPfo[Ys==0] = 0
            #BFF[0] = (OMPfo[0:4]+OMPfo[4:8])/2            
            #BFF[1] =(OMPfo[12:16]+OMPfo[16:20])/2
            Box1 = np.logical_and(Xs<-1.67, Ys<-0.8)
            Box2 = np.logical_and(Xs>-1.67, Xs<1.67, Ys<-0.8)
            Box3 = np.logical_and(Xs>1.67, Ys<-0.8)
            Box4 = np.logical_and(Xs<-1.67, Ys>0.8)
            Box5 = np.logical_and(Xs>-1.67, Xs<1.67, Ys>0.8)
            Box6 = np.logical_and(Xs>1.67, Ys>0.8)
           
            BFF[0] = np.sum(OMPfo[Box1])
            BFF[1] = np.sum(OMPfo[Box2])
            BFF[2] = np.sum(OMPfo[Box3])
            BFF[5] = np.sum(OMPfo[Box4])
            BFF[6] = np.sum(OMPfo[Box5])
            BFF[7] = np.sum(OMPfo[Box6])
            
            LpdB[jj] = 20*np.log10(np.std(BFF)/Po)
                      
            Chr[:, jj]= 20*np.log10((BFF+Po)/Po)
            Mop.set_array(Chr)
            
            Signal[jj*int(Fe/dfen) + np.arange(int(Fe/dfen))] = Sigs[:,0]
            t = np.arange(len(Signal))/Fe
            line.set_xdata(t)
            line.set_ydata(Signal)
            ax5.set_ylim([-np.max(np.abs(Signal)), np.max(np.abs(Signal))])
            Lpline.set_ydata(LpdB)
            ax4.set_ylim([70, np.max(LpdB)])
           # Map.set_array(20*np.log10((BF+Po)/Po))
           # Map.set_array(20*np.log10((BFF+Po)/Po).reshape((ny,nx)))
            Map.set_array(20*np.log10((OMPfo+Po)/Po).reshape((ny,nx)))
            jj+=1
            if jj>=1000 : 
                Signal = np.roll(Signal,-1000)
                Chr = np.roll(Chr,-1,axis = 1)
                LpdB = np.roll(LpdB,-1)
                jj = 999    
            
            fig.canvas.draw()
            fig.canvas.flush_events() 
            plt.draw()
   
            sw = BFSig/2
            ow = np.int32(sw*2**31)
            for i in range(len(ow)):
                data = struct.pack('<'+'l'*ns, *ow[i, [j for j in range(ns)]])     
                wo.writeframesraw(data)

wo.close()

#os.system('ffmpeg -y -i anim.mp4 -i sound.wav -c:v copy -c:a aac -strict experimental ' + prfx +'_'+ str(Debut) + '_' + str(Fin) + 'b.mp4')

