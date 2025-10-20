# megamicros.usb.py
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
@file megamicros.usb.py
@brief Define USB device handling functions
"""

from ctypes import addressof, byref, sizeof, create_string_buffer, CFUNCTYPE
import usb1

from megamicros.log import log
from megamicros.exception import MuException

USB_DEFAULT_INTERFACE        = 0x00
USB_DEFAULT_ENDPOINT_IN      = 0x81
USB_DEFAULT_TIMEOUT          = 1000  # in ms

LIBUSB_RECIPIENT_DEVICE      = 0x00
LIBUSB_REQUEST_TYPE_VENDOR   = 0x40
LIBUSB_ENDPOINT_OUT          = 0x00

                                                                            
class UsbException( MuException ):
    """ Exception base class for USB devices in Megamicros """

    def __init__( self, message: str="" ):
        super().__init__( message )

class Usb:
    """ Class representing a USB device """

    def __init__( self, vendor_id:int|None = None, product_id:int|None = None, bus_address:int|None = None, endpoint_in:int|None = None, endpoint_out:int|None = None ):
        self.__vendor_id = vendor_id
        self.__product_id = product_id
        self.__bus_address = bus_address
        self.__endpoint_in = endpoint_in
        self.__endpoint_out = endpoint_out
        self.__context: usb1.USBContext|None = None
        self.__usb_handle: usb1.USBDeviceHandle|None = None
        self.__is_open = False
        self.__is_claimed = False

        if vendor_id is not None and product_id is not None and bus_address is not None :
            self.open( vendor_id, product_id, bus_address, endpoint_in if endpoint_in is not None else USB_DEFAULT_ENDPOINT_IN, endpoint_out )


    def open( self, vendor_id:int, product_id:int, bus_address:int, endpoint_in:int, endpoint_out:int|None = None ) -> None:
        """ 
        Open the USB device connection - but don't claim it yet 
        Try to locate the device based on vendor_id, product_id, bus_address
        """

        log.info( f' .Connecting to USB device {vendor_id:04x}:{product_id:04x} ...' )
        self.__context = usb1.USBContext()
        self.__usb_handle = self.__context.openByVendorIDAndProductID( 
            vendor_id, 
            product_id,
            skip_on_error=True,
        )

        if self.__usb_handle is None:
            raise UsbException( 'Failed to connect to USB device: the device may be disconnected or user not allowed to access' )

        # Test claiming the interface:
        self.claim()

        self.__vendor_id = vendor_id
        self.__product_id = product_id
        self.__bus_address = bus_address
        self.__endpoint_in = endpoint_in
        self.__endpoint_out = endpoint_out

        # release the interface
        self.release()

        self.__is_open = True
        log.info( f' .Connected on USB device {self.__vendor_id:04x}:{self.__product_id:04x}' )


    def claim(self) -> None:
        """ Claim the USB device interface """
        if self.__is_claimed == False:
            if self.__usb_handle is not None:
                if self.__usb_handle.claimInterface( self.__bus_address ) == False:
                    raise UsbException( f'Failed to claim interface {self.__bus_address} on USB device {self.__vendor_id:04x}:{self.__product_id:04x}' )
                log.info( f' .Claimed interface {self.__bus_address} on USB device {self.__vendor_id:04x}:{self.__product_id:04x}' )

    def release(self) -> None:
        """ Release the USB device interface """
        if self.__is_claimed:
            if self.__usb_handle is not None:
                if self.__usb_handle.releaseInterface( self.__bus_address ) == False:
                    raise UsbException( f'Failed to release interface {self.__bus_address} on USB device {self.__vendor_id:04x}:{self.__product_id:04x}' )
                log.info( f' .Released interface {self.__bus_address} on USB device {self.__vendor_id:04x}:{self.__product_id:04x}' )

    def close( self ) -> None:
        """ Close the USB device connection """
        if self.__is_open:
            if self.__is_claimed:
                self.release()
            if self.__usb_handle is not None:
                self.__usb_handle.close()
            if self.__context is not None:
                self.__context.close()
            self.__is_open = False
            log.info( f' .Disconnected from USB device {self.__vendor_id:04x}:{self.__product_id:04x}' )

    def __ctrlWrite( self, request, data, time_out=USB_DEFAULT_TIMEOUT ):
        """
        Send a write command to the USB interface

        Parameters
        ----------
        request: int
            The request code to send
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

        if not self.__usb_handle:
            raise UsbException( 'Cannot write on usb device: no available handler. Please open device before using it!' )

        keeping_claimed = self.__is_claimed
        if not self.__is_claimed:
            self.claim()

        ndata = self.__usb_handle.controlWrite(
            LIBUSB_RECIPIENT_DEVICE | LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_ENDPOINT_OUT,  # bmRequestType
            request, 	    # command
            0,			    # command parameter value
            0,			    # index
            data,		    # data to send 
            time_out        # timeout in ms 
        )

        if ndata != sizeof( data ):
            log.warning( ' .In Usb.__ctrlWrite(): Command failed with ', ndata, ' data transfered against ', sizeof( data ), ' wanted ' )

        if not keeping_claimed:
            self.release()


    def __ctrlWriteReset( self, request, time_out=USB_DEFAULT_TIMEOUT ):
        """
        Send a reset write command to the MegaMicro FPGA through the usb interface.
        This command needs to perform a _controlTransfer() call instead of a controlWrite() call.
        This is because we have no data to transfer (0 length) while the buffer should not be empty.
        controlWrite() computes the data length on its own, that is something >0 leading to a LIBUSB_ERROR_PIPE [-9] exception
        """

        if not self.__usb_handle:
            raise UsbException( 'Cannot write on usb device: no available handler. Please open device before using it!' )

        keeping_claimed = self.__is_claimed
        if not self.__is_claimed:
            self.claim()
        
        data = create_string_buffer( 16 )
        try:
            ndata = self.__usb_handle._controlTransfer(
                LIBUSB_RECIPIENT_DEVICE | LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_ENDPOINT_OUT,
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
            log.warning( ' .In Usb.__ctrlWrite(): Command failed with ', ndata, ' data transfered against 0 wanted' )
        
        if not keeping_claimed:
            self.release()

    def syncBulkRead( self, size:int, time_out=USB_DEFAULT_TIMEOUT ) -> bytes:
        """
        Perform a synchronous bulk read transferon the USB device

        Parameters
        ----------
        size: int
            The number of bytes to read
        time_out: int, optional
            The USB command timeout in ms (default is 1000ms)

        Returns
        -------
        bytes
            The data read from the USB device
        """

        if not self.__usb_handle:
            raise UsbException( 'Cannot read from usb device: no available handler. Please open device before using it!' )

        keeping_claimed = self.__is_claimed
        if not self.__is_claimed:
            self.claim()

        try:
            data = self.__usb_handle.bulkRead(
                self.__endpoint_in,
                size,
                time_out,
            )
        except usb1.USBError as e:
            log.error( f"Error during bulk read of {size} bytes from USB device {self.__vendor_id:04x}:{self.__product_id:04x}: {e}" )
            raise UsbException( f"Error during bulk read of {size} bytes from USB device {self.__vendor_id:04x}:{self.__product_id:04x}: {e}" ) from e

        if not keeping_claimed:
            self.release()

        return data

    def asyncBulkTransfer( self, duration: int, time_out=USB_DEFAULT_TIMEOUT ) -> None:
        """
        Perform an asynchronous bulk transfer on the USB device
        Not implemented yet
        """
        raise NotImplementedError( 'Usb.asyncBulkTransfer() not implemented yet' )
    
    def __callback( self, transfer_id ) -> None:
        """
        Callback function for asynchronous bulk transfer on the USB device
        Not implemented yet
        """
        raise NotImplementedError( 'Usb.__callback() not implemented yet' )
    
    def asyncBulkTransferWait( self, time_out=USB_DEFAULT_TIMEOUT ) -> bytes:
        """
        Wait for the end of an asynchronous bulk transfer on the USB device
        Not implemented yet
        """
        raise NotImplementedError( 'Usb.asyncBulkTransferWait() not implemented yet' )
    
    def asyncBulkTransferStop( self ) -> None:
        """
        Stop an asynchronous bulk transfer on the USB device
        Not implemented yet
        """
        raise NotImplementedError( 'Usb.asyncBulkTransferStop() not implemented yet' )
    
    def __asyncBulkTransfer_thread( self, time_out=USB_DEFAULT_TIMEOUT ) -> None:
        """
        Thread function to perform an asynchronous bulk transfer on the USB device
        Not implemented yet
        """
        raise NotImplementedError( 'Usb.__asyncBulkTransfer_thread() not implemented yet' )
    
    def __asyncBulkTransferStop_thread( self ) -> None:
        """
        Thread function to stop an asynchronous bulk transfer on the USB device
        Not implemented yet
        """
        raise NotImplementedError( 'Usb.__asyncBulkTransferStop_thread() not implemented yet' )