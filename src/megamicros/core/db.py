# megamicros.core.db.py base class for antenna connected to an Aidb database
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


""" Provide the class for antenna with MEMs signals extracted from a *Aidb* database 

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import numpy as np
import threading
import requests

from megamicros.log import log
from megamicros.exception import MuException
from megamicros.aidb.query import AidbSession
import megamicros.core.base as base

DEFAULT_DB_PORT         = 9002

# =============================================================================
# Exception dedicaced to Megamicros Aidb systems
# =============================================================================

class MuDBException( MuException ):
    """Exception base class for Megamicros Aidb systems """


# =============================================================================
# The MemsArrayDB base class
# =============================================================================

class MemsArrayDB( base.MemsArray ):
    """ MEMs array class with input stream connected to a remote database.

    """

    __source: np.ndarray|None = None
    __available_frames_number: int|None = None

    __label_id: int = None                  # Database labekl identifier
    __file_id: int = None                   # Database file identifier
    __sequence_id: int = None               # Database sequence identifier in file
    __dbhost: str = None                    # Database host address
    __dbport: int = DEFAULT_DB_PORT         # Database port
    __login: str = None                     # Database user login
    __email: str = None                     # Database user password
    __password: str = None                  # Database user email


    @property
    def dbhost( self ) -> str:
        """ Get the Database host address """
        return self.__dbhost
    
    @property
    def dbport( self ) -> int:
        """ Get the Database port """
        return self.__dbport
    
    @property
    def login( self ) -> str:
        """ Get the Database user login """
        return self.__login
    
    @property
    def email( self ) -> str:
        """ Get the Database user email """
        return self.__email

    @property
    def label_id( self ) -> int:
        """ Get the Database label identifier """
        return self.__label_id
    
    @property
    def file_id( self ) -> int:
        """ Get the Database file identifier """
        return self.__file_id
    
    @property
    def sequence_id( self ) -> int:
        """ Get the Database sequence identifier in selected file """
        return self.__sequence_id


    def setLabelId( self, label_id: int ) -> None :
        """ Set the Database label identifier 
        
        Parameters
        ----------
        label_id: int
            The label identifier
        """
        self.__label_id = label_id

    def setFileId( self, file_id: int ) -> None :
        """ Set the Database file identifier 
        
        Parameters
        ----------
        file_id: int
            The file identifier
        """
        self.__file_id = file_id

    def setSequenceId( self, sequence_id: int ) -> None :
        """ Set the Database sequence identifier in current file
        
        Parameters
        ----------
        sequence_id: int
            The sequence identifier
        """
        self.__sequence_id = sequence_id

    def setCounter( self, force:bool=False ) -> None :
        """ Overload the parent `setCounter()` method by doing nothing.
        Indeed counter state is defined in the remote H5 file and cannot be modified.
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
            log.warning( f"The counter status cannot be modified, as it is defined in the remote H5 file. Use `counter_skip` instead" )

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
            log.warning( f"The sampling frequency cannot be modified as it is defined in the remote H5 file" )



    def __init__( self, dbhost: str, login: str, email: str, password: str, dbport=DEFAULT_DB_PORT, **kwargs ) -> None :
        """ Connect the antenna input stream to a labelized database 

        The connection to the database is verified. If the database is not available, an exception is raised. 
        
        Parameters
        ----------
        dbhost: str
            the database host address in the form ``http(s)://www.database.io``
        login: str
            database account login
        email: str
            database user email
        passwd: str
            account password
        """

        self.__dbhost = dbhost
        self.__dbport = dbport
        self.__login = login
        self.__email = email
        self.__password = password

        # Init base class
        super().__init__( kwargs=kwargs )

        # Set DB settings
        if len( kwargs ) > 0:
            self._set_settings( [], kwargs )

        # test connection to database and set settings fram database file
        try:
            with AidbSession( dbhost=self.dbhost, login=self.login, email=self.email, password=self.__password ) as session:
                # get meta data
                meta = session.get_sourcefile( self.file_id )
                self.setSamplingFrequency( meta['info']['sampling_frequency'], force=True  )
                self.setAvailableMems( available_mems_number=len( meta['info']['mems'] ) )
                self.setCounter( force=True ) if meta['info']['counter']==True else self.unsetCounter( force=True )
                self.unsetStatus( force=True )
                self.setAvailableAnalogs( available_analogs_number=len( meta['info']['analogs'] ) )

        except MuException as e:
            raise( f"Connection to database {dbhost} failed ({type(e).__name__}): {e}" )
            
        """
        try:
            with AidbSession( dbhost=dbhost, login=login, email=email, password=passwd ) as session:
                # get meta data
                meta = session.get_sourcefile( file_id )
                self.setSamplingFrequency( meta['info']['sampling_frequency'] )
                self.setAvailableMems( available_mems_number=len( meta['info']['mems'] ) )
                self.setCounter() if meta['info']['counter']==True else self.unsetCounter()
                self.setCounterSkip() if meta['info']['counter_skip']==True else self.unsetCounterSkip()
                self.setAvailableAnalogs( available_analogs_number=len( meta['info']['analogs'] ) )

                # get signal
                log.info( f" .Downloading..." )
                try:
                    # get all sequences
                    signal: list = session.load_labelized( 
                        sourcefile_id=file_id, 
                        label_id=label_id, 
                        limit=100, 
                        channels=self.mems
                    )

                except Exception as e:
                    raise f" .Downloading failed: {e}"
                
            # Save signals as ND array
            if sequence_id is None:
                self.__source = np.concatenate( signal, axis=1 )
            else:
                self.__source = signal[sequence_id]

            # check status channel
            # >>>>>>>

            samples_number, mems_number = self.__source.shape
            log.info( f" .Got {samples_number} samples on {mems_number} MEMs" )

        except Exception as e:
            raise MuException( f"Connection to database {dbhost} failed: {e}" )
            """


    def _set_settings( self, args, kwargs ) -> None :
        """ Set settings for MemsArrayDB objects 
        
        Parameters
        ----------
        args: array
            direct arguments of the run function
        args: array
            named arguments of the run function
        """

        # Check direct args
        if len( args ) > 0:
            raise MuDBException( "Direct arguments are not accepted for run() method" )
        
        try:  
            log.info( f" .Install MemsArrayDB settings" )

            if 'label_id' in kwargs:
                self.setLabelId( kwargs['label_id'] )

            if 'file_id' in kwargs:
                self.setFileId( kwargs['file_id'] )

            if 'sequence_id' in kwargs:
                self.setSequenceId( kwargs['sequence_id'] )

        except Exception as e:
            raise MuDBException( f"Run failed on settings: {e}")


    def _check_settings( self ) -> None :
        """ Check settings values for MemsArrayDB """

        # We cannot call the parent check_settings() method as it is not compatible for DB
        log.info( f" .Pre-execution checks for MemsArray.run()" )

        if self.mems is None or len( self.mems )==0:
            raise MuException( f"No activated MEMs" )
                
        if self.counter_skip is None:
            log.info( f" .Counter skipping not set -> set to False" )
            self.unsetCounterSkip()       
     
        if self.duration is None:
            raise MuException( f"No running duration set" )
        
        if self.datatype is base.MemsArray.Datatype.unknown:
            raise MuException( f"No datatype set" )
        
        if self.frame_length is None:
            log.info( f" .Frame length not set -> set to default" )
            self.setFrameLength( base.DEFAULT_FRAME_LENGTH )

        # Here we are
        log.info( f" .Pre-execution checks for MemsArrayDB.run()" )

        if self.sequence_id and ( not self.file_id or not self.label_id ) :
            raise MuDBException( f"Settings check failed: 'sequence_id' is defnied while 'label_id' or 'file_id' are not" )

        if self.label_id and not self.file_id:
            raise MuDBException( f"Settings check failed: 'label_id' is defined but not 'file_id'. Cannot iterate over all files" )
        
        if self.counter_skip and not self.counter:
            log.warning( f"`counter_skip` is set to True while `counter` is not available" )


    def run( self, *args, **kwargs ) :
        """ The main run method that run the remote antenna """

        if len( args ) > 0:
            raise MuDBException( f"Run() method does not accept direct arguments" )
        
        log.info( f" .Starting run execution" )
                
        # Set all settings
        # Run does not call the super().run() method so that we have to handle all settings here      
        try:
            super()._set_settings( [], kwargs=kwargs )
            self._set_settings( [], kwargs=kwargs )

        except Exception as e:
            raise MuDBException( f"Cannot run: settings loading failed ({type(e).__name__}): {e}" )
        
        # Check settings values
        try:
            self._check_settings()

        except Exception as e:
            raise MuDBException( f"Unable to execute run: control failure  ({type(e).__name__}): {e}" )

        # verbose
        if self.duration == 0:
            log.info( f" .Run infinite loop (duration=0)" )
        else :
            log.info( f" .Perform a {self.duration}s run loop" )

        log.info( f" .Frame length: {self.frame_length} samples (chunk size: {self.frame_length * 5 * 4} Bytes)" )
        log.info( f" .Sampling frequency: {self.sampling_frequency} Hz" )
        log.info( f" .Active MEMs: {self.mems}" )
        log.info( f" .Active analogic channels: {self.analogs}" )
        log.info( f" .Whether counter is active: {self.counter}" )
        log.info( f" .Skipping counter: {self.counter_skip}" )

        # If running time is limited: create the time delay thread as dameon thread and run it
        # As soon as the main program exits (for some reasons the running thread is stopped), the duration thread is killed.  
        if self.duration > 0:            
            self._async_duration_thread = threading.Thread( target= self._duration_thread, args=( self.duration, ) )
            self._async_duration_thread.daemon = True
            self._async_duration_thread.start()

        # Start run thread
        self._async_transfer_thread = threading.Thread( target= self.__run_thread )
        self._async_transfer_thread.start()
        

    def __run_thread( self ):

        # check for the counter channel but not for the status channel
        channels = self.mems
        if self.counter and not self.counter_skip:
            channels = [0] + list( np.array( channels ) + 1 )

        # Set chunk size
        channels_number = len( channels )
        chunk_size = self.frame_length * channels_number * 4

        # set endpoint url
        channels_str = ( ''.join( str( integer ) + ',' for integer in channels ) )[:-1]
        #channels_str = channels_str[:-1]

        url = f"{self.dbhost}sourcefile/{self.file_id}/range/1/10/channels/0/0/?channels={channels_str}"

        log.info( f" .Endpoint url: {url}" )

        try:
            with requests.get(url, stream=True) as response:
                # Check if the request was successful
                response.raise_for_status()

                # Get chunk of data from remote DB server
                self.setRunningFlag( True )
                for chunk in response.iter_content( chunk_size=chunk_size ):
                    # Process binary data by pushing them in the queue 
                    # Thanks to the queue, data are not lost if the reading process is too slow compared to the filling speed.
                    # However, the queue introduces a latency that can become problematic.
                    # If the user accepts the loss of data, it is possible to limit the size of the queue.
                    # In this case, once the size is reached, each new entry induces the deletion of the oldest one.
                    self.signal_q.put( self.__run_process_data( chunk ) )
                    if self.running == False:
                        log.info( " .Running stopped: normal thread termination" )
                        break

        except MuDBException as e:
            # Known exception:
            log.info( f" .Listening loop was stopped: {e}" )
        except Exception as e:
            # Uknnown exception:
            log.error( f" Listening loop stopped due to network error exception ({type(e).__name__}): {e}" )


    def __run_process_data( self, data: bytes ) -> any :
        """ Process data in the right format before sending it in the queue 
        
        Parameter
        ---------
        data: bytes
            input data 
        Return: bytes|np.ndarray
            output data in the format required by the user
        """
        print( 'data=', data )

        # User wants data as binary buffer of int32 
        if self.datatype == self.Datatype.bint32:
            pass
        
        # User wants data as numpy array of int32 
        elif self.datatype == self.Datatype.int32:
            # build np array from binary buffer
            data = np.frombuffer( data, dtype=np.int32 )

            # reshape MEMs signals column wise ( samples number X channels_number ) 
            frame_length = len( data ) // self.channels_number
            data =  np.reshape( data, ( self.channels_number, frame_length ) ).T
            
        # User wants data as numpy array of float32 
        elif self.datatype == self.Datatype.float32:
            # build np array from binary buffer
            data = np.frombuffer( data, dtype=np.int32 ).astype( np.float32 ) * self.sensibility 

            # reshape MEMs signals column wise ( samples number X channels_number )
            frame_length = len( data ) // self.channels_number 
            data = np.reshape( data, ( self.channels_number,  frame_length ) ).T

        # User wants data as binary buffer of float32 
        else:
            data = np.frombuffer( data, dtype=np.int32 ).astype( np.float32 ) * self.sensibility 
            data = np.ndarray.tobytes( data )
            
        return data
