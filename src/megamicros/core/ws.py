# megamicros.core.ws.py base class for antenna connected to a remote antenna server
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


""" Provide the class for antenna with MEMs signals extracted from a remote antenna

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import numpy as np
import websockets
import json
import asyncio
import threading
import time

from megamicros.log import log
from megamicros.exception import MuException
import megamicros.core.base as base


DEFAULT_MBS_SERVER_ADDRESS      = 'localhost'
DEFAULT_MBS_SERVER_PORT         = 9002
DEFAULT_H5_PASS_THROUGH         = False                     # whether server performs H5 saving or client 
DEFAULT_BACKGROUND_MODE         = False                     # whether background execution mode in on (True) or off (False)


# Megamicros dependances (should be removed)
DEFAULT_MEMS_INIT_WAIT          = 1000                      # Mems initializing time in milliseconds


# =============================================================================
# Exception dedicaced to Megamicros websocket systems
# =============================================================================

class MuWSException( MuException ):
    """Exception base class for Megamicros Winsokets systems """
    
    def __init__( self, message: str="" ):
        super().__init__( message )



# =============================================================================
# The MemsArrayWS base class
# =============================================================================


class MemsArrayWS( base.MemsArray ):
    """ MEMs array class with input stream connected to a remote megamicros server.

    """

    __server_host: str = DEFAULT_MBS_SERVER_ADDRESS
    __server_port: int = DEFAULT_MBS_SERVER_PORT
    __flag_success: bool = None
    __background_mode: bool = DEFAULT_BACKGROUND_MODE

    # H5 attributes
    __h5_pass_through: bool = DEFAULT_H5_PASS_THROUGH


    @property
    def h5_pass_through( self ) -> bool:
        """ Get the H5 compression local (False) or remote (True) flag """
        return self.__h5_pass_through
    
    @property
    def background_mode( self ) -> bool:
        """ Check if bacground mode is on (True) or off (False) """
        return self.__background_mode


    def setBackgroundMode( self ) -> None :
        """ Set the execution background mode on """
        self.__background_mode = True


    def unsetBackgroundMode( self ) -> None :
        """ Set the execution background mode off """
        self.__background_mode = False


    def setH5RecordingPassthrough( self ) -> None :
        """ Set the H5 recording passthrough mode on """
        self.__h5_pass_through = True


    def unsetH5RecordingPassthrough( self ) -> None :
        """ Set the H5 recording passthrough mode off """
        self.__h5_pass_through = False


    def __init__( self, host: str, port: int=DEFAULT_MBS_SERVER_PORT ):
        """ Connect the antenna input stream to a remote antenna 

        The connection to the remote server is verified. If the server is not available, an exception is raised. 

        Parameters
        ----------
        host: str
            The remote host address
        port: int, optional
            The remote port (default is 9002)
        """

        self.__server_host = host
        self.__server_port = port

        # check connection to the server
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  
            # There is no current event loop...
            loop = None

        if loop and loop.is_running():
            # One cannot add a second asyncio loop in an existant loop (in a Jupyterlab loop for example)
            # Next lines create a task with a return callback with no more execution after.
            #
            log.info( ' .Async event loop already running. Adding coroutine to the event loop...' )
            task = loop.create_task( self.__try_connect() )
            task.add_done_callback( self.__try_connect_check_error )
        else:
            asyncio.run( self.__try_connect() )

            if self.__flag_success == False:
                log.error( f"Unable to connect to remote server {self.__server_host}:{self.__server_port}" )
                raise MuWSException( f"Unable to connect to remote server {self.__server_host}:{self.__server_port}" )
            else:
                log.info( ' .Starting MegamicrosWS device [ready]' ) 
                return

        # Next lines are never seen...


    def __try_connect_check_error( self, t ):

        if t.result() == True:
            log.info( ' .Starting MegamicrosWS device [ready]' ) 
        else:
            log.error( f"Unable to connect to remote server {self.__server_host}:{self.__server_port}" )
        

    async def __try_connect( self ) -> bool :
        """ Open a connection to the server then get server settings before closing """

        self.__flag_success = False
        try:
            log.info( f" .Try connecting to ws://{self.__server_host}:{str(self.__server_port)}...") 

            async with websockets.connect( f"ws://{self.__server_host}:{str(self.__server_port)}" ) as websocket:
                # check server response
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Connection to server failed with error: {error}" )
                else:
                    log.info( f" .Received positive answer from server" )

                # get remote settings and set them
                log.info( f" .Getting settings values from remote receiver..." )
                await websocket.send( json.dumps( {'request': 'settings'} ) )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Unable to get settings from server: {error}" )
                log.info( f" .Received settings from server [ok]" )

                # init object with server response
                settings = response["response"]
                #self.setSamplingFrequency( settings['sampling_frequency'] )
                self.setAvailableMems( available_mems_number=len( settings['available_mems'] ) )
                #self.setCounter() if settings['counter']==True else self.unsetCounter()
                #self.setCounterSkip() if settings['counter_skip']==True else self.unsetCounterSkip()
                self.setAvailableAnalogs( available_analogs_number=len( settings['available_analogs'] ) )
                
        except websockets.exceptions.WebSocketException as e:
            log.error( f"Server connection failed due to websocket failure: {e}" )
            return False

        except Exception as e:
            log.error( f"Server connection failed: {e}" )
            return False
        
        self.__flag_success = True
        return True


    def __check_mbs_error( self, response ) -> bool|str :
        """ Check the response from MBS server concerning the presence of errors 
        
        Parameters
        ----------
        response: dict
            Response given by the remote server after its transformation in Python object
        
        Returns
        -------
        message: str|bool 
            string error message received from server or False if no message
        """

        if response['type'] == 'status' and response['response'] == 'error':
            return response['message'] if 'message' in response else 'Unknown error'
        else:
            return False


    def run( self, *args, **kwargs ) :
        """ The main run method that run the remote antenna """

        log.info( f" .Starting run execution" )

        # Check direct args
        if len( args ) != 0:
            raise MuWSException( "Direct arguments are not accepted for run() method" )
                
        # Set base settings      
        try:  
            log.info( f" .Install run settings" )

            if 'mems' in kwargs:
                self.setActiveMems( kwargs['mems'] )

            if 'analogs' in kwargs:
                self.setActiveAnalogs( kwargs['analogs'] )

            if 'counter' in kwargs:
                self.setCounter() if kwargs['counter'] is True else self.unsetCounter()

            if 'counter_skip' in kwargs:
                self.setCounterSkip() if kwargs['counter_skip'] is True else self.unsetCounterSkip()

            if 'status' in kwargs:
                self.setStatus() if kwargs['status'] is True else self.unsetStatus()

            if 'sampling_frequency' in kwargs:
                self.setSamplingFrequency( kwargs['sampling_frequency'] )

            if 'datatype' in kwargs:
                if kwargs['datatype'] is str:
                    try:
                        self.setDatatype( getattr( base.MemsArray.Datatype, kwargs['datatype'] ) )
                    except:
                        raise MuWSException( f"Unknown output datatype '{kwargs['datatype']}'" )
                elif kwargs['datatype'] is int:
                    try:
                        self.setDatatype( base.MemsArray.Datatype( kwargs['datatype'] ) )
                    except:
                        raise MuWSException( f"Unknown output datatype code '{kwargs['datatype']}'" )                    
                elif kwargs['datatype'] is base.MemsArray.Datatype :
                    self.setDatatype( kwargs['datatype'] )

            if 'duration' in kwargs:
                self.setDuration( kwargs['duration'] )

            if 'frame_length' in kwargs:
                self.setFrameLength( kwargs['frame_length'] )

            if 'h5_recording' in kwargs:
                self.setH5Recording() if kwargs['h5_recording'] else self.unsetH5Recording()

            if 'h5_pass_through' in kwargs:
                self.setH5RecordingPassthrough() if kwargs['h5_pass_through'] else self.unsetH5RecordingPassthrough()
        
            if 'h5_rootdir' in kwargs:
                self.setH5Rootdir( kwargs['h5_rootdir'] )

            if 'h5_dataset_duration' in kwargs:
                self.setH5DatasetDuration( kwargs['h5_dataset_duration'] )

            if 'h5_file_duration' in kwargs:
                self.setH5FileDuration( kwargs['h5_file_duration'] )

            if 'h5_compressing' in kwargs:
                if kwargs['h5_compressing'] == True:
                    algo = kwargs['h5_compression_algo'] if 'h5_compression_algo' in kwargs else base.DEFAULT_H5_COMPRESSION_ALGO
                    level =  kwargs['h5_gzip_level'] if 'h5_gzip_level' in kwargs else base.DEFAULT_H5_GZIP_LEVEL
                    self.setH5Compressing( algo=algo, level=level )
                else:
                    self.unsetH5Compressing()

            if 'background_mode' in kwargs:
                self.setBackgroundMode() if kwargs['background_mode']== True else self.unsetBackgroundMode()

                    
        except MuException as e:
            raise MuWSException( f"Run failed on settings: {e}")
            
        # Check for running
        try:
            log.info( f" .Pre-execution checks" )

            if self.mems is None or len( self.mems )==0:
                raise MuWSException( f"No activated MEMs" )
            
            if self.counter is None:
                log.info( f" .Counter was not set -> set to False" )
                self.unsetCounter()
            
            if self.counter_skip is None:
                log.info( f" .Counter skipping not set -> set to False" )
                self.unsetCounterSkip()       

            if self.status is None:
                log.info( f" .Status was not set -> set to False" )
                self.unsetStatus()         

            if self.sampling_frequency is None:
                raise MuWSException( f"No sampling frequency set" )

            if self.duration is None:
                raise MuWSException( f"No running duration set" )
            
            if self.datatype is base.MemsArray.Datatype.unknown:
                raise MuWSException( f"No datatype set" )
            
            if self.frame_length is None:
                log.info( f" .Frame length not set -> set to default" )
                self.setFrameLength( base.DEFAULT_FRAME_LENGTH )

            if self.h5_recording and self.h5_pass_through and not self.background_mode:
                raise MuWSException( f"Remote H5 recording is only available on background execution mode. Please set the background mode on" )

        except MuException as e:
            raise MuWSException( f"Run check failed: {e}")

        # verbose
        if self.duration == 0:
            log.info( f" .Run infinite loop (duration=0)" )
        else :
            log.info( f" .Perform a {self.duration}s run loop" )
        
        if self.callback_fn is not None:
            log.info( f" .Data transfer using the user callback function" )

        if self.h5_recording:
            if self.h5_pass_through:
                log.info( f" .Remote H5 recording by server on (pass-through mode)" )
            else:
                log.info( f" .Local H5 recording on" )
        else:
            log.info( f" .H5 recording off" )

        if self.background_mode:
            log.info( f" .Background execution mode on" )
        else:
            log.info( f" .Background execution mode off" )

        if self.sync:
            log.info( " .Synchronous execution mode on" )
        else:
            log.info( " .Asynchronous execution mode on" )

        # Start run thread
        self._async_transfer_thread = threading.Thread( target= self.run_thread )
        self._async_transfer_thread.start()

        # Wait until the thread terminates in sync mode:
        #if self.sync:
        self._async_transfer_thread.join()


    def run_thread( self ):
        try:
            log.info( " .Run thread execution started" )
            asyncio.run( self.__run() )
        except MuWSException as e:
            log.info( f" .Run thread halted on error: {e}" )
            self._async_transfer_thread_exception = e


    async def __run( self ):
        """ Perform a run execution on Megamicros remote receiver """

        log.info( f" .Connecting to remote host {self.__server_host}:{str(self.__server_port)}..." )
        async with websockets.connect( f"ws://{self.__server_host}:{str(self.__server_port)}" ) as websocket:
            log.info( " .Connected" )
            response = json.loads( await websocket.recv() )
            error = self.__check_mbs_error( response )
            if error:
                raise MuWSException( f"Connection to server failed: {error}" )        

            # send settings to server
            # Note that 'clockdiv', and 'mems_init_wait' should be set by the remote server since they are Megamicros parameters 
            settings = {
                'mems': self.mems,
                'analogs': self.analogs,
                'counter': self.counter,
                'counter_skip': self.counter_skip,
                'status': self.status,
                'clockdiv': int( 500000 // self.sampling_frequency ) - 1,
                'sampling_frequency': self.sampling_frequency,
                'datatype': 'int32' if self.datatype==base.MemsArray.Datatype.int32 or self.datatype==base.MemsArray.Datatype.bint32 else 'float32',
                'mems_init_wait': DEFAULT_MEMS_INIT_WAIT,
                'duration': self.duration
            }

            # Add H5 settings if H5_pass_through mode is on:
            if self.h5_recording and self.h5_pass_through:
                settings.update( {
                    'h5_recording': True,
                    'h5_rootdir': self.h5_rootdir,
                    'h5_dataset_duration': self.h5_dataset_duration,
                    'h5_file_duration': self.h5_file_duration,
                    'h5_compressing': self.h5_compressing,
                    'h5_compression_algo': self.h5_compression_algo,
                    'h5_gzip_level': self.h5_gzip_level
                } )

            if self.background_mode:
                # Play in background mode -> no more communicatiobn with the server
                run_command = {'request': 'run', 'settings': settings, 'origin': 'background'}
            else:
                run_command = {'request': 'run', 'settings': settings}

            # send run command to server:
            log.info( f" .Send running job command" )        
            await websocket.send( json.dumps( run_command ) )
            response = json.loads( await websocket.recv() )
            error = self.__check_mbs_error( response )
            if error:
                raise MuWSException( f"Run command failed on remote server: {error}" )

            # Start listening unless background mode is ON
            if not self.background_mode:
                log.info( " .Run command accepted by server" )
                # Start server listening 
                await self.__remote_run( websocket )

                # Stop H5 recording if not yet stopped
                # The following should be done at the base level :
                """
                if self.h5_recording and not self.__h5_pass_through and self._h5_started:
                    self.h5_close()
                
                if self.__transfer_index != 0:
                    log.info( f" .Total transfers received: {self.__transfer_index}. Total lost: {self.__transfer_lost} ({self.__transfer_lost*100/self.__transfer_index:.2f}%)")
                    log.info( f" .Total elapsed time: {self.__elapsed_time:.2f} s ({self.__elapsed_time*1000/self.__transfer_index:.2f} ms / frame)" )
                    log.info( f" .Mean completion time: {self.__mean_completion_time*1000:.2f} ms")
                    log.info( f" .Data rate estimation: {self.transfer_rate/1000:.2f} Ko/s (real time is: {self.sampling_frequency*4*self.channels_number/1000:.2f} Ko/s)" )
                else:
                    log.info( f" .No transfers received" )
                """
            else:
                log.info( " .Run command accepted by server in background mode" )

                # wait 2 seconds before halting 
                time.sleep( 2 )
                log.info( " .Halt connection with server and exit" )


    async def __remote_run( self, websocket ):
        """ Remote run command in foreground mode 
        
        Get data from server and populate the internal data queue - or call the user callback function 

        Parameters
        ----------
        websocket: 
            The open connection websocket
        """



