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



    #def __init__( self, dbhost: str, login: str, email: str, passwd: str, label_id:int, file_id: int|None=None, sequence_id: int|None=None, preload: bool=False ) -> None :
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
                self.setSamplingFrequency( meta['info']['sampling_frequency'] )
                self.setAvailableMems( available_mems_number=len( meta['info']['mems'] ) )
                self.setCounter() if meta['info']['counter']==True else self.unsetCounter()
                self.setCounterSkip() if meta['info']['counter_skip']==True else self.unsetCounterSkip()
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

        super()._check_settings()

        if self.sequence_id and ( not self.file_id or not self.label_id ) :
            raise MuDBException( f"Settings check failed: 'sequence_id' is defnied while 'label_id' or 'file_id' are not" )

        if self.label_id and not self.file_id:
            raise MuDBException( f"Settings check failed: 'label_id' is defined but not 'file_id'. Cannot iterate over all files" )
        

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

        # Start run thread
        self._async_transfer_thread = threading.Thread( target= self.__run_thread )
        self._async_transfer_thread.start()
        

    def __run_thread( self ):

        url = f"{self.dbhost}/sourcefile/{str(self.file_id)}/upload/"

        try:
            with requests.get(url, stream=True) as response:
                # Check if the request was successful
                response.raise_for_status()

                # Open the local file in binary write mode
                for chunk in response.iter_content(chunk_size=self.frame_length):
                    # Process binary data by pushing them in the queue 
                    # Thanks to the queue, data are not lost if the reading process is too slow compared to the filling speed.
                    # However, the queue introduces a latency that can become problematic.
                    # If the user accepts the loss of data, it is possible to limit the size of the queue.
                    # In this case, once the size is reached, each new entry induces the deletion of the oldest one.
                    self.signal_q.put( chunk )

        except MuDBException as e:
            # Known exception:
            log.info( f" .Listening loop was stopped: {e}" )
        except Exception as e:
            # Uknnown exception:
            log.error( f" Listening loop stopped due to network error exception ({type(e).__name__}): {e}" )