# -*- coding: utf-8 -*-
# import required libraries

#%%###########################################################################
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as lines
import omp
from scipy.spatial.distance import cdist
from scipy.signal import medfilt


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
NbMems = 25
Fe = 10e3
Po = 20e-6    

# Physical parameters
c0 = 343
rho0 = 1.2

# Topographic parameters
ROOM_SIZE = (8.40, 10.2, 2.05)          # 6 box + 1 couloir + 6 box + 6 box   

# LSrcx = 2.5*2 + 0.9    # 2 longueurs de box + une largeur d'allée
# LSrcy = 6*1.7          # 6 largeurs de box
LSrcz = 0.2

# Espace des sources et antenne vus de dessus : 
# --------------------------------
# 1 pixel est un carré de 85cm**2
# 1 box est divisé en 6x3 pixels 
# l'allée centrale en 1x12 pixels
# l'espace des sources surveillé par une antenne 
# est composé de 2 rangées de 6 boxs
# L'espace complet comprend 7x12 pixels
# L'origine du repère est au coin SW
#
# L'antenne est centrée et 
# les faisceaux ordonnés suivant 0-1-2-3 -> W-N-E-S
# 
Lbox = 2.5
lbox = 1.7
Lallee = 6*lbox
lAllee = 0.85
LSrcx = 2*Lbox+lAllee
LSrcy = 6*lbox
lpix = lbox/2

Lz = 2.05
Rm = np.load('Xm_Cohrmds.npy').T
Xm = Rm[0,:] + 2.95 
Ym = Rm[1,:] + 5.1
Zm = np.ones((1,NbMems))*Lz
Rm = np.vstack((Xm, Ym, Zm))

nx = int(np.round(LSrcx/lpix))
ny = int(np.round(LSrcy/lpix))
xs = np.linspace(lpix/2, LSrcx-lpix/2, nx)
ys = np.linspace(lpix/2, LSrcy-lpix/2, ny)
npix = nx*ny

[Xs, Ys] = np.meshgrid(xs,ys)
Xs = Xs.flatten()
Ys = Ys.flatten()
Zs = np.ones_like(Xs)*0.2
Rs = np.array([Xs, Ys, Zs])

Rms = cdist(Rm.T,Rs.T)

iBoxG = []
iBoxD = []
for i in range(6) : 
    iBoxG.append([ix for ix in range(npix) if Xs[ix]<=Lbox          and Ys[ix]>=i*lbox and Ys[ix]<(i+1)*lbox])
    iBoxD.append([ix for ix in range(npix) if Xs[ix]>=Lbox+lAllee   and Ys[ix]>=i*lbox and Ys[ix]<(i+1)*lbox])
iAllee = [ix for ix in range(npix) if Xs[ix]>=Lbox and Xs[ix]<=Lbox+lAllee]
iBoxG = np.array(iBoxG)
iBoxD = np.array(iBoxD)
iAllee = np.array(iAllee)
# Paramètres de l'analyse spectrale
dfen = 10 #Nombre de Snapshot par seconde
FrameLength = int(Fe/dfen)
Nfft = FrameLength 
f = np.fft.rfftfreq(Nfft,1/Fe)
# Matrice de Green en champ libre
dphi =  2*np.pi*Rms*f[:,None,None]/c0
G = np.exp(1j*dphi)

#%%
Mems =np.load('ScenarBruno.npy')
# 
MemsOff =[2,3,14,20,21,26,27]
MemsOn = [m for m in np.arange(32) if m not in MemsOff]
Mems = Mems[MemsOn,:].T
Signal = np.zeros(Mems.shape[0])
t = np.arange(len(Signal))/Fe 
NbFrames = int(Mems.shape[0]/FrameLength)

fig = plt.figure(1, clear = True, figsize=(20,10))

# Schéma de l'antenne
ax1 = fig.add_subplot(441)
ax1.scatter(Xm, Ym, c = np.arange(NbMems))
ax1.set_aspect('equal')
ax1.grid()

axs = fig.add_subplot(442)
Sline, = axs.plot(f, f)
axs.set_xlim([0,np.max(f)])

# Cartographie de l'espace source
# 
ax2 = fig.add_subplot(422)
Map = ax2.pcolormesh(ys,xs,np.mean(Rms,axis=0).reshape(ny,nx).T, vmin=0, vmax = 1)
ax2.set_xlim(0,LSrcy) 
ax2.set_ylim(0,LSrcx)
ax2.scatter(Ym,Xm, facecolors='none', edgecolors='grey', s=0.5)
ax2.set_aspect('equal')
ax2.set_title('Espace des sources - StdBF')
ax2.grid()
ax2.set_yticks([0,Lbox, Lbox+lAllee,LSrcx ])
ax2.set_xticks(np.arange(7)*lbox)

