# megamicros.core.np.py base class for antenna connected to a numpy array input stream
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


""" Provide the class for antenna with MEMs signals extracted from a numpy array 

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import numpy as np
import threading
import requests
from time import sleep, time

from megamicros_tools.log import log
from megamicros_tools.exception import MuException
from .base import MemsArray, DEFAULT_FRAME_LENGTH

DB_PROCESSING_DELAY_RATE				= 2/10						# computing delay rate relative to transfer buffer duration (adjusted for real time operation)


# =============================================================================
# Exception dedicaced to Megamicros NP systems
# =============================================================================

class MuNPException( MuException ):
    """Exception base class for Megamicros NP systems """


# =============================================================================
# The MemsArrayNP base class
# =============================================================================

class MemsArrayNP( MemsArray ):
    """ MEMs array class with input stream connected to a numpy array given as input.

    The MemsArrayNP class is a base class for antenna with MEMs signals extracted from a numpy array.
    We do not have any informations about the antenna that was used to record the data. So we have to set the antenna settings manually before using data.
    A MemsArrayNp object is supposed to work well with numpy array of int32 or float32 data type under the condition that settings are in correpondance with the data.

    Counter and status channels are not supposed to be in the input data. Those channels will be added to the output stream is the user requests them.
    """

    __input: np.ndarray = None
    __input_index: int = 0
    __input_dtype: np.dtype = None


    def __init__( self, input: np.ndarray, **kwargs ) -> None :
        """ Connect the antenna input stream to a numpy input array
        
        Parameters
        ----------
        input: np.ndarray
            input numpy array
        """

        # Init base class
        super().__init__( kwargs=kwargs )

        # Set NP settings
        if len( kwargs ) > 0:
            self._set_settings( [], kwargs )

        self.__input = input
        self.__input_index = 0
        self.__input_dtype = input.dtype

        log.info( f" .MemsArrayNP object created with input array {input.shape[0]} data x {input.shape[1]} channels" )

    def setAvailableMems( self, available_mems: int|tuple|list|np.ndarray ) -> None :
        """ Overload the parent `setAvailableMems()` method for control with __input data
        """

        super().setAvailableMems( available_mems )

        channels_number = self.available_mems_number + self.available_analogs_number
        if channels_number > self.__input.shape[1]:
            raise MuNPException( f"Available channels number ({channels_number}) is greater than the number of channels in the input array ({self.__input.shape[1]})" )


    def setAvailableAnalogs( self, available_analogs: int|tuple|list|np.ndarray ) -> None :
        """ Overload the parent `setAvailableAnalogs()` method for control with __input data
        """

        super().setAvailableAnalogs( available_analogs )

        channels_number = self.available_mems_number + self.available_analogs_number
        if channels_number > self.__input.shape[1]:
            raise MuNPException( f"Available channels number ({channels_number}) is greater than the number of channels in the input array ({self.__input.shape[1]})" )



    def _set_settings( self, args, kwargs ) -> None :
        """ Set settings for MemsArrayNP objects 
        
        Parameters
        ----------
        args: array
            direct arguments of the run function
        args: array
            named arguments of the run function
        """

        # Check direct args
        if len( args ) > 0:
            raise MuNPException( "Direct arguments are not accepted for run() method" )
        
        try:  
            log.info( f" .Install MemsArrayNP settings" )

            # Set settings
            keys_to_remove = []
            for key, value in kwargs.items():   
                if key == "available_mems_number":
                    self.setAvailableMems( value )
                    keys_to_remove.append( key )

                elif key == "available_analogs_number":
                    self.setAvailableAnalogs( value )
                    keys_to_remove.append( key )
            
            if len( keys_to_remove ) > 0:
                for key in keys_to_remove:
                    del kwargs[key]

            # Set parent settings
            super()._set_settings( args, kwargs )
                    
        except Exception as e:
            raise MuNPException( f"Settings install failed: {e}")


    def _check_settings( self ) -> None :
        """ Check settings values for MemsArrayDB """

        # We cannot call the parent check_settings() method as it is not compatible for DB
        log.info( f" .Pre-execution checks for MemsArray.run()" )
        super()._check_settings()

        # Here we are
        log.info( f" .Pre-execution checks for MemsArrayNP.run()" )

        # We have to control the input array shape with the settings
        if self.__input is None:
            raise MuNPException( f"No input array as stream for MemsArrayNP object" )

        channels_number = self.available_mems_number + self.available_analogs_number
        if channels_number > self.__input.shape[1]:
            raise MuNPException( f"Available channels number ({channels_number}) is greater than the number of channels in the input array ({self.__input.shape[1]})" )



    def run( self, *args, **kwargs ) :
        """ The main run method that run over the input data """

        if len( args ) > 0:
            raise MuNPException( f"Run() method does not accept direct arguments" )
        
        log.info( f" .Starting run execution" )
                
        # Set all settings
        try:
            self._set_settings( [], kwargs=kwargs )

        except Exception as e:
            raise MuNPException( f"Cannot run: settings loading failed ({type(e).__name__}): {e}" )
        
        # Check settings values
        try:
            self._check_settings()

        except Exception as e:
            raise MuNPException( f"Unable to execute run: control failure  ({type(e).__name__}): {e}" )

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

        # Start the timer if a limited execution time is requested 
        if self.duration > 0:
            self._thread_timer = threading.Timer( self.duration, self._run_endding )
            self._thread_timer_flag = True
            self._thread_timer.start()

        # Start run thread
        self._async_transfer_thread = threading.Thread( target= self.__run_thread )
        self._async_transfer_thread.start()
        

    def __run_thread( self ):
        """ Run thread for the MemsArrayNP object """

        # Set the mask transfert
        mask = list( np.isin( self.available_mems, self.mems ) )

        print( f"mask: {mask}")

        # Add analog channels if any
        if self.available_analogs_number > 0 and self.analogs_number > 0:
            mask = mask + list( np.isin( self.available_analogs, self.analogs ) )

        print( f"mask(2): {mask}")

        # Total channels number and masking flag
        channels_number = sum( mask )
        masking = channels_number != len(mask)

        print( f"masking: {masking}")

        initial_time: float = time()
        elapsed_time: float = 0
        transfer_index = 0                                          

        print( f"ok")

        try:
            # Get chunk of data from input numpy array
            log.info( f" .Reading input stream {self.__input.shape[0]} x {self.__input.shape[1]}" )

            print( f"chunk: {self.__input.shape}")

            transfert_start_time = time()
            frame_duration = self.frame_length / self.sampling_frequency
            processing_delay = frame_duration * DB_PROCESSING_DELAY_RATE
            self.setRunningFlag( True )
            while self.running:
                # Get chunk of data from input numpy array
                
                print( f"transfer_index: {transfer_index}")

                chunk = self.__input[ self.__input_index : self.__input_index + self.frame_length, : ]

                print( f"chunk: {chunk.shape}")

                # Process binary data by pushing them in the queue 
                # Thanks to the queue, data are not lost if the reading process is too slow compared to the filling speed.
                # However, the queue introduces a latency that can become problematic.
                # If the user accepts the loss of data, it is possible to limit the size of the queue.
                # In this case, once the size is reached, each new entry induces the deletion of the oldest one.

                # Select channels
                if masking:
                    chunk = chunk[mask,:]

                # Add counter values
                if self.counter and not self.counter_skip:
                    counter_values = np.arange( self.__input_index, self.__input_index + self.frame_length )
                    chunk = np.insert( chunk, 0, counter_values, axis=1 ),

                # Add 0 as status values 
                if self.status:
                    status_values = np.zeros( ( self.frame_length, 1 ) )
                    chunk = np.append( chunk, status_values, axis=1 )

                # Push data in the queue after conversion
                self.queue.put( self.__run_process_data( chunk ) )
                self.__input_index += self.frame_length
                transfer_index += 1

                # Loop on input array
                if self.__input_index + self.frame_length >= self.__input.shape[0]:
                    self.__input_index = 0
                    self.setRunningFlag( False )

                # Wait for the next transfert
                if ( time() - transfert_start_time ) < frame_duration - processing_delay:
                    sleep( frame_duration-time()+transfert_start_time-processing_delay )

                # Next transfert start time
                transfert_start_time = time()

            log.info( " .Running stopped: normal thread termination" )

        except MuNPException as e:
            # Known exception:
            log.info( f" .Listening loop was stopped: {e}" )
        except Exception as e:
            # Uknnown exception:
            log.error( f" Listening loop stopped due to error exception ({type(e).__name__}): {e}" )

        # Compute elapsed time
        elapsed_time = time() - initial_time
        if self.duration == 0:
            log.info( f" .Elapsed time: {elapsed_time} s")
        else:
            log.info( f" .Elapsed time: {elapsed_time}s (expected duration was: {self.duration} s)")

        log.info( f" .Proceeded to {transfer_index} transfers" )
        log.info( " .Run completed" )


    def __run_process_data( self, data: np.ndarray ) -> any :
        """ Process data in the right format before sending it to the queue 
        
        Notice that the antenna 'frame_length' value can cut signal into non integer parts number.
        As a result, last chunk can be shorter with less than 'frame_length' samples

        Parameter
        ---------
        data: np.ndarray
            input data. May be flot32, float64 or int32 numpy array
        Return: bytes|np.ndarray
            output data in the format requested by the user
        """

        # User wants data as binary buffer of int32 
        if self.datatype == self.Datatype.bint32:
            if self.__input_dtype == np.float64 or self.__input_dtype == np.float32:
                data = ( data / self.sensibility ).astype( np.int32 )
            data = np.ndarray.tobytes( data )
        
        # User wants data as numpy array of int32 
        elif self.datatype == self.Datatype.int32:
            if self.__input_dtype == np.float64 or self.__input_dtype == np.float32:
                data = ( data / self.sensibility ).astype( np.int32 )

        # User wants data as numpy array of float32 
        elif self.datatype == self.Datatype.float32:
            if self.__input_dtype == np.float64:
                data = data.astype( np.float32 )
            elif self.__input_dtype == np.int32:
                data = ( data * self.sensibility ).astype( np.float32 )

        # User wants data as binary buffer of float32
        elif self.datatype == self.Datatype.bfloat32:
            if self.__input_dtype == np.float64:
                data = data.astype( np.float32 )
            elif self.__input_dtype == np.int32:
                data = ( data * self.sensibility ).astype( np.float32 )
            data = np.ndarray.tobytes( data )
            
        return data
