# mmix::Usb::asyncBulkTransfer()

```cpp
    void mmic::Usb::asyncBulkTransfer( 
        unsigned char bus_address, 
        double duration,
        unsigned int timeout, 
        bool blocking 
    )
```

`asyncBulkTransfer` performs an asynchronous bulk usb transfer of input data through the bus given as argument.
It main purpose is to prepare the transfer process which is made by calling the private [`__asyncBulkTransfer_events_handler()`](__asyncBulkTransfer_events_handler.md) function. This call is done through a new dedicaced thread when in non blocking mode. 


## Arguments

### `unsigned char bus_address`

The usb bus address to which the transfer has to be done;

### `double duration`

The duration transfer in seconds. O means infinite transfer loop. 
Delays less than one seconds are accepted (``duration=0.01`` for example). 

### `unsigned int timeout`

The time without any data from the receiver after which the transfer is considered lost. 
A timeout always causes the processing loop to stop.

### `bool blocking`

Whether the function call is blocking or not.
The blocking mode forces the program to wait until the function is completed before continuing.
The non blocking mode causes the fonction to run in a new thread.
You can wait for the end of this thread by calling the ```Usb::wait()``` method.

You cannot ask for a blocking transfer with `duration=0` since it would cause the process to never stop.



