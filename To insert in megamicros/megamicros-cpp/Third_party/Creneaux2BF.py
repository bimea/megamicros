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



#%%###########################################################################
#Sensibilité : -26dBFS pour 104 dB soit 3.17 Pa
FS = 2**23
S = FS*10**(-26/20.) / 3.17
po = 20e-6
Fs = 10000
NumMicPlot = 1
plt.close('all')
datadir = './'

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
Lx = 9.42
Ly = 9.42
Lz = 2.2

Rm = np.load('Xm_Cohrmds.npy').T
Ym = Rm[0,:]
Xm = Rm[1,:]
Zm = np.ones((1,32))*Lz
Rm = np.vstack((Rm, Zm))
#Rm = Rm[:,8:16]

nx = 30
ny = 30
xs = np.linspace(-Lx/2, Lx/2, nx)
ys = np.linspace(-Ly/2, Ly/2, ny)
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

G = np.outer(f, Rms).reshape(f.shape[0],Rms.shape[0], Rms.shape[1])/c0
G = np.exp(+1j*2*np.pi*G)

#%%###################################################################
## Affichage 
##################################################################
#intialisation des graphiques
plt.ion()
fig = plt.figure(1, clear = True, figsize=(20,10))

dyndB = 3
ax11 = fig.add_subplot(441)
Map11 = ax11.imshow(np.zeros((ny,nx)), vmin=-dyndB, vmax = 0,extent = [-Lx/2,Lx/2, -Ly/2,Ly/2], cmap='inferno')
ax11.scatter(Rm[0],Rm[1], facecolors='none', edgecolors='grey', s=0.5)
ax11.set_aspect('equal')
ax11.set_title('BF fo +')
ax11.grid()

ax12 = fig.add_subplot(442)
Map12 = ax12.imshow(np.zeros((ny,nx)), vmin=1e-12, vmax = 10, extent = [-Lx/2,Lx/2, -Ly/2,Ly/2], cmap='inferno')
ax12.set_aspect('equal')
ax12.set_title('OMP fo +')
ax12.grid()


ax5 = fig.add_subplot(412)
line, = ax5.plot([],[])
ax5.set_xlim([0,100])
ax5.axis('off')

ax3 = fig.add_subplot(413)
Chr = np.zeros((8,1000))
Mop = ax3.pcolormesh(Chr, vmin=90, vmax = 120, cmap='inferno')

ax3.set_title('Chronogram')
ax3.grid()
ax3.set_ylim([0,8]) 
ax3.set_yticks(list(np.arange(1,4))+list(np.arange(5,9)))
labels = ['Box '+str(i) for i in range(1,7)]
labels = np.insert(labels, 3,'')
ax3.set_yticklabels(labels)

ax4 = fig.add_subplot(414)
Spgrm = np.ones((501,1000))
Mip = ax4.pcolormesh(np.arange(1000), f, Spgrm, vmin=90, vmax = 120, cmap = 'inferno')
ax4.set_title('Spgram')
ax4.set_xlim([0,1000])
ax4.set_ylim([0,1500])

#%%###################################################################
## Traitement données 
##################################################################
Prefix = ['mu5h-20220718-144608']
Seqs = []
for prfx in Prefix :
    print( 'Starting with prefix sequence: ' + prfx )
    h5Names = np.sort([fin for fin in os.listdir(datadir) if fin.endswith('h5')])
    h5Files = [h5.File(datadir + h5Name, 'r') for h5Name in h5Names]
    for h5f in h5Files :  
        fig.suptitle(h5f)
        Seqs = np.sort([int(s) for s in h5f['muh5'].keys()])
        Seqs = [str(i) for i in Seqs]
    NbSeqs = len(Seqs)
    print( 'Collected sequence number is: ' + str(NbSeqs) )

##################################################################
## Traitement des sequences et affichage du BF
##################################################################
    Debut = 150
    Duree = np.min((5*60, 539-Debut))                                                                                                 
    Fin = Debut+Duree
    energy_threshold = 0.01

    print( 'Process sequences...' )
   
    jj = 0
    NumSeq = 0
    Max = 0
    BFF = np.zeros(8)
    LpdB = np.zeros(1000)
    Signal = np.zeros(1000*1000)
    ifo  = np.argmin(np.abs(f-500)) 
    OMPfo = np.zeros((nx*ny,))
    #num = np.array(['200','230','270','310', '350', '390'])
    for Seq in Seqs[Debut:Fin]:
        # Pour chaque séquence d'une seconde:       
        Mems = h5f['muh5'][Seq]['sig'][1:,:].T/S
        print( 'processing sequence ' + prfx + ' - ' + str(int(Seq)) + '/' + str(NbSeqs)  + ', Seq: ' + str(Seq) )
        ax3.set_title('sequence ' + prfx + ' - ' + str(int(NumSeq)) + '/' + str(Duree)+' - ' +str(int(Seq)) + '/' + str(NbSeqs))
        NumSeq += 1
        for ii in range(dfen):
            # pour chaque trame de 100ms:
            Sigs = Mems[ii*int(Fe/dfen) + np.arange(int(Fe/dfen)),:]    
            Spec = np.fft.rfft(Sigs, axis=0)/np.sqrt(1000)
            SpecG = Spec[ifo, :, None]*G[ifo,:,:]
            BF = np.abs(np.sum(SpecG,0)/NbMems)**2
            ax12.set_title(str(np.max(BF)))
            #BFSig = np.fft.irfft(BFSpec, axis = 0)
            #BF = np.std(BFSig,axis = 0)
            
            
            #ifo  = np.argmax(np.mean(np.abs(Spec), axis=1)) 
            
            Dico = G[ifo,:,:]
            result = omp.omp(Dico, Spec[ifo,:], maxit = 1)
            OMPfo += result.coef+1e-12 #.reshape(nx,ny)

            
            Spgrm[:,jj] = 20*np.log10((np.abs(Spec[:,0])+Po)/Po)
            Mip.set_array(Spgrm)

            Signal[jj*int(Fe/dfen) + np.arange(int(Fe/dfen))] = Sigs[:,0]
            t = np.arange(len(Signal))/Fe
            line.set_xdata(t)
            line.set_ydata(Signal)
            ax5.set_ylim([-np.max(np.abs(Signal)), np.max(np.abs(Signal))])
          
            BFdB = 10*np.log10(BF/np.max(np.abs(BF)))           
            if np.max(BF)>10:
                Map11.set_array(BFdB.reshape((ny,nx)))
                Map12.set_array(OMPfo.reshape((ny,nx)))
            
            #Map.set_array(20*np.log10((OMPfo+Po)/Po).reshape((ny,nx)))
            jj+=1
            if jj>=1000 : 
                Signal = np.roll(Signal,-1000)
             #   Chr    = np.roll(Chr,-1,axis = 1)
                Spgrm  = np.roll(Spgrm,-1,axis = 1)
                #LpdB = np.roll(LpdB,-1)
                jj = 999    
            
            fig.canvas.draw()
            fig.canvas.flush_events() 
            plt.draw()
   
          