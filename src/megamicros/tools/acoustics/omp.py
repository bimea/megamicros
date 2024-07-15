# Megamicros_tools.acoustics.omp.py
#
# Copyright (c) 2024 Bimea
# Author: francois.ollivier@bimea.io
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

""" Orthogonal Matching Pursuit (OMP)

Orthogonal Matching Pursuit (OMP) is a greedy algorithm used for sparse signal approximation. 
It's often used in the field of signal processing and machine learning for tasks such as feature selection and sparse coding.

The algorithm works by iteratively selecting the dictionary elements (also known as "atoms") 
that are most correlated with the current residual (the difference between the original signal and the current approximation), 
and then updating the approximation and residual.

Here's a simplified description of the algorithm:
* Initialize the residual with the original signal and the approximation with zero.
* Find the dictionary atom that is most correlated with the current residual.
* Update the approximation by projecting the original signal onto the space spanned by the selected atoms.
* Update the residual by subtracting the updated approximation from the original signal.
* Repeat steps 2-4 until a stopping criterion is met (e.g., a maximum number of atoms have been selected, or the residual is below a certain threshold).

The "orthogonal" in OMP refers to the fact that the residual is kept orthogonal to the space spanned by the selected atoms, 
which leads to a more stable and accurate approximation compared to some other greedy algorithms.

L'algorithme OMP présente plusieurs avantages par rapport à d'autres méthodes de sélection de caractéristiques :

* Simplicité et efficacité : OMP est un algorithme "greedy" (glouton) qui sélectionne une à une les caractéristiques les plus corrélées avec le résidu courant.
Cela le rend relativement simple à comprendre et à implémenter, et efficace en termes de temps de calcul.
* Stabilité : L'OMP maintient le résidu orthogonal à l'espace engendré par les caractéristiques sélectionnées, 
ce qui conduit à une approximation plus stable et plus précise par rapport à certaines autres méthodes gloutonnes.
* Support pour la parcimonie : L'OMP est particulièrement adapté aux problèmes où la solution est parcimonieuse 
(c'est-à-dire qu'elle contient beaucoup de zéros). 
Il est capable de récupérer la solution exacte en présence de bruit, à condition que le signal soit suffisamment parcimonieux.
* Non-négativité : L'OMP peut être facilement adapté pour imposer une contrainte de non-négativité sur les coefficients, 
ce qui peut être utile dans certains contextes (par exemple, 
lorsque les caractéristiques représentent des quantités physiques qui ne peuvent pas être négatives).

Cependant, comme tout algorithme, l'OMP a aussi ses limites. 
Par exemple, il peut ne pas fonctionner aussi bien lorsque le signal n'est pas parcimonieux, 
ou lorsque les caractéristiques sont fortement corrélées entre elles.
Dans ces cas, il peut sélectionner une caractéristique au détriment d'une autre qui est presque identique
Pas de régularisation : Contrairement à d'autres méthodes comme Lasso ou Ridge, 
l'OMP ne dispose pas d'un mécanisme de régularisation pour contrôler la complexité du modèle. 
Cela peut conduire à un surapprentissage si le nombre de caractéristiques est très grand par rapport au nombre d'échantillons.
Choix du nombre de caractéristiques : L'OMP nécessite de spécifier le nombre de caractéristiques à sélectionner, 
ce qui peut être difficile à déterminer à l'avance. 
Certaines variantes de l'OMP permettent de déterminer ce nombre automatiquement, mais elles peuvent être plus complexes à mettre en œuvre.

Il est important de noter que le choix de l'algorithme de sélection de caractéristiques dépend du problème spécifique à résoudre, 
et qu'il n'y a pas d'algorithme qui soit le meilleur dans tous les cas.

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.bimea.io
"""

import numpy as np
from scipy.optimize import nnls
from megamicros.log import log
from megamicros.exception import MuException

class Result(object):
    """Result object for storing input and output data for omp.  When called from 
    `omp`, runtime parameters are passed as keyword arguments and stored in the 
    `params` dictionary.

    Attributes:
        X:  Predictor array after (optional) standardization.
        y:  Response array after (optional) standarization.
        ypred:  Predicted response.
        residual:  Residual vector.
        coef:  Solution coefficients.
        active:  Indices of the active (non-zero) coefficient set.
        err:  Relative error per iteration.
        params:  Dictionary of runtime parameters passed as keyword args.   
    """
    
    def __init__(self, **kwargs):
        
        # to be computed
        self.X = None
        self.y = None
        self.ypred = None
        self.residual = None
        self.coef = None
        self.active = None
        self.err = None
        
        # runtime parameters
        self.params = {}
        for key, val in kwargs.items():
            self.params[key] = val
            
    def update(self, coef, active, err, residual, ypred):
        """Update the solution attributes.
        """
        self.coef = coef
        self.active = active
        self.err = err
        self.residual = residual
        self.ypred = ypred


