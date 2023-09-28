# core.base.py base class for MegaMicros receivers
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


""" Provide the base class of MEMs arrays.

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import numpy as np
import queue
from enum import Enum
from megamicros.log import log
from megamicros.exception import MuException
from megamicros.aidb.query import AidbSession
from megamicros.data import MuAudio


DEFAULT_FRAME_LENGTH =              256
DEFAULT_SAMPLING_FREQUENCY =        50000
DEFAULT_QUEUE_SIZE =                2			# Queue size as the number of buffer that can be queued (0 means infinite signal queueing)
DEFAULT_DATATYPE				    = "int32"									# Default receiver incoming data type ("int32" or "float32") 

# Default H5 values
DEFAULT_H5_RECORDING				= False									    # Whether H5 recording is On or Off
DEFAULT_H5_SEQUENCE_DURATION		= 1										    # Time duration of a dataset in seconds
DEFAULT_H5_FILE_DURATION			= 15*60									    # Time duration of a complete H5 file in seconds
DEFAULT_H5_COMPRESSING				= False									    # Whether compression mode is On or Off
DEFAULT_H5_COMPRESSION_ALGO 		= 'gzip'								    # Compression algorithm (gzip, lzf, szip)
DEFAULT_H5_GZIP_LEVEL 				= 4										    # compression level for gzip algo (0 to 9, default 4) 
DEFAULT_H5_DIRECTORY				= './'									    # The default directory where H5 files are saved


class MemsArray:
    """ MEMs array base class.

    The MemsArray class models the operation of an antenna composed of any number of microphones
    Les microphones de l'antenne sont obligatoireement numérotés de 0 à `available_mems_number`. 
    Certains peuvent ne pas être *actifs*. `mems_number` donne le nombre de microphones actifs. 
    Les microphones sont définis par une position relative au centre de l'antenne. 
    Ces positions peuvent ne pas être connues. Il n'est alors pas possible de faire du filtrage spatial.
    Les positions des microphones peuvent ne pas être toutes déterminées. 
    C'est le cas lorsque des microphones sont devenus hors d'usage au moement de la mesure.
    Ces microphpjnes sont toujours identifiés comme *available*, mais ils doivent être désactivés dans l'antenne lorsque leurs signaux sont absents du flux entrant.

    Antenna microphones must be numbered from 0 to `available_mems_number`. 
    Some may not be *active*. `mems_number` gives the number of active microphones. 
    Microphones are defined by a position relative to the center of the antenna.
    These positions may not be known. In this case, spatial filtering is not possible.
    A problem arises when not all microphones are located.
    In this case, unlocated microphones must be placed at location (0, 0, 0) so that it can be determined which are not available.
    Calls to antenna definition parameters should follow the order: setAvailableMems(), setMemsPosition(), then setActiveMems()  
    """

    class Datatype(Enum):
        """ Antenna datatype enumeration

        Datatype decide for the output data format of the antenna

        Values
        ------
        unknown: 0
            no dataype specified
        int32: 1
            np.ndarray of 32bits integer data
        float32: 2
            np.ndarray of 32bits float data
        bint32: 3
            binary buffer of 32bits integer data
        bfloat32: 4
            binary buffer of 32bits float data
        """

        unknown = 0
        int32 = 1
        float32 = 2
        bint32 = 3
        bfloat32 = 4

        def __str__( self ):
            """ Convert a datatype integer code into its string enumeration """
            if self == self.unknown:
                return "Unknown"
            elif self == self.int32:
                return "int32"
            elif self == self.float32:
                return "float32"
            elif self == self.bint32:
                return "bint32"
            elif self == self.bfloat32:
                return "bfloat32"
            else:
                return "Unknown datatype"  

        def __int__( self ):
            """ Convert a datatype enumeration into its integer code """
            if self == self.unknown:
                return 0
            elif self == self.int32:
                return 1
            elif self == self.float32:
                return 2
            elif self == self.bint32:
                return 3
            elif self == self.bfloat32:
                return 4
            else:
                return -1
            
    # Antenna dimensions
    __mems: tuple|None = None
    __available_mems: tuple|None = None
    __analogs: tuple|None = None
    __available_analogs: tuple|None = None
    __mems_position: np.ndarray|None|None = None
    __counter: bool|None = None
    __counter_skip: bool|None = None
    __status: bool|None = None

    # Antenna properties
    __sampling_frequency: float = DEFAULT_SAMPLING_FREQUENCY

    # Output buffering
    __frame_length: int = DEFAULT_FRAME_LENGTH
    __it: int = 0
    __datatype: Datatype = getattr( Datatype, DEFAULT_DATATYPE ) 

    # Running properties
    __duration: int|None = None
    __callback_fn = None
    __callback_user_data = None
    __post_callback_fn = None
    __signal_q = queue.Queue()
    __signal_q_size = DEFAULT_QUEUE_SIZE
    __signal_buffer = None
    
    # Internal run parameters
    _async_transfer_thread = None
    _async_transfer_thread_exception: MuException = None

    # H5 attributes
    __h5_recording: bool = DEFAULT_H5_RECORDING
    __h5_rootdir: str = DEFAULT_H5_DIRECTORY
    __h5_dataset_duration: int = DEFAULT_H5_SEQUENCE_DURATION
    __h5_file_duration: int  = DEFAULT_H5_FILE_DURATION
    __h5_compressing: bool = DEFAULT_H5_COMPRESSING
    __h5_compression_algo: str = DEFAULT_H5_COMPRESSION_ALGO
    __h5_gzip_level: int = DEFAULT_H5_GZIP_LEVEL


    @property
    def h5_recording( self ) -> bool:
        """ Get the H5 recording flag """
        return self.__h5_recording

    @property
    def h5_rootdir( self ) -> str:
        """ Get the H5 recording root directory """
        return self.__h5_rootdir

    @property
    def h5_dataset_duration( self ) -> int:
        """ Get the MuH5 dataset duration """
        return self.__h5_dataset_duration

    @property
    def h5_file_duration( self ) -> int:
        """ Get the time duration of a complete MuH5 file in seconds """
        return self.__h5_file_duration

    @property
    def h5_compressing( self ) -> bool:
        """ Get the H5 compression boolean flag """
        return self.__h5_compressing

    @property
    def h5_compression_algo( self ) -> str:
        """ Get the H5 compression algorithm """
        return self.__h5_compression_algo
    
    @property
    def h5_gzip_level( self ) -> int:
        """ Get the H5 gzip compression level """
        return self.__h5_gzip_level

    @property
    def mems_number( self ) -> int:
        """ Get the active MEMs number """
        return len( self.__mems )
    
    @property
    def available_mems_number( self ) -> int:
        """ Get the available MEMs number """
        return len( self.__available_mems )

    @property
    def analogs_number( self ) -> int:
        """ Get the active analogs number """
        return len( self.__analogs )
    
    @property
    def available_analogs_number( self ) -> int:
        """ Get the available analogs number """
        return len( self.__available_analogs )
    
    @property
    def mems_position( self ) -> np.ndarray|None | None:
        """ Get the antenna mems positions
        
        Returns
        -------
            mems_position : np.ndarray|None | None
                array of 3D MEMs positions  
        """
        return self.__mems_position

    @property
    def available_mems( self ) -> tuple | None:
        """ Get the available mems list """
        return self.__available_mems
    
    @property
    def mems( self ) -> tuple | None:
        """ Get the activated MEMss list """
        return self.__mems
    
    @property
    def analogs( self ) -> tuple | None:
        """ Get the activated analog channels list """
        return self.__analogs

    @property
    def counter( self ) -> bool | None:
        """ Get the counter status """
        return self.__counter
    
    @property
    def counter_skip( self ) -> bool | None:
        """ Get the counter skipping status """
        return self.__counter_skip
    
    @property
    def status( self ) -> bool | None:
        """ Get the status state """
        return self.__status
    
    @property
    def datatype( self ) -> Datatype :
        """ Get the antenna output datatype """
        return self.__datatype

    @property
    def frame_length( self ) -> int:
        """ Get the output frames length """
        return self.__frame_length
    
    @property
    def sampling_frequency( self ) -> float:
        """ Get the antenna current sampling frequency """
        return self.__sampling_frequency
    
    @property
    def duration( self ) -> int | None:
        """ Get duration scheduled for running """
        return self.__duration

    @property
    def signal_q( self ) -> queue.Queue:
        """ Get the default queue """
        return self.__signal_q

    @property
    def signal_q_size( self ) -> int:
        """ Get the max length of the queue """
        return self.__signal_q_size

    @property
    def callback_fn( self ):
        """ Get the user callback function """
        return self.__callback_fn

    @property
    def post_callback_fn( self ):
        """ Get the user post callback function """
        return self.__post_callback_fn



    #def __init__( self, available_mems_number:int|None=None, mems_position:np.ndarray|None|None=None, unit: str|None=None ):
    def __init__( self, *args, **kwargs ):

        """Create an antenna object

        Parameters:
        -----------
        available_mems_number : int | None
            The total number of MEMs composing the antenna with MEMs numbered from 0 to `available_mems_number-1`
        mems_position : np.ndarray|None | None
            The 3D positions of the MEMs relative to the center of the antenna
        unit : str | None
            The unit used for mems_position ("meters", "centimeters", "millimeters"), default is "meters"
        """
        
        if len( args ) != 0:
            raise MuException( "Direct arguments are not accepted for MemsArray objects" )

        # No args -> nothing to do
        if len( kwargs ) == 0:
            return
                
        if 'available_mems_number' in kwargs:
            self.setAvailableMems( kwargs['available_mems_number'] )

        if 'mems_position' in kwargs:
            self.setMemsPosition( kwargs['mems_position'], unit=kwargs['unit'] if 'unit' in kwargs else None )
        
        if 'mems' in kwargs:
            self.setActiveMems( kwargs['mems'] )

        log.info( f" .Created a new antenna" )


    def setH5Recording( self ) -> None :
        """ Set the H5 recording on """
        self.__h5_recording = True


    def unsetH5Recording( self ) -> None :
        """ Set the H5 recording off """
        self.__h5_recording = False


    def setH5Rootdir( self, dir: str ) -> None :
        """ Set the H5 recording root directory """
        self.__h5_rootdir = dir


    def setH5DatasetDuration( self, duration: int ) -> None :
        """ Set the H5 dataset duration in seconds """
        self.__h5_dataset_duration = duration


    def setH5FileDuration( self, duration: int ) -> None :
        """ Set the H5 file duration in seconds """
        self.__h5_file_duration = duration


    def setH5Compressing( self, algo: str=DEFAULT_H5_COMPRESSION_ALGO, level: int=DEFAULT_H5_GZIP_LEVEL ) -> None :
        """ Set the H5 recording compressing mode on """

        if str != 'gzip':
            raise MuException( f"The H5 compressing algo '{algo}' is not implemented" )
        if algo == 'gzip' and ( level <0 or level > 9 ):
            raise MuException( f"Wrong compressing level <{level}>. Accepted values are between 0 and 9" )
        
        self.__h5_compressing = True
        self.__h5_compression_algo = algo
        self.__h5_gzip_level = level


    def unsetH5Compressing( self ) -> None :
        """ Set the H5 recording compressing mode off """
        self.__h5_compressing = False
        self.__h5_compression_algo = DEFAULT_H5_COMPRESSION_ALGO
        self.__h5_gzip_level = DEFAULT_H5_GZIP_LEVEL


    def setStatus( self ) -> None :
        """ Make status channel available. Status state will be added to output signals 

        See
        ---
            MemsArray.unsetStatus()
        """
        self.__status = True


    def unsetStatus( self ) -> None :
        """ Make status unavailable.

        See
        ---
            MemsArray.setStatus()
        """
        self.__status = False


    def setCounter( self ) -> None :
        """ Make counter available. Counter state will be added to output signals 

        See
        ---
            MemsArray.unsetCounter()
        """
        self.__counter = True

    def unsetCounter( self ) -> None :
        """ Make counter unavailable.

        See
        ---
            MemsArray.setCounter()
        """
        self.__counter = False

    def setCounterSkip( self ) -> None :
        """ If counter is available, do not add counter state in output signals

        See
        ---
            MemsArray.setCounter()
            MemsArray.unsetCounterSkip()
        """
        self.__counter_skip = True

    def unsetCounterSkip( self ) -> None :
        """ If counter is available, add counter state in output signals

        See
        ---
            MemsArray.setCounter()
            MemsArray.setCounterSkip()
        """
        self.__counter_skip = False


    def setDatatype( self, datatype: Datatype ) -> None :
        """ Set the output antenna data type

        Parameters
        ----------
        datatype: MemsArray.Datatype
            the antenna output data type among int32, float32, bint32, bfloat32...
        """

        self.__datatype = datatype


    def setAvailableMems( self, available_mems_number: int ) -> None :
        """Init antenna available MEMs.
        
        This funtion deactivates MEMs if some are already activated 

        Parameters
        ----------
        available_mems_number: int
            Antenna available MEMs number which will be numbered from 0 to `available_mems_number-1`
        """
        self.__available_mems = [i for i in range( available_mems_number )]

        # Deactivate MEMs
        if self.__mems is not None and max(self.__mems) >= available_mems_number:
            log.warning( f"Some MEMs are activated that do not match the new antenna definition: all MEMs are now unactivated" )
            self.__mems = None

        # Check positions matching if any
        if self.__mems_position is not None:
            if self.__mems_position.shape[0] != len( self.__available_mems ):
                raise MuException( f"Available_mems_number({available_mems_number}) do not match with MEMs positions ({self.__mems_position.shape[0]} MEMs)" )

        log.info( f" .Set {available_mems_number} MEMs numbered from 0 to {available_mems_number-1}" )


    def setMemsPosition( self, mems_position: np.ndarray|None, unit: str="meters" ) -> None :
        """ Set MEMs physical position
        
        Parameters
        ----------
        mems_position: np.ndarray|None
            3D array of MEMs position (shape = `(mems_number, 3)`)
        """

        if mems_position.shape[1] != 3:
            raise MuException( f"Array dimensions are not correct: shape is {mems_position.shape} but should be (mems_number, 3)" )

        # Build the available MEMs list if needed or check availability 
        if self.__available_mems is None:
            log.info( f" .Setting available MEMs numbered from 0 to {mems_position.shape[0]-1}" )
            self.__available_mems = [i for i in range(mems_position.shape[0])]
        else:
            if mems_position.shape[0] != len( self.__available_mems ):
                log.warning( f"MEMs locations do not match with available MEMs: reset available MEMS from 0 to {mems_position.shape[0]-1}" )
                self.__available_mems = [i for i in range(mems_position.shape[0])]

        # Check unlocated microphones with location set to (0, 0, 0)
        unlocated_mems = []
        for i, mem in enumerate( range( mems_position ) ):
            if np.all( mem==0 ) ==  True:
                unlocated_mems.append( i )
        if len( unlocated_mems ) > 0:
            log.info( f" .Following MEMS are unlocated: {unlocated_mems}" )
        
        # check matching with activated MEMs
        if self.__mems is not None:
            unlocated_activated = list( set( self.__mems ) & set( unlocated_mems ) )
            if len( unlocated_activated ) > 0:
                log.warning( f"Some activated MEMs are not located. Please check for {unlocated_activated} MEMs" )

        self.__mems_position = mems_position
        if unit == "centimeters":
            self.__mems_position /= 100
        elif unit == "millimeters":
            self.__mems_position /= 1000

        log.info( f" .Set a {mems_position.shape[0]} activable MEMs antenna with physical positions" )


    def setActiveMems( self, mems: tuple ) -> None :
        """ Activate mems

        All activated MEMs should be available. Raise an exception if not.
        Print a warning if some activated MEMs are not located while MEMs positions are defined.
        
        Parameters:
        -----------
        mems : tuple
            list or tuple of mems number to activate
        """

        if self.__available_mems is None:
            raise MuException( f"Cannot activate MEMs on antenna with no available MEMs" )

        # Check if activated MEMs are available. Raise an exception if not
        if False in np.isin( mems, self.__available_mems ):
            mask = np.logical_not( np.isin( mems, self.__available_mems ) )
            raise Exception( f"Some activated microphones ({np.array(mems)[mask]}) are not available on antenna.")

        # Warning if some activated MEMs are not located
        if self.__mems_position is not None:
            unlocated_mems = []
            for i, mem in enumerate( range( self.__mems_position ) ):
                if np.all( mem==0 ) ==  True:
                    unlocated_mems.append( i )
            if len( unlocated_mems ) > 0:
                unlocated_activated_mems = list( set(mems) & set(unlocated_mems) )
                if len( unlocated_activated_mems ) > 0:
                    log.warning( f"Following activated MEMs are unlocated: {unlocated_mems}" )

        self.__mems = mems
        log.info( f" .{len(mems)} MEMs were activated among 0 to {len(self.__available_mems)-1} available MEMs" )


    def setAvailableAnalogs( self, available_analogs_number: int ) -> None :
        """Init antenna available analogic channels.
        
        This funtion deactivates channels if some are already activated 

        Parameters
        ----------
        available_analogs_number: int
            Antenna available analogs number which will be numbered from 0 to `available_analogs_number-1`
        """

        self.__available_analogs = [i for i in range( available_analogs_number )]

        # Deactivate analogs
        if self.__analogs is not None and max(self.__analogs) >= available_analogs_number:
            log.warning( f"Some analogs are activated that do not match the new antenna definition: all analogic channels are now unactivated" )
            self.__analogs = None

        log.info( f" .Set {available_analogs_number} analog channels numbered from 0 to {available_analogs_number-1}" )


    def setActiveAnalogs( self, analogs: tuple ) -> None :
        """ Activate analogic channels

        All activated analogs should be available. Raise an exception if not.
        
        Parameters:
        -----------
        analogs : tuple
            list or tuple of analogs number to activate
        """

        if self.__available_analogs is None:
            raise MuException( f"Cannot activate analogs channels on antenna with no available analogs" )

        # Check if activated analogs are available. Raise an exception if not
        if False in np.isin( analogs, self.__available_analogs ):
            mask = np.logical_not( np.isin( analogs, self.__available_analogs ) )
            raise Exception( f"Some activated analogs ({np.array(analogs)[mask]}) are not available on antenna.")

        self.__analogs = analogs
        log.info( f" .{len(analogs)} analogic channels were activated among 0 to {len(self.__available_analogs)-1} available analogs" )


    def setFrameLength( self, frame_length: int ) -> None :
        """ Set the output frame length in samples number 
        
        Parameters:
        -----------
        frame_length : int
            the frame length in samples number
        """

        self.__frame_length = frame_length


    def setSamplingFrequency( self, sampling_frequency: float ) -> None :
        """ Set the antenna sampling frequency
        
        Parameters:
        -----------
        sampling_frequency : float
            The sampling frequency (default is given by DEFAULT_SAMPLING_FREQUENCY)
        """

        self.__sampling_frequency = sampling_frequency


    def setDuration( self, duration ) -> None :
        """ Set the duration for next run

        Parameters
        ----------
        duration: int
            durationscheduled for next run in seconds
        """

        self.__duration = duration


    def setQueueSize( self, queue_size: int ) -> None :
        """ Set the signal queue size 
        
        Parameters
        ----------
        queue_size: int
            The new queue size value
        """
        self.__signal_q_size = queue_size


    def setCallback( self, callback ) -> None :
        """ Set user callback funcion 
        
        Parameters
        ----------
        callback: 
            user call back function
        """

        self.__callback_fn = callback


    def setPostCallback( self, callback ) -> None :
        """ Set user post callback funcion 
        
        Parameters
        ----------
        callback: 
            user call back function
        """

        self.__post_callback_fn = callback


    def setCallbackData( self, callback_data ) -> None :
        """ Set user data for callback function 

        callback_data: Any
            user callback function data
        """

        self.__callback_user_data = callback_data


    def __iter__( self ) :
        """ Init iterations over the antenna data """

        self.__it = 0
        return self

    def __next__( self ) -> np.ndarray|None :
        """ next iteration over the antenna data 

        Note that as MemsArray is a base class without any data inside, one can only return random data
        """

        self.__it += 1

        if self.__counter is None or ( self.__counter == False or ( self.__counter == True and self.__counter_skip==True ) ):
            # send data without counter state
            return np.random.rand( self.__frame_length, self.mems_number ) * 2 - 1
        else:
            # add counter values
            counter = np.array( [[i for i in range(self.__frame_length)]] ).T + self.__it * self.__frame_length
            return np.concatenate( ( counter, ( np.random.rand( self.__frame_length, self.mems_number ) * 2 - 1 ) ), axis=1 )
