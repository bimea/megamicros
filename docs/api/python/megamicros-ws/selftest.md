# core-ws.MegamicrosWS.selftest

Perform a one-second recording test to obtain and update the remote Megamicros receiver settings.
Note that the test is performed with the default settings of the host but not with the current settings.
Only available mems and analogs are affected by the test results.

## Files

* src/megamicros/core_ws.py

??? Example

    ```python 
    MegamicrosWS mu32ws( 'your_server_address.com', '9002' )
    mu32ws.selftest()
    ```

If you want to know the actual values of available mems and available analogs after the test you can perform a *settings* request after the self-test:

??? Example "Example: performing a self-test and getting the detected available mems and analogs channels"

    ```python 
    MegamicrosWS mu32ws( 'your_server_address.com', '9002' )
    mu32ws.selftest()
    settings = mu32ws.settings()
    print( f"Found {settings['available_mems']} available mems and {settings['available_analog']} analogics " )
    ```

!!! Note

    It is not mandatory to perform an autotest right after the creation of the MegamicrosWS object.
    Indeed, a self-test is already performed during the creation process of the object, so that calling the settings method is sufficient.

