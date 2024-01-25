# megamicros.core.mu.py base class for antenna connected to a remote antenna server
#
# Copyright (c) 2024 Sorbonne Université
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


""" Provide the class for antenna with MEMs signals extracted from a megamicros antenna

Documentation
-------------
MegaMicros documentation is available on https:#readthedoc.biimea.io
"""


import numpy as np
import enum
import usb1
import libusb1
import json
import threading
import time
from ctypes import addressof, byref, sizeof, create_string_buffer, CFUNCTYPE

from megamicros.log import log
from megamicros.exception import MuException
import megamicros.core.base as base


# Mu32 USB-2 properties
MU32_USB2_VENDOR_ID		                = 0xFE27                # Mu32 Usb-2 vendor Id
MU32_USB2_VENDOR_PRODUCT	            = 0xAC00                # Mu32 Usb-2 vendor product
MU32_USB2_BUS_ADDRESS		            = 0x81                  # seen 0x82 in some python libraries but the doc says 0x81...
MU32_USB2_PLUGGABLE_BEAMS_NUMBER        = 4						# Max number of pluggable beams 
MU32_USB2_PLUGGABLE_ANALOGS_NUMBER      = 0                     # Max number of connectable annalogs

# Mu32 USB-3 properties
MU32_USB3_VENDOR_ID			            = 0xFE27                # Mu32 Usb-3 vendor Id
MU32_USB3_VENDOR_PRODUCT	            = 0xAC03                # Mu32 Usb-3 vendor product
MU32_USB3_BUS_ADDRESS		            = 0x81                  # Usb bus address (seen 0x82 in some python libraries but the doc says 0x81...)
MU32_USB3_PLUGGABLE_BEAMS_NUMBER        = 4						# Max number of pluggable beams 
MU32_USB3_PLUGGABLE_ANALOGS_NUMBER      = 0                     # Max number of connectable annalogs

# Mu128 USB-2 properties
MU128_USB2_VENDOR_ID		            = 0xFE27                # Mu128 Usb-2 vendor Id
MU128_USB2_VENDOR_PRODUCT	            = 0x0000                # Mu128 Usb-2 vendor product !!!!! UNKNOWN !!!!!
MU128_USB2_BUS_ADDRESS		            = 0x81					# seen 0x82 in some python libraries but the doc says 0x81...
MU128_USB2_PLUGGABLE_BEAMS_NUMBER       = 16					# Max number of pluggable beams
MU128_USB2_PLUGGABLE_ANALOGS_NUMBER     = 0                     # Max number of connectable annalogs

# Mu256 USB properties
MU256_USB3_VENDOR_ID		            = 0xFE27                # Mu256 Usb-3 vendor Id
MU256_USB3_VENDOR_PRODUCT	            = 0xAC01                # Mu256 Usb-3 vendor product
MU256_USB3_BUS_ADDRESS		            = 0x81                  # Usb bus address (seen 0x82 in some python libraries but the doc says 0x81...)
MU256_USB3_PLUGGABLE_BEAMS_NUMBER       = 32					# Max number of pluggable beams for 256 systems
MU256_USB3_PLUGGABLE_ANALOGS_NUMBER     = 4                     # Max number of connectable annalogs

# Mu1024 properties
MU1024_USB3_VENDOR_ID		            = 0xFE27                # Mu256 Usb-3 vendor Id
MU1024_USB3_VENDOR_PRODUCT	            = 0xAC02                # Not known actually. Should be checked 
MU1024_USB3_BUS_ADDRESS		            = 0x81	                # Usb bus address (seen 0x82 in some python libraries but the doc says 0x81...)
MU1024_USB3_PLUGGABLE_BEAMS_NUMBER      = 128					# Max number of pluggable beams for 1024 systems
MU1024_USB3_PLUGGABLE_ANALOGS_NUMBER    = 16                    # Max number of connectable annalogs

# Cypress FX3 commands
MU_CYPRESS_VENDOR_ID		            = 0x04b4
MU_CYPRESS_VENDOR_PRODUCT	            = 0x00bc
MU_CYPRESS_BUS_ADDRESS		            = 0x81
MU_CYPRESS_CMD_FX3_RESET	            = 0xA0					# Init FX3 usb controler using Cypress reset command


