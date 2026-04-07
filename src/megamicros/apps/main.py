# megamicros.apps.main.py
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

import argparse

from megamicros import __version__, welcome_msg, UsbDataSource
from megamicros.sources.usb import PRODUCT_MAP
from megamicros.log import log
from megamicros.exception import MuException

def arg_parse() -> tuple:

    parser = argparse.ArgumentParser()
    parser.add_argument( "-v", "--version", help=f"show megamicros installed version", action='store_true' )
    parser.add_argument( "--verbose", help=f"set verbose mode on", action='store_true' )
    parser.add_argument( "--check-usb", help=f"check usb device", action='store_true' )
    parser.add_argument( "--check-device", help=f"check megamicros device", action='store_true' )

    return parser.parse_args()

def main():

    args = arg_parse()

    if args.version:
        print( f"megamicros {__version__}" )
        return
    
    if args.verbose:
        log.setLevel( "INFO" )
    else:
        log.setLevel( "ERROR" )

    # Print welcome message
    print( welcome_msg )
    print( f"megamicros {__version__}" )

    if args.check_usb:
        print( "Checking USB not yet implemented" )

    elif args.check_device:
        print( "Checking Megamicros device..." )
        try:
            device_found, product_id = UsbDataSource.detectMegamicrosDevice()
            if device_found:
                device_hardware = PRODUCT_MAP.get(product_id, None)
                if device_hardware:
                    print( f">>>> Found {device_hardware} Megamicros device")
                else:
                    print( f"Device with Product ID 0x{product_id:04X} detected, but not recognized." )
            else:
                print( "No Megamicros device found." )

        except MuException as e:
            print( f"Failed: {e}")
    else:
        print( "No action specified. Use --help for available options." )


if __name__ == "__main__":
	main()
