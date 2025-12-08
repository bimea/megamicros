# megamicros.antenna.py
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
Core module of the Megamicros systems library

Features:
    - Base class for microphone arrays modelling.
    - Management of available and active microphones and analog inputs
    - Configuration of sampling frequency, data type, frame length, and acquisition duration
    - Support for counter activation
    - H5 local recording flag

Examples:
    Basic usage::

        from megamicros import log
        from megamicros.core.mu import Megamicros

        antenna = Megamicros()

        print( "Available MEMS: ", antenna.available_mems )
        print( "Available Analogs: ", antenna.available_analogs )

        antenna.run(
            mems=antenna.available_mems,
            sampling_frequency=50000,
            duration=10,
            frame_length=1024,
            datatype='int32'
        )
        antenna.wait()

        # Print frames stored in the queue
        print(f"queue content : {antenna.queue_content} frames")

        # Retrieve data from the queue
        for data in antenna:
            print( f"data={data}" )

    Advanced usage::

        See the Notebooks for advanced usage examples.

Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""


from ctypes import addressof, byref, sizeof, create_string_buffer
import time
import platform
import enum
import queue
import numpy as np

from ..usb import Usb
from ..log import log
from ..exception import MuException
from .base import MemsArray, TRANSFER_DATAWORDS_SIZE

# MegaMicro hardware commands
MU_CMD_RESET					= b'\x00'									# Reset: power off the microphones
MU_CMD_INIT						= b'\x01'									# Sampling frequency setting
MU_CMD_START					= b'\x02'									# Acquisition running command
MU_CMD_STOP						= b'\x03'									# Acquisition stopping command
MU_CMD_COUNT					= b'\x04'									# Number of expected samples for next acquisition running
MU_CMD_ACTIVE					= b'\x05'									# Channels selection (MEMs, analogics, counter and status activating)
MU_CMD_PURGE					= b'\x06'									# Purge FiFo. No doc found about this command
MU_CMD_DELAY					= b'\x07'									# Test and tunning command. Not used in production mode. See documentation (no write function provided so far)
MU_CMD_DATATYPE					= b'\x09'									# Set datatype
MU_CMD_FX3_RESET				= 0xC0										# Init FX3 usb controler
MU_CMD_FX3_PH					= 0xC4										# External FPGA reset (hard reset)
MU_CMD_FPGA_0					= 0xB0										# Send a 0 byte command to FPGA
MU_CMD_FPGA_1					= 0xB1										# Send a 1 byte command to FPGA
MU_CMD_FPGA_2					= 0xB2										# Send a 2 byte command to FPGA
MU_CMD_FPGA_3					= 0xB3										# Send a 3 byte command to FPGA
MU_CMD_FPGA_4					= 0xB4										# Send a 4 byte command to FPGA

# Memgamicros hardware code values																	
MU_CODE_DATATYPE_INT32			= b'\x00'									# Int32 datatype code
MU_CODE_DATATYPE_FLOAT32		= b'\x01'									# Float32 datatype code

# MegaMicro receiver properties
MU_BEAM_MEMS_NUMBER				= 8											# MEMS number per beam
MU_MEMS_UQUANTIZATION			= 24										# MEMs unsigned quantization 
MU_MEMS_QUANTIZATION			= MU_MEMS_UQUANTIZATION - 1					# MEMs signed quantization 
MU_MEMS_AMPLITUDE				= 2**MU_MEMS_QUANTIZATION					# MEMs maximal amlitude value for "int32" data type
MU_MEMS_SENSIBILITY				= 3.54e-6 	                                # MEMs sensibility factor (-26dBFS for 104 dB that is 3.17 Pa)
MU_DEFAULT_DATATYPE             = 'int32'                                   # Datatype for FPGA megamicros data 

# Default run propertie's values
DEFAULT_TIME_ACTIVATION			= 200										# Waiting time after MEMs powering in milliseconds
DEFAULT_TIME_ACTIVATION_RESET	= 10										# Waiting time between commands of the MegaMicro device reset sequence in milliseconds
DEFAULT_CLOCKDIV				= 0x09										# Default internal acquisition clock value
DEFAULT_SELFTEST_DURATION       = 0.1                                       # Default selftest duration in seconds     
DEFAULT_START_TRIGG_STATUS      = False								        # Default start trigger status (external hard (True) or internal soft (False))
DEFAULT_MEMS_SENSIBILITY        = 3.54e-6                                   # Default MEMS sensitivity (racine(2)/400 000 = 3,54µPa/digit)
DEFAULT_ANALOGS_SENSIBILITY     = 0.33                                      # Default analogs sensibility in V/digit (0.33 V/digit: 0x00FFFFFF on 24bits <-> 5.65Vcc)
DEFAULT_CLOCK_DIVIDER_REFERENCE = 500000                                    # Constant for the clock divider (500kHz)
AIKHOUS_CLOCK_DIVIDER_REFERENCE = 480000                                    # Constant for the clock divider for Aikhous systems (480kHz)
DEFAULT_SYNC_DELAY              = 10                                        # Default synchronization delay (10 for usual systems, 8 for Aikhous systems)
AIKHOUS_SYNC_DELAY              = 8                                         # Default synchronization delay for Aikhous systems

CONTROL_DATA_FAILURE            = False                                     # Perform control data failure if True
EXIT_ON_DATA_FAILURE            = True                                      # Exit on data failure (when data are lost during transfer)

MU_BUS_ADDRESS                  = 0x00                                      # Default USB bus address for MegaMicros devices
USB_DEFAULT_WRITE_TIMEOUT       = 1000                                      # Default USB write timeout in milliseconds
USB_DEFAULT_TRANSFER_TIMEOUT    = 1000                                      # Default USB transfer timeout in milliseconds
USB_DEFAULT_BUFFERS_NUMBER      = 8                                         # Default USB buffers number for data acquisition
USB_DEFAULT_QUEUE_LENGTH        = 0                                         # Default USB transfer queue length in number of frames (0 means infinite queueing)
USB_DEFAULT_QUEUE_TIMEOUT       = 2                                         # Default USB transfer queue get timeout in seconds (delay until the queue is considered as empty)


