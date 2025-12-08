# -*- coding: utf-8 -*-

"""
Module contenant toutes les fonctions pour
la calibration géométrique d'antenne

Created on Wed May 14 12:20:11 2014
@author: charles

Voir aussi: GéoCalib dans bimea/Manips
"""

from __future__ import division
import numpy as np
import scipy.signal as sig

import scipy.optimize as opt
import scipy as sp
import pylab as pl
from scipy.spatial.distance import squareform, pdist
from scipy import linalg as linalg

#import rpy2.robjects as ro
#from rpy2.robjects.numpy2ri import numpy2ri
#ro.conversion.py2ri = numpy2ri

#from rpy2.robjects.packages import importr

###############################################################################
#Util: Création d'une matrice de pondération pour MDS locale:
def makeWlocal(D, dmax):
    """
    Contruit une matrice de pondération pour MDS local.
    """
    W = np.zeros_like(D)
    W[np.where(D<=dmax)] = 1
    W[np.where(D>dmax)] = 0
    np.fill_diagonal(W, 0)
    return W

#MDS classique:
def cmds(D, Ndim):
    """
    Classical MDS: X = cmds(D, Ndim)

    Entrées
    -------
    D: (Nr,Nr) array numpy
        Matrice des distances mic-mic complète (ie avec symétrie)
    Ndim: int
        Dimension spatiale de l'antenne à calibrer
    
    Sortie
    ------
    X: (Nr,Ndim) array numpy 
        matrice des coordonnées de l'antenne
    """
    Nr = D.shape[0]
    #idxtril = np.tril_indices(Nr,k=0)
    
    J = np.identity(Nr) - np.ones((Nr,Nr)) / Nr
    B = -0.5 * np.dot(J, np.dot(D**2,J))
    eigenValues, eigenVectors = np.linalg.eig(B)
    idx = eigenValues.argsort()[::-1]
    eigenValues = eigenValues[idx]
    eigenVectors = eigenVectors[:,idx]
    
    return np.dot(eigenVectors[:,0:Ndim], np.diag(eigenValues[0:Ndim]**0.5))

#Smacof:
#def smacof(D, Ndim, typeMds = 'ratio', W = 'null' , init = 'null',
#           ties = 'primary', verbose = False, relax = False, modulus = 1, 
#           itmax = 1000, eps = 1e-6, SplineDegree = 2, SplineIntKnots = 2):
#    """
#    Smacof MDS: X = smacof(D, Ndim, typeMds, W, init, ties, verbose, ...)
#    
#    smacofSym function wrap from the R package of Smacof method.
#
#    Inputs
#    ------
#    D: (Nr,Nr) array numpy
#        Matrice des distances mic-mic complète (ie avec symétrie)
#    Ndim: int
#        Dimension de l'espace de sortie
#    typeMds: str
#        "ratio", "interval", "ordinal" ou "mspline"
#    W: 'null' ou (Nr,Nr) array numpy
#        Matrice de pondération de D
#    init: 'null' ou matrice d'initialisation
#        
#    ties: "primary", "secondary" ou "tertiary"
#        Utile pour le typeMds = "ordinal"
#    verbose: Boolean
#        
#    relax: Boolean
#        Relaxation lors de la majorisation
#    modulus: int
#        Number of smacof iterations per monotone regression call
#    itmax: int
#        Nb max d'itérations
#    eps: float
#        Convergence criterion
#    SplineDegree: int
#        Degree of the spline for "mspline" MDS type
#    SplineIntKnots: int
#        Number of interior knots of the spline for "mspline" MDS type
#        
#    
#    Outputs
#    -------
#    X: (Nr,Ndim) array numpy 
#        matrice des coordonnées de l'antenne
#    
#    Optimization Parameters: list (11 elements)
#        0 delta = diss
#        1 obsdiss = dhat
#        2 confdiss = confdiss
#        3 iord = dhat2$iord.prim,
#        4 stress = stress,
#        5 spp = spp,
#        6 ndim = p,
#        7 model = "Symmetric SMACOF",
#        8 niter = itel,
#        9 nobj = n,
#        10 type = type,
#        11 call = match.call()) 
#        
#    """
#    
#    rsmacof = importr('smacof')
#    
#    if W == 'null': W = ro.NULL
#    if init == 'null': init = ro.NULL
#     
#    stress = rsmacof.smacofSym(D, Ndim, typeMds, W, init, ties, verbose)
#    
#    output = np.array(stress[4]) # X Nr*Ndim
#    OptParams = [np.array(stress[0]), np.array(stress[1]), np.array(stress[2]),
#                 np.array(stress[3]), stress[5][0], np.array(stress[6]), 
#                stress[7][0], stress[8][0], stress[9][0], stress[10][0],
#                stress[11][0], stress[12]]
#    
#    return output, OptParams

