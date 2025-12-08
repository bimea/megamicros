# megamicros.apps.megamicros.py is the command line interface for megamicros.
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

import argparse

from megamicros import __version__, welcome_msg
from megamicros.log import log
from megamicros.exception import MuException
from megamicros.core.mu import Megamicros
from megamicros.usb import Usb

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
        print( "Checking USB..." )
        try:
            for system_name, system_info in Megamicros.Systems.items():
                if Usb.checkDeviceByVendorProduct( system_info['vendor_id'],  system_info['product_id'] ):
                    print( f"Found following {system_info['name']} Megamicros device found with following characteristics:")
                    print( f"  - system name: {system_info['name']}" )
                    print( f"  - usb vendor id: {system_info['vendor_id']:04x}" )
                    print( f"  - usb vendor product: {system_info['product_id']:04x}" )
                    print( f"  - usb bus address: {system_info['bus_address']}" )
                    print( f"  - pluggable mems number: {system_info['beams']*8}" )
                    print( f"  - pluggable analogs number: {system_info['analogs']}" )
                    return

            print("No Megamicros system found.")
            return

        except MuException as e:
            print( f"Failed: {e}")

    elif args.check_device:
        print( "Checking Megamicros device..." )
        try:
            antenna = Megamicros()
            available_mems, available_analogs = antenna.selftest(1)
            print( f"Found Megamicros device:")
            print( f"  - {len(available_mems)} available MEMs found")
            print( f"  - {len(available_analogs)} available analogs found")
            print( f"  - MEMs: {available_mems}" )
            print( f"  - Analogs: {available_analogs}" )

        except MuException as e:
            print( f"Failed: {e}")


if __name__ == "__main__":
	main()
