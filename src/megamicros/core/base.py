# megamicros.core.base.py
#
# ® Copyright 2024-2025 Bimea
# Author: bruno.gas@bimea.io
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
This module defines the base class for all microphone arrays in the Megamicros library.

Features:
    - Management of available and active microphones
    - Configuration of sampling frequency, data type, frame length, and acquisition duration
    - Support for counter activation and skipping in output streams
    - H5 local recording flag

Examples:
    Basic usage::

        from megamicros import log
        from megamicros.base import MemsArray

        antenna = MemsArray()
        antenna.run(
            mems=(0,1,2,3),
            sampling_frequency=44100,
            duration=60,
            frame_length=1024,
            datatype='int32'
        )
        antenna.wait()

    Advanced usage::

        See the Notebooks for advanced usage examples.

Note:
    The MemsArray is not fully implemented and acts as an abstract class for specific array implementations.

See Also:
    megamicros.mu for Megamicros class implementation.

Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""

import time
import queue
import numpy as np
from threading import Thread, Timer

from ..log import log
from ..exception import MuException

TRANSFER_DATAWORDS_SIZE		    = 4 									    # Size of transfer words in bytes (same for in32 and float32 data type which always states for 32 bits (-> 4 bytes) )

DEFAULT_FRAME_LENGTH            = 1024                                      # Default frame length in samples number for data transfer
DEFAULT_ACQ_DURATION            = 0                                         # Default acquisition duration in seconds (0 = infinite loop)
DEFAULT_SAMPLING_FREQUENCY      = 44100                                     # Default system sample rate for audio acquisition
DEFAULT_DATATYPE                = 'int32'                                   # Default datatype (int32 or float32)
DEFAULT_MEMS_SENSIBILITY        = 3.54e-6                                   # Default MEMS sensitivity (racine(2)/400 000 = 3,54µPa/digit)
DEFAULT_QUEUE_SIZE              = 0                                         # Queue limit after which the last signal is lost (0 means infinite signal queueing)
DEFAULT_QUEUE_TIMEOUT           = 1000                                      # Queue timeout in ms
DEFAULT_AVAILABLE_MEMS          = [i for i in range(32)]                    # Default available MEMs list for Megamicros systems (32 MEMs)
 

