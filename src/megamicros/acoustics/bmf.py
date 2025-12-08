# megamicros.acoustics.bmf.py
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
Define beamformer classes for beamforming usages

Features:
    - Abstract base class for beamformers
    - Frequency Domain Delay and Sum Beamformer Algorithm (BeamformerFDAS)
    - Several methods to compute the BMF:
        * `type='full'`: beamforming is computed over all the frequencies
        * `type='max'`: beamforming is only performed on the frequency givng the maximum energy (energy is computed on the first MEMs)
        * `type='mean'`: the power spectrum along MEMs 0 is viewed as a probability density which is approximated by a gaussian distribution. Beamforming is computed on the mean frequency of the gaussian distribution.
        * `type='gauss'`: the power spectrum along MEMs 0 is viewed as a probability density which is approximated by a gaussian distribution. Beamforming is computed on a range of frequencies around the mean frequency of the gaussian distribution with standard deviation as the width of the range.
        * `type='omp'`: find the location that best matches the phase distribution at the frequency for which energy is max using OMP algorithm
        
Examples:
    Basic usage::

        Comming soon...

    Advanced usage::

        See the Notebooks for advanced usage examples.

Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""

import numpy as np

from ..exception import MuException
from ..log import log
from ..acoustics.omp import omp, Result


SOUND_SPEED = 340.29

class MuBmfException( MuException ):
    """ Exception for beamformers """
    pass


class Beamformer:
    """ Abstract base class for beamformers """

    __mems_position: np.ndarray                         # 3D MEMs absolute positions in meters
    __locations: np.ndarray                             # 3D absolute positions of locations in the space where the beamforming is computed
    __sampling_frequency: float                         # Input sampling frequency
    __frame_length: int                                 # Input frame length in samples

    @property
    def mems_position( self ) -> np.ndarray:
        """ Get 3D absolute MEMS positions """

        return self.__mems_position

    @property
    def locations( self ) -> np.ndarray:
        """ Get 3D absolute location's positions """
        
        return self.__locations

    @property
    def sampling_frequency( self ) -> float:
        """ Sampling frequency """
        
        return self.__sampling_frequency
    
    @property
    def frame_length( self ) -> int:
        """ Sampling frequency """
        
        return self.__frame_length
    
    @property
    def mems_number( self ) -> int:
        """ MEMs number according the mems_position array """
        
        return np.shape( self.__mems_position )[0]
    
    @property
    def locations_number( self ) -> int:
        """ Locations number according the locations array """
        
        return np.shape( self.__locations )[0]
    

    def setMemsPosition( self, mems_position: np.ndarray|list|tuple ) -> None:
        """ Set the 3D absolute MEMs positions """

        if type( mems_position is list or type( mems_position is tuple ) ):
            mems_position = np.array( mems_position )

        if len( mems_position.shape ) != 2:
            raise MuException( f"Cannot set MEMs positions: MEMs positions must be a 2D array (MEMs_number x 3) but found {mems_position.shape}" )
        
        if mems_position.shape[1] != 3:
            raise MuException( f"Cannot set MEMs positions: MEMs positions must be a 3D array (MEMs_number x 3) but found {mems_position.shape}" )
        
        log.info( f" .Set beamformer on a {np.shape( mems_position )[0]} MEMs antenna" )
        self.__mems_position = mems_position


    def setLocations( self, locations: np.ndarray|list|tuple ) -> None:
        """ Set the space locations where to compute the BMF """

        if type( locations is list or type( locations is tuple ) ):
            locations = np.array( locations )

        if len( locations.shape ) != 2:
            raise MuException( f"Cannot set space locations: space locations must be a 2D array (locations_number x 3) but found {locations.shape}" )
        
        if locations.shape[1] != 3:
            raise MuException( f"Cannot set space locations: space locations must be a 3D array (MEMs_number x 3) but found {locations.shape}" )
        
        log.info( f" .Set {np.shape( locations )[0]} beamforming locations" )
        self.__locations = locations


    def setSamplingFrequency( self, sampling_frequency: float ) -> None :
        """ Set the sampling frequency of input signals """

        log.info( f" .Set beamformer sampling frequency to {sampling_frequency} Hz" )
        self.__sampling_frequency = sampling_frequency


    def setFrameLength( self, frame_length: float ) -> None :
        """ Set the input data buffer length in samples number """

        log.info( f" .Set beamformer frame length to {frame_length} Samples" )
        self.__frame_length = frame_length


    def __init__( self, mems_position: np.ndarray, locations: np.ndarray, sampling_frequency: float, frame_length: int ):
        """ Create a new beamformer instance 
        
        Parameters
        ----------
        mems_positions: np.ndarray
            The MEMs positions as a 2D array (MEMs_number x 3)
        locations: np.ndarray
            The space locations where to compute the BMF
        sampling_frequency: float
            The sampling frequency of input signals
        frame_length: int
            The frame length in samples number
        """

        self.setMemsPosition( mems_position )
        self.setSamplingFrequency( sampling_frequency )
        self.setLocations( locations )
        self.setFrameLength( frame_length )


