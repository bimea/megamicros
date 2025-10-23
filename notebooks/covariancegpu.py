# -*- coding: utf-8 -*-

"""
Module contenant toutes les fonctions pour le calcul
de covariance et cohérence sur GPU.

Created on Wed May 7 14:27:01 2014

@author: charles
"""

from pycuda.compiler import SourceModule as _SourceModule
import pycuda.gpuarray as _gpuarray
import scikits.cuda.cufft as _cufft

import numpy as _np

##############################################################################
#kernels gpu pour la covariance/cohérence

def _Compil_Pw2cov(): 
    """
    Estimateur de matrice covariance: Pw2cov(Pw,R,ksel,Nr,NFFT,B)
    """
    modPw2cov = _SourceModule("""
#include <pycuda-complex.hpp>
#include <stdio.h>
    
__global__ void Pw2cov(pycuda::complex<float> *Pw, pycuda::complex<float> *R, int *ksel, int Nr, int NFFT, int B)
{//--------------------------------------------------------------------------------
int i =  blockIdx.x*blockDim.x + threadIdx.x ; //indice suivant ligne de R
int j =  blockIdx.y*blockDim.y + threadIdx.y ; //indice suivant col de R
int k =  blockIdx.z*blockDim.z + threadIdx.z ; //indice suivant freq bin

pycuda::complex<float> Rijk (0.0,0.0);
pycuda::complex<float> normalisation(1.0/B,0.0);

int Bsize = NFFT/2 +1; // fonction rfft sur NFFT points supprime la symétrie 

int idxi;
int idxj;

for(int b=0;b<B;b++)
    {
    idxi = (i*B+b)*Bsize + ksel[k];
    idxj = (j*B+b)*Bsize + ksel[k];
    Rijk += Pw[idxi] * conj(Pw[idxj]);
    }

Rijk *= normalisation;
R[k*Nr*Nr + i*Nr + j] = Rijk;
//printf("%d %f ",k, ksel[k]);
}
""")
    return modPw2cov.get_function("Pw2cov")

def _Compil_Pw2coh():
    """
    Estimateur de matrice cohérence: Pw2coh(Pw,R,ksel,Nr,NFFT,B)
    """
    modPw2coh = _SourceModule("""
#include <pycuda-complex.hpp>
#include <stdio.h>
    
__global__ void Pw2coh(pycuda::complex<float> *Pw, pycuda::complex<float> *R, int *ksel, int Nr, int NFFT, int B)
{//--------------------------------------------------------------------------------
int i =  blockIdx.x*blockDim.x + threadIdx.x ; //indice suivant ligne de R
int j =  blockIdx.y*blockDim.y + threadIdx.y ; //indice suivant col de R
int k =  blockIdx.z*blockDim.z + threadIdx.z ; //indice suivant freq bin

pycuda::complex<float> Rijk (0.0,0.0);
pycuda::complex<float> normalisation(1.0/B,0.0);

int Bsize = NFFT/2 +1; // fonction rfft sur NFFT points supprime la symétrie 

int idxi;
int idxj;

for(int b=0;b<B;b++)
    {
    idxi = (i*B+b)*Bsize + ksel[k];
    idxj = (j*B+b)*Bsize + ksel[k];
    Rijk += Pw[idxi] * conj(Pw[idxj]) / pycuda::complex<float>(abs(Pw[idxi])*abs(Pw[idxj]),0.0) ;
    }

Rijk *= normalisation;
R[k*Nr*Nr + i*Nr + j] = Rijk;
}
""")
    return modPw2coh.get_function("Pw2coh")


