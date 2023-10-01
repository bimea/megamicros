import numpy as np
import queue
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


antenna.run(
    mems = [1, 2],
    duration=2,
    buffer_length=512,
    signal_q_size = 0,
)

i = 0
while True:
    try:
        data = antenna.signal_q.get( timeout=5 )
        print( f"[{i}]" )
        i += 1
        # do what you want with data...

    except queue.Empty:
        print( f"exit from loop at i={i}" )
        break

antenna.wait()

exit()




antenna.setActiveMems( [1, 2] )
antenna.run(
    duration=2,
    sync=False,
    buffer_length=512,
    counter = False,
    counter_skip = False,
    signal_q_size = 0,
    status = False,
    h5_recording=False,                          # H5 recording ON
    h5_pass_through=False,                       # perform F5 recording on server
    h5_rootdir='./',                            # directory where to save file
    h5_compressing=False,                       # Use compression or not
    background_mode=False,
)


for i, data in enumerate( antenna ):
    print( f"[{i}]" )

print( f"exit from loop at i={i}" )
antenna.wait()

antenna.run()

i = 0
while True:
    print( f"[{i}]" )
    try:
        data = antenna.signal_q.get( timeout=5 )
        i += 1
    except queue.Empty:
        print( f"exit from loop at i={i}" )
        break

antenna.wait()



