# megamicros.usb.py
#
# ® Copyright 2024-2026 Bimea
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

"""
Define USB device handling functions to communicate with Megamicros hardware.

Features:
    - Handle USB device connection, claiming, and release
    - Perform synchronous bulk read transfers
    - Perform direct or through queue asynchronous bulk read transfers
    - Support for control write commands to the USB device

Basic usage::

    try:
        if Usb.checkDeviceByVendorProduct( vendor_id=0xFE27, product_id=0xAC03 ):
            print( "Device found!" )
            usb_device = Usb()
            usb_device.open( vendor_id=0xFE27, product_id=0xAC03, bus_address=0x00, endpoint_in=0x81 )
            usb_device.claim()
            usb_device.release()
            usb_device.close()
        else:
            print( "Device not found!" )
    except Exception as e:
        print( f"An error occurred: {e}" )
    
Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""

from ctypes import addressof, byref, sizeof, create_string_buffer, CFUNCTYPE
import usb1
import threading
import queue

from .log import log
from .exception import MuException

# libusb constants (provided by the C libusb but not accessible through python/usb1)
LIBUSB_RECIPIENT_DEVICE      = 0x00             
LIBUSB_REQUEST_TYPE_VENDOR   = 0x40
LIBUSB_ENDPOINT_OUT          = 0x00

# Default constants to perform input bulk transfers from the usb device
USB_DEFAULT_INTERFACE        = 0x00
USB_DEFAULT_ENDPOINT_IN      = 0x81
USB_DEFAULT_TRANSFER_TIMEOUT  = 1000                # timeout in ms
USB_DEFAULT_WRITE_TIMEOUT     = 1000                # timeout in ms

USB_DEFAULT_BUFFERS_NUMBER   = 8                    # Default usb transfer buffers number
USB_DEFAULT_QUEUE_SIZE       = 0                    # Queue limit after which the last signal is lost (0 means infinite signal queueing)
USB_DEFAULT_QUEUE_TIMEOUT    = 1000                 # Queue get timeout in ms


                                                                            
class UsbException( MuException ):
    """ Exception base class for USB devices in Megamicros """

    def __init__( self, message: str="" ):
        super().__init__( message )

class Usb:
    """ Class representing a USB device """

    class Queue( queue.Queue ):
        """ Thread safe queue adapted to the Megamicros USB class 
        
        Original comportment is that of blocks insertion once maxsize is reached, until queue items are consumed.
        This implementation pop up the last element of the queue if maxsize is reached.
        """

        @property
        def transfert_lost( self ) -> bool:
            """ Get the transfer lost counter """
            return self.__transfert_lost
    
        def __init__( self, maxsize: int = 0 ):
            self.__transfert_lost: int = 0
            super().__init__( maxsize )

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
            # pop up the last element of the queue if maxsize is reached.
            if self.maxsize > 0 and self.qsize() >= self.maxsize:
                self.get()
                self.__transfert_lost += 1

            # Let parent class do the work 
            super().put( data )


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
        self.__buffer_size: int = 0
        self.__buffers_number: int = USB_DEFAULT_BUFFERS_NUMBER

        # Transfer parameters
        self.__transfer_timeout: int = USB_DEFAULT_TRANSFER_TIMEOUT
        self.__transfer_buffers: list[usb1.USBTransfer] = []
        self.__bulk_transfer_on: bool = False
        self.__on_stop_callback: callable|None = None
        self.__async_transfer_thread: threading.Thread|None = None
        self.__async_transfer_thread_exception: Exception|None = None
        self.__callback_transfert: callable|None = None

        # Timer management
        self.__timer_thread: threading.Timer|None = None

        # Queue management
        self.__queue_size: int = USB_DEFAULT_QUEUE_SIZE
        self.__queue: Usb.Queue = Usb.Queue( maxsize=USB_DEFAULT_QUEUE_SIZE )

        if vendor_id is not None and product_id is not None and bus_address is not None :
            self.open( vendor_id, product_id, bus_address, endpoint_in if endpoint_in is not None else USB_DEFAULT_ENDPOINT_IN, endpoint_out )

    def __del__( self ):
        self.close()
        log.info( ' .USB object destroyed' )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup even on exceptions."""
        self.close()
        return False  # Don't suppress exceptions

    def cleanup(self):
        """Explicit cleanup method - releases and closes USB device."""
        self.close()

    @property
    def buffer_size( self ) -> int:
        return self.__buffer_size

    @property
    def buffers_number( self ) -> int:
        return self.__buffers_number

    @property
    def transfer_timeout( self ) -> int:
        return self.__transfer_timeout

    @property
    def bus_address( self ) -> int:
        return self.__bus_address
    
    @property
    def queue( self ) -> 'Usb.Queue':
        return self.__queue
    
    @property
    def queue_size( self ) -> int:
        return self.__queue_size
    
    @property
    def queue_content( self ) -> int:
        return self.__queue.qsize()

    @property
    def transfer_lost( self ) -> int:
        return self.__queue.transfert_lost

    def isOpened( self ) -> bool:
        """ Check if the USB device is open """
        return self.__is_open

    @staticmethod
    def checkDeviceByVendorProduct( vendor_id:int, product_id:int ) -> bool:
        """ 
        Check if the connected USB device matches the given vendor_id and product_id

        Parameters
        ----------
        vendor_id: int
            The vendor ID to check
        product_id: int
            The product ID to check

        Returns
        -------
        bool
            True if the connected USB device matches the given vendor_id and product_id, False otherwise
        """

        context = usb1.USBContext()
        usb_handle = context.openByVendorIDAndProductID( 
            vendor_id, 
            product_id,
            skip_on_error=True,
        )

        if usb_handle is None:
            return False
        else:
            usb_handle.close()
            context.close()
            return True

    def setBufferSize( self, size:int ) -> None:
        """ Set the USB transfer buffer size in bytes"""
        self.__buffer_size = size

    def setBuffersNumber( self, number:int ) -> None:
        """ Set the USB transfer buffers number """
        self.__buffers_number = number

    def setQueueSize( self, size:int ) -> None:
        """ Set the USB transfer queue size in bytes (0 means infinite queueing) 
        Queue is cleared when size is changed
        """
        self.__queue_size = size
        self.__queue = Usb.Queue( maxsize=size )

    def setTransfertCallback( self, callback: callable ) -> None:
        """ Set the callback function to be called when a new USB transfer is received 
        The callback function should have the following signature: callback( data: bytes ) -> None
        """
        self.__callback_transfert = callback

    def setOnStopCallback( self, callback: callable ) -> None:
        """ Set the callback function to be called when the asynchronous bulk transfer stops """
        self.__on_stop_callback = callback

    def open( self, vendor_id:int, product_id:int, bus_address:int, endpoint_in:int, endpoint_out:int|None = None ) -> None:
        """ 
        Open the USB device connection - but don't claim it yet 
        Try to locate the device based on vendor_id, product_id, bus_address
        """

        log.info( f'Connecting to USB device {vendor_id:04x}:{product_id:04x} ...' )
        self.__context = usb1.USBContext()
        self.__usb_handle = self.__context.openByVendorIDAndProductID( 
            vendor_id, 
            product_id,
            skip_on_error=True,
        )

        if self.__usb_handle is None:
            raise UsbException( 'Failed to connect to USB device: the device may be disconnected or user not allowed to access' )

        self.__vendor_id = vendor_id
        self.__product_id = product_id
        self.__bus_address = bus_address
        self.__endpoint_in = endpoint_in
        self.__endpoint_out = endpoint_out

        # Test claiming the interface:
        self.claim()

        # release the interface
        self.release()

        self.__is_open = True
        log.info( f'Connected on USB device {self.__vendor_id:04x}:{self.__product_id:04x}' )


    def claim(self) -> None:
        """ Claim the USB device interface """
        try:
            if self.__is_claimed == False:
                if self.__usb_handle is not None:
                    if self.__usb_handle.claimInterface( self.__bus_address ) == False:
                        raise UsbException( f'Failed to claim interface {self.__bus_address} on USB device {self.__vendor_id:04x}:{self.__product_id:04x}' )
                    self.__is_claimed = True
        except UsbException as e:
            raise
        except Exception as e:
            log.error( f"Failed to claim USB device {self.__vendor_id:04x}:{self.__product_id:04x}: {e}" )
            raise

    def release(self) -> None:
        """ Release the USB device interface """
        try:
            if self.__is_claimed:
                if self.__usb_handle is not None:
                    if self.__usb_handle.releaseInterface( self.__bus_address ) == False:
                        raise UsbException( f'Failed to release interface {self.__bus_address} on USB device {self.__vendor_id:04x}:{self.__product_id:04x}' )
                    self.__is_claimed = False
        except UsbException as e:
            raise
        except Exception as e:
            log.error( f"Failed to release USB device {self.__vendor_id:04x}:{self.__product_id:04x}: {e}" )
            raise

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

    def ctrlWrite( self, request, data, time_out=USB_DEFAULT_WRITE_TIMEOUT ) -> None:
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

        try:
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

        except Exception as e:
            log.error( f"write failed on device: {e}" )
            raise


    def ctrlWriteReset( self, request, time_out=USB_DEFAULT_WRITE_TIMEOUT ) -> None:
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

    def syncBulkRead( self, size:int, time_out=USB_DEFAULT_TRANSFER_TIMEOUT ) -> bytes:
        """
        Perform a synchronous bulk read transfer on the USB device

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
    
    def bulkRead( self, size:int, timeout:int=USB_DEFAULT_TRANSFER_TIMEOUT ) -> bytes:
        """
        Perform a bulk read transfer on the USB device (alias for syncBulkRead).
        
        Parameters
        ----------
        size: int
            The number of bytes to read
        timeout: int, optional
            The USB command timeout in ms (default is 1000ms)
            
        Returns
        -------
        bytes
            The data read from the USB device
        """
        return self.syncBulkRead(size, timeout)
    
    def __callback( self, transfer: usb1.USBTransfer ) -> None:
        """
        Callback function for asynchronous bulk transfer on the USB device
        """
        status = transfer.getStatus()
        actual_length = transfer.getActualLength()
        
        log.debug(f"USB callback: status={status}, length={actual_length}")

        if status == usb1.TRANSFER_COMPLETED:
            if actual_length > 0:
                # Get data and call the user transfert callback or put it on the queue
                data = transfer.getBuffer()[:actual_length]
                if self.__callback_transfert is not None:
                    self.__callback_transfert( data )
                else:
                    self.__queue.put( data )
            else:
                log.debug(f"USB callback: transfer completed but 0 bytes received")

            # Resubmit the transfer
            if self.__bulk_transfer_on:
                transfer.submit()
        elif status == usb1.TRANSFER_CANCELLED:
            log.info(f"USB callback: transfer cancelled")
        elif status == usb1.TRANSFER_ERROR:
            log.error(f"USB callback: transfer error")
        elif status == usb1.TRANSFER_TIMED_OUT:
            log.debug(f"USB callback: transfer timed out")
        else:
            log.debug(f"USB callback: transfer status={status} (not COMPLETED)")

    def asyncBulkTransfer( self, duration: int ) -> None:
        """
        Perform an asynchronous bulk transfer on the USB device.
        This call is non blocking. The device is claimed during all the transfer 
        """

        if not self.__usb_handle:
            raise UsbException( 'Failed to start asynchronous bulk transfer: no available handler. Please open device before using it!' )

        if self.__buffers_number == 0:
            raise UsbException( 'Failed to start asynchronous bulk transfer: buffers number is not set.' )
        
        if self.__buffer_size == 0:
            raise UsbException( 'Failed to start asynchronous bulk transfer: no allocated buffers.' )

        if self.__async_transfer_thread is not None:
            raise UsbException( 'Failed to start asynchronous bulk transfer: another transfer is already running.' )
        
        # Claims the interface
        if not self.__is_claimed:
            self.claim()

        log.info( 'Init asynchronous bulk transfer...')

        # Clear previous transfer buffers if any
        self.__transfer_buffers.clear()

        # Clear the queue
        self.__queue.clear()

        # Allocate the list of transfer buffers
        for id in range( self.buffers_number ):
            transfer = self.__usb_handle.getTransfer()
            transfer.setBulk(
                usb1.ENDPOINT_IN | self.__endpoint_in,
                self.buffer_size,
                callback=self.__callback,
                user_data = id,
                timeout=self.transfer_timeout
            )
            self.__transfer_buffers.append( transfer )

        # Start the timer if a limited execution time is requested
        # In this case, the transfer ending is scheduled after duration seconds
        if duration > 0 :
            log.info( f"Starting thread timer for {duration} seconds..." )
            self.__timer_thread = threading.Timer( duration, self.__timer_end_of_transfer_thread )
            self.__timer_thread_flag = True
            self.__timer_thread.start()

        # Start run thread
        log.info( f"Starting asynchronous bulk transfer thread..." )
        self.__async_transfer_thread_exception = None
        self.__async_transfer_thread = threading.Thread( target= self.__asyncBulkTransfer_thread )
        self.__async_transfer_thread.start()

    def __asyncBulkTransfer_thread( self, time_out=USB_DEFAULT_TRANSFER_TIMEOUT ) -> None:
        """
        Thread function to perform an asynchronous bulk transfer on the USB device
        """
        log.info( "(Async bulk THREAD) Transfer thread execution started" )

        # Submit all transfers
        for transfer in self.__transfer_buffers:
            transfer.submit()

        # run de main transfer loop
        self.__bulk_transfer_on = True

        # Waits for pending transfers.
        # Once a transfer is finished, handleEvents() triggers the callback function
        try:
            while self.__bulk_transfer_on:
                while any( x.isSubmitted() for x in self.__transfer_buffers ) and self.__bulk_transfer_on:
                    self.__context.handleEvents()

            if not self.__bulk_transfer_on:
                log.info( f"(Async bulk THREAD) Quitting transfer loop due to end of process request..." )
            else:
                log.info( f"(Async bulk THREAD) Quitting transfer loop due to all transfers completed, timeout reached or error..." )
                self.__asyncBulkTransferStop()
    
        except usb1.USBError as e:
            log.error( f"(Async bulk THREAD) Error during asynchronous bulk transfer on USB device {self.__vendor_id:04x}:{self.__product_id:04x}: {e}" )
            log.error( f"(Async bulk THREAD) Error resulting in thread termination ({type(e).__name__}): {e}" )
            self.__async_transfer_thread_exception = e
            self.__asyncBulkTransferStop()

    def __asyncBulkTransferStop( self ) -> None:
        """
        Stop an asynchronous bulk transfer on the USB device
        """
        # Run user callback if any
        if self.__on_stop_callback is not None:
            self.__on_stop_callback()

        self.__bulk_transfer_on = False


    def __timer_end_of_transfer_thread( self ) -> None:
        """ Timer callback for run stopping """

        log.info( f"(Timer THREAD) Thread timer ended: stop the bulk transfer..." )
        self.__asyncBulkTransferStop()
        self.__thread_timer_flag = False
    
    def asyncBulkTransferWait( self, time_out=USB_DEFAULT_TRANSFER_TIMEOUT ) -> bytes:
        """
        Wait for the end of an asynchronous bulk transfer on the USB device.
        This is a blocking call.
        """

        if self.__async_transfer_thread is not None:
            log.info( "Waiting for asynchronous bulk transfer to end..." )
            self.__async_transfer_thread.join()
            self.__async_transfer_thread = None

        # Release the device if it was claimed for the transfer
        if self.__is_claimed:
            self.release()

        # Handle exceptions from the transfer thread if any
        if self.__async_transfer_thread_exception is not None:
            log.warning( "An exception occurred during asynchronous bulk transfer thread execution: " + str( self.__async_transfer_thread_exception ) )
            thread_exception = MuException( f"Thread exception ({type(self.__async_transfer_thread_exception).__name__}): {self.__async_transfer_thread_exception}" )
            self.__async_transfer_thread_exception = None
            raise thread_exception

    
    def asyncBulkTransferStop( self ) -> None:
        """
        Stop an asynchronous bulk transfer on the USB device
        Not implemented yet
        """
        raise NotImplementedError( 'Usb.asyncBulkTransferStop() not implemented yet' )
    
