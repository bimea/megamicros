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