# Chronogramme
ax3 = fig.add_subplot(212)
Chr = np.zeros((13,NbFrames))
Mop = ax3.pcolormesh(Chr, vmin = 0, vmax = 1 )
ax3.set_title('Chronogram')
ax3.grid()
ax3.set_ylim([0,13]) 
ax3.set_yticks(list(np.arange(1,7))+list(np.arange(7,14)))
labels = ['Box '+str(i) for i in range(1,13)]
labels = np.insert(labels, 6,'Allée')
ax3.set_yticklabels(labels)

# Niveau Lp
ax4 = fig.add_subplot(412)
# Signal d'un micro
line, = ax4.plot([],[])
Lpline, = ax4.plot([],[])
ax4.set_xlim([0,np.max(t)])
#ax4.axis('off')
Trans = np.load('TransitsBruno.npy' ) 
for Tr in Trans : 
    TrlineSig = lines.Line2D([Tr/Fe, Tr/Fe],
                        [-100, 100],
                        lw = 2, color ='red',
                        axes = ax4)
    TrlineChr = lines.Line2D([Tr/Fe*dfen, Tr/Fe*dfen],
                        [0, 13],
                        lw = 2, color ='red',
                        axes = ax3)
    ax4.add_line(TrlineSig)
    ax3.add_line(TrlineChr)

#plt.show()
#%%###################################################################
## Traitement données 

energy_threshold = 0.01
print( 'Process sequences...' )
jj = 0
Max = 0
Lp = np.zeros(NbFrames)
fcb = 600
fch = 4000

iBande = np.argwhere(np.logical_and(f>=fcb,f<=fch))
SpecAvgCum = np.zeros_like(f) 
OMPCum = np.zeros(npix) 
BFCum = np.zeros((1,npix)) 
BufLength = 5
SpecAvgBuf = np.zeros((int(Nfft/2+1), BufLength))
OMPImgBuf = np.zeros((npix, BufLength))
for iF in range(int(NbFrames)):
    # pour chaque trame de 100ms:
    Sigs = Mems[iF*FrameLength + np.arange(FrameLength),:]    
   # Sogs = Sigs/np.max(np.abs(Sigs))
    Lp[jj] = np.std(Sigs)
    if Lp[jj]>0.5 : 
        Spec = np.fft.rfft(Sigs, axis=0)#*f[:,None]
        SpecAvgBuf[:, iF%BufLength] = np.mean(np.abs(Spec), axis=1)   
        SpecAvgCum = np.mean(SpecAvgBuf, axis = 1) 
        SpecAvgdB = 20*np.log10(SpecAvgCum)
        dyndB = 30 
        Sline.set_ydata(SpecAvgdB)
        axs.set_ylim([np.max(SpecAvgdB)-dyndB, np.max(SpecAvgdB)])
        
        OMP = 0
        for ifo in iBande : 
            ix = ifo[0]
            Dico = G[ix,:,:]
            result = omp.omp(Dico, Spec[ix,:], maxit = 1, verbose = 0)
            OMPfo = result.coef+1e-12 
            OMP += OMPfo 
        OMPImgBuf[:, iF%BufLength] = OMP
        OMPAvg = np.mean(OMPImgBuf, axis = 1)
        for ii in range(6) : 
            Chr[ii,   jj] = np.sum(OMPAvg[iBoxG[ii]])
            Chr[ii+7, jj] = np.sum(OMPAvg[iBoxD[ii]])
        # Chr = medfilt(Chr,(1,9))
        ping = np.argmax(Chr[:,jj])
        Chr[:, jj] = 0
        Chr[ping, jj] = 1
                      
        Map.set_array((OMPAvg/np.max(OMPAvg)).reshape(ny,nx).T)
        Mop.set_array(Chr)

    Signal[jj*FrameLength + np.arange(FrameLength)] = Sigs[:,0]
    t = np.arange(len(Signal))/Fe
    line.set_xdata(t)
    line.set_ydata(Signal)
    Lpline.set_xdata(t[int(0.5*FrameLength):-FrameLength:FrameLength])
    Lpline.set_ydata(Lp)
    ax4.set_ylim([-np.max(Signal), np.max(Signal)])
    
    jj+=1

    plt.pause(0.1)
plt.show()




# %%