class Megamicros(MemsArray):
    """
    class MegaMicros
    
    Main class to handle MegaMicros devices. Support 32, 256 and 1024 systems
    """

    Systems = {
        # no megamicros type specified
        'unknown': {
            'name': 'unknown',
            'vendor_id': 0x0000,
            'product_id': 0x0000,
            'endpoint_in': 0x00,
            'bus_address': 0x00,
            'beams': 0,
            'analogs': 0,
            'counters': 0,
            'status': 0
        },
        # 32 channels megamicros device with USB2 port
        'mu32usb2': {
            'name': 'mu32usb2',
            'vendor_id': 0xFE27,
            'product_id': 0xAC00,
            'endpoint_in': 0x81,
            'bus_address': 0x00,
            'beams': 4,
            'analogs': 0,
            'counters': 1,
            'status': 1

        },
        # 32 channels megamicros device with USB3 port
        'mu32': {
            'name': 'mu32',
            'vendor_id': 0xFE27,
            'product_id': 0xAC03,
            'endpoint_in': 0x81,
            'bus_address': 0x00,
            'beams': 4,
            'analogs': 0,
            'counters': 1,
            'status': 1
        },
        # 32 channels megamicros device with USB3 port and one or more analogs
        'mu32a': {
            'name': 'mu32a',
            'vendor_id': 0xFE27,
            'product_id': 0xAC03,
            'endpoint_in': 0x81,
            'bus_address': 0x00,
            'beams': 4,
            'analogs': 2,
            'counters': 1,
            'status': 1
        },
        # 128 channels megamicros device with USB2 port (deprecated)
        'mu128': {
            'name': 'mu128',
            'vendor_id': 0xFE27,
            'product_id': 0x0000,
            'endpoint_in': 0x81,
            'bus_address': 0x00,
            'beams': 16,
            'analogs': 0,
            'counters': 1,
            'status': 1
        },
        # 256 channels megamicros device with USB3 port
        'mu256': {
            'name': 'mu256',
            'vendor_id': 0xFE27,
            'product_id': 0xAC02,
            'endpoint_in': 0x81,
            'bus_address': 0x00,
            'beams': 32,
            'analogs': 4,
            'counters': 1,
            'status': 1
        },
        # 256 channels megamicros Aikhous device with USB3 port
        'mu256h': {
            'name': 'mu256h',
            'vendor_id': 0xFE27,
            'product_id': 0xAC02,
            'endpoint_in': 0x81,
            'bus_address': 0x00,
            'beams': 32,
            'analogs': 4,
            'counters': 1,
            'status': 1
        },
        # 1024 channels megamicros device with USB3 port
        'mu1024': {
            'name': 'mu1024',
            'vendor_id': 0xFE27,
            'product_id': 0xAC01,
            'endpoint_in': 0x81,
            'bus_address': 0x00,
            'beams': 128,
            'analogs': 16,
            'counters': 4,
            'status': 4
        },
    }

    def __init__(self):
        """
        @brief Constructor
        """
        super().__init__()
        self.__system: dict = Megamicros.Systems['unknown']                 # Megamicros system type
        self.__usb: Usb=Usb()                                               # USB interface instance
        self.__usb_buffers_number: int=USB_DEFAULT_BUFFERS_NUMBER           # USB buffers number used in USB data acquisition process
        self.__available_analogs: list[int]=[]                              # Available analogs (connected and ok on the antenna)
        self.__analogs: list[int]=[]                                        # Activated analogs
        self.__analogs_sensibility: float=DEFAULT_ANALOGS_SENSIBILITY       # Analogs sensibility in V/digit (default to 0.33 V/digit: 0x00FFFFFF on 24bits <-> 5.65Vcc)
        self.__counters: list[int]=[0]                                      # Activated counters
        self.__status: list[int]=[]                                         # Activated status channels
        self.__clock_divider_reference: int=DEFAULT_CLOCK_DIVIDER_REFERENCE # Clock divider reference (sr = cdr/(clockdiv+1), default to 500kHz for usual systems, 480kHz for Aikhous systems) 
        self.__clockdiv: int=9                                              # Clock divider (default to 9 for 50kHz or 48kHz sampling frequencies)
        self.__sync_delay: int=10                                           # Default synchronization delay (10 for usual systems, 8 for Aikhous systems)
        self.__start_trigg_status: bool=False                               # Start trigger status (external hard (True) or internal soft (False))
        self.__time_activation: int=DEFAULT_TIME_ACTIVATION                 # Waiting time between commands of the MegaMicro device reset sequence in milliseconds

        # Check connected devices and open connection to the first found
        self.checkAndOpenDevice()
        mems_power, analogs_power = self.selftest( DEFAULT_SELFTEST_DURATION )

        # Set default sampling frequency in accordance with default megamicros systems
        self.setClockdiv( DEFAULT_CLOCKDIV )

        log.info(" .Megamicros device initialized")

    def __del__( self ):
        log.info( ' .Megamicros resources cleaned up' )

    @property
    def usb( self ) -> Usb:
        return self.__usb

    @property
    def analogs( self ) -> int:
        return self.__analogs
    
    @property
    def available_analogs( self ) -> float:
        return self.__available_analogs

    @property
    def analogs_sensibility( self ) -> float:
        return self.__analogs_sensibility

    @property
    def counters( self ) -> list[int]:
        """ Return the list of activated counters"""
        return self.__counters
    
    @property
    def counter( self ) -> bool:
        """ Return True if at least counter 0 is activated
        """
        return 0 in self.__counters
    
    @property
    def status(self) -> list[int]:
        """ Return the list of activated status channels """
        return self.__status

    @property
    def channels_number( self ) -> int:
        """ Return the total number of channels (MEMS, analogs, counters, status) """
        return len(self.mems) + len(self.analogs) + len(self.counters) + len(self.status)

    @property
    def clockdiv( self ) -> int:
        """ Return the clock divider (default to 9 for 50kHz or 48kHz sampling frequencies) """
        return self.__clockdiv
    
    @property
    def sync_delay( self ) -> int:
        """ Return the synchronization delay (10 for usual systems, 8 for Aikhous systems) """
        return self.__sync_delay

    @property
    def queue( self ) -> Usb.Queue:
        """ Get the USB queue instance """
        return self.__usb.queue

    @property
    def queue_size( self ) -> int:
        """ Get the USB queue size (e.g. maxsize) in bytes"""
        return self.__usb.queue.maxsize

    @property
    def queue_length( self ) -> int:
        """ Get the USB queue length in number of frames """
        if self.channels_number == 0 or self.frame_length == 0:
            return 0
        else:
            return self.__usb.queue.maxsize // ( self.frame_length * self.channels_number * TRANSFER_DATAWORDS_SIZE )

    @property
    def queue_content( self ) -> int:
        """ Get the number of elements currently in the USB queue """
        return self.__usb.queue.qsize()

    @property
    def transfer_lost( self ) -> int:
        return self.usb.transfer_lost

    @property
    def time_activation( self ) -> int:
        return self.__time_activation

    @property
    def insfos( self ) -> dict:
        """ Get current Megamicros configuration as a dictionary """
        infos_dict = {
            'system_name': self.__system['name'],
            'available_mems': self.available_mems,
            'active_mems': self.mems,
            'mems_sensibility': self.mems_sensibility,
            'available_analogs': self.available_analogs,
            'active_analogs': self.analogs,
            'analogs_sensibility': self.analogs_sensibility,
            'counters': self.counters,
            'status': self.status,
            'clockdiv': self.clockdiv,
            'sampling_frequency': self.sampling_frequency,
            'sync_delay': self.sync_delay,
            'datatype': self.datatype,
            'duration': self.duration,
            'frame_length': self.frame_length,
            'frame_duration': self.frame_duration,
            'channels_number': self.channels_number,
            'counter': self.counter,
            'h5_recording': self.__h5_recording
        }
        return infos_dict

    def setAvailableMems( self, mems: list[int] ) -> None:
        """ Set the available MEMs (connected and ok on the antenna)

        Parameters
        ----------
        mems: list[int]
            The available MEMs list
        """
        mems_number = self.__system['beams'] * MU_BEAM_MEMS_NUMBER
        # Check if a MEMS number in the list is >= mems_number:
        for m in mems:
            if m >= mems_number:
                raise MuException( f"Megamicros system {self.__system['name']} has only {mems_number} MEMS, cannot set available MEMS {mems}" )

        super().setAvailableMems(mems)

    def setAvailableAnalogs( self, analogs: list[int] ) -> None:
        """ Set the available analogs (connected and ok on the antenna)

        Parameters
        ----------
        analogs: list[int]
            The available analogs list
        """
        analogs_number = self.__system['analogs']
        # Check if an analog number in the list is >= analogs_number:
        for a in analogs:
            if a >= analogs_number:
                raise MuException( f"Megamicros system {self.__system['name']} has only {analogs_number} analogs, cannot set available analogs {analogs}" )
        self.__available_analogs = analogs

    def setActiveAnalogs( self, analogs: tuple ) -> None :
        """ Activate analogs
        
        Parameters:
        -----------
        analogs : tuple
            list or tuple of analogs number to activate
        """

        self.__analogs = analogs

    def setSyncDelay( self, delay: int ) -> None:
        """ Set the synchronization delay (10 for usual systems, 8 for Aikhous systems)

        Parameters:
        -----------
        delay : int
            The synchronization delay value
        """
        self.__sync_delay = delay

    def setQueueLength( self, length: int ) -> None:
        """ Set USB transfer queue length in number of frames
        """
        self.usb.setQueueSize( length * self.frame_length * self.channels_number * TRANSFER_DATAWORDS_SIZE )

    def checkAndOpenDevice(self) -> None:
        """
        Check and open the MegaMicros USB device
        
        Throw MuException in case of error during the USB transfer
        """
        try:
            if self.__usb.isOpened():
                raise MuException("MegaMicros device is already opened")

            if self.__usb.checkDeviceByVendorProduct(Megamicros.Systems['mu32usb2']['vendor_id'], Megamicros.Systems['mu32usb2']['product_id']):
                self.__system = Megamicros.Systems['mu32usb2']
                self.__clock_divider_reference = DEFAULT_CLOCK_DIVIDER_REFERENCE
                self.__sync_delay = DEFAULT_SYNC_DELAY
                self.__usb.open(
                    Megamicros.Systems['mu32usb2']['vendor_id'],
                    Megamicros.Systems['mu32usb2']['product_id'],
                    Megamicros.Systems['mu32usb2']['bus_address'],
                    Megamicros.Systems['mu32usb2']['endpoint_in']
                )

            if self.__usb.checkDeviceByVendorProduct(Megamicros.Systems['mu32']['vendor_id'], Megamicros.Systems['mu32']['product_id']):
                self.__system = Megamicros.Systems['mu32']
                self.__clock_divider_reference = DEFAULT_CLOCK_DIVIDER_REFERENCE
                self.__sync_delay = DEFAULT_SYNC_DELAY
                self.__usb.open(
                    Megamicros.Systems['mu32']['vendor_id'],
                    Megamicros.Systems['mu32']['product_id'],
                    Megamicros.Systems['mu32']['bus_address'],
                    Megamicros.Systems['mu32']['endpoint_in']
                )

            elif self.__usb.checkDeviceByVendorProduct(Megamicros.Systems['mu128']['vendor_id'], Megamicros.Systems['mu128']['product_id']):
                self.__system = Megamicros.Systems['mu128']
                self.__clock_divider_reference = DEFAULT_CLOCK_DIVIDER_REFERENCE
                self.__sync_delay = DEFAULT_SYNC_DELAY
                self.__usb.open(
                    Megamicros.Systems['mu128']['vendor_id'],
                    Megamicros.Systems['mu128']['product_id'],
                    Megamicros.Systems['mu128']['bus_address'],
                    Megamicros.Systems['mu128']['endpoint_in']
                )

            elif self.__usb.checkDeviceByVendorProduct(Megamicros.Systems['mu256']['vendor_id'], Megamicros.Systems['mu256']['product_id']):
                self.__system = Megamicros.Systems['mu256']
                self.__clock_divider_reference = DEFAULT_CLOCK_DIVIDER_REFERENCE
                self.__sync_delay = DEFAULT_SYNC_DELAY
                self.__usb.open(
                    Megamicros.Systems['mu256']['vendor_id'],
                    Megamicros.Systems['mu256']['product_id'],
                    Megamicros.Systems['mu256']['bus_address'],
                    Megamicros.Systems['mu256']['endpoint_in']
                )

            elif self.__usb.checkDeviceByVendorProduct(Megamicros.Systems['mu1024']['vendor_id'], Megamicros.Systems['mu1024']['product_id']):
                self.__system = Megamicros.Systems['mu1024']
                self.__clock_divider_reference = DEFAULT_CLOCK_DIVIDER_REFERENCE
                self.__sync_delay = DEFAULT_SYNC_DELAY
                self.__usb.open(
                    Megamicros.Systems['mu1024']['vendor_id'],
                    Megamicros.Systems['mu1024']['product_id'],
                    Megamicros.Systems['mu1024']['bus_address'],
                    Megamicros.Systems['mu1024']['endpoint_in']
                )

            else:
                raise MuException("No MegaMicros device found")

        except MuException as e:
            log.error(f"Error during MegaMicros device check and opening: {e}")
            raise

    def wait( self, duration: float=0 ) -> None:  
        """ Wait for a given duration in seconds

        Parameters:
        -----------
        duration : float
            The waiting duration in seconds
        """
        if duration > 0:
            time.sleep( duration )

        self.usb.asyncBulkTransferWait()
        self.usb.release()
        log.info( " .Megamicros acquisition process successfully ended" )

    def stop( self ) -> None:
        """ Stop data acquisition on the MegaMicros device
        """
        log.info( " .Stopping Megamicros acquisition process" )
        self.usb.asyncBulkTransferStop()
        self.usb.release()

    def run( self, *args, **kwargs ) -> None:
        """ Run data acquisition on the MegaMicros device through USB async bulk transfer
        """

        if len( args ) > 0:
            raise MuException( f"Run() method does not accept direct arguments" )

        self._set_run_settings( [], kwargs=kwargs )

        # 1024 systems not yet implemented
        if not self.__system['name'] in ['mu32', 'mu32usb2', 'mu32a', 'mu256', 'mu256h']:
            raise MuException(f"MegaMicros system {self.__system['name']} not supported yet for data acquisition")

        if self.channels_number == 0 :
            raise MuException("No channel activated for data acquisition")

        # Set USB configuration
        self.usb.setBuffersNumber( self.__usb_buffers_number )
        self.usb.setBufferSize( self.frame_length * self.channels_number * TRANSFER_DATAWORDS_SIZE )

        # verbose
        log.info( f" .Starting run execution on Megamicros device..." )
        log.info( f"  > Run infinite loop (duration=0)" if self.duration == 0 else f"  > Perform {self.duration}s run loop" )
        log.info( f"  > Sampling frequency: {self.sampling_frequency} Hz" )
        log.info( f"  > FPGA clockdiv value: {self.clockdiv}" )
        log.info( f"  > {len(self.mems)} activated microphones" )
        log.info( f"  > Activated microphones: {self.mems}" )
        log.info( f"  > MEMs sensibility: {self.mems_sensibility}" )
        log.info( f"  > {len(self.analogs)} activated analogic channels" )
        log.info( f"  > Activated analogic channels: {self.analogs }" )
        log.info( f"  > Analogics sensibility: {self.analogs_sensibility}" )
        log.info( f"  > Whether counter is activated: {'YES' if 0 in self.counters else 'NO'}" )
        log.info( f"  > Whether status is activated: {'YES' if 0 in self.status else 'NO'}" )
        log.info( f"  > Time activation (MEMS powering delay): {self.time_activation} ms" )
        log.info( f"  > Total channels number is {self.channels_number}" )
        log.info( f"  > Datatype: {str( self.datatype )}" )
        log.info( f"  > Frame length in samples number: {self.frame_length} samples" )
        log.info( f"  > Frame duration: {self.frame_duration} s ({self.frame_duration * 1000} ms)" )
        log.info( f"  > Frame size in bytes: {self.frame_length * self.channels_number * TRANSFER_DATAWORDS_SIZE}" )
        log.info( f"  > Number of USB transfer buffers: {self.__usb_buffers_number}" )
        log.info( f"  > USB queue length: {'infinite queuing' if self.queue_length == 0 else self.queue_length} (frames)" )
        log.info( f"  > USB queue size: {'infinite queuing' if self.usb.queue_size == 0 else self.usb.queue_size} (bytes)" )
        log.info( f"  > Starting from external triggering: {'True' if self.__start_trigg_status else 'False'}" )
        log.info( f"  > Local H5 recording {'on' if self.h5_recording else 'off'}" )

        # Claim USB interface
        self.usb.claim()

        # set device configuration
        try:
            self.__ctrlResetMu()
            self.__ctrlClockdiv( self.clockdiv, self.time_activation / 1000 )
            self.__ctrlTixels( 0 )
            self.__ctrlDatatype( self.datatype )
            self.__ctrlMems( request='activate', mems=self.mems )
            self.__ctrlCSA( counter=True if 0 in self.counters else False, status=True if 0 in self.status else False, analogs=self.analogs )
            self.__ctrlStart()

        except Exception as e:
            log.error(f"Error during device configuration: {e}")
            self.usb.release()
            raise

        # Run data acquisition through USB async bulk transfer
        try:
            self.usb.asyncBulkTransfer(self.duration)
        except Exception as e:
            log.error(f"Error during USB async bulk transfer: {e}")
            self.usb.release()
            raise


    def setSamplingFrequency( self, sampling_frequency: int ) -> None:
        """ Set the sampling frequency for next runs on the device. The clockdiv property is updated accordingly.
        
        Parameters:
        -----------
        sampling_frequency : float
            The sampling frequency (default is 50kHz or 48 kHz on Aikhous systems)
        """
        super().setSamplingFrequency(sampling_frequency)
        self.__clockdiv = ( self.__clock_divider_reference // self.sampling_frequency ) - 1

    def setClockdiv( self, clockdiv: int ) -> None:
        """ Set the clockdiv that state for the sampling frequency for next runs on the device. 
        The sampling frequency property is updated accordingly.

        Parameters:
        -----------
        clockdiv : int
            The clock divider (default is 9 for 50kHz or 48 kHz on Aikhous systems)
        """
        self.__clockdiv = clockdiv
        self.setSamplingFrequency(self.__clock_divider_reference // ( self.__clockdiv + 1 ))

    def setClockDividerReference( self, clock_divider_reference: int ) -> None:
        """ Set the clock divider reference that state for the sampling frequency for next runs on the device.
        The sampling frequency property is updated accordingly.
        This can be used for Aikhous systems that use a 480kHz clock divider reference instead of 500kHz for usual systems.

        Parameters:
        -----------
        clock_divider_reference : int
            The clock divider reference (default is 500kHz for usual systems, 480kHz for Aikhous systems)
        """
        self.__clock_divider_reference = clock_divider_reference
        self.setSamplingFrequency(self.__clock_divider_reference // ( self.__clockdiv + 1 ))

    def setStartTriggStatus( self, trigger_status: bool ) -> None:
        """ Set the start trigger status

        Parameters
        ----------
        trigger_status: bool
            The start trigger status (True for external hard trigger, False for internal soft trigger)
        """
        self.__start_trigg_status = trigger_status

    def setUsbBuffersNumber( self, number: int ) -> None:
        """ Set the USB buffers number used in USB the data acquisition process.
        Should never be set to less than 4 to ensure proper data transfer without overflow. 8 is a good default value.

        Parameters
        ----------
        number: int
            The USB buffers number
        """
        self.__usb_buffers_number = number

    def setCounter( self, counters: list[int] | bool ) -> None:
        """ Activate counters channels. Overload the parent setCounter method to considere multiple counters.
        """

        if isinstance( counters, bool ):
            if counters:
                self.__counters = [0]
            else:
                self.__counters = []
        else:
            self.__counters = counters

    def setCounters( self, counters: list[int] | bool ) -> None :
        """ Activate counters channels
        """

        if isinstance( counters, bool ):
            if counters:
                self.__counters = [0]
            else:
                self.__counters = []
        else:
            self.__counters = counters

    def setStatus( self, status: list[int] | bool) -> None :
        """ Activate status channels
        """

        if isinstance( status, bool ):
            if status:
                self.__status = [0]
            else:
                self.__status = []
        else:
            self.__status = status

    def setAnalogsSensibility( self, sensibility: float ) -> None:
        """ Set analogs sensibility
        
        Parameters:
        -----------
        sensibility : float
            The analogs sensibility in V/digit
        """

        self.__analogs_sensibility = sensibility

    def setTimeActivation( self, time_activation: int ) -> None:
        """ Set time activation after MEMs powering in milliseconds
        
        Parameters:
        -----------
        time_activation : int
            time activation after MEMs powering in milliseconds
        """

        self.__time_activation = time_activation

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
            if 'analogs' in kwargs:
                self.setActiveAnalogs( kwargs['analogs'] )
                del kwargs['analogs']

            if 'available_analogs' in kwargs:
                self.setAvailableAnalogs( kwargs['available_analogs'] )
                del kwargs['available_analogs']

            if 'counter' in kwargs:
                if isinstance( kwargs['counter'], list ) or isinstance( kwargs['counter'], tuple ):
                    self.setCounters( kwargs['counter'] )
                else:   
                    self.setCounter( kwargs['counter'] )
                del kwargs['counter']

            if 'counters' in kwargs:
                if isinstance( kwargs['counters'], list ) or isinstance( kwargs['counters'], tuple ):
                    self.setCounters( kwargs['counters'] )
                else:   
                    self.setCounter( kwargs['counters'] )
                del kwargs['counters']

            if 'sampling_frequency' in kwargs:
                self.setSamplingFrequency( kwargs['sampling_frequency'] )
                del kwargs['sampling_frequency']

            if 'clockdiv' in kwargs:
                self.setClockdiv( kwargs['clockdiv'] )
                del kwargs['clockdiv']

            if 'mems_sensibility' in kwargs:
                self.setMemsSensibility( kwargs['mems_sensibility'] )
                del kwargs['mems_sensibility']  

            if 'analogs_sensibility' in kwargs:
                self.setAnalogsSensibility( kwargs['analogs_sensibility'] )

            if 'queue_length' in kwargs:
                self.setQueueLength( kwargs['queue_length'] )
                del kwargs['queue_length']

            if 'time_activation' in kwargs:
                self.setTimeActivation( kwargs['time_activation'] )
                del kwargs['time_activation']

            super()._set_run_settings( [], kwargs )

        except Exception as e:
            raise MuException( f"Run failed on settings: {e}")


    def selftest(self, duration: int = DEFAULT_SELFTEST_DURATION) -> tuple[list[float], list[float]]:
        """
        @brief Perform a one-second recording test to obtain and update the Megamicros receiver settings.
        The test is performed with the default settings, not with the current settings. 
        Current settings are then updated with the tests results. 
        Check mems, analogs, status and counter channels.
        Update _available_mems and _available_analogs and others.
        The system should be detected before. 

        @param duration: duration of the selftest in seconds
        """

        # Compute MEMs energy using the bulk transfer method because the bulkRead method does not work on Windows
        if platform.system() == 'Windows':
            log.info(" .Performing selftest using bulk transfer method...")
            raise NotImplementedError( 'Usb.asyncBulkTransferWait() not implemented yet' )

        if not self.usb.isOpened():
            raise MuException("MegaMicros device is not opened")

        log.info(" .Performing selftest using bulk read method...")

        self.usb.claim()
        try:
            mems_number = self.__system['beams'] * MU_BEAM_MEMS_NUMBER
            analogs_number = self.__system['analogs']
            channels_number = mems_number + analogs_number + self.__system['counters'] + self.__system['status']
            frame_length = int( duration * self.sampling_frequency )
            buffer_size = channels_number * frame_length * TRANSFER_DATAWORDS_SIZE
            self.__ctrlResetMu()
            self.__ctrlClockdiv( DEFAULT_CLOCKDIV, DEFAULT_TIME_ACTIVATION / 1000 )
            self.__ctrlTixels( frame_length )
            self.__ctrlDatatype( 'int32' )
            self.__ctrlMems( request='activate', mems='all' )
            self.__ctrlCSA( counter=True, status=True, analogs='all' )
            self.__ctrlStart()
            bytes_read:bytearray = self.usb.syncBulkRead( 
                size=buffer_size, 
                time_out=USB_DEFAULT_TRANSFER_TIMEOUT 
            )
            self.__ctrlStop()

            if len( bytes_read ) != buffer_size:
                self.usb.release()
                raise MuException( f'Selftest failed: expected {buffer_size} bytes but got {len( bytes_read )} bytes' )

            log.info(" .Selftest completed successfully")

        except MuException as e:
            log.error(f"Error during selftest: {e}")
            self.usb.release()
            raise

        self.usb.release()

        # Check data length
        data = np.frombuffer( bytes_read, dtype=np.int32 )
        if len( data ) != frame_length * channels_number:
            # Windows platform failed on this test (Zadig driver issue ?)
            # Note that Zadig driver is based on libusb 0.1 porting for Windows while Python libusb is based on libusb 1.0
            if platform.system() == 'Windows':
                log.warning( f"Received {len(data)} data bytes instead of {frame_length * channels_number} ({frame_length} samples)" )
                if len( data ) > frame_length * channels_number:
                    log.warning( f"Windows platform detected --> Data length will be adjusted to {frame_length} samples." )
                    data = data[:frame_length * channels_number]
                else:
                    new_data_length = len( data ) // channels_number
                    log.warning( f"Windows platform detected --> Data length will be adjusted to {new_data_length*channels_number} ({new_data_length} samples)." )
                    if len( data ) % channels_number == 0:
                        log.warning( f"Removed exactly {frame_length - new_data_length} samples of {channels_number} channels each." )
                    else:
                        log.warning( f"Removed {frame_length * channels_number - len( data )} bytes than cannot be expressed as multiples of channels or samples number." )
                    data = data[:new_data_length * channels_number]
                    data_length = new_data_length
            else:
                raise MuException( f"Received {len(data)} data bytes instead of {frame_length * channels_number}" )
        

        # convert to float with sensibility factor
        if self.__system['name'] in ['mu32', 'mu32usb2', 'mu32a', 'mu256', 'mu256h']:

            # Reshape data to (channels, samples)
            data = data.reshape( ( channels_number, frame_length ), order='F' )

            # Get signals with sensibility factor
            mems_signal = data[1:mems_number+1].astype( np.float32 ) * self.mems_sensibility
            analogs_signal = data[mems_number+1:mems_number+analogs_number+1].astype( np.float32 ) * self.analogs_sensibility

            # Compute mean energy  
            mems_power = np.sum( mems_signal**2, axis=1 ) / frame_length
            if analogs_number > 0:
                analogs_power = np.sum( analogs_signal**2, axis=1 ) / frame_length
            else:
                analogs_power = np.array([])
                
            mems_power = np.where( mems_power > 0, 1, 0 )
            analogs_power = np.where( analogs_power > 1e-10 , 1, 0 )

            log.info( f" .Autotest results:" )
            log.info( f"  > equivalent recording time is: {frame_length / self.sampling_frequency} seconds" )
            log.info( f"  > Received {len(bytes_read)} data bytes: {frame_length} samples on {channels_number} channels")
            log.info( f"  > detected {len( np.where( mems_power > 0 )[0] )} active MEMs: {np.where( mems_power > 0 )[0].tolist()}" )
            if analogs_number > 0:
                log.info( f"  > detected {len( np.where( analogs_power > 0 )[0] )} active analogs: {np.where( analogs_power > 0 )[0].tolist()}" )
            else:
                log.info( f"  > detected no active analogs" )
            log.info( f"  > detected counter channel with values from {data[0][0]} to {data[0][-1]}" )
            log.info( f"  > estimated data lost: {data[0][-1] - data[0][0] + 1 - frame_length} samples" )
            log.info( f"  > detected status channel with values {data[channels_number-1][0]} <-> {data[channels_number-1][-1]}" )
            log.info( f" .Selftest endded successfully" )

            # Set available mems and analogs according to selftest results
            self.setAvailableMems(np.where(np.array(mems_power) > 0)[0].tolist())
            self.setAvailableAnalogs(np.where(np.array(analogs_power) > 0)[0].tolist())

            return mems_power.tolist(), analogs_power.tolist()
        else:
            raise MuException( f"Selftest not implemented for system type {self.__system['name']}" )
            


    def __ctrlWrite(self, request: int, data: bytes=b"", timeout=USB_DEFAULT_WRITE_TIMEOUT) -> None:
        """
        Send a control write USB request to the MegaMicros device

        Parameters
        ----------
        request: str
            USB request code
        data: bytes, optional
            USB request data (default to empty)

        Raises
        ------
        MuException
            In case of error during the USB transfer
        """
        try:
            if data == b"":
                self.__usb.ctrlWriteReset(request, timeout)
            else:
                self.__usb.ctrlWrite(request, data, timeout)
        
        except MuException as e:
            log.error(f"Error during control write request {request:#04x}: {e}")
            raise


    def __ctrlWriteReset(self, request: int, timeout=USB_DEFAULT_WRITE_TIMEOUT) -> None:
        """
        Send a control write USB request to the MegaMicros device with no data

        Parameters
        ----------
        request: str
            USB request code

        Raises
        ------
        MuException
            In case of error during the USB transfer
        """

        try:
            self.__usb.ctrlWriteReset(request, timeout)
        except MuException as e:
            log.error(f"Error during control write reset request {request:#04x}: {e}")
            raise


    def __ctrlTixels( self, samples_number ):
        """
        Set the samples number to be sent by the Megamicros system 
        """

        buf = create_string_buffer( 5 )
        buf[0] = MU_CMD_COUNT
        buf[1] = bytes(( samples_number & 0x000000ff, ) )
        buf[2] = bytes( ( ( ( samples_number & 0x0000ff00 ) >> 8 ),) )
        buf[3] = bytes( ( ( ( samples_number & 0x00ff0000 ) >> 16 ),) )
        buf[4] = bytes( ( ( ( samples_number & 0xff000000 ) >> 24 ),) )
        self.__ctrlWrite( 0xB4, buf, USB_DEFAULT_WRITE_TIMEOUT )


    def __ctrlResetAcq( self ):
        """
        Reset and purge fifo
        No documention found about the 0x06 code value. Use ctrlResetMu() instead for a complete system reset
        """
        buf = create_string_buffer( 1 )
        buf[0] = MU_CMD_RESET
        self.__ctrlWrite( 0xB0, buf, USB_DEFAULT_WRITE_TIMEOUT )
        buf[0] = MU_CMD_PURGE
        self.__ctrlWrite( 0xB0, buf, USB_DEFAULT_WRITE_TIMEOUT )


    def __ctrlResetFx3( self ):
        """
        Mu32 needs the 0xC4 command but not the 0xC2 unlike what is used on other programs...
        Regarding the Mu32 documentation, this control seems incomplete (/C0/C4/(B0 00)). 
        256 doc says that ctrlResetMu() is the complete sequence that should be used with fiber (/C0/C4/(B0 00)/C4/C0)
        while ctrlResetFx3() should only be used with USB with non-fiber USB.
        Please use ctrlResetMu() in all cases
        """
        try:
            self.__ctrlWriteReset( MU_CMD_FX3_RESET, USB_DEFAULT_WRITE_TIMEOUT )
            self.__ctrlWriteReset( MU_CMD_FX3_PH, USB_DEFAULT_WRITE_TIMEOUT )
        except Exception as e:
            log.error( f"Fx3 reset failed: {e}" ) 
            raise


    def __ctrlResetMu( self ):
        """
        full reset of Mu32 receiver using fiber or not
        """
        buf = create_string_buffer( 1 )
        buf[0] = MU_CMD_RESET
        try:
            self.__ctrlWriteReset( MU_CMD_FX3_RESET, USB_DEFAULT_WRITE_TIMEOUT )
            time.sleep( DEFAULT_TIME_ACTIVATION_RESET / 1000)
            self.__ctrlWriteReset( MU_CMD_FX3_PH, USB_DEFAULT_WRITE_TIMEOUT )
            time.sleep( DEFAULT_TIME_ACTIVATION_RESET / 1000)
            self.__ctrlWrite( MU_CMD_FPGA_0, buf, USB_DEFAULT_WRITE_TIMEOUT )
            time.sleep( DEFAULT_TIME_ACTIVATION_RESET / 1000)
            self.__ctrlWriteReset( MU_CMD_FX3_PH, USB_DEFAULT_WRITE_TIMEOUT )
            time.sleep( DEFAULT_TIME_ACTIVATION_RESET / 1000)
            self.__ctrlWriteReset( MU_CMD_FX3_RESET, USB_DEFAULT_WRITE_TIMEOUT )
            time.sleep( DEFAULT_TIME_ACTIVATION_RESET / 1000)
        except Exception as e:
            log.error( f"Mu32 reset failed: {e}" ) 
            raise

    def __ctrlResetFPGA( self ):
        """
        reset of FPGA
        """
        buf = create_string_buffer( 1 )
        buf[0] = MU_CMD_RESET
        try:
            self.__ctrlWrite( MU_CMD_FPGA_0, buf, USB_DEFAULT_WRITE_TIMEOUT )
        except Exception as e:
            log.error( f"FPGA reset failed: {e}" ) 
            raise


    def __ctrlClockdiv( self, clockdiv=0x09, time_activation=DEFAULT_TIME_ACTIVATION / 1000 ):
        """
        Init acq32: set sampling frequency and supplies power to microphones 
        """
        buf = create_string_buffer( 2 )
        buf[0] = MU_CMD_INIT
        buf[1] = clockdiv
        try:
            self.__ctrlWrite( MU_CMD_FPGA_1, buf, USB_DEFAULT_WRITE_TIMEOUT )
        except Exception as e:
            log.error( f"Mu32 clock setting and powerwing on microphones failed: {e}" ) 
            raise	

        """
        wait for mems activation
        """
        time.sleep( time_activation )


    def __ctrlDatatype( self, datatype='int32' ):
        """
        Set datatype
        ! note that float32 is not considered -> TO DO
        """ 
        buf = create_string_buffer( 2 )
        buf[0] = MU_CMD_DATATYPE
        if datatype=='int32':
            buf[1] = MU_CODE_DATATYPE_INT32
        elif datatype=='float32':
            buf[1] = MU_CODE_DATATYPE_FLOAT32
        else:
            raise MuException( 'Mu32::ctrlDatatype(): Unknown data type [%s]. Please, use [int32] or [float32]' % datatype )

        try:
            self.__ctrlWrite( MU_CMD_FPGA_1, buf, USB_DEFAULT_WRITE_TIMEOUT )
        except Exception as e:
            log.error( f"Mu32 datatype setting failed: {e}" ) 
            raise	


    def __ctrlMems( self, request:str, mems:str|list|tuple ='all' ):
        """
        Activate or deactivate MEMs

        Parameters
        ----------
        request: str
            The request type: activate or deactivate
        mems: str or array, optional
            The MEMs to activate or deactivate (default is 'all')
        """

        try:
            buf = create_string_buffer( 4 )
            buf[0] = MU_CMD_ACTIVE		
            buf[1] = 0x00					# module
            pluggable_mems_beams = self.__system['beams']
            if mems == 'all':
                if request == 'activate':
                    for beam in range( pluggable_mems_beams ):
                        buf[2] = beam		# beam number
                        buf[3] = 0xFF		# active MEMs map
                        self.__ctrlWrite( MU_CMD_FPGA_3, buf, USB_DEFAULT_WRITE_TIMEOUT )
                elif request == 'deactivate':
                    for beam in range( pluggable_mems_beams ):
                        buf[2] = beam		
                        buf[3] = 0x00		
                        self.__ctrlWrite( MU_CMD_FPGA_3, buf, USB_DEFAULT_WRITE_TIMEOUT )
                else:
                    raise MuException( 'Megamicros::ctrlMems(): Unknown parameter [%s]' % request )
            else:
                if request == 'activate':
                    map_mems = [0 for _ in range( pluggable_mems_beams )]
                    for mic in mems:
                        mic_index = mic % MU_BEAM_MEMS_NUMBER
                        beam_index = int( mic / MU_BEAM_MEMS_NUMBER )
                        if beam_index >= pluggable_mems_beams:
                            raise MuException( 'microphone index [%d] is out of range (should be less than %d)' % ( mic,  pluggable_mems_beams * MU_BEAM_MEMS_NUMBER ) )
                        map_mems[beam_index] += ( 0x01 << mic_index )

                    for beam in range( pluggable_mems_beams ):
                        if map_mems[beam] != 0:
                            buf[2] = beam
                            buf[3] = map_mems[beam]				
                            self.__ctrlWrite( MU_CMD_FPGA_3, buf, USB_DEFAULT_WRITE_TIMEOUT )
                else:
                    raise MuException( 'Megamicros::ctrlMems(): request [%s] is not implemented' % request )
        except Exception as e:
            log.error( f"Megamicros microphones activating failed: {e}" ) 
            raise	


    def __ctrlCSA( self, counter: bool, status: bool, analogs: str|list|tuple='all' ):
        """
        Activate or deactivate analogic, status and counter channels

        Parameters
        ----------
        counter: bool
            Activate or deactivate counter channel
        status: bool
            Activate or deactivate status channel
        analogs: list or tuple
            Activate or deactivate analogic channels
        """		

        pluggable_analogs_number = self.__system['analogs']
        if analogs == 'all':
            analogs = [i for i in range( pluggable_analogs_number)]
            
        buf = create_string_buffer( 4 )
        buf[0] = MU_CMD_ACTIVE		# command
        buf[1] = 0x00				# module
        buf[2] = 0xFF				# counter, status and analogic channels

        map_csa = 0x00
        if len( analogs ) > 0:
            for anl_index in analogs:
                map_csa += ( 0x01 << anl_index ) 
        if status:
            map_csa += ( 0x01 << 6 )
        if counter:
            map_csa += ( 0x01 << 7 )

        buf[3] = map_csa

        try:
            self.__ctrlWrite( MU_CMD_FPGA_3, buf, USB_DEFAULT_WRITE_TIMEOUT )
        except Exception as e:
            log.error( f"Mu32 analogic channels and status activating failed: {e}" ) 
            raise	


    def __ctrlStart( self ):
        """
        start acquiring by soft triggering
        """
        buf = create_string_buffer( 2 )
        buf[0] = MU_CMD_START
        buf[1] = 0x00

        try:
            self.__ctrlWrite( MU_CMD_FPGA_1, buf, USB_DEFAULT_WRITE_TIMEOUT )
        except Exception as e:
            log.error( f"Mu32 starting failed: {e}" ) 
            raise	

    def __ctrlStartTrig( self ):
        """
        start acquiring by external triggering
        """
        buf = create_string_buffer( 2 )
        buf[0] = MU_CMD_START
        buf[1] = 0x01										# front montant 
        #buf[1] = 0x01 + ( 0x01 << 7 )						# (état haut)

        try:
            self.__ctrlWrite( MU_CMD_FPGA_1, buf, USB_DEFAULT_WRITE_TIMEOUT )
        except Exception as e:
            log.error( f"Mu32 starting by external trig failed: {e}" ) 
            raise	

    def __ctrlStop( self ):
        """
        stop acquiring by soft triggering
        """
        buf = create_string_buffer( 2 )
        buf[0] = MU_CMD_STOP
        buf[1] = 0x00

        try:
            self.__ctrlWrite( MU_CMD_FPGA_1, buf, USB_DEFAULT_WRITE_TIMEOUT )
        except Exception as e:
            log.error( f"Mu32 stop failed: {e}" ) 
            raise


    def __ctrlPowerOffMic( self ):
        """
        powers off microphones
        """
        buf = create_string_buffer( 2 )
        buf[0] = MU_CMD_RESET

        try:
            self.__ctrlWrite( MU_CMD_FPGA_0, buf, USB_DEFAULT_WRITE_TIMEOUT )
        except Exception as e:
            log.error( f"Mu32 microphones powering off failed: {e}" ) 
            raise	

    def __iter__( self ) :
        """ Init iterations over the antenna data """

        self.__it = 0
        return self

    def __next__( self ) -> np.ndarray|StopIteration :
        """ next iteration over the antenna data 
        """
        
        try:
            data = self.usb.queue.get( timeout=USB_DEFAULT_QUEUE_TIMEOUT )
            # format data according to datatype
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
        """ Get the number of elemnts in the queue """

        if self.usb.queue is None:
            return 0
        else:
            return self.usb.queue_content
