import numpy as np
import matplotlib.pyplot as plt
from megamicros.log import log
from megamicros.core.ws import MemsArrayWS

log.setLevel( "INFO" )

# Set server access credentials
HOST = 'buzenval20.fr'
PORT = 9002


# Define the antenna
try:
    antenna = MemsArrayWS( host=HOST, port=PORT )
except Exception as e:
    print( f"Failed: {e}" )
    exit()

antenna.setActiveMems( [1, 2] )
antenna.run(
    duration=2,
    sync=True,
    buffer_length=512,
    counter = False,
    counter_skip = False,
    status = False,
    h5_recording=True,                          # H5 recording ON
    h5_pass_through=True,                       # perform F5 recording on server
    h5_rootdir='./',                            # directory where to save file
    h5_compressing=False,                       # Use compression or not
    background_mode=True,
)