class MemsArray :
    """
    MemsArray
    
    Base class to handle Antenna devices
    """

    class Queue( queue.Queue ):
        """ Thread safe embedded queue adapted to the MemsArray class
        
        Original comportment is that of blocks insertion once maxsize is reached, until queue items are consumed.
        This implementation pop up the last element of the queue if maxsize is reached.

        Queue elements are binary data blocks as received from the data generator.
        """
    
        def __init__( self, maxsize: int = 0 ):
            self.__transfert_lost: int = 0
            super().__init__( maxsize )

        @property
        def transfert_lost( self ) -> bool:
            """ Get the transfer lost counter """
            return self.__transfert_lost

        @property
        def queue_size( self ) -> int:
            """ Get the queue size (e.g. maxsize) """
            return self.maxsize

        def clear( self ) -> None:
            """ Clear the queue """
            # Manually empty the queue since Queue doesn't have a clear() method
            while not self.empty():
                try:
                    self.get_nowait()
                except queue.Empty:
                    break
            self.__transfert_lost = 0

        def put( self, data ):
            """ Put data in the queue. Pop up the last element if maxsize is reached """
            if self.maxsize > 0 and self.qsize() >= self.maxsize:
                # maxsize is reached: remove the last element to free space
                self.get()
                self.__transfert_lost += 1

            # Let parent class do the work 
            super().put( data )

    def __init__(self):
        """
        @brief Constructor
        """
        self.__available_mems: list[int]=DEFAULT_AVAILABLE_MEMS       # Available microphones (connected and ok on the antenna)
        self.__mems: list[int]=[]                                     # Activated microphones
        self.__mems_sensibility: float=DEFAULT_MEMS_SENSIBILITY       # MEMS sensibility in Pa/digit (default to 3.54e-6 Pa/digit)
        self.__mems_positions: list[list[float]]=[]                   # Microphones positions vectors
        self.__counter: bool=False                                    # Counter activation flag
        self.__counter_skip: bool=False                               # Whether to skip counter in output data stream
        self.__sampling_frequency: int=DEFAULT_SAMPLING_FREQUENCY     # Default system sample rate for audio acquisition
        self.__datatype: str=DEFAULT_DATATYPE                         # "int32" or "float32"
        self.__duration: int=DEFAULT_ACQ_DURATION                     # acquisition duration in seconds
        self.__frame_length: int=DEFAULT_FRAME_LENGTH                 # Frame length in samples number for data transfer
        self.__it = 0                                                 # Iterator index
        self.__running: bool = False                                  # Running flag
        self.__source_position: list[float] = [0.0, 0.0, np.inf]      # Source position in space [x,y,z] (default to far field)
        self.__halt_request: bool = False                             # Halt request flag True if a running stop has been requested
        self.__h5_recording: bool=False                               # H5 local recording flag

        # Queue management
        self.__queue: MemsArray.Queue = MemsArray.Queue( maxsize=DEFAULT_QUEUE_SIZE )

        # Thread management
        self.__timer_thread: Thread|None = None                         # Timer thread for limited duration runs
        self.__async_transfer_thread: Thread|None = None                # Asynchronous transfer thread
        self.__async_transfer_thread_exception: Exception|None = None   # Exception raised in the async thread

    @property
    def sampling_frequency( self ) -> int:
        return self.__sampling_frequency

    @property
    def mems( self ) -> list[int]:
        return self.__mems

    @property
    def available_mems( self ) -> list[int]:
        return self.__available_mems

    @property
    def mems_sensibility( self ) -> float:
        return self.__mems_sensibility

    @property
    def mems_position( self ) -> list[list[float]]:
        return self.__mems_positions

    @property
    def counter( self ) -> bool:
        return self.__counter
    
    @property
    def counter_skip( self ) -> bool:
        return self.__counter_skip

    @property
    def channels_number( self ) -> int:
        return len(self.mems) + (1 if self.counter else 0)

    @property
    def duration( self ) -> int:
        return self.__duration
    
    @property
    def datatype( self ) -> str:
        return self.__datatype
    
    @property
    def frame_length( self ) -> int:
        return self.__frame_length
    
    @property
    def frame_duration( self ) -> float:
        return self.__frame_length / self.sampling_frequency
    
    @property
    def h5_recording( self ) -> bool:
        return self.__h5_recording

    @property
    def queue( self ) -> 'MemsArray.Queue':
        """ Get the data transfer queue """
        return self.__queue

    @property
    def queue_size( self ) -> int:
        """ Get the queue size (e.g. maxsize) in bytes"""
        return self.__queue.maxsize

    @property
    def queue_length( self ) -> int:
        """ Get the queue length in number of frames """
        if self.channels_number == 0 or self.frame_length == 0:
            return 0
        else:
            return self.__queue.maxsize // ( self.frame_length * self.channels_number * TRANSFER_DATAWORDS_SIZE )

    @property
    def queue_content( self ) -> int:
        """ Get the number of elements currently in the queue """
        return self.__queue.qsize()

    @property
    def transfer_lost( self ) -> int:
        """ Get the transfer lost counter """
        return self.__queue.transfert_lost
    
    @property
    def running( self ) -> bool:
        """ Get the running flag. True if a run thread is active, False otherwise """
        return self.__running
    
    @property
    def source_position( self ) -> list[float]:
        """ Get source position in space [x,y,z] """
        return self.__source_position

    @property
    def infos( self ) -> dict :
        """ Get current MemsArray configuration as a dictionary """
        infos_dict = {
            'available_mems': self.__available_mems,
            'active_mems': self.__mems,
            'sampling_frequency': self.__sampling_frequency,
            'datatype': self.__datatype,
            'duration': self.__duration,
            'frame_length': self.__frame_length,
            'frame_duration': self.frame_duration,
            'channels_number': self.channels_number,
            'counter': self.__counter,
            'mems_sensibility': self.__mems_sensibility,
            'mems_positions': self.__mems_positions,
            'h5_recording': self.__h5_recording
        }
        return infos_dict

    def setQueueLength( self, length: int ) -> None:
        """ Set transfer queue length in number of frames

        Parameters
        ----------
        length : int
            The transfer queue length in number of frames
        """
        self.__queue = MemsArray.Queue( maxsize=length * self.frame_length * self.channels_number * TRANSFER_DATAWORDS_SIZE )

    def setDuration( self, duration: int ) -> None:
        """ Set duration of next acquisition run in seconds 

        Parameters
        ----------
        duration: int
            The acquisition duration in seconds (0 = infinite loop)
        """
        self.__duration = duration

    def setAvailableMems( self, mems: list[int] ) -> None:
        """ Set the available MEMs (connected and ok on the antenna)

        Parameters
        ----------
        mems: list[int]
            The available MEMs list
        """
        self.__available_mems = mems

    def setActiveMems( self, mems: tuple ) -> None :
        """ Activate mems
        
        Parameters:
        -----------
        mems : tuple
            list or tuple of mems number to activate
        """

        # Set parent property
        self.__mems = mems

    def setSamplingFrequency( self, sampling_frequency: int ) -> None:
        self.__sampling_frequency = sampling_frequency

    def setCounter( self, counter: bool=True ) -> None:
        self.__counter = counter

    def setCounterSkip( self, counter_skip: bool=True ) -> None:
        """ Set whether to skip counter in output data stream
        
        Parameters:
        -----------
        counter_skip : bool
            Whether to skip counter in output data stream
        """

        if counter_skip and not self.counter:
            log.warning( " .Counter skip requested but counter is not activated" )

        self.__counter_skip = counter_skip

    def setFrameLength( self, length: int ) -> None:
        """ Set the frame length in samples number. This property also updates the USB buffer length in samples number.

        Parameters
        ----------
        length: int
            The frame length / USB buffer length in samples number
        """
        self.__frame_length = length
        self.__frame_duration = length / self.sampling_frequency

    def setDatatype( self, datatype: str ) -> None:
        """ Set data type for acquisition
        
        Parameters:
        -----------
        datatype : str
            datatype string ('int32' or 'float32')
        """

        if datatype not in ['int32', 'float32']:
            raise MuException( f"Datatype {datatype} not supported. Available datatypes are 'int32' and 'float32'" )

        self.__datatype = datatype

    def setMemsSensibility( self, sensibility: float ) -> None:
        """ Set MEMs sensibility
        
        Parameters:
        -----------
        sensibility : float
            The MEMs sensibility in Pa/digit
        """

        self.__mems_sensibility = sensibility

    def setMemsPosition( self, positions: list[list[float]] ) -> None:
        """ Set MEMs positions
        
        Parameters:
        -----------
        positions : list[list[float]]
            list of MEMs positions vectors [[x1,y1,z1], [x2,y2,z2], ...]

        Note
        ----
        The available MEMs are automatically updated to match the number of provided positions.
        """

        self.__mems_positions = positions
        self.__available_mems = list(range(len(positions)))

    def setSourcePosition( self, position: list[float] ) -> None:
        """ Set source position in space [x,y,z]
        
        Parameters:
        -----------
        position : list[float]
            The source position in space [x,y,z]
        """

        if len(position) != 3:
            raise MuException( f"Source position must be a list of 3 floats [x,y,z], got {position}" )

        self.__source_position = position

        
    def _set_run_settings( self, args, kwargs ) -> None :
        """ Set settings for run method
        
        Parameters
        ----------
        args: array
            direct arguments of the run function
        kwargs: array
            named arguments of the run function
        """
        
        if len( args ) > 0:
            log.warning( f" .Direct arguments are not accepted. Use named arguments instead ({args})" )
            raise MuException( "Direct arguments are not accepted" )

        try:
            if 'mems' in kwargs:
                self.setActiveMems( kwargs['mems'] )

            if 'available_mems' in kwargs:
                self.setAvailableMems( kwargs['available_mems'] )
                del kwargs['available_mems']

            if 'counter' in kwargs:
                self.setCounter( kwargs['counter'] )

            if 'counter_skip' in kwargs:
                self.setCounterSkip( kwargs['counter_skip'] )

            if 'sampling_frequency' in kwargs:
                self.setSamplingFrequency( kwargs['sampling_frequency'] )

            if 'mems_position' in kwargs:
                self.setMemsPosition( kwargs['mems_position'] )

            if 'datatype' in kwargs:
                self.setDatatype( kwargs['datatype'] )

            if 'duration' in kwargs:
                self.setDuration( kwargs['duration'] )

            if 'frame_length' in kwargs:
                self.setFrameLength( kwargs['frame_length'] )

        except Exception as e:
            raise MuException( f"Run failed on settings: {e}")

    def run( self, *args, **kwargs ) :
        """ The main run method that runs the antenna """

        if len( args ) > 0:
            raise MuException( f"Run() method does not accept direct arguments" )

        self._set_run_settings( [], kwargs=kwargs )

        if self.channels_number == 0 :
            raise MuException("No channel activated for data acquisition")

        # verbose
        log.info( f" .Starting run execution on Virtual device..." )
        log.info( f"  > Run infinite loop (duration=0)" if self.duration == 0 else f"  > Perform {self.duration}s run loop" )
        log.info( f"  > Sampling frequency: {self.sampling_frequency} Hz" )
        log.info( f"  > {len(self.mems)} activated microphones" )
        log.info( f"  > Activated microphones: {self.mems}" )
        log.info( f"  > MEMs sensibility: {self.mems_sensibility}" )
        log.info( f"  > Whether counter is activated: {'YES' if self.counter else 'NO'}" )
        log.info( f"  > Total channels number is {self.channels_number}" )
        log.info( f"  > Datatype: {str( self.datatype )}" )
        log.info( f"  > Frame length in samples number: {self.frame_length} samples" )
        log.info( f"  > Frame duration: {self.frame_duration} s ({self.frame_duration * 1000} ms)" )
        log.info( f"  > Frame size in bytes: {self.frame_length * self.channels_number * TRANSFER_DATAWORDS_SIZE}" )
        log.info( f"  > Transfer queue length: {'infinite queuing' if self.queue_length == 0 else self.queue_length} (frames)" )
        log.info( f"  > Transfer queue size: {'infinite queuing' if self.queue_size == 0 else self.queue_size} (bytes)" )
        log.info( f"  > Local H5 recording {'on' if self.h5_recording else 'off'}" )

        # init running flags and queue
        self.__halt_request = False
        self.__queue.clear()

        # Start the timer if a limited execution time is requested 
        if self.duration > 0:
            self.__timer_thread = Timer( self.duration, self.__run_time_ending )
            self.__timer_thread.start()

        # Start run thread
        self.__async_transfer_thread = Thread( target= self.__run_thread )
        self.__async_transfer_thread.start()


    def __run_time_ending( self ) -> None:
        """ End timer callback for run stopping. This callback requests for stopping the run thread."""

        log.info( f" .End of timer: requesting for stopping run thread..." )
        self.__halt_request = True


    def __run_thread( self ) -> None :
        """ Default base run thread execution

        Generates random data
        """

        try:
            log.info( " .Run thread execution started" )
            
            self.__running = True
            mems_number = len( self.mems )
            start_time = time.time()
            frame_duration = self.frame_duration
            frame_count = 0
            while self.__running:
                # generates random data
                if self.counter is None :
                    # send data without counter state
                    data = ( np.random.rand( self.frame_length, mems_number ) * 2 - 1 ).astype( np.float32 )
                else:
                    # add counter values
                    counter = np.array( [[i for i in range(self.frame_length)]] ).T + self.__it * self.frame_length
                    data = ( np.concatenate( ( counter, ( np.random.rand( self.frame_length, mems_number ) * 2 - 1 ) ), axis=1 ) ).astype( np.float32 )

                # post them in the internal queue as binary buffer
                self.queue.put( data.tobytes() )

                # Check for halt request
                if self.__halt_request:
                    log.info( " .Halt request received: stopping run thread..." )
                    self.__running = False

                # wait for next frame time to sensure real time generation
                frame_count += 1
                elapsed_time = time.time() - start_time
                expected_time = frame_count * frame_duration
                time_to_wait = expected_time - elapsed_time
                if time_to_wait > 0:
                    time.sleep( time_to_wait )
                    
            log.info( " .Running stopped: normal thread termination" )

        except Exception as e:
            log.error( f" .Error resulting in thread termination ({type(e).__name__}): {e}" )
            self.__async_transfer_thread_exception = e

    def wait( self ) -> None :
        """ Wait for the end of the thread execution. This is a blocking function."""
        log.info( f" .Waiting for the end of the thread execution..." )

        if self.__async_transfer_thread is not None:
            self.__async_transfer_thread.join()
            self.__async_transfer_thread = None

        if self.__async_transfer_thread_exception is not None:
            thread_exception = MuException( f"Thread exception ({type(self.__async_transfer_thread_exception).__name__}): {self.__async_transfer_thread_exception}" )
            self.__async_transfer_thread_exception = None
            raise thread_exception

    def stop( self ) -> None :
        """ Stop current running """

        log.info( " .Request for stopping thread execution" )

        if self.running:
            log.info( " .Stopping current run thread execution..." )
            self.__halt_request = True
        else:
            log.warning( "Failed to stop: No current thread running" )



    def __iter__( self ) :
        """ Init iterations over the antenna data """

        self.__it = 0
        return self

    def __next__( self ) -> np.ndarray|StopIteration :
        """ next iteration over the antenna data 
        """
        
        try:
            # Get data from the queue and format them according to datatype
            data = self.__queue.get( timeout=DEFAULT_QUEUE_TIMEOUT / 1000 )
            if self.datatype == 'int32':
                data = np.frombuffer( data, dtype=np.int32 )
                data = data.reshape( ( -1, self.frame_length ), order='F' )
            elif self.datatype == 'float32':
                data = np.frombuffer( data, dtype=np.float32 )
                data = data.reshape( ( -1, self.frame_length ), order='F' )
            else:
                raise MuException( f"Unknown datatype {self.datatype}" )
            self.__it += 1
            return data

        except queue.Empty:
            raise StopIteration

    def __len__( self) -> int : 
        """ Get the number of elements currently in the queue """

        if self.queue is None:
            return 0
        else:
            return self.queue_content