#Robust MDS:
def smart_logspace(start, stop, num):
    startexp, stopexp = np.log10(start), np.log10(stop)
    return np.logspace(startexp, stopexp, num)

def _Slambda(var, lbda): #Soft thresholding Operator
    out = sp.sign(var) * sp.maximum(sp.absolute(var) - lbda/2, 0.0)
    return out


def _e_vect(n,N):
    out = np.zeros((1,N)).T
    out[n,0] = 1
    return out

def _Lmake(N, W=None):
    L = np.zeros((N,N))
    if W==None:
            L[:,:] = -1
            L += N*np.eye(N)
    else:
        for nn in range(N):
            for mm in range(nn,N):
                L += W[nn,mm]*np.dot(_e_vect(nn,N)-_e_vect(mm,N), (_e_vect(nn,N)-_e_vect(mm,N)).T)
    return L

def rmdsw(D, lbda=0.5, Ndim=3, W=None, Xinit=None, Maxit=5000, EpsLim=10**-6, EpsType="Forero2012", verbose=1):
    
    Nr = D.shape[0]
    
    if W == None: #On prend tous les éléments de D en compte: wij=1 pour tt (i,j)
        W = np.ones((Nr,Nr))
        np.fill_diagonal(W, 0)
    
    Wflat = squareform(W)    
    Dflat = squareform(D)
        
    X = np.zeros((Maxit, Ndim, Nr))
    if Xinit == None:
        X[0,:,:] = np.random.randn(Ndim, Nr)
    else:
        X[0,:,:] = Xinit.T # Xinit.T
    
    O = np.zeros((Maxit, Nr*(Nr-1)/2))
    
    L = _Lmake(Nr, W)
    Lpinv = linalg.pinv(L)
    
    A1 = np.zeros((Nr,Nr))
    A11 = np.zeros((Nr*(Nr-1)/2,))
    L1 = np.zeros((Nr,Nr))
    
    Eps = np.zeros(Maxit,)
    Err = np.zeros_like(Eps)
    
    for t in range(Maxit-1):
        if verbose: print(f't: {t:d} , Eps(t-1): { Eps[t-1]:.7f}')
        DDt = pdist(X[t,:,:].T)    
        #Calcul O(t+1):
        for nm in range(Nr*(Nr-1)//2):
                O[t+1,nm] = _Slambda(Wflat[nm]*(Dflat[nm] - DDt[nm]), lbda)
        
        #Calcul X(t+1)
        #Calcul de L1(O(t+1), X(t))
        for nm in range(Nr*(Nr-1)//2):
                if DDt[nm] != 0 and Dflat[nm] > O[t+1,nm]:
                    A11[nm] = Wflat[nm] * (Dflat[nm]-O[t+1,nm])/DDt[nm]
                else:
                    A11[nm] = 0
        
        A1 = squareform(A11)
        L1 = sp.diag(A1.sum(1)) - A1
        #Calcul X(t+1)
        X[t+1,:,:] = sp.dot(X[t,:,:], sp.dot(L1, Lpinv))
        if EpsType=="Forero2012":
            Eps[t] = linalg.norm(X[t+1,:,:]-X[t,:,:])/linalg.norm(X[t+1,:,:])
        elif EpsType=="meters":
            Eps[t] = linalg.norm(X[t+1,:,:]-X[t,:,:])
        #Err[t] = cal.errXthXest(ant.Xmic[:,0:2], X[t,:,:].T)
        if Eps[t] < EpsLim:
            break
    
    Err = Err[0:t+1]
    Eps = Eps[0:t+1]
    X = X[0:t+1,:,:].transpose(0,2,1)
    O = O[0:t+1,:]
    
    return X, O, Eps

def rmds_LambdaTune(D, lbdas, NOutlierLim, Ndim, Dlim, Xinit, Maxit, EpsLim, EpsType):
    
    Nlbda = lbdas.size
    Nr = D.shape[0]
    W = makeWlocal(D, Dlim)
    NW =  squareform(W).sum()
    
    #antExp.SetX(np.concatenate((Xsmacof, np.zeros((Nr,3-Ndim))), axis=1) )
    #print "smacof ok"
    #raw_input()
    
    Xest = np.zeros((Nlbda, Nr, Ndim))
    Oest = np.zeros((Nlbda, Nr*(Nr-1)//2))
    NOutliers = np.zeros((Nlbda,))
    
    for itlbda in range(Nlbda):
        print(f'lambda: {itlbda:d}/{Nlbda:d} ({lbdas[itlbda]:.3f})')
        lbda = lbdas[itlbda]
        
        if itlbda == 0:
            X, O, Eps = rmdsw(D, lbda, Ndim, W, Xinit, Maxit, EpsLim, EpsType, 1)
        else:
            X, O, Eps = rmdsw(D, lbda, Ndim, W, Xest[itlbda-1,:,:], Maxit, EpsLim, EpsType, 0)
        
        Oest[itlbda,:] = O[-1,:]
        Xest[itlbda,:,:] = X[-1,:,:]
        #Errest[itlbda] = Err[-1]
        NOutliers[itlbda] = np.where(O[-1,:] != 0)[0].__len__()
        
        #print '%.1f p100 d''outliers' %(100 * NOutliers[itlbda] / NW)
        #pl.pause(0.01)
        
        if NOutliers[itlbda] / NW > NOutlierLim :
            Oest = Oest[0:itlbda, :]
            Xest = Xest[0:itlbda, :, :]
            NOutliers = NOutliers[0:itlbda]
            lbdas = lbdas[0:itlbda]
            break  #!!!problème, le break n'est pas pris en compte

    return Xest, Oest, NOutliers, lbdas

###############################################################################
#Quelques ondelettes maison...:

def haar_ort(N, n):
    out = np.zeros((N,))
    out[N*(2**n - 1)/2**(n+1) : N//2] = 1.
    out[N//2 : N*(2**n + 1)/2**(n+1)] = -1.
    out *= np.sqrt(2**n/N)
    return out

def haar(N, a):
    """
    Fenêtre de Haar de N samples, égal à:
    1/(2a) entre -a et 0, -1/(2a) entre 0 et a, et 0 ailleurs.
    """
    if a > N//2: a = N//2
    out = np.zeros((N,))
    out[N//2-a : N//2] = 1.
    out[N//2 : N//2+a] = -1.
    out *= np.sqrt(1./(2*a))
    return out

def saw(N, a):
    if a>N//2: a = N//2
    out = np.zeros((N,))
    out[N//2-a : N//2] = np.linspace(0,1,a)
    out[N//2 : N//2+a] = np.linspace(-1,0,a)
    out *= np.sqrt(2**0.5/a)
    return out

###############################################################################
#Estimation D

def _fNMopt(d, mici, micj, C, freq, c0):
    """
    fNMopt(d, mici, micj, Coherence, freq)
    
    Fonction qui retourne l'erreur quadratique entre le modèle du champ 
    diffus en sinc et la cohérence mesurée.
    Pratique pour utiliser avec scipy.optimize.fmin (méthode Nelder-Mead)
    """
    return np.sum( (C[:,mici,micj].real - np.sinc(2.0*freq*d/c0))**2*sig.windows.tukey(len(freq),0.2))


import scipy.special
def _fNMoptStBern(d, mici, micj, C, freq, c0):
    """
    fNMopt(d, mici, micj, Coherence, freq)
    
    Fonction qui retourne l'erreur quadratique entre le modèle du champ 
    diffus en sinc et la cohérence mesurée.
    Pratique pour utiliser avec scipy.optimize.fmin (méthode Nelder-Mead)
    """
    return np.sum( (C[:,mici,micj].real - scipy.special.jv(0,2.0*np.pi*freq*d/c0))**2 )

def _fLMopt(d, mici, micj, C, freq, c0):
    """
    fLMopt(d, mici, micj, Coherence, freq)
    
    Fonction qui retourne la différence entre le modèle du champ 
    diffus en sinc et la cohérence mesurée.
    
    Levenburg-Marquardt
    """
    return C[:,mici,micj].real - np.sinc(2*freq*d/c0)*sig.windows.tukey(len(freq),0.2)



def C2Dfit(C, freq, D_init, c0, Err=False):
    """
    Estimateur de la matrice de distances D via un fit du modèle en sinus cardinal.
    
    Méthode de Nelder-Mead.
    """
    Nr = C.shape[1]
    Dopt = np.zeros((Nr,Nr))
    ErrOut = np.zeros_like(Dopt)
    
    print(f"Fit des sinc: {Nr:d} mics")
    if D_init.__class__ == np.ndarray:
        assert D_init.shape == C.shape[1:3], "D_init et C de tailles différentes"
        for ii in range(Nr):
            print(f"{ii:d}")
            for jj in range(ii+1,Nr):
                Dopt[ii,jj], ErrOut[ii,jj], z,z,z = opt.fmin(_fNMopt, [D_init[ii,jj]], (ii,jj, C, freq, c0), disp=0, full_output=1)
    else:
        for ii in range(Nr):
            print(f"{ii:d}")
            for jj in range(ii+1,Nr):
                Dopt[ii,jj], ErrOut[ii,jj], z,z,z = opt.fmin(_fNMopt, [D_init], (ii,jj, C, freq, c0), disp=0, full_output=1)
    
    print(" ")
    if Err==True:
        return Dopt + Dopt.T, ErrOut
    else:
        return Dopt + Dopt.T

def C2DfitStBern(C, freq, D_init, c0, Err=False):
    """
    Estimateur de la matrice de distances D via un fit du modèle en sinus cardinal.
    
    Méthode de Nelder-Mead.
    """
    Nr = C.shape[1]
    Dopt = np.zeros((Nr,Nr))
    ErrOut = np.zeros_like(Dopt)
    
    print(f"Fit des sinc: {Nr:d} mics")
    if D_init.__class__ == np.ndarray:
        assert D_init.shape == C.shape[1:3], "D_init et C de tailles différentes"
        for ii in range(Nr):
            print(f"{ii:d}")
            for jj in range(ii+1,Nr):
                Dopt[ii,jj], ErrOut[ii,jj], z,z,z = opt.fmin(_fNMoptStBern, [D_init[ii,jj]], (ii,jj, C, freq, c0), disp=0, full_output=1)
       
                
    else:
        for ii in range(Nr):
            print(f"{ii:d}")
            for jj in range(ii+1,Nr):
                Dopt[ii,jj], ErrOut[ii,jj], z,z,z = opt.fmin(_fNMoptStBern, [D_init], (ii,jj, C, freq, c0), disp=0, full_output=1)
    
    print(" ")
    if Err==True:
        return Dopt + Dopt.T, ErrOut
    else:
        return Dopt + Dopt.T


def C2DfitLSq(C, freq, D_init, c0):
    """
    Estimateur de la matrice de distances D via un fit du modèle en sinus cardinal.
    
    Méthode de Levenberg-Marquardt.
    """
    Nr = C.shape[1]
    doptAnt = np.zeros((Nr,Nr))

    if D_init.__class__ == np.ndarray:
        assert D_init.shape == C.shape[1:3], "D_init et C de tailles différentes"
        for ii in range(Nr):
            print(f"{ii:d}/{Nr:d}")
            for jj in range(ii+1,Nr):
                doptAnt[ii,jj], dump = opt.leastsq(_fLMopt, [D_init[ii,jj]], (ii,jj, C, freq, c0))
                
    else:
        for ii in range(Nr):
            print(f"{ii:d}/{Nr:d}")
            for jj in range(ii+1,Nr):
                doptAnt[ii,jj], dump = opt.leastsq(_fLMopt, [D_init], (ii,jj, C, freq, c0))
    
    return doptAnt + doptAnt.T
    
def DenoiseD(D, Ndim, epslim=0.5, itmax = 100):
    """
    DenoiseD(D, Ndim, epslim=0.5, itmax = 100)
    
    Fonction de débruitage d'une matrice de distances D.
    
    Cf. "Robust Array Calibration using Time Delays with Application to Ultrasound Tomography"
    """
    
    #Pour phi1/phi2/phi3: cf. "Robust Array Calibration using Time Delays with Application to Ultrasound Tomography"

    Q = D**2
    Q = (Q+Q.T)/2 #phi1
    ii=0
    loop = True
    
    while loop:
        ii += 1
        np.fill_diagonal(Q, 0.0) #phi2
        Q = Q.clip(0.) #phi3
        u, s, v = pl.svd(Q)
        Qplus = np.dot(u[:,0:Ndim+2], np.dot(np.diag(s[0:Ndim+2]), v[0:Ndim+2,:]) )
        eps = np.linalg.norm(Qplus-Q)
        print(eps.round(3)), 
        if eps > epslim: 
            Q = Qplus
        elif ii > itmax:
            loop = False
        else:
            loop = False
    
    print("Nb itération: {ii:d}, eps={eps:.4f}")
    return Q**0.5

###############################################################################
#Fonctions d'analyse des résultats

def errXthXest(Xth, Xest):
    """
    errXthXest(Xth, Xest):
    
    Retourne l'erreur quadratique entre Xth et Xest. Invariant selon toute 
    translation/rotation sur Xth et/ou Xmes. 
    
    Inputs
    ------
    Xth: (Nr, Ndim) numpy array
        Matrice de Nr coordonnées en dimension Ndim
    
    Xth: (Nr, Ndim) numpy array
        Matrice de Nr coordonnées en dimension Ndim
        
    Output
    -------
    Erreur quadratique (ramenée en mètre)
    """
    
    assert Xth.shape == Xest.shape, "Xth et Xest de tailles différentes"
    Nr = Xth.shape[0]
    J = np.identity(Nr) - np.ones((Nr,Nr)) / Nr
    return np.linalg.norm(  np.dot(J, np.dot(Xth, np.dot(Xth.T, J)))
                            - np.dot(J, np.dot(Xest, np.dot(Xest.T, J))), 
                            ord='fro') / Nr

        
def DthVSDmes(Dth, Dmes):
    """
    plot le nuage de points Dmes(Dth)
    """
    assert Dth.shape[0]==Dmes.shape[0], "Dth et Dmes de taille différentes"
    assert np.array_equal(Dth, Dth.T) , "Dth asymétrique."
    assert np.array_equal(Dmes, Dmes.T) , "Dmes asymétrique."
    
    Nr = Dth.shape[0]
    
    idxtriu = np.triu_indices(Nr,k=1) #indices mat. trig. sup., sans diagonale
    #Dthflt = Dth.take(idxtriu[0]).take(idxtriu[1], axis=1).flatten()
    #Dmesflt = Dmes.take(idxtriu[0]).take(idxtriu[1], axis=1).flatten()
    Dthflt = Dth[idxtriu[0], idxtriu[1]].flatten()
    Dmesflt = Dmes[idxtriu[0], idxtriu[1]].flatten()
    
    pl.figure()
    pl.plot(Dthflt, Dmesflt, '*')
    pl.plot(Dthflt, Dthflt, 'k')


def rotate2D(X, mic):
    """
    rotate2D(X, mic)
    
    Applique une rotation sur X telle que le micro mic est sur l'axe (O,x).
    """
    rmic = pl.norm(X[mic,:])
    Rot = np.array([
                    [X[mic,0]/rmic, -X[mic,1]/rmic],
                    [X[mic,1]/rmic, X[mic,0]/rmic]
                    ])
    return np.dot(X, Rot)

def c0corrector(X, Xth):
    """
    c0corrector(X, Xth)
    
    Corrige l'erreur de X du au choix a priori arbitraire de la vitesse du son.
    """
    def err_cel(c):
        return errXthXest(Xth, c*X)

    cest = opt.fmin(err_cel, [1.0])
    return cest*X, cest
    
def get_D(X):
    '''
    Retourne la matrice de distances de X.
    '''
    return squareform(pdist(X))

def rmsd(V, W):
    """ Calculate Root-mean-square deviation from two sets of vectors V and W.
    """
    D = len(V[0])
    N = len(V)
    rmsd = 0.0
    for v, w in zip(V, W):
        rmsd += sum([(v[i]-w[i])**2.0 for i in range(D)])
    return np.sqrt(rmsd/N)

def kabsch(P, Q, output=False):
    """ The Kabsch algorithm

    http://en.wikipedia.org/wiki/Kabsch_algorithm

    The algorithm starts with two sets of paired points P and Q.
    P and Q should already be centered on top of each other.

    Each vector set is represented as an NxD matrix, where D is the
    the dimension of the space.

    The algorithm works in three steps:
    - a translation of P and Q
    - the computation of a covariance matrix C
    - computation of the optimal rotation matrix U

    The optimal rotation matrix U is then used to
    rotate P unto Q so the RMSD can be caculated
    from a straight forward fashion.

    """

    # Computation of the covariance matrix
    C = np.dot(np.transpose(P), Q)

    # Computation of the optimal rotation matrix
    # This can be done using singular value decomposition (SVD)
    # Getting the sign of the det(V)*(W) to decide
    # whether we need to correct our rotation matrix to ensure a
    # right-handed coordinate system.
    # And finally calculating the optimal rotation matrix U
    # see http://en.wikipedia.org/wiki/Kabsch_algorithm
    V, S, W = np.linalg.svd(C)
    d = (np.linalg.det(V) * np.linalg.det(W)) < 0.0

    if d:
        S[-1] = -S[-1]
        V[:,-1] = -V[:,-1]

    # Create Rotation matrix U
    U = np.dot(V, W)

    # Rotate P
    P = np.dot(P, U)

    if output:
        return P, rmsd(P, Q)

    return rmsd(P, Q)
