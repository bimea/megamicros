# megamicros.core.cb.py base class for antenna connected to external callback function
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


""" Provide the class for antenna with MEMs signals extracted by an external callback function 

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.bimea.io
"""

import numpy as np
import threading
from time import sleep, time

from megamicros.log import log
from megamicros.exception import MuException
from .base import MemsArray, DEFAULT_FRAME_LENGTH

DB_PROCESSING_DELAY_RATE				= 2/10						# computing delay rate relative to transfer buffer duration (adjusted for real time operation)


# =============================================================================
# Exception dedicaced to Megamicros NP systems
# =============================================================================

class MuCBException( MuException ):
    """Exception base class for Megamicros CB systems """


# =============================================================================
# The MemsArrayCB base class
# =============================================================================

class MemsArrayCB( MemsArray ):
    """ MEMs array class with input stream connected to an external callback function as input.

    As for NP antenna, we do not have any informations about the antenna that is used to play the data. 
    So we have to set the antenna settings manually before running it.
    A MemsArrayCB object is supposed to work well with callback which deliver binary data bint32 or bfloat32 or nupy array data int32 or float32.

    Counter and status channels can be present in the input data.
    """

    __input: np.ndarray = None
    __input_index: int = 0
    __input_dtype: np.dtype = None
    __user_in_callback = None
    __user_in_callback_args = None
    __input_dtype: np.dtype = None


    def __init__( self, user_in_callback, user_in_callback_args, **kwargs ) -> None :
        """ Connect the antenna input stream to the user callback
        
        Parameters
        ----------
        user_in_callback: callback
            The user callback function that will deliver the input data
        user_in_callback_args: array
            The arguments that will be provided to the user callback function
        """

        # Init base class
        super().__init__( kwargs=kwargs )

        # Set NP settings
        if len( kwargs ) > 0:
            self._set_settings( [], kwargs )

        self.__user_in_callback = user_in_callback
        self.__user_in_callback_args = user_in_callback_args

        log.info( f" .MemsArrayCB object created" )


    def setInCallback( self, callback: any ) -> None :
        """ Set the user callback function 
        
        Parameters
        ----------
        callback: any
            The user callback function that will deliver the input data
        """

        self.__user_in_callback = callback


    def setInCallbackArgs( self, args: any ) -> None :
        """ Set the user callback arguments 
        
        Parameters
        ----------
        args: any
            The arguments that will be provided to the user callback function
        """

        self.__user_in_callback_args = args


    def _set_settings( self, args, kwargs: dict ) -> None :
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
            raise MuCBException( "Direct arguments are not accepted for run() method" )
        
        try:  
            log.info( f" .Install MemsArrayCB settings" )

            # Set settings
            keys_to_remove = []
            for key, value in kwargs.items():   
                if key == "user_in_callback":
                    self.setInCallback( value )
                    keys_to_remove.append( key )

                elif key == "user_in_callback_args":
                    self.setInCallbackArgs( value )
                    keys_to_remove.append( key )
            
            if len( keys_to_remove ) > 0:
                for key in keys_to_remove:
                    del kwargs[key]

            # Set parent settings
            super()._set_settings( args, kwargs )

                    
        except Exception as e:
            raise MuCBException( f"Settings install failed: {e}")


    def _check_settings( self ) -> None :
        """ Check settings values for MemsArrayCB """

        log.info( f" .Pre-execution checks for MemsArray.run()" )
        super()._check_settings()

        # Here we are
        log.info( f" .Pre-execution checks for MemsArrayCB.run()" )

        # We have to control the input array shape with the settings
        if self.__user_in_callback is None:
            raise MuCBException( f"No input callback given for MemsArrayCB object" )

        if self.__user_in_callback_args is None:
            raise MuCBException( f"No input callback arguments given for MemsArrayCB object" )
        

    def run( self, *args, **kwargs ) :
        """ The main run method that run over the input data """

        if len( args ) > 0:
            raise MuCBException( f"Run() method does not accept direct arguments" )
        
        log.info( f" .Starting run execution" )
                
        # Set all settings
        try:
            self._set_settings( [], kwargs=kwargs )

        except Exception as e:
            raise MuCBException( f"Cannot run: settings loading failed ({type(e).__name__}): {e}" )
        
        # Check settings values
        try:
            self._check_settings()

        except Exception as e:
            raise MuCBException( f"Unable to execute run: control failure  ({type(e).__name__}): {e}" )

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
        """ Run thread for the MemsArrayCB object """

        # Set the mask transfert
        mask = list( np.isin( self.available_mems, self.mems ) )

        print( f"mask: {mask}")

        # Add analog channels if any
        if self.available_analogs_number > 0 and self.analogs_number > 0:
            mask = mask + list( np.isin( self.available_analogs, self.analogs ) )

        # Add or remove counter if counter is in input stream
        if self.counter:
            # User does not want to get counter
            if self.counter_skip:
                mask = [False] + mask
            # User want the counter
            else:
                mask = [True] + mask

        # Add or remove status if status is in input stream
        if self.status:
            mask = mask + [True]

        print( f"mask(2): {mask}")

        # Total channels number and masking flag
        channels_number = sum( mask )
        masking = channels_number != len(mask)

        print( f"masking: {masking}")

        initial_time: float = time()
        elapsed_time: float = 0
        transfer_index = 0                                          

        try:
            # Get first chunk of data from input callback
            log.info( f" .Executing user callback function..." )

            # Get first chunk of data from input callback
        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            
            self.__input = self.__user_in_callback( *self.__user_in_callback_args )
            self.__input_dtype = self.__input.dtype

            frame_length, channels_number = self.__input.shape
            if frame_length != self.frame_length:
                log.warning( f" .Input data frame length ({frame_length}) does not match the requested frame length ({self.frame_length})" )
                log.info( f" .Change the frame length to {frame_length}" )
                self.setFrameLength( frame_length )
            
            if channels_number != self.channels_number:
                if not self.status and channels_number == self.channels_number + 1:
                    log.warning( f" .Input data channels number ({channels_number}) does not match the requested channels number ({self.channels_number})" )
                    log.info( f" .Add the status as available channel. Please verify that I am right !" )
                    mask = mask + [False]
                else:
                    raise MuCBException( f"Input data channels number ({channels_number}) does not match the requested channels number ({self.channels_number})" )

            log.info( f" .Input data shape: {self.__input.shape} ({self.frame_length} data x {self.channels_number})" )

            transfert_start_time = time()
            frame_duration = self.frame_length / self.sampling_frequency
            processing_delay = frame_duration * DB_PROCESSING_DELAY_RATE
            self.setRunningFlag( True )
            while self.running:
                # Process binary data by pushing them in the queue 
                # Thanks to the queue, data are not lost if the reading process is too slow compared to the filling speed.
                # However, the queue introduces a latency that can become problematic.
                # If the user accepts the loss of data, it is possible to limit the size of the queue.
                # In this case, once the size is reached, each new entry induces the deletion of the oldest one.

                # No more data to process -> end of loop
                if self.__input.shape[0] != self.frame_length:
                    self.setRunningFlag( False )
                    break

                # Get chunk of data from input numpy array and select channels
                if masking:
                    chunk = self.__input[:,mask]
                else:
                    chunk = self.__input

                # Push data in the queue after conversion
                self.queue.put( self.__run_process_data( chunk ) )
                self.__input_index += self.frame_length
                transfer_index += 1

                # Loop on input array
                if self.__input_index + self.frame_length >= self.__input.shape[0]:
                    self.__input_index = 0
                    self.setRunningFlag( False )

                # Wait for the next transfert
                #if ( time() - transfert_start_time ) < frame_duration - processing_delay:
                #    sleep( frame_duration-time()+transfert_start_time-processing_delay )

                # Next transfert start time
                transfert_start_time = time()
                self.__input = self.__user_in_callback( *self.__user_in_callback_args )

            log.info( " .Running stopped: normal thread termination" )

        except MuCBException as e:
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
