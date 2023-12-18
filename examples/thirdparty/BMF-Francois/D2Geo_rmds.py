#%%
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  4 14:39:58 2022

@author: francois
"""

import numpy as np
from rcbox.rmds import rmdsw, RMDS
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation as R
#%%
plt.close('all')
D = np.load('d_4.npy')[:,:,-1]
E = np.load('e_4.npy')[:,:,-22]
W = 1-E/np.max(E)
np.fill_diagonal(W, 0)

#plt.pcolormesh(D.T)
#plt.plot(np.mean(D,axis=1))
#plt.plot(D[32:64,-1])
plt.imshow(W)
plt.colorbar()
#%%
mems_Bruno = np.array((
        (0, 3.82, 0), (0, 9.82, 0), (0, 15.82, 0), (0,  21.82, 0), (0,  27.82, 0), (0, 33.82, 0), (0, 39.82, 0), (0, 45.82, 0),
        (45.81, 0, 0), (39.81, 0, 0), (33.81, 0, 0), (27.81, 0, 0), (21.81, 0, 0), (15.81, 0, 0), (9.81, 0, 0) , (3.81, 0, 0),
        (49.63, 45.82, 0), (49.63, 39.82, 0), (49.63, 33.82, 0), (49.63,  27.82, 0), (49.63,  21.82, 0), (49.63, 15.82, 0), (49.63, 9.82, 0), (49.63, 3.82, 0),
        (3.81, 49.63, 0), (9.81, 49.63, 0), (15.81, 49.63, 0), (21.81, 49.63, 0), (27.81, 49.63, 0), (33.81, 49.63, 0), (39.81, 49.63, 0), (45.81, 49.63, 0)
    ))/100

OrdreVrai = list(np.arange(8)) + list(np.arange(8) + 24) + list(np.arange(8) + 16) + list(np.arange(8) + 8)
mems_Correct = mems_Bruno[OrdreVrai]

MemsOff =[2,3,14,20,21,26,27]
MemsOn = [m for m in np.arange(32) if m not in MemsOff]

Rm_Br = mems_Bruno[:,:2].T
Rm_Br = Rm_Br[:, MemsOn]

X_Br = Rm_Br[0,:]
Y_Br = Rm_Br[1,:]

Rm_Co = mems_Correct[:,:2].T
Rm_Co = Rm_Co[:, MemsOn]

X_Th = Rm_Co[0,:]
X_Th-=np.min(X_Th)
Y_Th = Rm_Co[1,:]
#%%
#Xmiters, Outliers, Eps = rmdsw(D *dm/np.min(np.diag(D, k=1)) , lbda=0.0025, Ndim=2, W=W, Xinit=Rm[:2,:], Maxit=25000, EpsLim=1e-12, EpsType="meters", verbose=1)
Xmiters, Outliers, Eps = rmdsw(D  , lbda=0.025, Ndim=2, W=W, Xinit=None, Maxit=25000, EpsLim=1e-12, EpsType="meters", verbose=1)
def align(X, x_ref):
    
    d = x_ref.shape[1]
    centroid_ref = x_ref.mean(axis=0)
    x_ref_centered = x_ref - centroid_ref

    x_to_align = X[-1, ...]
    
    centroid_to_align = x_to_align.mean(axis=0)
    x_to_align_centered = x_to_align - centroid_to_align

    cov = x_to_align_centered.T @ x_ref_centered

    u, s, v = np.linalg.svd(cov)

    e = np.eye(d)
    e[-1, -1] = np.sign(s.prod())

    # create Rotation matrix U
    r = v.T @ e @ u.T

    # apply rotation
    x_aligned_centered = x_to_align_centered @ r
    return x_aligned_centered + centroid_ref

Xma = align(Xmiters, Rm_Co[:2,:].T)

XmPigs = Xma[:, 0]
YmPigs = Xma[:, 1]
#%%

fig = plt.figure(figsize = (20, 10))
ax = fig.add_subplot(111)
lineMics_Th = ax.scatter(X_Th, Y_Th, cmap='jet', s = 100, c = np.arange(25), label = 'Théorique')
ax.set_aspect('equal')
ax.grid()

   
lineMics_Br = ax.scatter(X_Br-np.min(X_Br)+1,Y_Br,  marker='o', s = 100, cmap='jet', c = np.arange(25), label = 'Bruno')
lineMics_Cg = ax.scatter(XmPigs-np.min(XmPigs)+2,YmPigs-np.min(YmPigs), s=100, marker='o', cmap='jet', c = np.arange(25),  label = 'Calibration')
ax.legend(bbox_to_anchor=(1.05, 1.0), loc='upper left')
plt.tight_layout
plt.show()

#np.save('Xm_Cohrmds.npy', Xma)
# %%

fig = plt.figure(figsize = (10, 10))
ax = fig.add_subplot(111)
lineMics_Th = ax.scatter(X_Th, Y_Th, s=500, marker='o', facecolors = 'white', linewidth=3, edgecolors = 'black', label = 'Théorique')
ax.set_aspect('equal')
ax.grid()
    
lineMics_Cg = ax.scatter(XmPigs,YmPigs, s=500, marker='x', c = 'red', label = 'Calibration')
ax.legend(bbox_to_anchor=(1.05, 1.0), loc='upper left')
plt.tight_layout
plt.show()

#%%