# System names
MU32_SYSTEM_NAME				        = 'Mu32'
MU32USB2_SYSTEM_NAME			        = 'Mu32-USB2'
MU128_SYSTEM_NAME				        = 'Mu128'
MU256_SYSTEM_NAME				        = 'Mu256'
MU1024_SYSTEM_NAME				        = 'Mu1024'


# USB properties
USB_DEFAULT_TIMEOUT				        = 1000                              # Default timeout for USB commands
USB_RECIPIENT_DEVICE			        = 0x00  
USB_REQUEST_TYPE_VENDOR			        = 0x40
USB_ENDPOINT_OUT				        = 0x00
USB_DEFAULT_BUFFERS_NUMBER		        = 8
USB_DEFAULT_BUFFER_LENGTH		        = base.DEFAULT_FRAME_LENGTH         # Default buffer length in samples number: same as frame length


# MegaMicro hardware commands
MU_CMD_RESET					= b'\x00'									# Reset: power off the microphones
MU_CMD_INIT						= b'\x01'									# Sampling frequency setting
MU_CMD_START					= b'\x02'									# Acquisition running command
MU_CMD_STOP						= b'\x03'									# Acquisition stopping command
MU_CMD_COUNT					= b'\x04'									# Number of expected samples for next acqusition running
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
MU_CMD_DATATYPE					= b'\x09'									# Set datatype


# MemgaMicro hardware code values																	
MU_CODE_DATATYPE_INT32			= b'\x00'									# Int32 datatype code
MU_CODE_DATATYPE_FLOAT32		= b'\x01'									# Float32 datatype code


# MegaMicro receiver properties
MU_BEAM_MEMS_NUMBER				= 8											# MEMS number per beam
MU_MEMS_UQUANTIZATION			= 24										# MEMs unsigned quantization 
MU_MEMS_QUANTIZATION			= MU_MEMS_UQUANTIZATION - 1					# MEMs signed quantization 
MU_MEMS_AMPLITUDE				= 2**MU_MEMS_QUANTIZATION					# MEMs maximal amlitude value for "int32" data type
MU_MEMS_SENSIBILITY				= 1/(MU_MEMS_AMPLITUDE*10**(-26/20)/3.17)	# MEMs sensibility factor (-26dBFS for 104 dB that is 3.17 Pa)
MU_TRANSFER_DATAWORDS_SIZE		= 4											# Size of transfer words in bytes (same for in32 and float32 data type which always states for 32 bits (-> 4 bytes) )


# Default run propertie's values
DEFAULT_TIME_ACTIVATION			= 1											# Waiting time after MEMs powering in seconds
DEFAULT_TIME_ACTIVATION_RESET	= 0.01										# Waiting time between commands of the MegaMicro device reset sequence  
DEFAULT_CLOCKDIV				= 0x09										# Default internal acquisition clock value
DEFAULT_SELFTEST_DURATION       = 0.1                                       # Default selftest duration in seconds     
DEFAULT_START_TRIGG_STATUS      = False								        # Default start trigger status (external hard (True) or internal soft (False))


# =============================================================================
# Exception dedicaced to Megamicros antenna systems
# =============================================================================

class MuUsbException( MuException ):
    """Exception base class for Megamicros Winsokets systems """
    
    def __init__( self, message: str="" ):
        super().__init__( message )


# =============================================================================
# The Megamicros base class
# =============================================================================


