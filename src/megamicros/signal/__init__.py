# megamicros.signal.py python software for data processing
#
# ® Copyright 2024-2025 Bimea
# Author: bruno.gas@bimea.io
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
This module provides a set of tools for signal processing and analysis.

Features:
    - Compute energy, wiener entropy, Q50 and perform signal segmentation 

Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""

import numpy as np
from scipy import signal

from ..exception import MuException
from ..log import log


def wiener_entropy( signal: np.ndarray, sampling_frequency: float, frame_duration: float, hop: int|None=None ):
    """ Compute Wiener entropy for a sound signal (Wiener entropy is a measure of the signal complexity)
    The entropy is computed on consecutiv frames of the signal using the following formula:
    Wiener = exp( sum( log( e^2 ) ) / N ) / sum( e^2 ) / N

    Parameters
    ----------
    signal: np.ndarray
        The sound signal to be processed
    sampling_frequency: float
        The sampling frequency of the sound signal
    frame_duration: float
        The duration in seconds of the sliding frame used for processing the Wiener entropy
    hop: int
        The number of samples between two consecutive frames default value is equal to the frame width (not implemented yet)
    
    Returns
    -------
    wiener: np.ndarray
        The Wiener entropy of the signal computed on a sliding window
    frame_width: int
        The width of the frame used for Wiener entropy computing
    """        

    # Check if the signal is a mono signal and transform it to mono if it is not
    if len( signal.shape ) > 1:
        if signal.shape[0] == 1 and signal.shape[1] > 1:
            signal = signal[0,:]
        elif signal.shape[1] == 1 and signal.shape[0] > 1:
            signal = signal[:,0]
        else:
            raise MuException( "The signal must be a mono signal" )

    # Hop is not implemented yet
    if hop is not None:
        raise MuException( "Hop is not implemented yet for Wiener entropy computing" )

    frame_width = int( frame_duration * sampling_frequency )
    if frame_width > len( signal ):
        raise MuException( "The frame width must be smaller than the signal length" )
    
    frames_number = int( len( signal ) // frame_width )
    lost_samples_number = len( signal ) % frame_width
    signal = signal[:len(signal)-lost_samples_number]
    signal = np.reshape( signal, (frames_number, frame_width) )
    spectrum = np.fft.rfft( signal, axis=1 )
    wiener = np.zeros( frames_number )
    for i in range( frames_number ):
        e_2 = np.abs( spectrum[i,:] )**2
        le = np.log( e_2 )
        wiener[i] = np.exp( np.sum( le )/frame_width ) / np.sum( e_2 ) / frame_width

    return wiener, frame_width



def energy( signal: np.ndarray, sampling_frequency: float, frame_duration: float, hop: int|None=None ):
    """ Compute energy on a sliding window for a sound signal 
    
    Parameters
    ----------
    signal: np.ndarray
        The sound signal to be processed
    sampling_frequency: int
        The sampling frequency of the sound signal
    frame_duration: float
        The duration in seconds of the sliding frame used for processing the energy
    hop: int
        The number of samples between two consecutive frames default value is equal to the frame width
    
    Returns
    -------
    energy: np.ndarray
        The energy of the signal computed on on a sliding window
    frame_width: int
        The width of the frame used for energy computing
    """

    # Check if the signal is a mono signal and transform it to mono if it is not
    if len( signal.shape ) > 1:
        if signal.shape[0] == 1 and signal.shape[1] > 1:
            signal = signal[0,:]
        elif signal.shape[1] == 1 and signal.shape[0] > 1:
            signal = signal[:,0]
        else:
            raise MuException( "The signal must be a mono signal" )

    frame_width = int( frame_duration * sampling_frequency )
    if frame_width > len( signal ):
        raise MuException( "The frame width must be smaller than the signal length" )

    # Adjust the hop size
    if hop is None:
        hop = frame_width

    # Init an array to store the energy of each frame
    energy = np.zeros((len(signal) - frame_width) // hop + 1)

    # Calculer l'énergie pour chaque fenêtre
    for i in range( 0, len( signal ) - frame_width, hop ):
        frame = signal[i:i+frame_width]
        energy[i // hop] = np.sum( frame**2 )

    return energy, frame_width




def q50( signal: np.ndarray, sampling_frequency: int, frame_duration: float=0.1 ):
    """ Compute Q50 indice (Spectral center of gravity in the upper half of the spectrum) for a sound signal 
    
    Parameters
    ----------
    signal: np.ndarray
        The sound signal to be processed
    sampling_frequency: int
        The sampling frequency of the sound signal
    frame_duration: float
        The duration in seconds of the sliding frame used for processing the Q50 indice. Default is 0.1s
        Note that some samples may be lost at the end of the signal if the frame width is not a divisor of the signal size.
    """

    if not isinstance( signal, np.ndarray ):
        raise MuException( "The signal must be a numpy array" )
    
    # Check if the signal is a mono signal and transform it to mono if it is not
    if len( signal.shape ) > 1:
        if signal.shape[0] == 1 and signal.shape[1] > 1:
            signal = signal[0,:]
        elif signal.shape[1] == 1 and signal.shape[0] > 1:
            signal = signal[:,0]
        else:
            raise MuException( "The signal must be a mono signal" )
    
    samples_number = np.size( signal )
    frame_width = int( frame_duration * sampling_frequency )
    frames_number = int( samples_number / frame_width )
    lost_samples_number = samples_number % frame_width
    signal = signal[:samples_number - lost_samples_number]
    signal = np.reshape( signal, (frames_number, frame_width) )
    spectrum = np.fft.rfft( signal, axis=1 )
    modspec2 = np.abs( spectrum )    
    modspec2 *= modspec2   

    n_freq = np.size( modspec2,1 )
    frequencies = np.array( [i for i in range( n_freq )] ) * sampling_frequency / n_freq / 2
    
    q50 = np.zeros( frames_number )
    for i in range( frames_number ):
        e = np.abs( spectrum[i,:] )
        e_2 = np.abs( e * e )
        ew = e_2 * frequencies
        q50[i] = np.sum( ew ) / np.sum( e_2 )

    return q50, frequencies

def segment( signal: np.ndarray, seg_threshold: float=50, seg_interval: float=10, frame_width: int|None=None, frame_overlap: int|None=None):
    """ Segment a positive defined signal (energy, Q50, etc.). Segmentation is performed using a threshold and a minimum interval.

    Parameters
    ----------
    q50: np.ndarray
        The signal to be segmented
    seg_threshold: float
        The threshold used for segmentation in percent of the max amplitude. Default is 50%
    seg_interval: float
        The minimum interval for a segment in percent of the length of the signal. Default is 10%
    frame_width: int
        The width of the frame used for anterior signal generation. Default is None
    frame_overlap: int
        The overlap of the frame used for anterior signal generation. Default is None

    Returns
    -------
    signal_segments: np.ndarray
        The segmented signal as a list of (begin, end) segments tuples
    signal_seg: np.ndarray
        The segmented signal as a binary [0,1] signal of same length as the input signal
    """

    if frame_width is not None or frame_overlap is not None:
        raise MuException( "frame_width and frame_overlap are not yet implemented" )
    
    # Check if the signal is a mono signal and transform it to mono if it is not
    if len( signal.shape ) > 1:
        if signal.shape[0] == 1 and signal.shape[1] > 1:
            signal = signal[0,:]
        elif signal.shape[1] == 1 and signal.shape[0] > 1:
            signal = signal[:,0]
        else:
            raise MuException( "The signal must be a mono signal" )
    
    samples_number = np.size( signal )
    signal_max = np.max( signal )
    actual_threshold = seg_threshold * signal_max / 100
    signal_seg = np.empty( samples_number )
    signal_seg.fill( 0 )

    kernel_size = int( seg_interval * samples_number // 100 )
    i = 0
    signal_segments = []
    while i < samples_number:
        if signal[i] >= actual_threshold:
            j = i
            while j < samples_number and signal[j] >= actual_threshold:
                # browse the signal while the threshold is reached
                j += 1  
            if j - i >= kernel_size:
                # segment found
                signal_seg[i:j] = 1
                signal_segments.append( (i,j) )
            else:
                # segment too short
                pass
            i = j
        else:
            i += 1

    return signal_segments, signal_seg