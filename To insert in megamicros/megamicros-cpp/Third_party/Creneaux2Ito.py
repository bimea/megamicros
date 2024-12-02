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
Zm = np.ones((1,NbMems))*Lz
Rm = np.vstack((Rm, Zm))

nx = 10
ny = 10
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
ff = 50
dms = np.exp(-1j*2*np.pi*f[ff]*Rms)/c0
dRms = np.zeros((np.sum(range(NbMems)),ns))
kk = 0
for ii in range(NbMems):
    for jj in range(ii):
        print(kk, ii, jj)
        dRms[kk,:] = Rms[ii,:]-Rms[jj,:]
        kk+=1
dRms/=c0
#%%###################################################################


#%%###################################################################
## Traitement données 
##################################################################
h5f = h5.File('mu5h-20220718-144608.h5', 'r')
Seqs = np.sort([int(s) for s in h5f['muh5'].keys()])
Seqs = [str(i) for i in Seqs]
NbSeqs = len(Seqs)
print( h5f.filename +' - Collected sequence number is: ' + str(NbSeqs) )

##################################################################
## Traitement des sequences et affichage du BF
##################################################################
Debut =0
#Duree = np.min((5*60, 539-Debut))
Duree = 100                                                                                              
Fin = Debut+Duree
energy_threshold = 0.01

print( 'Process sequences...' )
   
jj = 0
NumSeq = 0
Max = 0
NBuf = 32
NbF = nfft//2+1
PhixxBuf = np.zeros((NBuf,NbMems,NbMems), dtype='complex')
sMMSE = np.zeros((NbSeqs*dfen, ns))
for Seq in Seqs[Debut:Fin]:
# Pour chaque séquence d'une seconde:       
    Mems = h5f['muh5'][Seq]['sig'][1:,:]/S
    x = np.zeros((dfen, NbMems, NbF), dtype='complex')        
    for ii in range(dfen):
        Frame = Mems[:,ii*int(Fe/dfen) + np.arange(int(Fe/dfen))]    
        x[ii,:,:] = np.fft.rfft(Frame, axis=1)              
        PhixxBuf[jj%NBuf,:,:] = np.outer(x[ii,:,ff],np.conj(x[ii,:,ff]))
        Phixx = np.mean(PhixxBuf, axis=0)
        phixx = PhixxBuf[jj % NBuf,:,:]     
        
        for s in range(ns):
            Num = 0
            Den = 0        
            ll = 0
            for nn in range(NbMems) : 
                for mm in range(nn) :
                    Num += np.sin(2*np.pi*f[ff]*dRms[ll,s]) * np.imag(x[ii,nn,ff]*x[ii,mm,ff]) 
                    Den += np.sin(2*np.pi*f[ff]*dRms[ll,s])**2
                    ll += 1
            phiss = -np.real(Num/Den)                 
            phiyy =  np.mean(np.abs(x[ii,:,ff])**2, axis=0)
            p =  phiss/phiyy
            if p<0 :
                p = 0
            if p>1 : 
                p = 1
            yNum = np.conj(dms[:,s].T)@(np.linalg.pinv(Phixx)@x[ii,:,ff])
            yDen = np.conj(dms[:,s].T)@(np.linalg.pinv(Phixx)@dms[:,s])
            sMMSE[jj,s] = np.abs(p*yNum/yDen)
        print(jj,np.argmax(sMMSE[jj,:]))
 
        jj+=1               
        
                
       
