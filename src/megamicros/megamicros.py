# megamicros.megamicros.py
#
# Copyright (c) 2024-2025 Bimea
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
@file megamicros.megamicros.py
@brief core module of the MegaMicros library
"""

from ctypes import addressof, byref, sizeof, create_string_buffer
import time
from .usb import Usb, USB_DEFAULT_WRITE_TIMEOUT
from .log import log
from .exception import MuException

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
MU_TRANSFER_DATAWORDS_SIZE		= 4											# Size of transfer words in bytes (same for in32 and float32 data type which always states for 32 bits (-> 4 bytes) )
MU_DEFAULT_DATATYPE             = 'int32'                                   # Datatype for FPGA megamicros data 

# Default run propertie's values
DEFAULT_TIME_ACTIVATION			= 1											# Waiting time after MEMs powering in seconds
DEFAULT_TIME_ACTIVATION_RESET	= 0.01										# Waiting time between commands of the MegaMicro device reset sequence  
DEFAULT_CLOCKDIV				= 0x09										# Default internal acquisition clock value
DEFAULT_SELFTEST_DURATION       = 0.1                                       # Default selftest duration in seconds     
DEFAULT_START_TRIGG_STATUS      = False								        # Default start trigger status (external hard (True) or internal soft (False))
DEFAULT_MEMS_SENSIBILITY        = 3.54e-6                                   # Default MEMS sensitivity (racine(2)/400 000 = 3,54µPa/digit)
DEFAULT_CLOCK_DIVIDER_REFERENCE = 500000                                    # Constant for the clock divider (500kHz)
AIKHOUS_CLOCK_DIVIDER_REFERENCE = 480000                                    # Constant for the clock divider for Aikhous systems (480kHz)
DEFAULT_SYNC_DELAY              = 10                                        # Default synchronization delay (10 for usual systems, 8 for Aikhous systems)
AIKHOUS_SYNC_DELAY              = 8                                         # Default synchronization delay for Aikhous systems

CONTROL_DATA_FAILURE            = False                                     # Perform control data failure if True
EXIT_ON_DATA_FAILURE            = True                                      # Exit on data failure (when data are lost during transfer)

MU_BUS_ADDRESS                  = 0x00                                      # Default USB bus address for MegaMicros devices

# Mu32 USB-2 properties
MU32_USB2_VENDOR_ID		                = 0xFE27                # Mu32 Usb-2 vendor Id
MU32_USB2_VENDOR_PRODUCT	            = 0xAC00                # Mu32 Usb-2 vendor product
MU32_USB2_ENDPOINT_IN                   = 0x81                  # Endpoint in address (seen 0x82 in some python libraries but the doc says 0x81...)
MU32_USB2_PLUGGABLE_BEAMS_NUMBER        = 4						# Max number of pluggable beams 
MU32_USB2_PLUGGABLE_ANALOGS_NUMBER      = 0                     # Max number of connectable annalogs

# Mu32 USB-3 properties
MU32_USB3_VENDOR_ID			            = 0xFE27                # Mu32 Usb-3 vendor Id
MU32_USB3_VENDOR_PRODUCT	            = 0xAC03                # Mu32 Usb-3 vendor product
MU32_USB3_ENDPOINT_IN                   = 0x81                  # Endpoint in address
MU32_USB3_PLUGGABLE_BEAMS_NUMBER        = 4						# Max number of pluggable beams 
MU32_USB3_PLUGGABLE_ANALOGS_NUMBER      = 2                     # Max number of connectable annalogs

# Mu128 USB-2 properties
MU128_USB2_VENDOR_ID		            = 0xFE27                # Mu128 Usb-2 vendor Id
MU128_USB2_VENDOR_PRODUCT	            = 0x0000                # Mu128 Usb-2 vendor product !!!!! UNKNOWN !!!!!
MU128_USB2_ENDPOINT_IN                   = 0x81                  # Endpoint in address
MU128_USB2_PLUGGABLE_BEAMS_NUMBER       = 16					# Max number of pluggable beams
MU128_USB2_PLUGGABLE_ANALOGS_NUMBER     = 0                     # Max number of connectable annalogs

# Mu256 USB properties
MU256_USB3_VENDOR_ID		            = 0xFE27                # Mu256 Usb-3 vendor Id
MU256_USB3_VENDOR_PRODUCT	            = 0xAC01                # Mu256 Usb-3 vendor product
MU256_USB3_ENDPOINT_IN                   = 0x81                  # Endpoint in address
MU256_USB3_PLUGGABLE_BEAMS_NUMBER       = 32					# Max number of pluggable beams for 256 systems
MU256_USB3_PLUGGABLE_ANALOGS_NUMBER     = 4                     # Max number of connectable annalogs

# Mu1024 properties
MU1024_USB3_VENDOR_ID		            = 0xFE27                # Mu256 Usb-3 vendor Id
MU1024_USB3_VENDOR_PRODUCT	            = 0xAC02                # Not known actually. Should be checked
MU1024_USB3_ENDPOINT_IN                   = 0x81                  # Endpoint in address
MU1024_USB3_PLUGGABLE_BEAMS_NUMBER      = 128					# Max number of pluggable beams for 1024 systems
MU1024_USB3_PLUGGABLE_ANALOGS_NUMBER    = 16                    # Max number of connectable annalogs


class MArray :
    """
    @class MArray
    @brief Base class to handle MegaMicros devices
    """

    def __init__(self):
        """
        @brief Constructor
        """
        self.__microphones_number: int=0                              # Available microphones on the antenna
        self.__active_microphones: list[int]=[]                       # Activated microphones
        self.__microphones_positions: list[list[float]]=[]            # Microphones positions vectors
        self.__counter: bool=False                                    # Counter activation flag
        self.__counter_skip: bool=False                               # Whether the counter is removed or not in output stream
        self.__status: bool=False                                     # Status activation flag
        self.__sampling_frequency: float=0.0                          # System sample rate for audio acquisition
        self.__datatype: str="int32"                                  # "int32" or "float32"
        self.__duration: int=0                                        # acquisition duration in seconds
        self.__frame_length: int=0                                    # frame length in samples number for data transfer

class Megamicros(MArray):
    """
    @class MegaMicros
    @brief Main class to handle MegaMicros devices. Support 32, 256 and 1024 systems
    """

    def __init__(self):
        """
        @brief Constructor
        """
        super().__init__()
        self.__usb: Usb=Usb()                                         # USB interface instance
        self.__pluggable_beams_number: int=0                          # pluggable beams on the antenna (connected or not)
        self.__available_mems: list[int]=[]                           # Available microphones (connected and ok on the antenna)
        self.__active_mems: list[int]=[]                              # Activated microphones
        self.__pluggable_analogs_number: int=0                        # pluggable analogs on the antenna (connected or not)
        self.__available_analogs: list[int]=[]                        # Available analogs (connected and ok on the antenna)
        self.__active_analogs: list[int]=[]                           # Activated analogs
        self.__mems_sensibility: float=3.54e-6                        # MEMS sensibility in Pa/digit (default to 3.54e-6 Pa/digit)
        self.__clock_divider_reference: int=0                         # Clock divider reference (sr = cdr/(clockdiv+1) ) 
        self.__clockdiv: float=9.0                                    # Clock divider (default to 9 for 50kHz or48kHz sampling frequencies)
        self.__sync_delay: int=10                                     # Default synchronization delay (10 for usual systems, 8 for Aikhous systems)
        self.__wait_delay: int=0                                      # Wait delay between start command and

        self.checkAndOpenDevice()
        log.info(" .Megamicros device initialized")

    def checkAndOpenDevice(self) -> None:
        """
        @brief Check and open the MegaMicros USB device
        @throw MuException in case of error during the USB transfer
        """
        try:
            if self.__usb.isOpened():
                raise MuException("MegaMicros device is already opened")

            if self.__usb.checkDeviceByVendorProduct(MU32_USB2_VENDOR_ID, MU32_USB2_VENDOR_PRODUCT):
                self.__pluggable_beams_number = MU32_USB2_PLUGGABLE_BEAMS_NUMBER
                self.__pluggable_analogs_number = MU32_USB2_PLUGGABLE_ANALOGS_NUMBER
                self.__clock_divider_reference = DEFAULT_CLOCK_DIVIDER_REFERENCE
                self.__sync_delay = DEFAULT_SYNC_DELAY
                self.__usb.open(MU32_USB2_VENDOR_ID, MU32_USB2_VENDOR_PRODUCT, MU_BUS_ADDRESS, MU32_USB2_ENDPOINT_IN)

            elif self.__usb.checkDeviceByVendorProduct(MU32_USB3_VENDOR_ID, MU32_USB3_VENDOR_PRODUCT):
                self.__pluggable_beams_number = MU32_USB3_PLUGGABLE_BEAMS_NUMBER
                self.__pluggable_analogs_number = MU32_USB3_PLUGGABLE_ANALOGS_NUMBER
                self.__clock_divider_reference = DEFAULT_CLOCK_DIVIDER_REFERENCE
                self.__sync_delay = DEFAULT_SYNC_DELAY
                self.__usb.open(MU32_USB3_VENDOR_ID, MU32_USB3_VENDOR_PRODUCT, MU_BUS_ADDRESS, MU32_USB3_ENDPOINT_IN)

            elif self.__usb.checkDeviceByVendorProduct(MU256_USB3_VENDOR_ID, MU256_USB3_VENDOR_PRODUCT):
                self.__pluggable_beams_number = MU256_USB3_PLUGGABLE_BEAMS_NUMBER
                self.__pluggable_analogs_number = MU256_USB3_PLUGGABLE_ANALOGS_NUMBER
                self.__clock_divider_reference = DEFAULT_CLOCK_DIVIDER_REFERENCE
                self.__sync_delay = DEFAULT_SYNC_DELAY
                self.__usb.open(MU256_USB3_VENDOR_ID, MU256_USB3_VENDOR_PRODUCT, MU_BUS_ADDRESS, MU256_USB3_ENDPOINT_IN)

            elif self.__usb.checkDeviceByVendorProduct(MU1024_USB3_VENDOR_ID, MU1024_USB3_VENDOR_PRODUCT):
                self.__pluggable_beams_number = MU1024_USB3_PLUGGABLE_BEAMS_NUMBER
                self.__pluggable_analogs_number = MU1024_USB3_PLUGGABLE_ANALOGS_NUMBER
                self.__clock_divider_reference = DEFAULT_CLOCK_DIVIDER_REFERENCE
                self.__sync_delay = DEFAULT_SYNC_DELAY
                self.__usb.open(MU1024_USB3_VENDOR_ID, MU1024_USB3_VENDOR_PRODUCT, MU_BUS_ADDRESS, MU1024_USB3_ENDPOINT_IN)

            else:
                raise MuException("No MegaMicros device found")

        except MuException as e:
            log.error(f"Error during MegaMicros device check and opening: {e}")
            raise



    def __ctrlWrite(self, request: int, data: bytes=b"", timeout=USB_DEFAULT_WRITE_TIMEOUT) -> None:
        """
        @brief Send a control write USB request to the MegaMicros device
        @param request: USB request code
        @param data: USB request data (default to empty)
        @throw MuException in case of error during the USB transfer
        """
        try:
            if data == b"":
                self.__usb.ctrlWriteReset(request, timeout)
            else:
                self.__usb.ctrlWrite(request, data, timeout)
        
        except MuException as e:
            log.error(f"Error during control write request {request:#04x}: {e}")
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
        self.__ctrlWrite( 0xB4, buf )


    def __ctrlResetAcq( self ):
        """
        Reset and purge fifo
        No documention found about the 0x06 code value. Use ctrlResetMu() instead for a complete system reset
        """
        buf = create_string_buffer( 1 )
        buf[0] = MU_CMD_RESET
        self.__ctrlWrite( 0xB0, buf )
        buf[0] = MU_CMD_PURGE
        self.__ctrlWrite( 0xB0, buf )


    def __ctrlResetFx3( self ):
        """
        Mu32 needs the 0xC4 command but not the 0xC2 unlike what is used on other programs...
        Regarding the Mu32 documentation, this control seems incomplete (/C0/C4/(B0 00)). 
        256 doc says that ctrlResetMu() is the complete sequence that should be used with fiber (/C0/C4/(B0 00)/C4/C0)
        while ctrlResetFx3() should only be used with USB with non-fiber USB.
        Please use ctrlResetMu() in all cases
        """
        try:
            self.__ctrlWriteReset( MU_CMD_FX3_RESET, time_out=1 )
            self.__ctrlWriteReset( MU_CMD_FX3_PH, time_out=1 )
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
            self.__ctrlWriteReset( MU_CMD_FX3_RESET, time_out=1 )
            time.sleep( DEFAULT_TIME_ACTIVATION_RESET )
            self.__ctrlWriteReset( MU_CMD_FX3_PH, time_out=1 )
            time.sleep( DEFAULT_TIME_ACTIVATION_RESET )
            self.__ctrlWrite( MU_CMD_FPGA_0, buf )
            time.sleep( DEFAULT_TIME_ACTIVATION_RESET )
            self.__ctrlWriteReset( MU_CMD_FX3_PH, time_out=1 )
            time.sleep( DEFAULT_TIME_ACTIVATION_RESET )
            self.__ctrlWriteReset( MU_CMD_FX3_RESET, time_out=1 )
            time.sleep( DEFAULT_TIME_ACTIVATION_RESET )
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
            self.__ctrlWrite( MU_CMD_FPGA_0, buf )
        except Exception as e:
            log.error( f"FPGA reset failed: {e}" ) 
            raise


    def __ctrlClockdiv( self, clockdiv=0x09, time_activation=DEFAULT_TIME_ACTIVATION ):
        """
        Init acq32: set sampling frequency and supplies power to microphones 
        """
        buf = create_string_buffer( 2 )
        buf[0] = MU_CMD_INIT
        buf[1] = clockdiv
        try:
            self.__ctrlWrite( MU_CMD_FPGA_1, buf )
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
            self.__ctrlWrite( MU_CMD_FPGA_1, buf )
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
            if mems == 'all':
                if request == 'activate':
                    for beam in range( self.__pluggable_beams_number ):
                        buf[2] = beam		# beam number
                        buf[3] = 0xFF		# active MEMs map
                        self.__ctrlWrite( MU_CMD_FPGA_3, buf )
                elif request == 'deactivate':
                    for beam in range( self.__pluggable_beams_number ):
                        buf[2] = beam		
                        buf[3] = 0x00		
                        self.__ctrlWrite( MU_CMD_FPGA_3, buf )
                else:
                    raise MuException( 'Megamicros::ctrlMems(): Unknown parameter [%s]' % request )
            else:
                if request == 'activate':
                    map_mems = [0 for _ in range( self.__pluggable_beams_number )]
                    for mic in mems:
                        mic_index = mic % MU_BEAM_MEMS_NUMBER
                        beam_index = int( mic / MU_BEAM_MEMS_NUMBER )
                        if beam_index >= self.__pluggable_beams_number:
                            raise MuException( 'microphone index [%d] is out of range (should be less than %d)' % ( mic,  self.__pluggable_beams_number*MU_BEAM_MEMS_NUMBER ) )
                        map_mems[beam_index] += ( 0x01 << mic_index )

                    for beam in range( self.__pluggable_beams_number ):
                        if map_mems[beam] != 0:
                            buf[2] = beam
                            buf[3] = map_mems[beam]				
                            self.__ctrlWrite( MU_CMD_FPGA_3, buf )
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

        if analogs == 'all':
            analogs = [i for i in range( self.__pluggable_analogs_number )]
            
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
            self.__ctrlWrite( MU_CMD_FPGA_3, buf )
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
            self.__ctrlWrite( MU_CMD_FPGA_1, buf )
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
            self.__ctrlWrite( MU_CMD_FPGA_1, buf )
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
            self.__ctrlWrite( MU_CMD_FPGA_1, buf )
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
            self.__ctrlWrite( MU_CMD_FPGA_0, buf )
        except Exception as e:
            log.error( f"Mu32 microphones powering off failed: {e}" ) 
            raise	