##############################################################################
#kernels gpu pour la covariance/coherence récursive
def _Compil_Pw2covRec(): 
    """
    Estimateur recursif de matrice covariance: Pw2cov(Pw,R,ksel,Nr,NFFT,B)
    """
    modPw2covRec=_SourceModule("""
#include <pycuda-complex.hpp>
    
__global__ void Pw2covRec(pycuda::complex<float> *Pw, pycuda::complex<float> *R, int *ksel, int Nr, int NFFT, int b)
{//--------------------------------------------------------------------------------
int i =  blockIdx.x*blockDim.x + threadIdx.x ; //indice suivant ligne de R
int j =  blockIdx.y*blockDim.y + threadIdx.y ; //indice suivant col de R
int k =  blockIdx.z*blockDim.z + threadIdx.z ; //indice suivant freq bin

pycuda::complex<float> Rijk (0.0,0.0);

int Bsize = NFFT/2 +1; // fonction rfft sur NFFT points supprime la symétrie 
int idxi = Bsize*i+ksel[k];
int idxj = Bsize*j+ksel[k];

Rijk = Pw[idxi] * conj(Pw[idxj]);

R[k*Nr*Nr + i*Nr + j] = (R[k*Nr*Nr + i*Nr + j]*pycuda::complex<float>(b-1,0.0) + Rijk)/pycuda::complex<float>(b,0.0);
}
""")
    return modPw2covRec.get_function("Pw2covRec")
    
def _Compil_Pw2covRecDouble(): 
    """
    Estimateur recursif de matrice covariance: Pw2cov(Pw,R,ksel,Nr,NFFT,B)
    """
    modPw2covRec=_SourceModule("""
#include <pycuda-complex.hpp>
    
__global__ void Pw2covRec(pycuda::complex<double> *Pw, pycuda::complex<double> *R, int *ksel, int Nr, int NFFT, int b)
{//--------------------------------------------------------------------------------
int i =  blockIdx.x*blockDim.x + threadIdx.x ; //indice suivant ligne de R
int j =  blockIdx.y*blockDim.y + threadIdx.y ; //indice suivant col de R
int k =  blockIdx.z*blockDim.z + threadIdx.z ; //indice suivant freq bin

pycuda::complex<double> Rijk (0.0,0.0);

int Bsize = NFFT/2 +1; // fonction rfft sur NFFT points supprime la symétrie 
int idxi = Bsize*i+ksel[k];
int idxj = Bsize*j+ksel[k];

Rijk = Pw[idxi] * conj(Pw[idxj]);

R[k*Nr*Nr + i*Nr + j] = (R[k*Nr*Nr + i*Nr + j]*pycuda::complex<double>(b-1,0.0) + Rijk)/pycuda::complex<double>(b,0.0);
}
""")
    return modPw2covRec.get_function("Pw2covRec")


def _Compil_Pw2cohRec(): 
    """
    Estimateur recursif de matrice coherence: Pw2coh(Pw,R,ksel,Nr,NFFT,B)
    """
    modPw2cohRec=_SourceModule("""
#include <pycuda-complex.hpp>
    
__global__ void Pw2cohRec(pycuda::complex<float> *Pw, pycuda::complex<float> *R, int *ksel, int Nr, int NFFT, int b)
{//--------------------------------------------------------------------------------
int i =  blockIdx.x*blockDim.x + threadIdx.x ; //indice suivant ligne de R
int j =  blockIdx.y*blockDim.y + threadIdx.y ; //indice suivant col de R
int k =  blockIdx.z*blockDim.z + threadIdx.z ; //indice suivant freq bin

pycuda::complex<float> Rijk (0.0,0.0);

int Bsize = NFFT/2 +1; // fonction rfft sur NFFT points supprime la symétrie 
int idxi = Bsize*i+ksel[k];
int idxj = Bsize*j+ksel[k];

Rijk = Pw[idxi] * conj(Pw[idxj]) / pycuda::complex<float>(abs(Pw[idxi])*abs(Pw[idxj]),0.0);

R[k*Nr*Nr + i*Nr + j] = (R[k*Nr*Nr + i*Nr + j]*pycuda::complex<float>(b-1,0.0) + Rijk)/pycuda::complex<float>(b,0.0);
}
""")
    return modPw2cohRec.get_function("Pw2cohRec")
    
