# Remote antenna

The python class `MegamicrosWS` is intended to be used with the MBS server.
That is, rather than programming for a Megamicros device connected on your own laptop, you programm for a remote device connected to the internet using the C++ MBS server.
The `MegamicrosWS` class acts as an interface between you and the MBS server.
Since the interface derives from the base parent class `Megamicros`, programming with `MegamicrosWS` is somewhat identical to programming with other classes derived from `Megamicros` such as `Megamicros32`or `Megamicros256`or even `MegamicrosH5`.

## Example

Here is the simplest example of how to connect to the MBS server and get some informations:

```python

# See: ./Megamicros/examples/mu32ws_selftest.py
from megamicros.core_ws import Megamicros, MegamicrosWS

mu32ws = MegamicrosWS( remote_host='localhost', remote_port=9002 )
mu32ws.selftest()

settings = mu32ws.settings()
print( f"System type is: {Megamicros.System(settings['system'])}" )
print( f"Sampling frequency: {settings['sampling_frequency']}" )
print( f"Available mems: {settings['available_mems']}" )
print( f"Activated mems: {settings['mems']}" )
...
```

