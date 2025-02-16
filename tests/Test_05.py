import platform
from ctypes import addressof, byref, sizeof, create_string_buffer, CFUNCTYPE
import usb1
import libusb1

# STM32 (SLBP) :
USB3_VENDOR_ID                          = 0x0483
USB3_VENDOR_PRODUCT                     = 0x5740
# TELEMAKE :
#USB3_VENDOR_ID                          = 0xFE27
#USB3_VENDOR_PRODUCT                     = 0xAD00
# Mu256 :
#USB3_VENDOR_ID                          = 0xFE27
#USB3_VENDOR_PRODUCT                     = 0xAC01

USB_RECIPIENT__DEVICE = 0x00
USB_RECIPIENT__INTERFACE = 0x01
USB_RECIPIENT__ENDPOINT = 0x02
USB_RECIPIENT__OTHER = 0x03

USB_INTERFACE                           = 1
USB_DEFAULT_TIMEOUT                     = 5000
USB_RECIPIENT_DEVICE			        = USB_RECIPIENT__DEVICE
#USB_REQUEST_TYPE_VENDOR			    = 0x40 // Ne fonctionne pas sur les proto télémaque, utiliser 0x21
USB_REQUEST_TYPE_VENDOR			        = 0x21
USB_ENDPOINT_OUT				        = 0x00


def ctrlWrite( handle, request, data, time_out=USB_DEFAULT_TIMEOUT, recipient_device=USB_RECIPIENT_DEVICE, type_vendor=USB_REQUEST_TYPE_VENDOR, endpoint_out=USB_ENDPOINT_OUT ):
    """
    Send a write command to the Megamicros FPGA through the usb interface

    Parameters
    ----------
    handle: USBDeviceHandle
        USB device handle
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

    if handle is None:
        raise Exception( "USB device not connected" )

    ndata = handle.controlWrite(
                    # command type
        recipient_device | type_vendor | endpoint_out,
        request, 	# command
        0,			# command parameter value
        0,			# index
        data,		# data to send 
        time_out 
    )

    if ndata != sizeof( data ):
        print( 'ctrlWrite(): command failed with ', ndata, ' data transfered against ', sizeof( data ), ' wanted ' )


def ctrlEmptyWrite( handle, request, time_out=USB_DEFAULT_TIMEOUT, recipient_device=USB_RECIPIENT_DEVICE, type_vendor=USB_REQUEST_TYPE_VENDOR, endpoint_out=USB_ENDPOINT_OUT ):
    """
    Send a write command to the device with no data to transfer (0 length). 
    Do not use controlWrite() if tou have no data to send.
    controlWrite() computes the data length on its own, that is something >0 leading to a LIBUSB_ERROR_PIPE [-9] exception
    """

    if handle is None:
        raise Exception( "USB device not connected" )
    
    data = create_string_buffer( 16 )
    try:
        ndata = handle._controlTransfer(
            recipient_device | type_vendor | endpoint_out,
            request, 
            0,
            0, 
            data, 
            0,
            time_out,
        )
    except Exception as e:
        print( f"empty write failed on device: {e}" )
        raise

    if ndata != 0:
        print( f"ctrlEmptyWrite(): command failed with {ndata} data transfered against 0 wanted" )



def check_device():
    """ Check megamicros devices connected to the host

    Populate class properties about devices connected to the host
    Throw an exception if no device is found
    """

    print(' .Checking usb devices...')

    with usb1.USBContext() as context:

        found: bool = False
        device_vendor_id: int = 0
        device_product_id: int = 0
        for usb_device in context.getDeviceIterator( skip_on_error=True ):
            device_vendor_id = usb_device.getVendorID()
            device_product_id = usb_device.getProductID()
            if device_vendor_id == USB3_VENDOR_ID and device_product_id == USB3_VENDOR_PRODUCT:
                print(" .Found System [D'ALEMBERT] device")
                found = True
                break

        if not found:
            raise Exception( "No D'ALEMBERT device found" )

        # Try to connect to the device
        handle = context.openByVendorIDAndProductID( device_vendor_id, device_product_id, skip_on_error=True, )

        if handle is None:
            raise Exception( "Failed to connect to USB device: the device may be disconnected or user not allowed to access" )
        else:
            print( f" .Connected on USB device {platform.system()}: {device_vendor_id:04x}:{device_product_id:04x}" )

        # Print device characteristics
        print( f" .Found following device {device_vendor_id:04x}:{device_product_id:04x} characteristics :" )
        print( f"  > OS System: {platform.system()}" )
        print( f"  > Bus number: {usb_device.getBusNumber()}" )
        print( f"  > Ports number: {usb_device.getPortNumber()}" )
        print( f"  > Device address: {usb_device.getDeviceAddress()} ({usb_device.getDeviceAddress():04x})" )
        if platform.system() != 'Windows':
            print( f"  > Device name: {usb_device.getProduct()}" )
            print( f"  > Manufacturer: {usb_device.getManufacturer()}" )
            print( f"  > Serial number: {usb_device.getSerialNumber()}" )

        deviceSpeed =  usb_device.getDeviceSpeed()
        if deviceSpeed  == libusb1.LIBUSB_SPEED_LOW:
            print( f"  > Device speed:  [LOW SPEED] (The OS doesn\'t report or know the device speed)" )
        elif deviceSpeed == libusb1.LIBUSB_SPEED_FULL:
            print( f"  > Device speed:  [FULL SPEED] (The device is operating at low speed (1.5MBit/s))" )
        elif deviceSpeed == libusb1.LIBUSB_SPEED_HIGH:
            print( f"  > Device speed:  [HIGH SPEED] (The device is operating at full speed (12MBit/s))" )
        elif deviceSpeed == libusb1.LIBUSB_SPEED_SUPER:
            print( f"  > Device speed:  [SUPER SPEED] (The device is operating at high speed (480MBit/s))" )
        elif deviceSpeed == libusb1.LIBUSB_SPEED_SUPER_PLUS:
            print( f"  > Device speed:  [SUPER PLUS SPEED] (The device is operating at super speed (5000MBit/s))" )
        elif deviceSpeed == libusb1.LIBUSB_SPEED_UNKNOWN:
            print( f"  > Device speed:  [LIBUSB_SPEED_UNKNOWN] (The device is operating at unknown speed)" )
        else:
            print( f"  > Device speed:  [?] (The device is operating at unknown speed)" )

        # try to claim the device
        try:
            with handle.claimInterface( USB_INTERFACE ):
                pass
        except Exception as e:
            raise Exception( f'USB device buzy: cannot claim: {e}' )


def open_device( context ):
    """ Open the device by vendor and product ID """
    return context.openByVendorIDAndProductID( USB3_VENDOR_ID, USB3_VENDOR_PRODUCT, skip_on_error=True, )



def main():
    usb_handle: usb1.USBDeviceHandle | None = None
    
    try:
        check_device()

        print( " .Sending command to the device..." )

        with usb1.USBContext() as context:
            usb_handle = context.openByVendorIDAndProductID( USB3_VENDOR_ID, USB3_VENDOR_PRODUCT, skip_on_error=True, )
            ctrlWrite( usb_handle, 0xB0, b'' )

            # if you have no data to transfer try instead the empty write function:
            # ctrlEmptyWrite( usb_handle, 0xB0 )


    except Exception as e:
        print( f"Error: {e}" )
        exit(1)


if __name__ == "__main__":
	main()
