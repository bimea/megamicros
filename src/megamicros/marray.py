# megamicros.marray.py
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
@file megamicros.marray.py
@brief Base class for microphone arrays modelling
"""

from .log import log
from .exception import MuException

DEFAULT_FRAME_LENGTH            = 1024                                      # Default frame length in samples number for data transfer
DEFAULT_ACQ_DURATION            = 0                                         # Default acquisition duration in seconds (0 = infinite loop)
DEFAULT_SAMPLING_FREQUENCY      = 44100                                     # Default system sample rate for audio acquisition
MU_DEFAULT_DATATYPE             = 'int32'                                   # Default datatype (int32 or float32)

class MArray :
    """
    @class MArray
    @brief Base class to handle MegaMicros devices
    """

    def __init__(self):
        """
        @brief Constructor
        """
        self.__available_mems: list[int]=[]                           # Available microphones (connected and ok on the antenna)
        self.__available_analogs: list[int]=[]                        # Available analogs (connected and ok on the antenna)
        self.__mems: list[int]=[]                                     # Activated microphones
        self.__analogs: list[int]=[]                                  # Activated analogs
        self.__mems_positions: list[list[float]]=[]                   # Microphones positions vectors
        self.__counter: bool=True                                     # Counter activation flag
        self.__counter_skip: bool=False                               # Whether counters are removed or not in output stream
        self.__sampling_frequency: int=DEFAULT_SAMPLING_FREQUENCY     # Default system sample rate for audio acquisition
        self.__datatype: str=MU_DEFAULT_DATATYPE                      # "int32" or "float32"
        self.__duration: int=DEFAULT_ACQ_DURATION                     # acquisition duration in seconds
        self.__frame_length: int=DEFAULT_FRAME_LENGTH                 # Frame length in samples number for data transfer
        self.__h5_recording: bool=False                               # H5 local recording flag

    @property
    def sampling_frequency( self ) -> int:
        return self.__sampling_frequency

    @property
    def available_mems( self ) -> float:
        return self.__available_mems

    @property
    def available_analogs( self ) -> float:
        return self.__available_analogs

    @property
    def mems( self ) -> int:
        return self.__mems

    @property
    def analogs( self ) -> int:
        return self.__analogs

    @property
    def counter( self ) -> bool:
        return self.__counter
    
    @property
    def counter_skip( self ) -> bool:
        return self.__counter_skip

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

    def setAvailableAnalogs( self, analogs: list[int] ) -> None:
        """ Set the available analogs (connected and ok on the antenna)

        Parameters
        ----------
        analogs: list[int]
            The available analogs list
        """
        self.__available_analogs = analogs

    def setSamplingFrequency( self, sampling_frequency: int ) -> None:
        self.__sampling_frequency = sampling_frequency

    def setCounter( self, counter: bool=True ) -> None:
        self.__counter = counter

    def setCounterSkip( self, counter_skip: bool=True ) -> None:
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

    def setActiveMems( self, mems: tuple ) -> None :
        """ Activate mems
        
        Parameters:
        -----------
        mems : tuple
            list or tuple of mems number to activate
        """

        # Set parent property
        self.__mems = mems

    def setActiveAnalogs( self, analogs: tuple ) -> None :
        """ Activate analogs
        
        Parameters:
        -----------
        analogs : tuple
            list or tuple of analogs number to activate
        """

        # Set parent property
        self.__analogs = analogs

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

    def setMemsPosition( self, positions: list[list[float]] ) -> None:
        """ Set MEMs positions
        
        Parameters:
        -----------
        positions : list[list[float]]
            list of MEMs positions vectors [[x1,y1,z1], [x2,y2,z2], ...]
        """

        self.__mems_positions = positions

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
            if 'available_mems' in kwargs:
                self.setAvailableMems( kwargs['available_mems'] )

            if 'mems' in kwargs:
                self.setActiveMems( kwargs['mems'] )

            if 'available_analogs' in kwargs:
                self.setAvailableAnalogs( kwargs['available_analogs'] )

            if 'analogs' in kwargs:
                self.setActiveAnalogs( kwargs['analogs'] )

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
