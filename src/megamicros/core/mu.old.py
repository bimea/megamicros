# megamicros.core.mu.py base class for antenna connected to a remote antenna server
#
# Copyright (c) 2024 Sorbonne Université
# Author: bruno.gas@bimea.io
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
import platform
from ctypes import addressof, byref, sizeof, create_string_buffer, CFUNCTYPE

from megamicros_tools.log import log
from megamicros_tools.exception import MuException
from .base import MemsArray, DEFAULT_SAMPLING_FREQUENCY, DEFAULT_FRAME_LENGTH


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
USB_DEFAULT_BUFFER_LENGTH		        = DEFAULT_FRAME_LENGTH         # Default buffer length in samples number: same as frame length


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
MU_DEFAULT_DATATYPE             = 'int32'                                   # Datatype for FPGA megamicros data 


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


class Megamicros( MemsArray ):
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
    __pluggable_beams_number: int = 0
    __pluggable_analogs_number: int = 0
    __start_trigg_status: bool = DEFAULT_START_TRIGG_STATUS
    __clockdiv: int = DEFAULT_CLOCKDIV
    __usb_handle: usb1.USBDeviceHandle | None= None
    __usb_buffer_length: int = USB_DEFAULT_BUFFER_LENGTH
    __usb_buffers_number: int = USB_DEFAULT_BUFFERS_NUMBER
    __usb_buffer_duration: float = USB_DEFAULT_BUFFER_LENGTH / DEFAULT_SAMPLING_FREQUENCY
    __usb_buffer_words_length: int = 0
    __usb_transfer_index: int = 0
    __fpga_counter_state: int = 0
    __fpga_previous_counter_state: int = 0

    @property
<<<<<<< HEAD
    def system_type( self ) -> SystemType:
        return self.__system_type

    @property
=======
    def pluggable_beams_number( self ) -> int:
        return self.__pluggable_beams_number

    @property
    def pluggable_analogs_number( self ) -> int:
        return self.__pluggable_analogs_number
    
    @property
