# megamicros.muh5.py H5 file handler for MegaMicros libraries
#
# Copyright (c) 2023 Sorbonne Université
# Author: bruno.gas@sorbonne-universite.fr
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Megamicros documentation is available on https://readthedoc.bimea.io
"""

import numpy as np
import h5py

from .log import log, logging
from .core.mu import MU_MEMS_SENSIBILITY

class MuH5:
    
    @property
    def sampling_frequency( self ):
        return self.__sampling_frequency

    @property
    def mems_number( self ):
        return self.__mems_number
    
    @property
    def available_mems( self ):
        return self.__available_mems

    @property
    def channels_number( self ):
        return self.__channels_number

    @property
    def duration( self ):
        return self.__duration

    @property
    def status( self ) -> bool:
        return self.__status
    
    @property
    def samples_number( self ):
        return self.__samples_number


    def __init__( self, filename:str ):

        """ open h5 file and get informations from """
        self.__filename = filename
        with h5py.File( filename, 'r' ) as f:

            """ Control whether H5 file is a MuH5 file """
            if not f['muh5']:
                raise Exception( f"{filename} seems not to be a MuH5 file: unrecognized format" )

            """ get fil informations """
            group = f['muh5']
            self.__info = dict( zip( group.attrs.keys(), group.attrs.values() ) )
            self.__sampling_frequency = self.__info['sampling_frequency']
            self.__available_mems = list( self.__info['mems'] )
            self.__mems_number = len( self.__available_mems )
            self.__available_analogs = list( self.__info['analogs'] )
            self.__analogs_number = len( self.__available_analogs )
            self.__duration = self.__info['duration']
            self.__counter = self.__info['counter'] and not self.__info['counter_skip']
            self.__status = True if 'status' in self.__info and self.__info['status'] else False
            self.__channels_number = self.__mems_number + self.__analogs_number + ( 1 if self.__counter else 0 ) + ( 1 if self.__status else 0 )
            self.__dataset_length = self.__info['dataset_length']
            self.__dataset_number = self.__info['dataset_number']
            self.__samples_number = self.__dataset_number * self.__dataset_length

            log.info( f" .Created MuH5 object from {filename} file " )
            

    def get_signal( self, channels: list, mems_sensibility:float=MU_MEMS_SENSIBILITY ) -> np.ndarray:
        """
        Extract signal from file

        Parameters
        ----------
        * channels (list<int>): list of channels to extract
        * mems_sensibility: mems semsibility factor. if 0, the original signal is returned as it is (int32), otherwise as float32
        """

        """ build the mask from the channels list given as argument """
        mask = [ True if channel in channels else False for channel in range(self.channels_number) ]

        sound = np.zeros( ( len( channels ), self.__samples_number ), dtype=np.int32 )

        with h5py.File( self.__filename, 'r' ) as f:
            offset = 0
            for dataset_index in range( self.__dataset_number ):
                dataset = f['muh5/' + str( dataset_index ) + '/sig']
                sound[:,offset:offset+self.__dataset_length] = np.array( dataset[:] )[mask,:]
                offset += self.__dataset_length

        """ product with mems sensibility factor if one is given """
        if mems_sensibility is not None or mems_sensibility != 0:
            first_mems = 1 if self.__counter else 0
            last_mems = first_mems + self.__mems_number - 1
            mask = [ True if channel >= first_mems and channel <= last_mems else False for channel in channels ]
            sound = sound.astype( np.float32 )
            sound[mask,:] = sound[mask,:] * mems_sensibility

        return sound

    def get_one_channel_signal( self, channel_number, mems_sensibility:float=MU_MEMS_SENSIBILITY  ) -> np.ndarray:
        """
        Get only one channel signal whose channel number is given as argument
        """
        if channel_number >= self.channels_number:
            raise Exception( f"Index overflow: cannt extract channel [{channel_number}] from MuH5 with only [{self.channels_number}] channels " )

        return self.get_signal( [channel_number], mems_sensibility=mems_sensibility )

    def get_all_channels_signal( self, mems_sensibility:float=MU_MEMS_SENSIBILITY  ) -> np.ndarray:
        """
        Get all channels signal
        """        

        return self.get_signal( [i for i in range( self.__channels_number )], mems_sensibility=mems_sensibility )