def _Compil_Pw2cohRecDouble(): 
    """
    Estimateur recursif de matrice coherence: Pw2coh(Pw,R,ksel,Nr,NFFT,B)
    """
    modPw2cohRec=_SourceModule("""
#include <pycuda-complex.hpp>
    
__global__ void Pw2cohRec(pycuda::complex<double> *Pw, pycuda::complex<double> *R, int *ksel, int Nr, int NFFT, int b)
{//--------------------------------------------------------------------------------
int i =  blockIdx.x*blockDim.x + threadIdx.x ; //indice suivant ligne de R
int j =  blockIdx.y*blockDim.y + threadIdx.y ; //indice suivant col de R
int k =  blockIdx.z*blockDim.z + threadIdx.z ; //indice suivant freq bin

pycuda::complex<double> Rijk (0.0,0.0);

int Bsize = NFFT/2 +1; // fonction rfft sur NFFT points supprime la symétrie 
int idxi = Bsize*i+ksel[k];
int idxj = Bsize*j+ksel[k];

Rijk = Pw[idxi] * conj(Pw[idxj]) / pycuda::complex<double>(abs(Pw[idxi])*abs(Pw[idxj]),0.0);

R[k*Nr*Nr + i*Nr + j] = (R[k*Nr*Nr + i*Nr + j]*pycuda::complex<double>(b-1,0.0) + Rijk)/pycuda::complex<double>(b,0.0);
}
""")
    return modPw2cohRec.get_function("Pw2cohRec")

_Pw2cov = _Compil_Pw2cov()
_Pw2coh = _Compil_Pw2coh()
_Pw2cohRec = _Compil_Pw2cohRec()
_Pw2cohRecDouble = _Compil_Pw2cohRecDouble()
_Pw2covRec = _Compil_Pw2covRec()
_Pw2covRecDouble = _Compil_Pw2covRecDouble()

###################################################################
# Fonctions python à appeler pour le calcul d'une:
#
# a) Covariance non récursive (DD->RAM 1x, RAM->GPU 1x)
# b) Cohérence non récursive (DD->RAM 1x, RAM->GPU 1x)
# c) Covariance récursive (DD->RAM 1x, RAM->GPU itéré par bloc)
# d) Cohérence récursive (DD->RAM 1x, RAM->GPU itéré par bloc)

