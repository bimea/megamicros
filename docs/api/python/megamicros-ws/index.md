# megamicros.MegamicrosWS( Megamicros )

This class extends the Megamicros class by adding support for remote receivers handling.
Everything you usually do with base classes like `Mu32` to `Mu1024` can be done in the same way by the `MegamicrosWS` class.

Let's take the following example which performs a self-test on your usb connected receiver:

```python 
Mu32 mu32
mu32.selftest()
```

With a remote receiver on the net, you can do the same with the `MegamicrosWS` class or its children (let's say `Mu32ws` for example):

```python 
Mu32WS mu32ws( 'your_server_address.com', '9002' )
mu32ws.selftest()
```

If you know your remote device is a 32 Megamicros series, then you can use the children `Mu32ws` class.
Otherwise you should use the `MegamicrosWS` class which determinbes by itself the remote system type:

```python 
MegamicrosWS mu32ws( 'your_server_address.com', '9002' )
mu32ws.selftest()
Print( f"Remote system type is: {mu32ws.system}" )
```

??? Example "Example: getting remote settings"

    ```python
    MegamicrosWS = Mu32ws( 'your_server_address.com', '9002'  )
    print( f"System type is: {Megamicros.System(mu32ws.system)}" )
    print( f"Sampling frequency: {mu32ws.sampling_frequency}" )
    print( f"Available mems: {mu32ws.available_mems}" )
    print( f"Activated mems: {mu32ws.mems}" )
    ```

## Policy


## File

* src/megamicros/core-ws.py

## Types and defines

* [defines](defines.md)

## Public getters

* [system]{system.md}

## Public members methods

* [Constructor](constructor.md)
* [selftest](selftest.md)
* [run](run.md)
* [h5](h5.md)
* [scheduler](scheduler.md)
* [listen](listen.md)
* [wait](wait.md)
* [stop](stop.md)
* [is_alive](is_alive.md)