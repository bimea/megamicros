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
from megamicros.log import log
from megamicros.exception import MuException
import megamicros.core.base as base


DEFAULT_REMOTE_PORT = 9002
DEFAULT_REMOTE_ADDRESS = 'localhost'

# =============================================================================
# Exception dedicaced to Megamicros websocket systems
# =============================================================================

class MuWSException( MuException ):
    """Exception base class for Megamicros Winsokets systems """



# =============================================================================
# The MemsArrayWS base class
# =============================================================================


class MemsArrayWS( base.MemsArray ):
    """ MEMs array class with input stream connected to a remote megamicros server.

    """

    __remote_host: str = DEFAULT_REMOTE_ADDRESS
    __remote_port: int = DEFAULT_REMOTE_PORT

    def __init__( self, host: str, port: int=DEFAULT_REMOTE_PORT ):
        """ Connect the antenna input stream to a remote antenna 

        The connection to the remote server is verified. If the server is not available, an exception is raised. 

        Parameters
        ----------
        host: str
            The remote host address
        port: int, optional
            The remote port (default is 9002)
        """

        





# >>>>>>>>>>>>>>>>>>


    __source: np.ndarray|None = None
    __available_frames_number: int|None = None

    def __init__( self, dbhost: str, login: str, email: str, passwd: str, label_id:int, file_id: int|None=None, sequence_id: int|None=None, preload: bool=False ) -> None :
        """ Connect the antenna input stream to a labelized database 

        The connection to the database is verified. If the database is not available, an exception is raised. 
        If the `preload` parameter is set to `True`, the antenna signals are uploaded and buffered once from this stage. 
        
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
        label_id: int
            signal label
        file_id: int, optional
            file identifier. Default is all files containing the labelized signals
        sequence_id: int, optional
            sequence identifier. Default is all the sequences located in the file
        preload: bool, optional
            Whether to load the whool sequence once or not. Default is `False` 
        """


        if file_id is None:
            raise MuException( f"Sorry, working on several files is not yet implemented" )
        
        # test connection to database
        if preload == False:
            try:
                with AidbSession( dbhost=dbhost, login=login, email=email, password=passwd ) as session:
                    # get meta data
                    meta = session.get_sourcefile( file_id )
                    self.setSamplingFrequency( meta['info']['sampling_frequency'] )
                    self.setAvailableMems( len( meta['info']['mems'] ) )
                    self.setCounter() if meta['info']['counter']==True else self.unsetCounter()
                    self.setCounterSkip() if meta['info']['counter_skip']==True else self.unsetCounterSkip()
                    self.setAvailableAnalogs( len( meta['info']['analogs'] ) )

            except MuException as e:
                raise( f"Connection to database {dbhost} failed: {e}" )
            
        # test connection and get signals from database
        else:
            try:
                with AidbSession( dbhost=dbhost, login=login, email=email, password=passwd ) as session:
                    # get meta data
                    meta = session.get_sourcefile( file_id )
                    self.setSamplingFrequency( meta['info']['sampling_frequency'] )
                    self.setAvailableMems( len( meta['info']['mems'] ) )
                    self.setCounter() if meta['info']['counter']==True else self.unsetCounter()
                    self.setCounterSkip() if meta['info']['counter_skip']==True else self.unsetCounterSkip()
                    self.setAvailableAnalogs( len( meta['info']['analogs'] ) )

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

    def __iter__( self ) :
        """ Init iterations over the antenna data """

        if self.__source is None:
            raise MuException( f"No input source stream. Cannot iterate" )
        self.__it = 0
        return self

    def __next__( self ) -> np.ndarray|None :
        """ next iteration over the antenna data 

        """

        self.__it += 1

        if self.__counter is None or ( self.__counter == False or ( self.__counter == True and self.__counter_skip==True ) ):
            # send data without counter state
            return np.random.rand( self.__frame_length, self.mems_number ) * 2 - 1
        else:
            # add counter values
            counter = np.array( [[i for i in range(self.__frame_length)]] ).T + self.__it * self.__frame_length
            return np.concatenate( ( counter, ( np.random.rand( self.__frame_length, self.mems_number ) * 2 - 1 ) ), axis=1 )