def covariance(P, kSel, Nr, NFFT, B):
    """
    Estimateur de la matrice de cohérence de Nr microphones, pour un set de bins fréquentiels choisi.

    Méthode: moyennage de B produits Pi*conj(Pj), avec Pi=rfft(pi) et Pj=rfft(pj) sur NFFT points.

    Attention mémoire: transfert de l'acquisition vers GPU en 1 fois! (voir coherenceRec() sinon)
    
    Entrées
    -------
    P: (Nr, Ns) array de float32
        Acquisition des pressions des Nr microphones, Ns échantillons.
    kSel: (M,) array d'int
        Indices des bins fréquentiels où la cohérence sera calculée.
        Fréquences correspondantes à celles de la rfft de P.
    Nr: int
        nombre de microphones.
    NFFT: int
        Nombre d'échantillon des blocs pour la fft.
    B: int
       Nombre total de blocs à moyenner.
    
    Sortie
    ------
    R: (M, Nr, Nr) array de complex64
        M matrices (Nr, Nr) de cohérence aux fréquences choisies.
    """
    plan = _cufft.cufftPlan1d(NFFT, _cufft.CUFFT_R2C, Nr*B)
    Pgpu = _gpuarray.zeros((Nr,NFFT*B), _np.float32)
    Pwgpu = _gpuarray.zeros((Nr,B*(NFFT//2+1)), _np.complex64)
    Rgpu = _gpuarray.zeros((kSel.size,Nr,Nr),_np.complex64)
    kSelGPU = _gpuarray.to_gpu(kSel)

    Pgpu.set(P[:,0:NFFT*B].copy())
    _cufft.cufftExecR2C(plan,Pgpu.ptr,Pwgpu.ptr)    
    _Pw2cov(Pwgpu, Rgpu, kSelGPU, _np.int32(Nr), _np.int32(NFFT), _np.int32(B),
           grid = (1,int(Nr),int(kSel.size)), block = (int(Nr),1,1)) #x,y,z des grid/bloc <-> i,j,k
    R = Rgpu.get()

    _cufft.cufftDestroy(plan)
    for arr in [Rgpu, Pwgpu, Pgpu, kSelGPU]:
        arr.gpudata.free()    
    return R

def coherence(P, kSel, Nr, NFFT, B):
    """
    Estimateur de la matrice de cohérence de Nr microphones, pour un set de bins fréquentiels choisi.

    Méthode: moyennage de B produits Pi*conj(Pj)/(abs(Pi)*abs(Pj)), avec Pi=rfft(pi) et Pj=rfft(pj) sur NFFT points.

    Attention mémoire: transfert de l'acquisition vers GPU en 1 fois! (voir coherenceRec() sinon)
    
    Entrées
    -------
    P: (Nr, Ns) array de float32
        Acquisition des pressions des Nr microphones, Ns échantillons.
    kSel: (M,) array d'int
        Indices des bins fréquentiels où la cohérence sera calculée.
        Fréquences correspondantes à celles de la rfft de P.
    Nr: int
        nombre de microphones.
    NFFT: int
        Nombre d'échantillon des blocs pour la fft.
    B: int
       Nombre total de blocs à moyenner.
    
    Sortie
    ------
    R: (M, Nr, Nr) array de complex64
        M matrices (Nr, Nr) de cohérence aux fréquences choisies.
    """
    plan = _cufft.cufftPlan1d(NFFT, _cufft.CUFFT_R2C, Nr*B)
    Pgpu = _gpuarray.zeros((Nr,NFFT*B), _np.float32)
    Pwgpu = _gpuarray.zeros((Nr,B*(NFFT//2+1)), _np.complex64)
    Rgpu = _gpuarray.zeros((kSel.size,Nr,Nr),_np.complex64)
    kSelGPU = _gpuarray.to_gpu(kSel)

    Pgpu.set(P[:,0:NFFT*B].copy())
    _cufft.cufftExecR2C(plan,Pgpu.ptr,Pwgpu.ptr)
    _Pw2coh(Pwgpu, Rgpu, kSelGPU, _np.int32(Nr), _np.int32(NFFT), _np.int32(B),
           grid = (1,int(Nr),int(kSel.size)), block = (int(Nr),1,1)) #x,y,z des grid/bloc <-> i,j,k
    R = Rgpu.get()
    
    _cufft.cufftDestroy(plan)
    for arr in [Rgpu, Pwgpu, Pgpu, kSelGPU]:
        arr.gpudata.free()
    return R


def covarianceRec(P, kSel, Nr, NFFT, B): 
    """
    Estimateur de la matrice de covariance de Nr microphones, pour un set de bins fréquentiels choisi.

    Méthode: moyennage de B produits Pi*conj(Pj), avec Pi=rfft(pi) et Pj=rfft(pj) sur NFFT points.

    Transfert de l'acquisition vers GPU en B fois, mais HD->RAM  en 1 fois!
    
    Entrées
    -------
    P: (Nr, Ns) array de float32
        Acquisition des pressions des Nr microphones, Ns échantillons.
    kSel: (M,) array d'int
        Indices des bins fréquentiels où la cohérence sera calculée.
        Fréquences correspondantes à celles de la rfft de P.
    Nr: int
        nombre de microphones.
    NFFT: int
        Nombre d'échantillon des blocs pour la fft.
    B: int
       Nombre total de blocs à moyenner.
    
    Sortie
    ------
    R: (M, Nr, Nr) array de complex64
        M matrices de cohérence aux fréquences choisies.
    """    
    plan = _cufft.cufftPlan1d(NFFT, _cufft.CUFFT_R2C, Nr)
    Pgpu = _gpuarray.zeros((Nr,NFFT), _np.float32)
    Pwgpu = _gpuarray.zeros((Nr,(NFFT//2+1)), _np.complex64)
    Rgpu = _gpuarray.zeros((kSel.size,Nr,Nr),_np.complex64)
    kSelGPU = _gpuarray.to_gpu(kSel)
    
    for b in range(1,B+1):
        Pbuf = P[:,(b-1)*NFFT:b*NFFT].copy()
        Pgpu.set(Pbuf)
        _cufft.cufftExecR2C(plan,Pgpu.ptr,Pwgpu.ptr)
        _Pw2covRec(Pwgpu, Rgpu, kSelGPU, _np.int32(Nr), _np.int32(NFFT), _np.int32(b),
           grid = (1,int(Nr),int(kSel.size)), block = (int(Nr),1,1)) #x,y,z des grid/bloc <-> i,j,k
    
    Rrec = Rgpu.get()

    for arr in [Rgpu, Pwgpu, Pgpu, kSelGPU]:
        arr.gpudata.free()
    return Rrec
    
def covarianceRecdouble(P, kSel, Nr, NFFT, B): 
    """
    Estimateur de la matrice de covariance de Nr microphones, pour un set de bins fréquentiels choisi.
    
    !Double Précision!

    Méthode: moyennage de B produits Pi*conj(Pj), avec Pi=rfft(pi) et Pj=rfft(pj) sur NFFT points.

    Transfert de l'acquisition vers GPU en B fois, mais HD->RAM  en 1 fois!
    
    Entrées
    -------
    P: (Nr, Ns) array de float64
        Acquisition des pressions des Nr microphones, Ns échantillons.
    kSel: (M,) array d'int
        Indices des bins fréquentiels où la cohérence sera calculée.
        Fréquences correspondantes à celles de la rfft de P.
    Nr: int
        nombre de microphones.
    NFFT: int
        Nombre d'échantillon des blocs pour la fft.
    B: int
       Nombre total de blocs à moyenner.
    
    Sortie
    ------
    R: (M, Nr, Nr) array de complex128
        M matrices de cohérence aux fréquences choisies.
    """    
    plan = _cufft.cufftPlan1d(NFFT, _cufft.CUFFT_D2Z, Nr)
    Pgpu = _gpuarray.zeros((Nr,NFFT), _np.float64)
    Pwgpu = _gpuarray.zeros((Nr,(NFFT//2+1)), _np.complex128)
    Rgpu = _gpuarray.zeros((kSel.size,Nr,Nr),_np.complex128)
    kSelGPU = _gpuarray.to_gpu(kSel)
    
    for b in range(1,B+1):
        Pbuf = P[:,(b-1)*NFFT:b*NFFT].astype(_np.float64).copy()
        Pgpu.set(Pbuf)
        _cufft.cufftExecD2Z(plan,Pgpu.ptr,Pwgpu.ptr)
        _Pw2covRecDouble(Pwgpu, Rgpu, kSelGPU, _np.int32(Nr), _np.int32(NFFT), _np.int32(b),
           grid = (1,int(Nr),int(kSel.size)), block = (int(Nr),1,1)) #x,y,z des grid/bloc <-> i,j,k
    
    Rrec = Rgpu.get()

    for arr in [Rgpu, Pwgpu, Pgpu, kSelGPU]:
        arr.gpudata.free()
    return Rrec

def coherenceRec(P, kSel, Nr, NFFT, B):
    """
    Estimateur de la matrice de cohérence de Nr microphones, pour un set de bins fréquentiels choisi.

    Méthode: moyennage de B produits Pi*conj(Pj)/(abs(Pi)*abs(Pj)), avec Pi=rfft(pi) et Pj=rfft(pj) sur NFFT points.

    Transfert de l'acquisition vers GPU en B fois, mais HD->RAM  en 1 fois!
    
    Entrées
    -------
    P: (Nr, Ns) array de float32
        Acquisition des pressions des Nr microphones, Ns échantillons.
    kSel: (M,) array d'int
        Indices des bins fréquentiels où la cohérence sera calculée.
        Fréquences correspondantes à celles de la rfft de P.
    Nr: int
        nombre de microphones.
    NFFT: int
        Nombre d'échantillon des blocs pour la fft.
    B: int
       Nombre total de blocs à moyenner.
    
    Sortie  
    ------
    R: (M, Nr, Nr) array de complex64
        M matrices de cohérence aux fréquences choisies.
    """
    plan = _cufft.cufftPlan1d(NFFT, _cufft.CUFFT_R2C, Nr)
    Pgpu = _gpuarray.zeros((Nr,NFFT), _np.float32)
    Pwgpu = _gpuarray.zeros((Nr,(NFFT//2+1)), _np.complex64)
    Rgpu = _gpuarray.zeros((kSel.size,Nr,Nr),_np.complex64)
    kSelGPU = _gpuarray.to_gpu(kSel)
    
    for b in range(1,B+1):
        Pbuf = P[:,(b-1)*NFFT:b*NFFT].copy()
        Pgpu.set(Pbuf)
        _cufft.cufftExecR2C(plan,Pgpu.ptr,Pwgpu.ptr)
        _Pw2cohRec(Pwgpu, Rgpu, kSelGPU, _np.int32(Nr), _np.int32(NFFT), _np.int32(b),
           grid = (1,int(Nr),int(kSel.size)), block = (int(Nr),1,1)) #x,y,z des grid/bloc <-> i,j,k
    
    Rrec = Rgpu.get()
    
    _cufft.cufftDestroy(plan)
    for arr in [Rgpu, Pwgpu, Pgpu, kSelGPU]:
        arr.gpudata.free()
    return Rrec


def coherenceRecdouble(P, kSel, Nr, NFFT, B):
    """
    Estimateur de la matrice de cohérence de Nr microphones, pour un set de bins fréquentiels choisi.
    
    !Double Précision!
    
    Méthode: moyennage de B produits Pi*conj(Pj)/(abs(Pi)*abs(Pj)), avec Pi=rfft(pi) et Pj=rfft(pj) sur NFFT points.

    Transfert de l'acquisition vers GPU en B fois, mais HD->RAM  en 1 fois!
    
    Entrées
    -------
    P: (Nr, Ns) array de float64
        Acquisition des pressions des Nr microphones, Ns échantillons.
    kSel: (M,) array d'int
        Indices des bins fréquentiels où la cohérence sera calculée.
        Fréquences correspondantes à celles de la rfft de P.
    Nr: int
        nombre de microphones.
    NFFT: int
        Nombre d'échantillon des blocs pour la fft.
    B: int
       Nombre total de blocs à moyenner.
    
    Sortie
    ------
    R: (M, Nr, Nr) array de complex128
        M matrices de cohérence aux fréquences choisies.
    """
    plan = _cufft.cufftPlan1d(NFFT, _cufft.CUFFT_D2Z, Nr)
    Pgpu = _gpuarray.zeros((Nr,NFFT), _np.float64)
    Pwgpu = _gpuarray.zeros((Nr,(NFFT//2+1)), _np.complex128)
    Rgpu = _gpuarray.zeros((kSel.size,Nr,Nr),_np.complex128)
    kSelGPU = _gpuarray.to_gpu(kSel)
    
    for b in range(1,B+1):
        Pbuf = P[:,(b-1)*NFFT:b*NFFT].astype(_np.float64).copy()
        Pgpu.set(Pbuf)
        _cufft.cufftExecD2Z(plan,Pgpu.ptr,Pwgpu.ptr)
        _Pw2cohRecDouble(Pwgpu, Rgpu, kSelGPU, _np.int32(Nr), _np.int32(NFFT), _np.int32(b),
           grid = (1,int(Nr),int(kSel.size)), block = (int(Nr),1,1)) #x,y,z des grid/bloc <-> i,j,k
    
    Rrec = Rgpu.get()
    
    _cufft.cufftDestroy(plan)
    for arr in [Rgpu, Pwgpu, Pgpu, kSelGPU]:
        arr.gpudata.free()
    return Rrec
