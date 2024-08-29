# megamicros.core.h5.py base class for antenna reading H5 file as data input
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


""" Provide the class for antenna with MEMs signals extracted from a *MuH5* file 

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.bimea.io
"""
# comment

import os
from time import sleep, time
import numpy as np
import threading
import h5py

from megamicros.log import log
from megamicros.exception import MuException
from .base import MemsArray, DEFAULT_FRAME_LENGTH

H5_PROCESSING_DELAY_RATE				= 4/10						# computing delay rate relative to transfer buffer duration (adjusted for real time operation)


# =============================================================================
# Exception dedicaced to Megamicros H5 systems
# =============================================================================

class MuH5Exception( MuException ):
    """Exception base class for Megamicros MuH5 systems """


# =============================================================================
# The MemsArrayH5 base class
# =============================================================================

class MemsArrayH5( MemsArray ):
    """ MEMs array class with input stream comming from a MuH5 file.

    MuH5 file is a H5 file that follows the special Megamicros format
    """

    __loop: bool = False                 # Whether or not the current file is played in loop
    __filename: str = None               # H5 filename or directory name where to find H5 files
    __files= list()

    __current_file: h5py.File = None
    __current_filename: str = None
    __start_time: int = 0
    __transfer_index: int = 0
    __dataset_index: int = 0
    __dataset_index_ptr: int = 0
    __real_time: bool = True            # Whether or not file is played in real time or not

    # H5 file properties
    __file_timestamp: float = None
    __file_date: str = None
    __file_duration: int = None
    __file_comment: str = None
    __dataset_number: int = None
    __dataset_duration: int = None
    __dataset_length: int = None



    @property
    def files( self ) -> list:
        """
        Get the H5 files list to be processed 
        """
        return self.__files

    @property
    def current_filename( self ) -> list:
        """
        Get the current H5 file being read 
        """
        return self.__current_filename

    @property
    def start_time( self ) -> int:
        """
        Get the start time choosen by user to start H5 file processing
        """
        return self.__start_time
    
    @property
    def real_time( self ) -> int:
        """
        Check whether the H5 file is played in realtime or not
        """
        return self.__real_time

    @property
    def loop( self ) -> bool:
        """
        Whether reading process is in loop mode (True) or not (False)
        """
        return self.__loop

    @property
    def file_timestamp( self ) -> float:
        """
        Get the H5 current file creation timestamp
        """
        return self.__file_timestamp

    @property
    def file_date( self ) -> str:
        """
        Get the H5 current file creation date
        """
        return self.__file_date

    @property
    def dataset_number( self ) -> str:
        """
        Get the H5 current file dataset number
        """
        return self.__dataset_number
    
    @property
    def dataset_duration( self ) -> str:
        """
        Get the H5 current file dataset duration in seconds
        """
        return self.__dataset_duration
    
    @property
    def dataset_length( self ) -> str:
        """
        Get the H5 current file dataset length
        """
        return self.__dataset_length

    @property
    def file_duration( self ) -> str:
        """
        Get the H5 current file duration in seconds
        """
        return self.__file_duration
    
    @property
    def file_comment( self ) -> str:
        """
        Get the H5 current file dataset user comment
        """
        return self.__file_comment

    @property
    def annotations( self ) -> dict:
        """ 
        Get the H5 file annotations
        """
        return self._annotations()

    def setStartTime( self, start_time: int ):
        """
        Set the start time user wants to start H5 file processing 

        start_time: int
            start time in seconds
        """
        self.__start_time = start_time

    def setRealTime( self ):
        """
        Set real time ON
        """
        self.__real_time = True

    def unsetRealTime( self ):
        """
        Set real time OFF
        """
        self.__real_time = False

    def setFiles( self, filename: str ) -> None:
        """
        Set the list of available H5 files to play

        Parameters:
        -----------
        * filename: str 
            the MuH5 file name or the directory where to find H5 files
        """

        # Get H5 file or directory.
        self.__files = list()

        # Get h5 files name in directory
        if os.path.isdir( filename ):
            log.info( f" .Check directory {filename} for MuH5 files" )
            for file in os.listdir( filename ):
                if file.endswith( '.h5' ):
                    # Current file is a H5 file: Check if this is a MuH5 file
                    with h5py.File( file, 'r' ) as h5_file:
                        if not 'muh5' in h5_file:
                            # not a MuH5 file
                            continue

                    # current file is a MuH5 file : add to the list
                    self.__files.append( file )

            log.info( f" .Found {len( self.__files )} MuH5 files in directory {filename} " )
            if len( self.__files ) == 0:
                raise MuH5Exception( f"Found no MuH5 files in {filename} directory" )

        # filename is not a directory: check if it is a MuH5 file
        elif os.path.exists( filename ):
            # filename is a file 
            if filename.endswith( '.h5' ):
                # current file is a H5 file
                with h5py.File( filename, 'r' ) as h5_file:
                    if not 'muh5' in h5_file:
                        # this is not a MuH5 file
                        raise MuH5Exception( f"Error: {filename} is not a MuH5 file" )
    
                # current file is a MuH5 file : add to the list
                self.__files.append( filename )
                log.info( f" .Found {filename} MuH5 file" )
            else:
                # current file is not a H5 file
                raise MuH5Exception( f"Error: {filename} is not a H5 file" )
        else:
            raise MuH5Exception( f"Error: no file MuH5 file found or {filename} does not exist" )

        self.__filename = filename

    
    def setCounter( self, force:bool=False ) -> None :
        """ Overload the parent `setCounter()` method by doing nothing.
        Indeed counter state is defined in the H5 file and cannot be modified.
        """

        if force:
            super().setCounter()
        else:
            log.warning( f"The counter status cannot be modified, as it is defined in the remote H5 file. Use `counter_skip` instead" )


    def unsetCounter( self, force:bool=False ) -> None :
        """ Overload the parent `unsetCounter()` method by doing nothing.
        Indeed counter state is defined in the remote H5 file and cannot be modified. 
        """
        
        if force:
            super().unsetCounter()
        else:
            log.warning( f"The counter status cannot be modified, as it is defined in the H5 file. Use `counter_skip` instead" )


    def setStatus( self, force:bool=False ) -> None :
        """ Overload the parent `setStatus()` method by doing nothing.
        """

        if force:
            super().setStatus()
        else:
            log.warning( f"The channel status cannot be modified. There is usually no status channel in MuH5 files." )


    def unsetStatus( self, force:bool=False ) -> None :
        """ Overload the parent `unsetStatus()` method by doing nothing.
        """

        if force:
            super().unsetStatus()
        else:
            log.warning( f"The channel status cannot be modified. There is usually no status channel in MuH5 files." )


    def setSamplingFrequency( self, sampling_frequency: float, force:bool=False ) -> None :
        """ Overload the parent `setSamplingFrequency()` method by doing nothing.
        
        Parameters:
        -----------
        sampling_frequency : float
            The sampling frequency (default is given by DEFAULT_SAMPLING_FREQUENCY)
        force: bool
            Force to update sampling frequency
        """

        if force:
            super().setSamplingFrequency( sampling_frequency )
        else:
            log.warning( f"The sampling frequency cannot be modified as it is defined in the H5 file" )


    def __init__( self, filename: str, **kwargs ) -> None :
        """ Connect the antenna input stream to an input MuH5 file 

        File(s) existance is verified. If the file(s) are not available, an exception is raised. 
        
        Parameters
        ----------
        filename: str
            the MuH5 filename or the directory name where to find MuH5 file(s)
        """

        # Init base class
        super().__init__( kwargs=kwargs )

        # filename is mandatory
        self.setFiles( filename )

        # Set H5 settings
        if len( kwargs ) > 0:
            self._set_settings( [], kwargs )

        # Open the first H5 file in list and set settings from this file
        try:
            if self.files == None or len( self.files ) == 0:
                raise MuH5Exception( f"No H5 file(s) loaded. Failed to create object" ) 
            
            # get meta data
            with h5py.File( self.files[0], 'r' ) as file:
                if 'muh5' in file:
                    group = file['muh5']
                    meta = dict( zip( group.attrs.keys(), group.attrs.values() ) )
                    self.setSamplingFrequency( meta['sampling_frequency'], force=True  )
                    self.setAvailableMems( available_mems=list( meta['mems'] ) )
                    self.setCounter( force=True ) if meta['counter']==True else self.unsetCounter( force=True )
                    self.unsetStatus( force=True )
                    self.setAvailableAnalogs( available_analogs=list( meta['analogs'] ) )

                    self.__file_timestamp = meta['timestamp']
                    self.__file_date = meta['date']
                    self.__file_duration = meta['duration']
                    self.__file_comment = meta['comment']
                    self.__dataset_number = meta['dataset_number']
                    self.__dataset_duration = meta['dataset_duration']
                    self.__dataset_length = meta['dataset_length']

                else:
                    raise MuH5Exception( f"{self.files[0]} does not appear to be a MuH5 file: cannot find the 'muh5' H5 group" )

        except Exception as e:
            raise MuH5Exception( f"Failed to get meta info from {self.files[0]} H5 file ({type(e).__name__}): {e}" )


    def _annotations( self ):
        """ Check if annotations are available on H5 file and set them if any
        
        Return 
        ------
        annotations: dict
            annotations dictionary with label_id, labeling_id, datetime_start, datetime_end
        """

        # Check if annotations are available
        annotations: dict = {}
        with h5py.File( self.files[0], 'r' ) as file:
            if 'annotations/labels' in file:
                log.info( f"found annotations/labels in file" )
            group = file['muh5']
            log.info( f"found MuH5 group" )
            if 'annotations/labels' in group:
                log.info( f"found annotations/labels in MuH5 group" )
            if 'annotations/labels' in group and group['annotations/labels'].attrs['count'] > 0:
                annot_group = group['annotations/labels']
                count = annot_group.attrs['count']
                log.info( f" .Found {count} annotations in {self.files[0]} MµH5 file with format {annot_group.attrs['format']}" )
                annotations:dict = {
                    'label_id': np.zeros( count, dtype=np.int32 ),
                    'labeling_id': np.zeros( count, dtype=np.int32 ),
                    'sample_start': np.zeros( count, dtype=np.int32 ),
                    'sample_end': np.zeros( count, dtype=np.int32 )
                }

                for index in range( count ):
                    annot = annot_group[str( index )]
                    annotations['label_id'][index] = annot[0]
                    annotations['labeling_id'][index] = annot[1]
                    annotations['sample_start'][index] = annot[2]
                    annotations['sample_end'][index] = annot[3]

        return annotations



    def _check_settings( self ) -> None :
        """ Check settings values for MemsArrayH5 """

        # We cannot call the parent check_settings() method as it is not compatible for H5
        log.info( f" .Pre-execution checks for MemsArray object" )

        if self.mems is None or len( self.mems )==0:
            raise MuException( f"No activated MEMs" )
                
        if self.counter_skip is None:
            log.info( f" .Counter skipping not set -> set to False" )
            self.unsetCounterSkip()       
     
        if self.duration is None:
            raise MuException( f"No running duration set" )

        if self.datatype is MemsArray.Datatype.unknown:
            raise MuException( f"No datatype set" )
        
        if self.frame_length is None:
            log.info( f" .Frame length not set -> set to default" )
            self.setFrameLength( DEFAULT_FRAME_LENGTH )

        # Here we are
        log.info( f" .Pre-execution checks for MemsArrayH5 object" )
        
        if self.counter_skip and not self.counter:
            log.warning( f"`counter_skip` is set to True but `counter` is not available" )


    def _set_settings( self, args, kwargs ) -> None :
        """ Set settings for MemsArrayH5 objects 
        
        Parameters
        ----------
        args: array
            direct arguments of the run function
        args: array
            named arguments of the run function
        """

        # Check direct args
        if len( args ) != 0:
            raise MuH5Exception( "Direct arguments are not accepted" )
        
        try:  
            log.info( f" .Install MemsArrayH5 settings" )

            if 'real_time' in kwargs:
                self.setRealTime() if kwargs['real_time'] else self.unsetRealTime()

            if 'start_time' in kwargs:
                self.setStartTime( kwargs['start_time'] )
            
        except Exception as e:
            raise MuH5Exception( f"Run failed on settings: {e}")
        

    def getBFE( self ) -> dict:
        """ Get the BFE data from H5 file in one shot
        
        Parameters
        ----------
        return: dict
            the BFE data as a dictionary with keys 'BFE', 'energy', 'indexes', 'locations', 'mems_position'
        """

        # Run over H5 files
        for index, file in enumerate( self.files ):
            self.__current_filename = file
            log.info( f" .Processing {self.__current_filename} H5 file... " )

            try:
                with h5py.File( self.__current_filename, 'r' ) as self.__current_file:

                    if 'muh5' in self.__current_file:
                        group = self.__current_file['muh5']
                        meta = dict( zip( group.attrs.keys(), group.attrs.values() ) )

                        # Verbose
                        log.info( f" > {self.file_duration}s ({(self.file_duration/60):.2f}min) of data in H5 file" )
                        log.info( f" > Whether counter is available: {self.counter}" )
                        log.info( f" > {len( self.available_mems )} available mems" )
                        log.info( f" > {len( self.available_analogs )} available analogic channels" )
                        log.info( f" > Total available channels number is {self.available_channels_number}" )
                        log.info( f" > Total actual channels number is {self.channels_number}" )
                        log.info( f" > Sampling frequency: {self.sampling_frequency} Hz" )
                        log.info( f" > Active MEMs: {self.mems}" )
                        log.info( f" > Active analogic channels: {self.analogs}" )
                        log.info( f" > Whether counter is active: {self.counter and not self.counter_skip}" )

                        log.info( f" > Datatype: {str( self.datatype )}" )
                        if meta['compression']:
                            log.info( f" > Compression mode: ON" )
                        else:
                            log.info( f" > compression mode: OFF" )

                        if 'muh5/bfe' in self.__current_file:
                            log.info( f" .BFE data extraction" )

                            group_bfe = self.__current_file['muh5/bfe']
                            if 'antenna' in group_bfe:
                                group_antenna = self.__current_file['muh5/bfe/antenna']
                                antenna = dict( zip( group_antenna.attrs.keys(), group_antenna.attrs.values() ) )
                                log.info( f" > Mems number: {antenna['mems_number']}" )
                                log.info( f" > Locations number: {antenna['locations_number']}" )
                            else:
                                antenna = {}
                                log.warning( f"Cannot find BFE antenna properties in {self.__current_filename} H5 file (no `muh5/bfe/antenna` group found)" )

                            BFE = []
                            BFE_count = []
                            sub_groups_number = len( group_bfe ) - 1
                            for i in range( sub_groups_number ):
                                print('sub-group: ', i)
                                if str( i ) in group_bfe:
                                    group = group_bfe[str( i )]
                                    print('group: ', group)
                                    BFE.append( np.array( group['sig'] ) )
                                    BFE_count.append( np.array( group['count'] ) )

                            data = {
                                'antenna': antenna,
                                'BFE': BFE,
                                'count': np.concatenate( BFE_count )
                            }

                            return data
                            
                        else:
                            raise MuH5Exception( f"Cannot find BFE data in {self.__current_filename} H5 file (no `muh5/bfe` group found)" )

                        # Leave once the first file is processed 
                        break

            except Exception as e:
                log.error( f"getBFE failed on Exception ({type(e).__name__}): {e}" )
                raise e
            except :
                log.error( f"getBFE failed on unexpected unknown Exception ({type(e).__name__}): {e}" )
                raise e      
    

    def get( self ) -> np.array:
        """ Get all channels from H5 file in one shot

        Parameters
        ----------
        return: np.array
            the signal as a numpy array
        """

        # Run over H5 files
        for index, file in enumerate( self.files ):
            self.__current_filename = file
            log.info( f" .Processing {self.__current_filename} H5 file... " )

            try:
                with h5py.File( self.__current_filename, 'r' ) as self.__current_file:

                    if 'muh5' in self.__current_file:
                        group = self.__current_file['muh5']
                        meta = dict( zip( group.attrs.keys(), group.attrs.values() ) )

                        # Force datatype settings to that of H5 file because we do not provide yet a way to change it 
                        self.setDatatype( meta['datatype'] )
                        samples_number = self.dataset_length * self.dataset_number

                        # Verbose
                        log.info( f" .{self.file_duration}s ({(self.file_duration/60):.2f}min) of data in H5 file" )
                        log.info( f" .Whether counter is available: {self.counter}" )
                        log.info( f" .{len( self.available_mems )} available mems" )
                        log.info( f" .{len( self.available_analogs )} available analogic channels" )
                        log.info( f" .Total available channels number is {self.available_channels_number}" )
                        log.info( f" .Total actual channels number is {self.channels_number}" )
                        log.info( f" .Sampling frequency: {self.sampling_frequency} Hz" )
                        log.info( f" .Active MEMs: {self.mems}" )
                        log.info( f" .Active analogic channels: {self.analogs}" )
                        log.info( f" .Whether counter is active: {self.counter and not self.counter_skip}" )

                        log.info( f" .Datatype: {str( self.datatype )}" )
                        if meta['compression']:
                            log.info( f" .Compression mode: ON" )
                        else:
                            log.info( f" .compression mode: OFF" )
                        
                        # Set the mask for mems and analogs selecting
                        # - mask: the binary mask for selected channels to get
                        # - masking: True if somme channels are masked, False for complete copy
                        # - channels_number: selected microphones + selected analogs + counter if available
                        mask = list( np.isin( self.available_mems, self.mems ) )

                        # Add analog channels if any
                        if self.available_analogs_number > 0 and self.analogs_number > 0:
                            mask = mask + list( np.isin( self.available_analogs, self.analogs ) )

                        # Add or remove counter if counter is in H5 file 
                        if self.counter:
                            # User does not want to get counter
                            if self.counter_skip:
                                mask = [False] + mask
                            # User want to get counter values
                            else:
                                mask = [True] + mask

                        # Add or remove status if status is in H5 file
                        if 'status' in meta and meta['status'] == True:
                            # User want the status channel
                            if self.status:
                                mask = mask + [True]
                            else:
                            # He doesn't
                                mask = mask + [False]

                        # Total channels number and masking flag
                        channels_number = sum( mask )
                        masking = channels_number != len(mask)

                        data = np.zeros( (channels_number, samples_number), dtype=np.int32 )
                        for dataset_index in range( self.dataset_number ):
                            dataset = self.__current_file['muh5/' + str( dataset_index ) + '/sig']
                            if masking:
                                data[:,dataset_index*self.dataset_length:(dataset_index+1)*self.dataset_length] = np.array( dataset[:] )[mask,:]
                            else:
                                data[:,dataset_index*self.dataset_length:(dataset_index+1)*self.dataset_length] = np.array( dataset[:] )                        
        
            except Exception as e:
                log.error( f"get failed on Exception ({type(e).__name__}): {e}" )
                raise e
            except :
                log.error( f"get failed on unexpected unknown Exception ({type(e).__name__}): {e}" )
                raise e

        return data


    def get_old( self, channels:list|tuple = (0,) ) -> any:
        """ Get channels from H5 file in one shot

        Parameters
        ----------
        channels: list|tuple|np.array
            list of channels to get
        return: np.array
            the signal as a numpy array
        """

        if type( channels ) is np.array:
            channels = list( channels )

        # Run over H5 files
        for index, file in enumerate( self.files ):
            self.__current_filename = file
            log.info( f" .Processing {self.__current_filename} H5 file... " )

            try:
                with h5py.File( self.__current_filename, 'r' ) as self.__current_file:

                    if 'muh5' in self.__current_file:
                        group = self.__current_file['muh5']
                        meta = dict( zip( group.attrs.keys(), group.attrs.values() ) )

                        # Force datatype settings to that of H5 file because we do not provide yet a way to change it 
                        self.setDatatype( meta['datatype'] )
                        samples_number = self.dataset_length * self.dataset_number

                        # Verbose
                        log.info( f" .{self.file_duration}s ({(self.file_duration/60):.2f}min) of data in H5 file" )
                        log.info( f" .Whether counter is available: {self.counter and not self.counter_skip}" )
                        log.info( f" .{len( self.available_mems )} available mems" )
                        log.info( f" .{len( self.available_analogs )} available analogic channels" )
                        log.info( f" .Requested channels: {channels}" )
                        log.info( f" .Total available channels number is {self.available_channels_number}" )
                        log.info( f" .Total actual channels number is {self.channels_number}" )
                        log.info( f" .Datatype: {str( self.datatype )}" )
                        if meta['compression']:
                            log.info( f" .Compression mode: ON" )
                        else:
                            log.info( f" .compression mode: OFF" )

                        # Checks
                        if len( channels ) > self.channels_number:
                            raise MuH5Exception( f"Error: requested {len( channels )} channels but only {self.channels_number} are available" )

                        if max( channels ) >= self.channels_number:
                            raise MuH5Exception( f"Error: requested channel {max( channels )} is out of range" )

                        # Set the mask for mems and analogs selecting
                        mask = list( np.isin( self.available_mems, channels ) )
                        masking = len( mask ) != self.channels_number

                        data = np.zeros( (len( channels ), samples_number), dtype=np.int32 )
                        for dataset_index in range( self.dataset_number ):
                            dataset = self.__current_file['muh5/' + str( dataset_index ) + '/sig']
                            if masking:
                                data[:,dataset_index*self.dataset_length:(dataset_index+1)*self.dataset_length] = np.array( dataset[:] )[mask,:]
                            else:
                                data[:,dataset_index*self.dataset_length:(dataset_index+1)*self.dataset_length] = np.array( dataset[:] )
                        
        
            except Exception as e:
                log.error( f"get failed on Exception ({type(e).__name__}): {e}" )
                raise e
            except :
                log.error( f"get failed on unexpected unknown Exception ({type(e).__name__}): {e}" )
                raise e

        return data
    

    def run( self, *args, **kwargs ) :
        """ The main run method that runs the remote antenna """

        if len( args ) > 0:
            raise MuH5Exception( f"Run() method does not accept direct arguments" )
        
        log.info( f" .Starting run execution" )
                
        # Set all settings
        # Run does not call the super().run() method, so we have to handle all settings here      
        try:
            super()._set_settings( [], kwargs=kwargs )
            self._set_settings( [], kwargs=kwargs )

        except Exception as e:
            raise MuH5Exception( f"Cannot run: settings loading failed ({type(e).__name__}): {e}" )
        
        # Check settings values
        try:
            self._check_settings()

        except Exception as e:
            raise MuH5Exception( f"Unable to execute run: control failure  ({type(e).__name__}): {e}" )

        # verbose
        if self.duration == 0:
            log.info( f" .Run infinite loop (duration=0)" )
        else :
            log.info( f" .Perform a {self.duration}s run loop" )

        log.info( f" .Frame length: {self.frame_length} samples (chunk size: {self.frame_length * self.channels_number * 4} Bytes)" )
        log.info( f" .Sampling frequency: {self.sampling_frequency} Hz" )
        log.info( f" .Active MEMs: {self.mems}" )
        log.info( f" .Active analogic channels: {self.analogs}" )
        log.info( f" .Whether counter is active: {self.counter}" )
        log.info( f" .Skipping counter: {self.counter_skip}" )
        log.info( f" .Desired playing duration: { str(self.duration) + ' s' if self.duration != 0 else 'not limited'}" )

        # Start running
        self.setRunningFlag( True )

        # Start the timer if a limited execution time is requested and real time is ON
        if self.duration > 0 and self.real_time:
            self._thread_timer = threading.Timer( self.duration, self._run_endding )
            self._thread_timer_flag = True
            self._thread_timer.start()

        # Start run thread
        self._async_transfer_thread = threading.Thread( target= self.__run_thread )
        self._async_transfer_thread.start()


    def __run_thread( self ):
        """ Run over H5 files 
        
        Notice that continuity between files is not managed
        """

        initial_time: float = time()
        elapsed_time: float = 0

        while self.running:
            # Run over H5 files
            for index, file in enumerate( self.files ):
                self.__current_filename = file
                log.info( f" .Processing {self.__current_filename} H5 file... " )

                # Reset starting time for next files
                if index > 0:
                    self.setStartTime( 0 )

                # Transfer loop
                try:
                    with h5py.File( self.__current_filename, 'r' ) as self.__current_file:

                        if 'muh5' in self.__current_file:
                            group = self.__current_file['muh5']
                            meta = dict( zip( group.attrs.keys(), group.attrs.values() ) )

                            # Set settings according H5 file meta parameters                            
                            mems = self.mems
                            self.setActiveMems( [] )
                            self.setAvailableMems( available_mems = list( meta['mems'] ) )
                            self.setActiveMems( mems )

                            analogs = self.analogs
                            self.setActiveAnalogs( [] )
                            self.setAvailableAnalogs( available_analogs = list( meta['analogs'] ) )
                            self.setActiveAnalogs( analogs )

                            self.setSamplingFrequency( meta['sampling_frequency'], force=True  )
                            self.setCounter( force=True ) if meta['counter']==True and meta['counter_skip']==False else self.unsetCounter( force=True )
                            self.unsetStatus( force=True )

                            self.__file_timestamp = meta['timestamp']
                            self.__file_date = meta['date']
                            self.__file_duration = meta['duration']
                            self.__file_comment = meta['comment']
                            self.__dataset_number = meta['dataset_number']
                            self.__dataset_duration = meta['dataset_duration']
                            self.__dataset_length = meta['dataset_length']

                            # Verbose
                            log.info( f" .{self.file_duration}s ({(self.file_duration/60):.2f}min) of data in H5 file" )
                            log.info( f" .Starting time: {self.start_time}s" )
                            log.info( f" .Real time: {'ON' if self.real_time else 'OFF'}" )
                            log.info( f" .Whether counter is available: {meta['counter'] and not meta['counter_skip']}" )
                            log.info( f" .{len( self.available_mems )} available mems" )
                            log.info( f" .{self.mems_number} activated microphones" )
                            log.info( f" .Activated microphones: {self.mems}" )
                            log.info( f" .{self.available_analogs_number} available analogic channels" )
                            log.info( f" .{self.analogs_number} activated analogic channels" )
                            log.info( f" .Activated analogic channels: {self.analogs }" )
                            log.info( f" .Whether counter is activated: {self.counter and not self.counter_skip}" )
                            log.info( f" .Whether status is activated: {self.status}" )
                            log.info( f" .Total available channels number is {self.available_channels_number}" )
                            log.info( f" .Total actual channels number is {self.channels_number}" )
                            log.info( f" .Datatype: {str( self.datatype )}" )
                            log.info( f" .Frame length in samples number: {self.frame_length} ({self.frame_length*1000/self.sampling_frequency} ms duration)" )			
                            log.info( f" .Frame length in 32 bits words number: {self.frame_length}x{self.channels_number}={self.frame_length*self.channels_number} words ({self.frame_length*self.channels_number*4} Bytes)" )
                            if meta['compression']:
                                log.info( f" .Compression mode: ON" )
                            else:
                                log.info( f" .compression mode: OFF" )
                            log.info( f" .Reading in loop mode: {self.loop}" )

                            transfer_index = 0                                          # transfer buffer counting
                            dataset_index: int = 0                                      # current dataset
                            dataset_index_ptr: int = 0                                  # current index in current dataset 

                            if self.start_time > 0:
                                # Start from requested starting time
                                if self.start_time > meta['duration']:
                                    raise MuException( f"Cannot read file at {self.start_time}s start time. File duration ({meta['duration']}) is too short" )
                                
                                if not self.real_time and self.start_time + self.duration > meta['duration']:
                                    raise MuException( f"Cannot read file at {self.start_time}s start time on {self.duration}s duration: File duration ({meta['duration']}) is too short" )
                                
                                dataset_index = int( ( self.start_time * self.sampling_frequency ) // meta['dataset_length'] )
                                dataset_index_ptr = int( ( self.start_time * self.sampling_frequency ) % meta['dataset_length'] )

                            else:
                                # Start from beginning
                                if not self.real_time and self.duration > meta['duration']:
                                    raise MuException( f"Cannot read file on {self.duration}s duration: File duration ({meta['duration']}) is too short" )

                                dataset_index = 0
                                dataset_index_ptr = 0

                            # Fill buffer with first dataset
                            dataset = self.__current_file['muh5/' + str( dataset_index ) + '/sig']
                            log.info( f" .first dataset: [{dataset_index}]" )
                            dataset_index += 1

                            # Set the mask for mems and analogs selecting
                            # - mask: the binary mask for selecting channels to get
                            # - masking: True if somme channels are masked, False for complete copy
                            # - channels_number: selected microphones + counter if available and selected + selected analogs
                            mask = list( np.isin( self.available_mems, self.mems ) )

                            # Add analog channels if any
                            if self.available_analogs_number > 0 and self.analogs_number > 0:
                                mask = mask + list( np.isin( self.available_analogs, self.analogs ) )

                            # Add or remove counter if counter is in H5 file 
                            if self.counter:
                                # User does not want to get counter
                                if self.counter_skip:
                                    mask = [False] + mask
                                # User want the counter
                                else:
                                    mask = [True] + mask

                            # Add or remove status if status is in H5 file
                            if 'status' in meta and meta['status'] == True:
                                # User want the status channel
                                if self.status:
                                    mask = mask + [True]
                                else:
                                # He doesn't
                                    mask = mask + [False]

                            # Total channels number and masking flag
                            channels_number = sum( mask )
                            masking = channels_number != len(mask)

                            if masking:
                                transfer_buffer = np.array( dataset[:] )[mask,:]
                            else:
                                transfer_buffer = np.array( dataset[:] )

                            # Start transfer
                            transfert_start_time = time()
                            frame_duration = self.frame_length / self.sampling_frequency
                            processing_delay = frame_duration * H5_PROCESSING_DELAY_RATE
                            file_endeed: bool = False

                            # Must control the loop if real time is OFF (there is no more timer)
                            if not self.real_time:
                                max_transfer_index = int( self.duration * self.sampling_frequency / self.frame_length )
                                log.info( f" .Real time OFF: max transfers number set to : {max_transfer_index} transfers ({(max_transfer_index*self.frame_length/self.sampling_frequency):.2f} s equivalent signal duration)" )
                            else:
                                max_transfer_index = 0

                            while not file_endeed and self.running == True:
                                # Check if we have to stop if real time if OFF:
                                if not self.real_time and transfer_index >= max_transfer_index:
                                    log.info( f" .Real time OFF: stop playing current file {self.__current_filename}" )
                                    self.setRunningFlag( False )
                                    break

                                # There is enough data in current dataset: process to transfert
                                if dataset_index_ptr + self.frame_length <= self.__dataset_length:
                                    # Wait for real time operation
                                    if self.real_time and ( time() - transfert_start_time ) < frame_duration - processing_delay:
                                        sleep( frame_duration-time()+transfert_start_time-processing_delay )

                                    # Transfer buffer
                                    transfert_start_time = time()
                                    self.queue.put( self.__run_process_data( transfer_buffer[:,dataset_index_ptr:dataset_index_ptr+self.frame_length] ) )                            
                                    dataset_index_ptr += self.frame_length
                                    transfer_index += 1

                                else:
                                    # Not enough data in current dataset: open next dataset
                                    if dataset_index < self.__dataset_number:

                                        # Next dataset exists: get last data of current dataset, open next and complete buffer
                                        current_dataset_last_samples_number = self.__dataset_length - dataset_index_ptr
                                        buffer = transfer_buffer[:,dataset_index_ptr:dataset_index_ptr+self.__dataset_length]
                                        log.info( f"  > Dataset [{'muh5/' + str( dataset_index ) + '/sig'}]" )
                                        dataset = self.__current_file['muh5/' + str( dataset_index ) + '/sig']

                                        # Fill buffer with next dataset
                                        if masking:
                                            transfer_buffer = np.array( dataset[:] )[mask,:]
                                        else:
                                            transfer_buffer = np.array( dataset[:] )

                                        new_dataset_first_samples_number = self.frame_length - current_dataset_last_samples_number
                                        buffer = np.append( buffer, transfer_buffer[:,:new_dataset_first_samples_number], axis=1 )

                                        # Wait for real time synchro
                                        if self.real_time and  ( time() - transfert_start_time ) < frame_duration - processing_delay:
                                            sleep( frame_duration-time()+transfert_start_time - processing_delay )
                                        
                                        # Transfer buffer
                                        transfert_start_time = time()
                                        self.queue.put( self.__run_process_data( buffer ) )
                                        transfer_index += 1

                                        dataset_index_ptr = new_dataset_first_samples_number
                                        dataset_index += 1

                                    # No more dataset: save current buffer and stop playing
                                    else:    
                                        buffer = transfer_buffer[:,dataset_index_ptr:self.__dataset_length]
                                        buffer = np.append( buffer, np.zeros( (channels_number, self.frame_length - self.__dataset_length + dataset_index_ptr), dtype=np.int32), axis=1 )
                                        
                                        # Wait for real time synchro
                                        if self.real_time and time() - transfert_start_time < frame_duration - processing_delay:
                                            sleep( frame_duration-time()+transfert_start_time - processing_delay )

                                        # Transfer buffer
                                        transfert_start_time = time()
                                        self.queue.put( self.__run_process_data( buffer ) )
                                        transfer_index += 1

                                        file_endeed = True
                                        log.info( f" .No more dataset: stop playing current file {self.__current_filename}" )

                        else:
                            raise MuH5Exception( f"Error: file {self.__current_filename} is not a MuH5 file" )


                except MuH5Exception as e:
                    log.error( f"Quitting run() execution on MuH5Exception: {e}" )
                    raise e
                except Exception as e:
                    log.error( f"Quitting run() execution on Exception ({type(e).__name__}): {e}" )
                    raise e
                except :
                    log.error( f"Quitting run() on unexpected unknown Exception ({type(e).__name__}): {e}" )
                    raise e


        # Compute elasped time
        elapsed_time = time() - initial_time

        if self.duration == 0:
            log.info( f" .Elapsed time: {elapsed_time:.2f} s")
        else:
            if self.real_time:
                log.info( f" .Elapsed time: {elapsed_time:.2f} s (expected duration was: {self.duration} s)")
            else:
                log.info( f" .Elapsed time: {elapsed_time:.2f} s")

        log.info( f" .Proceeded to {transfer_index} transfers" )
        log.info( " .Run completed" )


    def __run_process_data( self, data: np.ndarray ) -> any :
        """ Process data in the right format before sending it to the queue 
        
        Notice that the antenna 'frame_length' value can cut signal into non integer parts number.
        As a result, last chunk can be shorter with less than 'frame_length' samples

        Parameter
        ---------
        data: np.ndarray
            input data, supposed to be numpy array of int32
        Return: bytes|np.ndarray
            output data in the format required by the user
        """

        # User wants data as binary buffer of int32
        if self.datatype == self.Datatype.bint32:
            data = np.ndarray.tobytes( data.T )
        
        # User wants data as numpy array of int32: nothing to do but transposing
        elif self.datatype == self.Datatype.int32:
            data = data.T

        # User wants data as numpy array of float32 
        elif self.datatype == self.Datatype.float32:
            data = ( data.astype( np.float32 ) * self.sensibility ).T

        # User wants data as binary buffer of float32
        else:
            data = ( data.astype( np.float32 ) * self.sensibility ).T
            data = np.ndarray.tobytes( data )
            
        return data