class BeamformerFDAS( Beamformer ):
    """ Frequency Domain Delay and Sum Beamformer Algorithm """

    __f_axis: np.ndarray                        # Frequency axis in Hertz
    __fft_low_cut_off: float                    # FFT low cut off frequency
    __fft_high_cut_off: float                   # FFT high cut off frequency
    __fft_window_size: int                      # FFT window size in samples number

    __mems_number: int                          # MEMs number according the mems_position array
    __band_width: tuple = [0, 1]                # Normalized frequencies bandwidth
    __fft_low_cut_off_index: int                # Bandwidth start frequency range idex
    __fft_high_cut_off_index: int               # Bandwidth end frequency range index
    __band_width_length: int                    # Bandwidth length in samples number

    __D: np.ndarray                             # Inter mems/locations distance matrix
    __H: np.ndarray                             # beamforming matrix
    __BFE: np.ndarray                           # Beamforming energy
    __BFSpec: np.ndarray                        # Complex spectrum computed on all beams (locations_number x frequencies_number)
    __FFT: np.ndarray                           # Complex spectrum computed on all channels (channels_number x frequencies_number)
    
    @property
    def BFE( self ) -> np.ndarray:
        """ Beamforming energy array """

        return self.__BFE
    
    @property
    def D( self ) -> np.ndarray:
        """ Distances matrix """

        return self.__D

    @property
    def H( self ) -> np.ndarray:
        """ Beamforming matrix """

        return self.__H
    
    @property
    def SV( self, freq, pos ) -> np.ndarray:
        """ Steering vector for a given position and frequency """

        return self.__H[freq, pos, :]

    @property
    def FFT( self ) -> np.ndarray:
        """ FFT matrix """

        return self.__FFT

    def getBeamformingEnergy( self ) -> np.ndarray:
        """ Get the beamforming energy array """

        return self.__BFE

    def getFrequenciesAxis( self ) -> np.ndarray:
        """ Get the frequencies axis """

        return self.__f_axis

    def setFFtWindowSize( self, fft_window_size):
        """ Set the FFT window size in samples number 
        
        Note that it is not required that the FFT window size is the same as frame length. But only same size is allowed for now
        """
        if fft_window_size != self.frame_length:
            raise MuBmfException( f"Cannot set FFT window size to {fft_window_size} samples. Should be same as frame length ({self.frame_length} samples)" )

        log.info( f" .Set beamformer FFT window size to {fft_window_size} samples" )
        self.__fft_window_size = fft_window_size


    def __init__( self, mems_position: np.ndarray, locations: np.ndarray, sampling_frequency: float, frame_length: int, bandwidth: tuple|None=None ):
        """ Create a new Frequency Domain Adaptive Beamformer by delay and sum method instance 
        Parameters
        ----------
        mems_positions: np.ndarray
            The MEMs positions as an array of 3D array positions (MEMs number x 3)
        locations: np.ndarray
            The space locations where to compute the BMF as an array of 3D array positions (locations number x 3)
        sampling_frequency: float
            The sampling frequency of input signals
        frame_length: int
            The frame length in samples number
        bandwidth: tuple, optional
            The normalized frequencies bandwidth. Default is [0, 1] which means all frequencies from 0 to Fe/2
        """
        
        super().__init__( mems_position, locations, sampling_frequency, frame_length )

        locations_number = np.shape( self.locations )[0]
        self.setFFtWindowSize( self.frame_length )

        # time axis in seconds
        t = np.arange( self.__fft_window_size )/self.sampling_frequency

        # frequency axis in Hz
        self.__f_axis = np.fft.rfftfreq( self.__fft_window_size, 1/self.sampling_frequency )

        # frequencies number
        freq_number = self.__f_axis.size

        # frequency step
        frequency_step = self.sampling_frequency / freq_number / 2

        # bandwidth range
        if bandwidth is not None:
            self.__band_width = bandwidth
        else:
            self.__band_width = [0, 1]
        
        self.__fft_low_cut_off_index = int( self.sampling_frequency * self.__band_width[0] / frequency_step / 2 )
        self.__fft_high_cut_off_index = int( self.sampling_frequency * self.__band_width[1] / frequency_step / 2 ) - 1
        self.__band_width_length = self.__fft_high_cut_off_index - self.__fft_low_cut_off_index + 1
        self.__fft_low_cut_off = self.__fft_low_cut_off_index * frequency_step
        self.__fft_high_cut_off = (self.__fft_high_cut_off_index+1) * frequency_step

        # print info
        log.info( f" .BeamformerFDAS Initilization:" )
        log.info( f"  > Found antenna with {self.mems_number} MEMs microphones" )
        log.info( f"  > FFT window size is {self.__fft_window_size} samples" )
        log.info( f"  > Time range: [0, {t[-1]}] s" )
        log.info( f"  > Sampling frequency: {self.sampling_frequency} Hz" )
        log.info( f"  > Frequency range: [0, { self.__f_axis[-1]}] Hz ({freq_number} beams)" )
        log.info( f"  > frequency step: {frequency_step:.2f} Hz" )
        log.info( f"  > frequency bandwidth: [{self.__fft_low_cut_off:.2f}, {self.__fft_high_cut_off:.2f}] Hz" )
        log.info( f"  > frequency bandwidth indexes: [{self.__fft_low_cut_off_index}, {self.__fft_high_cut_off_index}] ( {self.__band_width_length} spectral ray)" )

        # Init distance matrix
        log.info( f" .Build distances matrix D ({locations_number} x {self.mems_number})" ) 
        self.__D = np.ndarray( (locations_number, self.mems_number), dtype=float )
        for s in range( locations_number ):
            for m in range( self.mems_number ):
                self.__D[s, m] = np.linalg.norm( np.array( self.mems_position[m] ) - self.locations[s] )

        # Allocate and build the H complex transfer function matrix (preformed channels)
        log.info( f" .Build preformed channels matrix H ({freq_number} x {locations_number} x {self.mems_number})" ) 
        self.__H = np.outer(  self.__f_axis, self.__D ).reshape( freq_number, locations_number, self.mems_number )/SOUND_SPEED
        self.__H = np.exp( 1j*2*np.pi*self.__H )

        self.__FFT = None


    def compute( self, signal: np.ndarray, type='full' ) -> np.ndarray:
        """ Process beamforming on input signals

        If the signal length is smaller than the `__fft_window_size` parameter, the input is zero padded.
        If it is larger, the input signal is cropped.
        
        There are several methods to compute the BMF:
        * `type='full'`: beamforming is computed over all the frequencies
        * `type='max'`: beamforming is only performed on the frequency givng the maximum energy (energy is computed on the first MEMs)
        * `type='mean'`: the power spectrum along MEMs 0 is viewed as a probability density which is approximated by a gaussian distribution. Beamforming is computed on the mean frequency of the gaussian distribution.
        * `type='gauss'`: the power spectrum along MEMs 0 is viewed as a probability density which is approximated by a gaussian distribution. Beamforming is computed on a range of frequencies around the mean frequency of the gaussian distribution with standard deviation as the width of the range.
        * `type='omp'`: find the location that best matches the phase distribution at the frequency for which energy is max using OMP algorithm
        
        Parameters
        ----------
        signal: np.ndarray
            the MEMs signal line wise (samples_number X mems_number)

        Return
        ------
        BFE: np.ndarray
            The beamformed energy channels (location_number x 1)
        """
        signal_length, mems_number = signal.shape
        # Control input size
        if signal_length > self.__fft_window_size:
            log.warning( f" .bmf > Input signal is longer than FFT width: it will be truncated" )
            self._in = signal[:self.__fft_window_size,:]
        elif signal_length < self.__fft_window_size:
            log.warning( f" .bmf > Input signal is shorter than FFT width: it will be zero-padded" )
            self._in = np.pad( signal, ( ( 0,self.__fft_window_size-signal_length), (0,0) ) )

        # Process beamforming on input signal involving all frequencies
        if type == 'full':
            self.__FFT = np.fft.rfft( signal, n=self.__fft_window_size, axis=0 )
            # SpecH = self.__FFT[:, None, :] * self.__H
            # BFSpec = np.sum( SpecH, -1 ) / self.mems_number
            # self.__BFE = np.sum( ( np.abs( BFSpec )**2 )[self.__fft_low_cut_off_index:self.__fft_high_cut_off_index+1,:], 0 ) / self.__band_width_length

            SpecH = self.__FFT[self.__fft_low_cut_off_index:self.__fft_high_cut_off_index, None, :] * self.__H[self.__fft_low_cut_off_index:self.__fft_high_cut_off_index,:,:]
            BFSpec = np.sum( SpecH, -1 ) / self.mems_number
            # self.__BFE = np.sum( np.abs( BFSpec )**2, 0 ) / self.__band_width_length
            self.__BFE = np.sum( np.abs( BFSpec ), 0 ) / self.__band_width_length
            self.__BFE = self.__BFE**2
            # Compute power in db:
            self.__BFE = 10 * np.log(self.__BFE)

            return self.__BFE, None, None

        # compute beamforming on frequency with max energy
        elif type == "max":
            # compute spectrum on all channels            
            self.__FFT = np.fft.rfft( signal, n=self.__fft_window_size, axis=0 )

            # find the max energy on first MEMs microphone
            #freq_max_index = np.argmax( np.abs( Spec[:,0] )**2 )
            freq_max_index = np.argmax( np.mean( np.abs( self.__FFT ), axis=1 ) )

            # compute bmf on the selected frequency
            SpecH = self.__FFT[freq_max_index, None, :] * self.__H[freq_max_index,:,:]
            BFSpec = np.sum( SpecH, -1 ) / self.mems_number

            self.__BFE = np.abs( BFSpec )**2 / BFSpec.size
            selected_frequency = self.__f_axis[freq_max_index]
            band_width = None
            return self.__BFE, selected_frequency, band_width

        # compute beamforming on the mean energy frequency
        elif type == "mean":
            # compute spectrum on all channels            
            self.__FFT = np.fft.rfft( signal, n=self.__fft_window_size, axis=0 )

            # find the mean energy frequency on channel 0
            Spec0 = np.abs( self.__FFT[:,0] )**2
            Spec0_density = Spec0 / np.sum( Spec0 )
            freq_mean = np.sum(  self.__f_axis * Spec0_density )

            # find the nearest frequency in the FFT axis
            freq_mean_index = np.searchsorted( self.__f_axis, freq_mean )

            # Get the nearest frequency index
            if freq_mean_index > 0:
                if np.abs(self.__f_axis[freq_mean_index-1] - freq_mean) < np.abs(self.__f_axis[freq_mean_index] - freq_mean):
                    freq_mean_index = freq_mean_index - 1
            
            # compute bmf on the selected frequency
            SpecH = self.__FFT[freq_mean_index, None, :] * self.__H[freq_mean_index,:,:]
            BFSpec = np.sum( SpecH, -1 ) / self.mems_number
            self.__BFE = np.abs( BFSpec )**2 / BFSpec.size
            selected_frequency = self.__f_axis[freq_mean_index]
            band_width = None


        # compute beamforming on frequencies around the mean energy frequency bounded by standard deviation
        elif type == "gauss":
            # compute spectrum on all channels            
            self.__FFT = np.fft.rfft( signal, n=self.__fft_window_size, axis=0 )

            # find the mean energy frequency on channel 0
            Spec0 = np.abs( self.__FFT[:,0] )**2
            Spec0_density = Spec0 / np.sum( Spec0 )
            freq_mean = np.sum(  self.__f_axis * Spec0_density )
            std_dev = np.sqrt( np.sum( (self.__f_axis - freq_mean)**2 * Spec0_density ) ) / 2

            # find the nearest frequency in the FFT axis
            freq_mean_index = np.searchsorted( self.__f_axis, freq_mean )

            # Get the nearest frequency index
            if freq_mean_index > 0:
                if np.abs(self.__f_axis[freq_mean_index-1] - freq_mean) < np.abs(self.__f_axis[freq_mean_index] - freq_mean):
                    freq_mean_index = freq_mean_index - 1

            # Find bandwith correponding to standard deviation
            Df = self.__f_axis[1] - self.__f_axis[0]
            std_dev_nindex = int( std_dev / Df )

            freq_min_index = max( freq_mean_index - std_dev_nindex, 0 )
            freq_max_index = min( freq_mean_index + std_dev_nindex, self.__f_axis.size )
            
            # compute bmf on the selected frequency
            SpecH = self.__FFT[freq_min_index:freq_max_index, None, :] * self.__H[freq_min_index:freq_max_index,:,:]
            BFSpec = np.sum( SpecH, -1 ) / self.mems_number
            self.__BFE = np.sum( np.abs( BFSpec )**2, 0 ) / BFSpec.size
            selected_frequency = self.__f_axis[freq_mean_index]
            band_width = std_dev


        # Find the location that best matches the phase distribution at the frequency for which energy is max
        elif type == "omp":
            # compute spectrum on all channels            
            self.__FFT = np.fft.rfft( signal, n=self.__fft_window_size, axis=0 )

            # init result vector
            omp_fo = np.zeros( self.locations_number )

            # frequency index carrying max energy
            freq_max_index = np.argmax( np.mean( np.abs( self.__FFT ), axis=1 ) )

            # Set dictionnary as the set of all phases complex multiplicators at the i_f0 frequency 
            Dico = self.__H[freq_max_index,:,:].T

            # Compute the first decomposition coef given by matching pursuit 
            result: Result = omp( Dico, self.__FFT[freq_max_index,:], maxit=1, verbose=False )

            # Get coef in the location vector (that could be reshaped as (nx, ny))  
            omp_fo = result.coef + 1e-12
            self.__BFE = omp_fo

            selected_frequency = self.__f_axis[freq_max_index]
            band_width = None


        return self.__BFE, selected_frequency, band_width


    def plotBfe( self, room_width: float, room_depth: float, x_npos: float, y_npos: float, position=None, prediction=None ):
        """ Plot the BFE in a room and highlight the max value and the source position"""

        bfe_room = np.reshape( self.__BFE, ( x_npos, y_npos ) )

        fig, ax = plt.subplots()
        img = ax.imshow( bfe_room, origin='lower' )
        if prediction is not None:
            ax.set_title( f"BFE - max found at ({prediction[0]:.2f},{prediction[1]:.2f}) meters" )

        xticks = np.linspace( 0, x_npos-1, 10 )
        xticks_number = len( xticks )
        yticks = np.linspace( 0, y_npos-1, 10 )
        yticks_number = len( yticks )
        ax.set_xticks( xticks, labels=np.array( [i for i in range( xticks_number )] )*room_width//(xticks_number-1) )
        ax.set_yticks( yticks, labels=np.array( [i for i in range( yticks_number )] )*room_depth//(yticks_number-1) )

        if position is not None:
            ax.scatter( position[0]*x_npos/room_width, position[1]*y_npos/room_depth, color='green' )

        if prediction is not None:
            ax.scatter( prediction[0]*x_npos/room_width, prediction[1]*y_npos/room_depth, color='orange' )

        fig.colorbar( img, ax=ax, label='Interactive colorbar' )

        return ax