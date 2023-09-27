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

from megamicros.log import log
from megamicros.exception import MuException
import megamicros.core.base as base


DEFAULT_MBS_SERVER_ADDRESS = 'localhost'
DEFAULT_MBS_SERVER_PORT = 9002


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
        #asyncio.run( self.__try_connect() 

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
                self.setSamplingFrequency( settings['sampling_frequency'] )
                self.setAvailableMems( len( settings['available_mems'] ) )
                self.setCounter() if settings['counter']==True else self.unsetCounter()
                self.setCounterSkip() if settings['counter_skip']==True else self.unsetCounterSkip()
                self.setAvailableAnalogs( len( settings['available_analogs'] ) )


                
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

