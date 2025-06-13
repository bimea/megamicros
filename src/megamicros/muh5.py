# megamicros.muh5.py H5 file handler for MegaMicros libraries
#
# Copyright (c) 2023 Sorbonne Université
# Author: bruno.gas@sorbonne-universite.fr
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

"""
Megamicros documentation is available on https://readthedoc.bimea.io

"""

import numpy as np
import h5py

from .log import log, logging

MEMS_SENSIBILITY = 1/((2**23)*10**(-26/20)/3.17)                            # # MEMs sensibility factor (-26dBFS for 104 dB that is 3.17 Pa)

class MuH5:

    class Header:
        data: str
        timestamp: float
        dataset_number: int
        dataset_duration: int
        dataset_length: int
        channels_number: int
        sampling_frequency: float
        duration: float
        datatype: str
        mems: list|tuple
        mems_number: int
        analogs: list|tuple
        analogs_number: int
        counter: bool
        status: bool
        counter_skip: bool
        comments: str
        compression: bool
        system: None|str
        annotations: None|bool

    class Group:
        """ MuH5 group class, the root group mandatory for MµH5 files """
        group: h5py.Group


    _filename: str = ''
    _info = {}
    _sampling_frequency: float = 0
    _available_mems: int = 0
    _mems_number: int = 0
    _available_analogs: int = 0
    _analogs_number: int = 0
    _channels_number: int = 0
    _duration: int = 0
    _counter: bool = False
    _status: bool = False
    _dataset_length: int = 0
    _dataset_number: int = 0
    _samples_number: int = 0
    
    @property
    def sampling_frequency( self ):
        return self._sampling_frequency

    @property
    def mems_number( self ):
        return self._mems_number

    @property
    def channels_number( self ):
        return self._channels_number

    @property
    def duration( self ):
        return self._duration

    @property
    def duration( self ):
        return self._duration

    @property
    def samples_number( self ):
        return self._samples_number


    def __init__( self, filename:str ):

        """ open h5 file and get informations from """
        self._filename = filename
        with h5py.File( filename, 'r' ) as f:

            """ Control whether H5 file is a MuH5 file """
            if not f['muh5']:
                raise Exception( f"{filename} seems not to be a MuH5 file: unrecognized format" )

            """ get fil informations """
            group = f['muh5']
            self._info = dict( zip( group.attrs.keys(), group.attrs.values() ) )
            self._sampling_frequency = self._info['sampling_frequency']
            self._available_mems = list( self._info['mems'] )
            self._mems_number = len( self._available_mems )
            self._available_analogs = list( self._info['analogs'] )
            self._analogs_number = len( self._available_analogs )
            self._duration = self._info['duration']
            self._counter = self._info['counter'] and not self._info['counter_skip']
            self._status = True if 'status' in self._info and self._info['status'] else False
            self._channels_number = self._mems_number + self._analogs_number + ( 1 if self._counter else 0 ) + ( 1 if self._status else 0 )
            self._dataset_length = self._info['dataset_length']
            self._dataset_number = self._info['dataset_number']
            self._samples_number = self._dataset_number * self._dataset_length

            log.info( f" .Created MuH5 object from {filename} file " )
            

    def get_signal( self, channels: list, mems_sensibility:float=MEMS_SENSIBILITY ) -> np.ndarray:
        """
        Extract signal from file

        Parameters
        ----------
        * channels (list<int>): list of channels to extract
        * mems_sensibility: mems semsibility factor. if 0, the original signal is returned as it is (int32), otherwise as float32
        """

        """ build the mask from the channels list given as argument """
        mask = [ True if channel in channels else False for channel in range(self.channels_number) ]

        sound = np.zeros( ( len( channels ), self._samples_number ), dtype=np.int32 )

        with h5py.File( self._filename, 'r' ) as f:
            offset = 0
            for dataset_index in range( self._dataset_number ):
                dataset = f['muh5/' + str( dataset_index ) + '/sig']
                sound[:,offset:offset+self._dataset_length] = np.array( dataset[:] )[mask,:]
                offset += self._dataset_length

        """ product with mems sensibility factor if one is given """
        if mems_sensibility is not None or mems_sensibility != 0:
            first_mems = 1 if self._counter else 0
            last_mems = first_mems + self.mems_number - 1
            mask = [ True if channel >= first_mems and channel <= last_mems else False for channel in channels ]
            sound = sound.astype( np.float32 )
            sound[mask,:] = sound[mask,:] * mems_sensibility

        return sound

    def get_one_channel_signal( self, channel_number, mems_sensibility:float=MEMS_SENSIBILITY  ) -> np.ndarray:
        """
        Get only one channel signal whose channel number is given as argument
        """
        if channel_number >= self.channels_number:
            raise Exception( f"Index overflow: cannt extract channel [{channel_number}] from MuH5 with only [{self.channels_number}] channels " )

        return self.get_signal( [channel_number], mems_sensibility=mems_sensibility )

    def get_all_channels_signal( self, mems_sensibility:float=MEMS_SENSIBILITY  ) -> np.ndarray:
        """
        Get all channels signal
        """        

        return self.get_signal( [i for i in range( self.channels_number )], mems_sensibility=mems_sensibility )