class Megamicros( base.MemsArray ):
    """ MEMs array class with input stream connected to a remote megamicros server.

    """
    class SystemType( enum.Enum ):
        """ Megamicros antenna type enumeration

        Values
        ------
        unknown: 0
            no megamicros type specified
        mu32usb2: 1
            32 channels megamicros device with USB2 port
        mu32: 2
            32 channels megamicros device with USB3 port
        mu128: 3
            128 channels megamicros device with USB2 port (deprecated)
        mu256: 4
            256 channels megamicros device with USB3/OF port
        mu1024: 5
            1024 channels megamicros device with USB3/OF port
        """

        unknown = 0
        mu32usb2 = 1
        mu32 = 2
        mu128 = 3
        mu256 = 4
        mu1024 = 5

        def __str__( self ):
            """ Convert a megamicros type integer code into its string enumeration """
            if self == self.unknown:
                return "Unknown"
            elif self == self.mu32usb2:
                return "Mu32-USB2"
            elif self == self.mu32:
                return "Mu32"
            elif self == self.mu128:
                return "Mu128"
            elif self == self.mu256:
                return "Mu256"
            elif self == self.mu1024:
                return "Mu1024"
            else:
                return "Unknown megamicros type"  

        def __int__( self ):
            """ Convert a datatype enumeration into its integer code """
            if self == self.unknown:
                return 0
            elif self == self.mu32usb2:
                return 1
            elif self == self.mu32:
                return 2
            elif self == self.mu128:
                return 3
            elif self == self.mu256:
                return 4
            elif self == self.mu1024:
                return 5
            else:
                return -1


    __system_type: SystemType = SystemType.unknown
    __usb_vendor_id = 0
    __usb_vendor_product = 0
    __usb_bus_address = 0
    __pluggable_beams_number = 0
    __pluggable_analogs_number = 0
    __start_trigg_status = DEFAULT_START_TRIGG_STATUS
    __clockdiv = DEFAULT_CLOCKDIV
    __usb_handle: usb1.USBDeviceHandle | None= None
    __usb_buffer_length = USB_DEFAULT_BUFFER_LENGTH
    __usb_buffers_number = USB_DEFAULT_BUFFERS_NUMBER

    @property
    def start_trigg_status( self ) -> int:
        return self.__start_trigg_status

    @property
    def usb_buffer_length( self ) -> int:
        return self.__usb_buffer_length
    
    @property
    def usb_buffers_number( self ) -> int:
        return self.__usb_buffers_number
    
    @property
    def clockdiv( self ) -> int:
        return self.__clockdiv

    def setStartTriggStatus( self, status: bool ) -> None:
        """ Set the start trigger status

        Parameters
        ----------
        status: bool
            The start trigger status (True for external hard trigger, False for internal soft trigger)
        """
        self.__start_trigg_status = status

    def setUsbBufferLength( self, length: int ) -> None:
        """ Set the USB buffer length in samples number

        Parameters
        ----------
        length: int
            The USB buffer length in samples number
        """
        self.__usb_buffer_length = length

    def setUsbBuffersNumber( self, number: int ) -> None:
        """ Set the USB buffers number

        Parameters
        ----------
        number: int
            The USB buffers number
        """
        self.__usb_buffers_number = number

    def setSamplingFrequency( self, sampling_frequency: float ) -> None :
        """ Overload the parent method to set the clockdiv property on FPGA
        
        Parameters:
        -----------
        sampling_frequency : float
            The sampling frequency (default is 50kHz)
        """

        # Set clockdiv property
        self.__clockdiv = int( ( 500000 - sampling_frequency ) / sampling_frequency )

        if self.__clockdiv < 9:
            raise MuUsbException( f"Sampling frequency {sampling_frequency} is not valid (clockdiv={self.__clockdiv}<9): limit is 50kHz" )

        # Set parent property
        super().setSamplingFrequency( ( self.__clockdiv + 1 )/500000 )
        log.info( f" .Set sampling frequency to {self.sampling_frequency} Hz" )


    def __init__( self, **kwargs ):
        """ Connect the antenna input stream to a megamicros antenna 

        The connection to the remote server is verified. If the server is not available, an exception is raised. 

        Parameters
        ----------
        host: str
            The remote host address
        port: int, optional
            The remote port (default is 9002)
        """

        # Init base class
        super().__init__( kwargs=kwargs )

        # Set Megamicros settings
        if len( kwargs ) > 0:
            self._set_settings( [], kwargs )

        # Check USB megamicros device
        self.__check_device()

        # Autotest for getting antenna properties
        mems_power, analogs_power = self.__selftest()

        self.setAvailableMems( np.where( mems_power > 0 )[0].tolist() )
        self.setAvailableAnalogs( np.where( analogs_power > 0 )[0].tolist() )


    def _set_settings( self, args, kwargs ) -> None :
        """ Set settings for Megamicros objects 
        
        Parameters
        ----------
        args: array
            direct arguments of the run function
        kwargs: array
            named arguments of the run function
        """

        # Check direct args
        if len( args ) != 0:
            raise MuUsbException( "Direct arguments are not accepted" )
        
        try:  
            log.info( f" .Installing Megamicros settings..." )

            if 'usb_buffers_number' in kwargs:
                self.setUsbBuffersNumber(  kwargs['usb_buffers_number'] )

            if 'usb_buffer_length' in kwargs:
                self.setUsbBufferLength(  kwargs['usb_buffer_length'] )

        except Exception as e:
            raise MuUsbException( f"Init settings failed: {e}")




    def __check_device( self ):
        """ Check megamicros devices connected to the host

        Populate class properties about devices connected to the host
        Throw an exception if no device is found
        """

        log.info(' .Checking usb devices...')

        with usb1.USBContext() as context:

            for usb_device in context.getDeviceIterator( skip_on_error=True ):
                device_vendor_id = usb_device.getVendorID()
                device_product_id = usb_device.getProductID()
                if device_vendor_id == MU32_USB2_VENDOR_ID and device_product_id == MU32_USB2_VENDOR_PRODUCT:
                    log.info(' .Found Megamicros [Mu32-USB2] device')
                    self.__system_type = self.SystemType.mu32usb2
                    self.__usb_vendor_id = device_vendor_id
                    self.__usb_vendor_product = device_product_id
                    self.__usb_bus_address = MU32_USB2_BUS_ADDRESS
                    self.__pluggable_beams_number = MU32_USB2_PLUGGABLE_BEAMS_NUMBER
                    self.__pluggable_analogs_number = MU32_USB2_PLUGGABLE_ANALOGS_NUMBER
                    break
                elif device_vendor_id == MU32_USB3_VENDOR_ID and device_product_id == MU32_USB3_VENDOR_PRODUCT:
                    log.info(' .Found Megamicros [Mu32] device')
                    self.__system_type = self.SystemType.mu32
                    self.__usb_vendor_id = device_vendor_id
                    self.__usb_vendor_product = device_product_id
                    self.__usb_bus_address = MU32_USB3_BUS_ADDRESS
                    self.__pluggable_beams_number = MU32_USB3_PLUGGABLE_BEAMS_NUMBER
                    self.__pluggable_analogs_number = MU32_USB3_PLUGGABLE_ANALOGS_NUMBER
                    break
                elif device_vendor_id == MU128_USB2_VENDOR_ID and device_product_id == MU128_USB2_VENDOR_PRODUCT:
                    log.info(' .Found Megamicros [Mu128] device')
                    self.__system_type = self.SystemType.mu128
                    self.__usb_vendor_id = device_vendor_id
                    self.__usb_vendor_product = device_product_id
                    self.__usb_bus_address = MU128_USB2_BUS_ADDRESS
                    self.__pluggable_beams_number = MU128_USB2_PLUGGABLE_BEAMS_NUMBER
                    self.__pluggable_analogs_number = MU128_USB2_PLUGGABLE_ANALOGS_NUMBER
                    break
                elif device_vendor_id == MU256_USB3_VENDOR_ID and device_product_id == MU256_USB3_VENDOR_PRODUCT:
                    log.info(' .Found Megamicros [Mu256] device')
                    self.__system_type = self.SystemType.mu256
                    self.__usb_vendor_id = device_vendor_id
                    self.__usb_vendor_product = device_product_id
                    self.__usb_bus_address = MU256_USB3_BUS_ADDRESS
                    self.__pluggable_beams_number = MU256_USB3_PLUGGABLE_BEAMS_NUMBER
                    self.__pluggable_analogs_number = MU256_USB3_PLUGGABLE_ANALOGS_NUMBER
                    break
                elif device_vendor_id == MU1024_USB3_VENDOR_ID and device_product_id == MU1024_USB3_VENDOR_PRODUCT:
                    log.info(' .Found Megamicros [Mu1024] device')
                    self.__system_type = self.SystemType.mu1024
                    self.__usb_vendor_id = device_vendor_id
                    self.__usb_vendor_product = device_product_id
                    self.__usb_bus_address = MU1024_USB3_BUS_ADDRESS
                    self.__pluggable_beams_number = MU1024_USB3_PLUGGABLE_BEAMS_NUMBER
                    self.__pluggable_analogs_number = MU1024_USB3_PLUGGABLE_ANALOGS_NUMBER
                    break
                elif device_vendor_id == MU_CYPRESS_VENDOR_ID and device_product_id == MU_CYPRESS_VENDOR_PRODUCT:
                    log.warning( f"Found Cypress device. If USB device is not present you may face to USB connection problem. Please disconnect or run usb soft disconnecting program." )

            if self.__system_type == self.SystemType.unknown:
                raise MuUsbException( 'No Megamicros device found' )

            # Try to connect to the device
            handle = context.openByVendorIDAndProductID( 
                self.__usb_vendor_id, 
                self.__usb_vendor_product,
                skip_on_error=True,
            )

            if handle is None:
                raise MuUsbException( 'Failed to connect to USB device: the device may be disconnected or user not allowed to access' )
            else:
                log.info( f' .Connected on USB device {self.__usb_vendor_id:04x}:{self.__usb_vendor_product:04x}' )

            # try to claim the device
            try:
                with handle.claimInterface( 0 ):
                    pass
            except Exception as e:
                raise MuUsbException( f'USB device buzy: cannot claim: {e}' )
            

            # Print device characteristics
            log.info( f" .Found following device {self.__usb_vendor_id:04x}:{self.__usb_vendor_product:04x} characteristics :" )
            log.info( f"  > Bus number: {usb_device.getBusNumber()}" )
            log.info( f"  > Ports number: {usb_device.getPortNumber()}" )
            log.info( f"  > Device address: {usb_device.getDeviceAddress()} ({usb_device.getDeviceAddress():04x})" )
            log.info( f"  > Device name: {usb_device.getProduct()}" )
            log.info( f"  > Manufacturer: {usb_device.getManufacturer()}" )
            log.info( f"  > Serial number: {usb_device.getSerialNumber()}" )

            deviceSpeed =  usb_device.getDeviceSpeed()
            if deviceSpeed  == libusb1.LIBUSB_SPEED_LOW:
                log.info( f"  > Device speed:  [LOW SPEED] (The OS doesn\'t report or know the device speed)" )
            elif deviceSpeed == libusb1.LIBUSB_SPEED_FULL:
                log.info( f"  > Device speed:  [FULL SPEED] (The device is operating at low speed (1.5MBit/s))" )
            elif deviceSpeed == libusb1.LIBUSB_SPEED_HIGH:
                log.info( f"  > Device speed:  [HIGH SPEED] (The device is operating at full speed (12MBit/s))" )
            elif deviceSpeed == libusb1.LIBUSB_SPEED_SUPER:
                log.info( f"  > Device speed:  [SUPER SPEED] (The device is operating at high speed (480MBit/s))" )
            elif deviceSpeed == libusb1.LIBUSB_SPEED_SUPER_PLUS:
                log.info( f"  > Device speed:  [SUPER PLUS SPEED] (The device is operating at super speed (5000MBit/s))" )
            elif deviceSpeed == libusb1.LIBUSB_SPEED_UNKNOWN:
                log.info( f"  > Device speed:  [LIBUSB_SPEED_UNKNOWN] (The device is operating at unknown speed)" )
            else:
                log.info( f"  > Device speed:  [?] (The device is operating at unknown speed)" )


    def _check_settings( self ) -> None :
        """ Check settings values for Megamicros and parents settings """

        super()._check_settings()

        if self.usb_buffer_length != self.frame_length:
            log.warning( f" .USB buffer length ({self.usb_buffer_length}) and frame length ({self.frame_length}) should be the same" )
            log.info( f" .Set usb_buffer_length to {self.frame_length} samples" )
            self.setUsbBufferLength( self.frame_length )


    def run( self, *args, **kwargs ) :
        """ The main run method that runs the Megamicros antenna """

        if len( args ) > 0:
            raise MuUsbException( f"Run() method does not accept direct arguments" )
                
        # Set all settings
        # Run does not call the super().run() method so that we have to handle all settings here      
        try:
            super()._set_settings( [], kwargs=kwargs )
            self._set_settings( [], kwargs=kwargs )

        except Exception as e:
            raise MuUsbException( f"Cannot run: settings loading failed ({type(e).__name__}): {e}" )
            
        # Set job on 'run': this is the only job available for Megamicros 
        self.setJob( 'run' )

        # Check settings values
        try:
            self._check_settings()
        except Exception as e:
            raise MuUsbException( f"Unable to execute run: control failure  ({type(e).__name__}): {e}" )

        # verbose
        buffer_words_length = self.usb_buffer_length * self.channels_number
        log.info( f" .Starting run execution" )
        log.info( f"  > Run infinite loop (duration=0)" if self.duration == 0 else f"  > Perform a {self.duration}s run loop" )
        log.info( f"  > {self.mems_number} activated microphones" )
        log.info( f"  > Activated microphones: {self.mems}" )
        log.info( f"  > MEMs sensibility: {self.sensibility}" )
        log.info( f"  > {self.analogs_number} activated analogic channels" )
        log.info( f"  > Activated analogic channels: {self.analogs }" )
        log.info( f"  > Whether counter is activated: {self.counter}" )
        log.info( f"  > Whether status is activated: {self.status}" )
        log.info( f"  > Total channels number is {self.channels_number}" )
        log.info( f"  > Datatype: {str( self.datatype )}" )
        log.info( f"  > Number of USB transfer buffers: {self.usb_buffers_number}" )
        log.info( f"  > Frame length in samples number: {self.frame_length} samples")
        log.info( f"  > Buffer length in samples number: {self.usb_buffer_length} samples ({self.usb_buffer_length*1000/self.sampling_frequency} ms duration)" )			
        log.info( f"  > Buffer length in 32 bits words number: {self.usb_buffer_length}x{self.channels_number}={buffer_words_length} ({buffer_words_length*MU_TRANSFER_DATAWORDS_SIZE} bytes)" )
        log.info( f"  > starting from external triggering: {'True' if self.start_trigg_status else 'False'}" )
        log.info( f"  > Local H5 recording {'on' if self.h5_recording else 'off'}" )

        # Check if the USB device is connected and free
        if self.__system_type == self.SystemType.unknown:
            raise MuUsbException( 'Cannot start run process: USB device not connected' )
        
        if self.__usb_handle is not None:
            raise MuUsbException( 'Cannot perform run process: USB device buzy' )

        # Start the timer if a limited execution time is requested
        # In this case, the timeout causes a stop command to be sent to the server
        # We have then to wait for the remote server to end the transfer
        if self.duration > 0 :
            self._thread_timer = threading.Timer( self.duration, self._run_endding )
            self._thread_timer_flag = True
            self._thread_timer.start()

        # Start run thread
        self._async_transfer_thread = threading.Thread( target= self.__run_thread )
        self._async_transfer_thread.start()


    def __run_thread( self ) -> None :
        """ Start run execution

        Start FPGA, listen to the Megamicros USB interface and post data in the internal queue
        """

        try:
            log.info( " .Run thread execution started" )
            
            self.setRunningFlag( True )
            with usb1.USBContext() as context:

                self.__usb_handle = context.openByVendorIDAndProductID( 
                    self.__usb_vendor_id, 
                    self.__usb_vendor_product,
                    skip_on_error=True,
                )

                if self.__usb_handle is None:
                    raise MuUsbException( 'Failed to connect to USB device: the device may be disconnected or user not allowed to access' )

                log.info( f' .Connected on USB device {str( self.__system_type )}: {self.__usb_vendor_id:04x}:{self.__usb_vendor_product:04x}' )

                # Claim the device
                with self.__usb_handle.claimInterface( 0 ):

                    # Init FPGA and send acquisition starting command
                    self.__ctrlResetMu()
                    self.__ctrlClockdiv( self.clockdiv, DEFAULT_TIME_ACTIVATION )
                    self.__ctrlTixels( 0 )
                    self.__ctrlDatatype( self.datatype )
                    self.__ctrlMems( request='activate', mems=self.mems )
                    self.__ctrlCSA( counter=self.counter, status=self.status, analogs=self.analogs )
                    if self.start_trigg_status:
                        self.__ctrlStartTrig()
                    else:
                        self.__ctrlStart()

                    # Open H5 file if recording on
                    if self.h5_recording:
                        self.h5_start()

                    # Allocate the list of transfer objects
                    transfer_list: list[usb1.USBTransfer] = []
                    buffer_size = self.usb_buffer_length * self.channels_number * MU_TRANSFER_DATAWORDS_SIZE
                    for id in range( self.usb_buffers_number ):
                        transfer = self.__usb_handle.getTransfer()
                        transfer.setBulk(
                            usb1.ENDPOINT_IN | self.__usb_bus_address,
                            buffer_size,
                            callback=self.__callback,
                            user_data = id,
                            timeout=USB_DEFAULT_TIMEOUT
                        )
                        transfer_list.append( transfer )
                        transfer.submit()

                    # Start the recording loop
                    while self.running:

                        # Main recording loop.
                        # Waits for pending tranfers while there are any.
                        # Once a transfer is finished, handleEvents() trigers callback  
                        while any( x.isSubmitted() for x in transfer_list ):
                            context.handleEvents()

                        log.info( f" .quitting recording loop" )
                        break

                    # Stop recording
                    if self.h5_recording:
                        self.h5_stop()

                    # After loop processing
                    # Attempt to cancel transfers that could be yet pending
                    for transfer in transfer_list:
                        if transfer.isSubmitted():
                            log.info( f" .cancelling transfer [{transfer.getUserData()}] (may take a while) ..." )
                            try:
                                transfer.cancel()
                            except:
                                pass
                    
                    while any( x.isSubmitted() for x in transfer_list ):
                        context.handleEvents()

                    log.info( f" .cancelling transfer [done]" )

                    # Send stop command to Megamicros FPGA (too late ?)
                    self.__ctrlStop()

                    # Flush Mu32 remaining data from buffers
                    log.info( f" .flushing buffers..." )
                    for id in range( self.usb_buffers_number ):
                        transfer = transfer_list[id]
                        if not transfer.isSubmitted():
                            transfer.setBulk(
                                usb1.ENDPOINT_IN | self.__usb_bus_address,
                                buffer_size,
                                callback=self.__callback_flush,
                                user_data = id,
                                timeout=10
                            )
                            try:
                                transfer.submit()
                            except Exception as e:
                                log.info( f" .transfer [{transfer.getUserData()}] flushing failed: {e}" )

                    while any( x.isSubmitted() for x in transfer_list ):
                        context.handleEvents()

                    log.info( f" .flushing [done]" )
                        
                    # Reset Mu32 and powers off microphones
                    self.__ctrlResetMu()

            log.info( ' .end of acquisition' )

        except Exception as e:
            log.error( f" .Error resulting in thread termination ({type(e).__name__}): {e}" )
            self._async_transfer_thread_exception = e



    def __ctrlWrite( self, request, data, time_out=USB_DEFAULT_TIMEOUT, recipient_device=USB_RECIPIENT_DEVICE, type_vendor=USB_REQUEST_TYPE_VENDOR, endpoint_out=USB_ENDPOINT_OUT ):
        """
        Send a write command to the Megamicros FPGA through the usb interface

        Parameters
        ----------
        request: int
            The request code
        data: bytes
            The data to send
        time_out: int, optional
            The USB command timeout in ms (default is 1000ms)
        recipient_device: int, optional
            The USB recipient device (default is 0x00)
        type_vendor: int, optional
            The USB request type (default is 0x40)
        endpoint_out: int, optional
            The USB endpoint out (default is 0x00)
        """

        if self.__usb_handle is None:
            raise MuUsbException( 'USB device not connected' )

        ndata = self.__usb_handle.controlWrite(
                        # command type
            recipient_device | type_vendor | endpoint_out,
            request, 	# command
            0,			# command parameter value
            0,			# index
            data,		# data to send 
            time_out 
        )

        if ndata != sizeof( data ):
            log.warning( 'Mu32::ctrlWrite(): command failed with ', ndata, ' data transfered against ', sizeof( data ), ' wanted ' )

    def __ctrlWriteReset( self, request, time_out=USB_DEFAULT_TIMEOUT, recipient_device=USB_RECIPIENT_DEVICE, type_vendor=USB_REQUEST_TYPE_VENDOR, endpoint_out=USB_ENDPOINT_OUT ):
        """
        Send a reset write command to the MegaMicro FPGA through the usb interface.
        This command needs to perform a _controlTransfer() call instead of a controlWrite() call.
        This is because we have no data to transfer (0 length) while the buffer should not be empty.
        controlWrite() computes the data length on its own, that is something >0 leading to a LIBUSB_ERROR_PIPE [-9] exception
        """

        if self.__usb_handle is None:
            raise MuUsbException( 'USB device not connected' )
        
        data = create_string_buffer( 16 )
        try:
            ndata = self.__usb_handle._controlTransfer(
                recipient_device | type_vendor | endpoint_out, 
                request, 
                0,
                0, 
                data, 
                0,
                time_out,
            )
        except Exception as e:
            log.error( f"reset write failed on device: {e}" )
            raise

        if ndata != 0:
            log.warning( 'Mu32::ctrlWriteReset(): command failed with ', ndata, ' data transfered against 0 wanted ' )


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


    def __selftest( self, duration=DEFAULT_SELFTEST_DURATION ) -> tuple:
        """ Perform a test on the antenna system and get its properties then populate class properties with them 
        
        The USB port is suposed free and the antenna connected to the host

        Parameters
        ----------
        duration: float, optional
            The selftest duration in seconds (default is 0.1s)
        
        Returns
        -------
        mems_power: np.array
            The MEMs power numpy array
        analogs_power: array
            The analogs power numpy array
        """

        if self.__system_type == self.SystemType.unknown:
            raise MuUsbException( 'Cannot perform selftest: USB device not connected' )
        
        if self.__usb_handle is not None:
            raise MuUsbException( 'Cannot perform selftest: USB device buzy' )
        
        try:
            data_length = int( duration * self.sampling_frequency )
            log.info( f" .Performing Megamicros selftest on {duration} s ({data_length} samples) ..." )

            # Try to connect to the device
            with usb1.USBContext() as context:

                self.__usb_handle = context.openByVendorIDAndProductID( 
                    self.__usb_vendor_id, 
                    self.__usb_vendor_product,
                    skip_on_error=True,
                )

                if self.__usb_handle is None:
                    raise MuUsbException( 'Failed to connect to USB device: the device may be disconnected or user not allowed to access' )
                else:
                    log.info( f' .Connected on USB device {str( self.__system_type )}: {self.__usb_vendor_id:04x}:{self.__usb_vendor_product:04x}' )

                # try to claim the device
                with self.__usb_handle.claimInterface( 0 ):

                    mems_number = self.__pluggable_beams_number * MU_BEAM_MEMS_NUMBER
                    analogs_number = self.__pluggable_analogs_number
                    channels_number = mems_number + analogs_number + 2
                    self.__ctrlResetMu()
                    self.__ctrlClockdiv( DEFAULT_CLOCKDIV, DEFAULT_TIME_ACTIVATION )
                    self.__ctrlTixels( data_length )
                    self.__ctrlDatatype( 'int32' )
                    self.__ctrlMems( request='activate', mems='all' )
                    self.__ctrlCSA( counter=True, status=True, analogs='all' )
                    self.__ctrlStart()            
                    data:bytearray = self.__usb_handle.bulkRead( 
                        self.__usb_bus_address, 
                        data_length * MU_TRANSFER_DATAWORDS_SIZE * channels_number, 
                        0 
                    )
                    self.__ctrlStop()

        except Exception as e:
            raise MuUsbException( f"Selftest failed: {e}" )

        # Compute mean energy        
        data = np.frombuffer( data, dtype=np.int32 )
        data = data.reshape( ( channels_number, data_length ), order='F' )

        channels_power = np.sum( data**2, axis=1 ) / data_length
        mems_power = channels_power[1:mems_number+1]
        if analogs_number > 0:
            analogs_power = channels_power[mems_number+1:mems_number+analogs_number+1]
        else:
            analogs_power = np.array([])
			
        log.info( f" .Autotest results:" )
        log.info( f"  > equivalent recording time is: {data_length / self.sampling_frequency} " )
        log.info( f"  > Received {len(data)} data bytes: {data_length} samples on {channels_number} channels")
        log.info( f"  > detected {len( np.where( mems_power > 0 )[0] )} active MEMs: {np.where( mems_power > 0 )[0]}" )
        if analogs_number > 0:
            log.info( f"  > detected {len( np.where( analogs_power > 0 )[0] )} active analogs: {np.where( analogs_power > 0 )[0]}" )
        else:
            log.info( f"  > detected no active analogs" )
        log.info( f"  > detected counter channel with values from {data[0][0]} to {data[0][-1]}" )
        log.info( f"  > estimated data lost: {data[0][-1] - data[0][0] + 1 - data_length} samples" )
        log.info( f"  > detected status channel with values {data[channels_number-1][0]} <-> {data[channels_number-1][-1]}" )
        log.info( f" .Selftest endded successfully" )

        # free the USB device
        self.__usb_handle = None

        return mems_power, analogs_power