def omp( X, y, nonneg=True, ncoef=None, maxit=10, tol=1e-3, ztol=1e-12, verbose=False ):
    """Compute sparse orthogonal matching pursuit solution with unconstrained
    or non-negative coefficients.
    
    Parameters
    ----------
    X: dict
        Dictionary array of size n_samples x n_features. 
    y: np.array 
        Reponse array of size n_samples x 1.
    nonneg: boolean
        Enforce non-negative coefficients. Default is True.
    ncoef: int
        Max number of coefficients.  Set to n_features/2 by default.
    tol: float
        Convergence tolerance.  If relative error is less than tol * ||y||_2, exit.
    ztol: float
        Residual covariance threshold.  If all coefficients are less than ztol * ||y||_2, exit.
    verbose: Boolean
        print some info at each iteration.
        
    Returns
    -------
    result:  Result object.  
        See Result.__doc__ for more info.
    """
    
    def norm2(x):
        return np.linalg.norm(x) / np.sqrt(len(x))
    
    # initialize result object
    result = Result(nnoneg=nonneg, ncoef=ncoef, maxit=maxit, tol=tol, ztol=ztol)
    if verbose:
        print(result.params)
    
    # check types, try to make somewhat user friendly
    if type(X) is not np.ndarray:
        X = np.array(X)
    if type(y) is not np.ndarray:
        y = np.array(y)
        
    # check that n_samples match
    if X.shape[0] != len(y):
        raise MuException( f"OMP: X and y must have same number of rows (samples)" )
    
    # store arrays in result object    
    result.y = y
    result.X = X
    
    # for rest of call, want y to have ndim=1
    if np.ndim(y) > 1:
        y = np.reshape(y, (len(y),))
        
    # by default set max number of coef to half of total possible
    if ncoef is None:
        ncoef = int(X.shape[1]/2)
    
    # initialize things
    X_transpose = X.T                        # store for repeated use
    #active = np.array([], dtype=int)         # initialize list of active set
    active = []
    coef = np.zeros(X.shape[1], dtype=float) # solution vector
    residual = y                             # residual vector
    ypred = np.zeros(y.shape, dtype=float)
    ynorm = norm2(y)                         # store for computing relative err
    err = np.zeros(maxit, dtype=float)       # relative err vector
    
    # Check if response has zero norm, because then we're done. This can happen
    # in the corner case where the response is constant and you normalize it.
    if ynorm < tol:     # the same as ||residual|| < tol * ||residual||
        log.warning( 'OMP: Norm of the response is less than convergence tolerance.' )
        result.update(coef, active, err[0], residual, ypred)
        return result
    
    # convert tolerances to relative
    tol = tol * ynorm       # convergence tolerance
    ztol = ztol * ynorm     # threshold for residual covariance
    
    log.info(' .OMP: Iteration, relative error, number of non-zeros')
   
    # main iteration
    for it in range(maxit):
        
        # compute residual covariance vector and check threshold
        rcov = np.dot(X_transpose, residual)
        if nonneg:
            i = np.argmax(rcov)
            rc = rcov[i]
        else:
            i = np.argmax(np.abs(rcov))
            rc = np.abs(rcov[i])
        if rc < ztol:
            log.warning('OMP: All residual covariances are below threshold.')
            break
        
        # update active set
        if i not in active:
            #active = np.concatenate([active, [i]], axis=1)
            active.append(i)
            
        # solve for new coefficients on active set
        if nonneg:
            #coefi, _ = nnls(X[:, active], y)
            # ComplexWarning: Casting complex values to real discards the imaginary part -> explicit convertion to float64:
            coefi, _ = nnls(X[:, active].real, y.real)
        else:
            coefi, _, _, _ = np.linalg.lstsq(X[:, active], y)

        coef[active] = coefi   # update solution
        
        # update residual vector and error
        residual = y - np.dot(X[:,active], coefi)
        ypred = y - residual
        err[it] = norm2(residual) / ynorm  
        
        # print status
        log.info( f" > {it}, {err[it]}, {len(active)}" )
            
        # check stopping criteria
        if err[it] < tol:  # converged
            log.info(' .OMP: Converged.')
            break
        if len(active) >= ncoef:   # hit max coefficients
            log.info(' .OMP: Found solution with max number of coefficients.')
            break
        if it == maxit-1:  # max iterations
            log.info(' .OMP: Hit max iterations.')
    
    result.update(coef, active, err[:(it+1)], residual, ypred)
    return result

if __name__ == '__main__':
    pass