>>>>>>> 723e088865acbb006c3cb408ebc4768b532626b7
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

    @property
    def usb_buffer_duration( self ) -> int:
        return self.__usb_buffer_duration

    @property
    def usb_transfer_index( self ) -> int:
        return self.__usb_transfer_index

    @property
    def usb_buffer_words_length( self ) -> int:
        return self.__usb_buffer_words_length
    

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

        Update usb_buffer_duration at the same time

        Parameters
        ----------
        length: int
            The USB buffer length in samples number
        """
        self.__usb_buffer_length = length
        self.__usb_buffer_duration = length / self.sampling_frequency

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
        super().setSamplingFrequency( 500000 / ( self.__clockdiv + 1 ) )
        log.info( f" .Set sampling frequency to {self.sampling_frequency} Hz" )


    def setActiveMems( self, mems: tuple ) -> None :
        """ Activate mems

        Overload the parent method for adding the actual buffer length according the channels number
        
        Parameters:
        -----------
        mems : tuple
            list or tuple of mems number to activate
        """

        # Set parent property
        super().setActiveMems( mems )

        # Set buffer duration estimation
        self.__usb_buffer_words_length = self.usb_buffer_length * self.channels_number


    def setActiveAnalogs( self, analogs: tuple ) -> None :
        """ Activate analogs

        Overload the parent method for adding the actual buffer length according the channels number
        
        Parameters:
        -----------
        analogs : tuple
            list or tuple of analogs number to activate
        """

        # Set parent property
        super().setActiveAnalogs( analogs )

        # Set buffer duration estimation
        self.__usb_buffer_words_length = self.usb_buffer_length * self.channels_number

    def setCounter( self ) -> None :
        """ Activate counter

        Overload the parent method for adding the actual buffer length according the channels number
        """

        # Set parent property
        super().setCounter()

        # Set buffer duration estimation
        self.__usb_buffer_words_length = self.usb_buffer_length * self.channels_number

    def unsetCounter( self ) -> None :
        """ Deactivate counter

        Overload the parent method for adding the actual buffer length according the channels number
        """

        # Set parent property
        super().unsetCounter()

        # Set buffer duration estimation
        self.__usb_buffer_words_length = self.usb_buffer_length * self.channels_number

    def setStatus( self ) -> None :
        """ Activate status

        Overload the parent method for adding the actual buffer length according the channels number
        """

        # Set parent property
        super().setStatus()

        # Set buffer duration estimation
        self.__usb_buffer_words_length = self.usb_buffer_length * self.channels_number

    def unsetStatus( self ) -> None :
        """ Deactivate status

        Overload the parent method for adding the actual buffer length according the channels number
        
        Parameters:
        -----------
        status : bool
            True for activating the status
        """

        # Set parent property
        super().unsetStatus()

        # Set buffer duration estimation
        self.__usb_buffer_words_length = self.usb_buffer_length * self.channels_number

    def __init__( self, **kwargs ):
        """ Connect the antenna input stream to a megamicros antenna 

        The connection to the remote server is verified. If the server is not available, an exception is raised. 

        Parameters
        ----------
        """

        # Init base class
        super().__init__( kwargs=kwargs )

        # Set Megamicros settings
        if len( kwargs ) > 0:
            self._set_settings( [], kwargs )

        # Check USB megamicros device
        self.__check_device()

        # Prevent recursive call when __self_test is called on Windows platform
        # On windows platform '__self_test' creates a new Megamicros object which call '__self_test' again
        if 'no_check' in kwargs and kwargs['no_check'] == True:
            self.setAvailableMems( [ i for i in range( self.pluggable_beams_number * MU_BEAM_MEMS_NUMBER ) ] )
            self.setAvailableAnalogs( [ i for i in range( self.pluggable_analogs_number) ] )
            return

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
            log.info( f"  > OS System: {platform.system()}" )
            log.info( f"  > Bus number: {usb_device.getBusNumber()}" )
            log.info( f"  > Ports number: {usb_device.getPortNumber()}" )
            log.info( f"  > Device address: {usb_device.getDeviceAddress()} ({usb_device.getDeviceAddress():04x})" )
            if platform.system() != 'Windows':
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
            log.info( f" .Setting usb_buffer_length to {self.frame_length} samples" )
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
        log.info( f" .Starting run execution" )
        log.info( f"  > Run infinite loop (duration=0)" if self.duration == 0 else f"  > Perform {self.duration}s run loop" )
        log.info( f"  > Sampling frequency: {self.sampling_frequency} Hz" )
        log.info( f"  > FPGA clockdiv value: {self.clockdiv}" )
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
        log.info( f"  > Buffer length in 32 bits words number: {self.usb_buffer_length}x{self.channels_number}={self.usb_buffer_words_length} ({self.usb_buffer_words_length*MU_TRANSFER_DATAWORDS_SIZE} bytes)" )
        log.info( f"  > Buffer duration: {self.usb_buffer_duration} s" )
        log.info( f"  > Starting from external triggering: {'True' if self.start_trigg_status else 'False'}" )
        log.info( f"  > Local H5 recording {'on' if self.h5_recording else 'off'}" )

        # Check if the USB device is connected and free
        if self.__system_type == self.SystemType.unknown:
            raise MuUsbException( 'Cannot start run process: USB device not connected' )
        
        if self.__usb_handle is not None:
            raise MuUsbException( 'Cannot perform run process: USB device buzy' )

        # Start the timer if a limited execution time is requested
        # In this case, the timeout causes a stop command to be sent to the server
        # We have then to wait for the remote server to end the transfer
        # We have also to take care of the microphones power-on duration
        if self.duration > 0 :
            self._thread_timer = threading.Timer( self.duration + DEFAULT_TIME_ACTIVATION, self._run_endding )
            self._thread_timer_flag = True
            self._thread_timer.start()

        # Start run thread
        self._async_transfer_thread = threading.Thread( target= self.__run_thread )
        self._async_transfer_thread.start()

    def __callback_flush( self, transfer: usb1.USBTransfer ):
        """ Callback flushing function: only intended to flush MegaMicro internal buffers

        Parameters
        ----------
        transfer: usb1.USBTransfer
            The transfer object
        """

        if transfer.getActualLength() > 0:
            log.info( f" .flushed {transfer.getActualLength()} data bytes from transfer buffer [{transfer.getUserData()}]" )


    def __callback( self, transfer: usb1.USBTransfer ):
        """ Internal callback function: 
        
        check transfer error, read data from USB device, queue data, 
        call the user callback function if any and submit next transfer

        Parameters
        ----------
        transfer: usb1.USBTransfer
            The transfer object
        """

        transfer_timestamp = time.time() - self.usb_buffer_duration


        # Transfer not completed -> skip data transfer without runing user callback
        # Data is lost, if any
        if transfer.getStatus() != usb1.TRANSFER_COMPLETED:

            if transfer.getStatus() == usb1.TRANSFER_CANCELLED:
                log.info( f" .transfer [{transfer.getUserData()}] cancelled." )
            elif transfer.getStatus() == usb1.TRANSFER_NO_DEVICE:
                log.critical( f"transfer [{transfer.getUserData()}]: no device. Exit from internal callback transfer." )
            elif transfer.getStatus() == usb1.TRANSFER_ERROR:
                log.error( f"transfer [{transfer.getUserData()}] error. Exit from internal callback transfer." )

            # Tranfer timeout
            elif transfer.getStatus() == usb1.TRANSFER_TIMED_OUT:
                
                # This may due to trigger signal not send -> nothing to do but waiting for it...
                # Submit a new transfer and return
                if self.start_trigg_status:
                    log.warning( f"transfer [{transfer.getUserData()}] timed out. Waiting for external trigger signal..." )
                    if( self.running ):
                        try:
                            transfer.submit()
                        except Exception as e:
                            log.error( f"Megamicros.__callback(): transfer submit failed: {e}. Aborting..." )
                            self._recording = False
                    return
                
                # Unexpected timeout: exit from call back without submitting
                else:
                    log.error( f"Megamicros::__callback(): Unexpected transfer [{transfer.getUserData()}] timed out. Exit from internal callback." )

            elif transfer.getStatus() == usb1.TRANSFER_STALL:
                log.error( f"Megamicros.__callback(): Transfer [{transfer.getUserData()}] stalled. Exit from internal callback." )
            elif transfer.getStatus() == usb1.TRANSFER_OVERFLOW:
                log.error( f"Megamicros.__callback(): Transfer [{transfer.getUserData()}] overflow. Exit from internal callback." )
            else:
                log.error( f"Megamicros.__callback(): Transfer [{transfer.getUserData()}] unknown error. Exit from internal callback." )

            # Stop acquisition process before exiting    
            self.setRunningFlag( False )
            return

        # Transfer seems correct: get data from buffer
        # Datatype is only 'int32'. If user datatype is 'float32', data will be converted later (when queuing data)
        data = np.frombuffer( transfer.getBuffer()[:transfer.getActualLength()], dtype=np.int32 )

        # Buffer is not fully completed. Some data are missing
        # Submit again anyway but current transfer is lost
        if len( data ) != self.usb_buffer_words_length:

            log.warning( f" .lost {self.usb_buffer_words_length - len( data )} lost samples. Retry transfer" )
            if( self.running ):
                try:
                    transfer.submit()
                except Exception as e:
                    log.error( f"Megamicros.__callback(): transfer submit failed: {e}" )
                    self.setRunningFlag( False )
            return

        # counter flag is True: performs data control such as to know if some data have been lost
        # This usually appears when user callback function takes too long.
        # Control is done by substracting the frame last counter value with the frame first counter value. 
        # Result should be equal to the buffer size in samples number
        # Beware that, if not, it means that samples have been lost or, 
        # whorst than that, data is no longer aligned in which case this difference no longer makes sense.
        # Submit transfer again but current transfer is lost. 
        # A restart request should be sent to the server to restart the acquisition process. See in the future...
        if self.counter:
            ctrl_buffer_length = data[self.usb_buffer_words_length-self.channels_number] - data[0] + 1
            if ctrl_buffer_length != self.usb_buffer_length:
                log.warning( f"Megamicros.__callback(): from transfer[{transfer.getUserData()}]: data has been lost. Send a restart request...")
                if( self.running ):
                    try:
                        transfer.submit()
                    except Exception as e:
                        log.error( f"Megamicros.__callback(): transfer submit failed: {e}" )
                        self.setRunningFlag( False )
                return

            # All seems correct
            # save current counter value and performs data control by comparing with actual counter values
            self.__fpga_previous_counter_state = self.__fpga_counter_state
            self.__fpga_counter_state = data[self.usb_buffer_words_length-self.channels_number]
            if self.__fpga_counter_state - self.__fpga_previous_counter_state > self.usb_buffer_length and self.__fpga_previous_counter_state != 0:
                log.info( f" .{self.__fpga_counter_state - self.__fpga_previous_counter_state - self.usb_buffer_length} samples lost it seems.")

        data = np.reshape( data, ( self.usb_buffer_length, self.channels_number ) ).T

        # Remove counter signal if requested by user
        if self.counter and self.counter_skip:
            data = data[1:,:]

        # Call user callback processing function if any.
        # Not yet implementd..
        # ...

        # Queue size is limited and filled -> delete older element before queuing new:  
        if self.queue_size > 0 and self.queue.qsize() >= self.queue_size:
            self.queue.get()

        # Push data and timestamp in the object signal queue
        self.queue.put( data )

        # Resubmit transfer once data is processed and while recording mode is on
        if( self.running ):
            try:
                transfer.submit()
            except Exception as e:
                log.error( f"Megamicros.__callback(): transfer submit failed: {e}. Aborting..." )
                self.setRunningFlag( False )

        # Update transfer counter
        self.__transfer_index += 1
	

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
                    self.__ctrlDatatype( 'int32' )
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
                    self.__fpga_counter_state = self.__fpga_previous_counter_state = 0
                    self.__transfer_index = 0
                    start_time = time.time()
                    while self.running:
                        # Main recording loop.
                        # Waits for pending tranfers while there are any.
                        # Once a transfer is finished, handleEvents() trigers callback  
                        while any( x.isSubmitted() for x in transfer_list ):
                            context.handleEvents()

                        log.info( f" .quitting recording loop" )
                        break

                    # Send stop command to Megamicros FPGA
                    #self.__ctrlStop()

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

            elapsed_time = time.time() - start_time
            mean_completion_time = elapsed_time/self.__transfer_index if self.__transfer_index != 0 else 0

            log.info( f' .End of acquisition' )
            log.info( f'  > Performed {self.__transfer_index} transfer(s), received {self.__transfer_index * self.usb_buffer_words_length * MU_TRANSFER_DATAWORDS_SIZE} bytes' )
            log.info( f'  > Equivalent recording time: {(self.__transfer_index * self.usb_buffer_duration):.2f} s' )
            log.info( f'  > Transfer rate: {(self.__transfer_index * self.usb_buffer_words_length * MU_TRANSFER_DATAWORDS_SIZE / self.__transfer_index / self.usb_buffer_duration / 1024 / 1024):.2f} MB/s' )
            log.info( f'  > Elapsed time: {elapsed_time:.2f} s')
            log.info( f'  > Mean completion time: {mean_completion_time*1000:.4f} ms')

        except Exception as e:
            log.error( f" .Error resulting in thread termination ({type(e).__name__}): {e}" )
            self._async_transfer_thread_exception = e
        
        # Don't forget to declare the USB device free
        self.__usb_handle = None



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

        # Compute MEMs energy using the bulk transfer method because the bulkRead methgod does not work on Windows
        if platform.system() == 'Windows':

            log.info( f" .detected windows OS: using bulk transfer method for selftest..." )
            antenna = Megamicros( no_check=True )
            mems_number = self.__pluggable_beams_number * MU_BEAM_MEMS_NUMBER
            analogs_number = self.__pluggable_analogs_number
            channels_number = mems_number + analogs_number + 2
            antenna.run(      
                mems=[i for i in range(mems_number)],
                analogs=[i for i in range(analogs_number)],
                duration=1,
                sampling_frequency=50000,
                counter = True,
                counter_skip=False, 
                status=True,
                buffer_length=256,
            )

            # Get signals
            signals = np.ndarray( (antenna.channels_number, 0 ) )
            for data in antenna:
                signals = np.concatenate( ( signals, data ), axis=1 )

            signal_length = signals.shape[1]

            power = np.sum( signals**2, axis=1 ) / signal_length
            mems_power = power[1:mems_number+1]
            if analogs_number > 0:
                analogs_power = power[mems_number+1:mems_number+analogs_number+1]
            else:
                analogs_power = np.array([])

            log.info( f" .Autotest results:" )
            log.info( f"  > equivalent recording time is: {signal_length / antenna.sampling_frequency} " )
            log.info( f"  > Received {signal_length*channels_number*4} data bytes: {signal_length} samples on {channels_number} channels")
            log.info( f"  > detected {len( np.where( mems_power > 0 )[0] )} active MEMs: {np.where( mems_power > 0 )[0]}" )
            if analogs_number > 0:
                log.info( f"  > detected {len( np.where( analogs_power > 0 )[0] )} active analogs: {np.where( analogs_power > 0 )[0]}" )
            else:
                log.info( f"  > detected no active analogs" )
            log.info( f"  > detected counter channel with values from {int(signals[0][0])} to {int(signals[0][-1])}" )
            log.info( f"  > estimated data lost: {int(signals[0][-1] - signals[0][0] + 1 - signal_length)} samples" )
            log.info( f"  > detected status channel with values {int(signals[channels_number-1][0])} <-> {int(signals[channels_number-1][-1])}" )
            log.info( f" .Selftest endded successfully" )

            return mems_power, analogs_power

        # Performs bulkRead on other platforms
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

        # Check data length
        data = np.frombuffer( data, dtype=np.int32 )
        if len( data ) != data_length * channels_number:
            # Windows platform failed on this test (Zadig driver issue ?)
            # Note that Zadig driver is based on libusb 0.1 porting for Windows while Python libusb is based on libusb 1.0
            if platform.system() == 'Windows':
                log.warning( f"Received {len(data)} data bytes instead of {data_length * channels_number} ({data_length} samples)" )
                if len( data ) > data_length * channels_number:
                    log.warning( f"Windows platform detected --> Data length will be adjusted to {data_length} samples." )
                    data = data[:data_length * channels_number]
                else:
                    new_data_length = len( data ) // channels_number
                    log.warning( f"Windows platform detected --> Data length will be adjusted to {new_data_length*channels_number} ({new_data_length} samples)." )
                    if len( data ) % channels_number == 0:
                        log.warning( f"Removed exactly {data_length - new_data_length} samples of {channels_number} channels each." )
                    else:
                        log.warning( f"Removed {data_length * channels_number - len( data )} bytes than cannot be expressed as multiples of channels or samples number." )
                    data = data[:new_data_length * channels_number]
                    data_length = new_data_length
            else:
                raise MuUsbException( f"Received {len(data)} data bytes instead of {data_length * channels_number}" )

        # Compute mean energy        
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
    


    def check_device():
        """ Check USB devices connected to the host and

        This is a static methgod that do not populate class properties
        Throw an exception if no meegamicros device is found
        """

        log.info(' .Checking usb devices...')

        with usb1.USBContext() as context:

            system_type = Megamicros.SystemType.unknown
            for usb_device in context.getDeviceIterator( skip_on_error=True ):
                device_vendor_id = usb_device.getVendorID()
                device_product_id = usb_device.getProductID()
                if device_vendor_id == MU32_USB2_VENDOR_ID and device_product_id == MU32_USB2_VENDOR_PRODUCT:
                    log.info(' .Found Megamicros [Mu32-USB2] device')
                    system_type = Megamicros.SystemType.mu32usb2
                    usb_vendor_id = device_vendor_id
                    usb_vendor_product = device_product_id
                    usb_bus_address = MU32_USB2_BUS_ADDRESS
                    pluggable_beams_number = MU32_USB2_PLUGGABLE_BEAMS_NUMBER
                    pluggable_analogs_number = MU32_USB2_PLUGGABLE_ANALOGS_NUMBER
                    break
                elif device_vendor_id == MU32_USB3_VENDOR_ID and device_product_id == MU32_USB3_VENDOR_PRODUCT:
                    log.info(' .Found Megamicros [Mu32] device')
                    system_type = Megamicros.SystemType.mu32
                    usb_vendor_id = device_vendor_id
                    usb_vendor_product = device_product_id
                    usb_bus_address = MU32_USB3_BUS_ADDRESS
                    pluggable_beams_number = MU32_USB3_PLUGGABLE_BEAMS_NUMBER
                    pluggable_analogs_number = MU32_USB3_PLUGGABLE_ANALOGS_NUMBER
                    break
                elif device_vendor_id == MU128_USB2_VENDOR_ID and device_product_id == MU128_USB2_VENDOR_PRODUCT:
                    log.info(' .Found Megamicros [Mu128] device')
                    system_type = Megamicros.SystemType.mu128
                    usb_vendor_id = device_vendor_id
                    usb_vendor_product = device_product_id
                    usb_bus_address = MU128_USB2_BUS_ADDRESS
                    pluggable_beams_number = MU128_USB2_PLUGGABLE_BEAMS_NUMBER
                    pluggable_analogs_number = MU128_USB2_PLUGGABLE_ANALOGS_NUMBER
                    break
                elif device_vendor_id == MU256_USB3_VENDOR_ID and device_product_id == MU256_USB3_VENDOR_PRODUCT:
                    log.info(' .Found Megamicros [Mu256] device')
                    system_type = Megamicros.SystemType.mu256
                    usb_vendor_id = device_vendor_id
                    usb_vendor_product = device_product_id
                    usb_bus_address = MU256_USB3_BUS_ADDRESS
                    pluggable_beams_number = MU256_USB3_PLUGGABLE_BEAMS_NUMBER
                    pluggable_analogs_number = MU256_USB3_PLUGGABLE_ANALOGS_NUMBER
                    break
                elif device_vendor_id == MU1024_USB3_VENDOR_ID and device_product_id == MU1024_USB3_VENDOR_PRODUCT:
                    log.info(' .Found Megamicros [Mu1024] device')
                    system_type = Megamicros.SystemType.mu1024
                    usb_vendor_id = device_vendor_id
                    usb_vendor_product = device_product_id
                    usb_bus_address = MU1024_USB3_BUS_ADDRESS
                    pluggable_beams_number = MU1024_USB3_PLUGGABLE_BEAMS_NUMBER
                    pluggable_analogs_number = MU1024_USB3_PLUGGABLE_ANALOGS_NUMBER
                    break
                elif device_vendor_id == MU_CYPRESS_VENDOR_ID and device_product_id == MU_CYPRESS_VENDOR_PRODUCT:
                    log.warning( f"Found Cypress device. If USB device is not present you may face to USB connection problem. Please disconnect or run usb soft disconnecting program." )

            if system_type == Megamicros.SystemType.unknown:
                raise MuUsbException( 'No Megamicros device found' )

            # Try to connect to the device
            handle = context.openByVendorIDAndProductID( 
                usb_vendor_id, 
                usb_vendor_product,
                skip_on_error=True,
            )

            if handle is None:
                raise MuUsbException( 'Failed to connect to USB device: the device may be disconnected or user not allowed to access' )
            else:
                log.info( f' .Connected on USB device {usb_vendor_id:04x}:{usb_vendor_product:04x}' )

            # try to claim the device (even if nothing to do, just trying to see if the device is free)
            try:
                with handle.claimInterface( 0 ):
                    pass
            except Exception as e:
                raise MuUsbException( f'USB device buzy: cannot claim: {e}' )

            # Print device characteristics
            log.info( f" .Found following device {usb_vendor_id:04x}:{usb_vendor_product:04x} characteristics :" )
            log.info( f"  > OS System: {platform.system()}" )
            log.info( f"  > Bus number: {usb_device.getBusNumber()}" )
            log.info( f"  > Ports number: {usb_device.getPortNumber()}" )
            log.info( f"  > Device address: {usb_device.getDeviceAddress()} ({usb_device.getDeviceAddress():04x})" )
            if platform.system() != 'Windows':
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


            # free the USB device
            handle = None

        return {
            'system_type': system_type,
            'usb_vendor_id': usb_vendor_id,
            'usb_vendor_product': usb_vendor_product,
            'usb_bus_address': usb_bus_address,
            'pluggable_beams_number': pluggable_beams_number,
            'pluggable_analogs_number': pluggable_analogs_number
        }


    def selfest():
        """ Check megamicros devices connected to the host and perform autotest

        This is a static method that run a minimalist megamicros antenna for seltesting
        Throw an exception if no megamicros device is found or if seltest failed

        Return
        ------
        mems_power: np.array
            The MEMs power numpy array
        analogs_power: array
            The analogs power numpy array
        """

        log.info(' .Checking megamicros device...')

        antenna = Megamicros()

        return antenna.available_mems, antenna.available_analogs

