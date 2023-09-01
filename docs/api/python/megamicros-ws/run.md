# core-ws.MegamicrosWS.run

The run method excutes a recording process on the remote Megamicros receiver. 

## Run settings

The run method accepts parameters that are the settings of the receiver for the recording to work.
Without those settings the receiver performs the run with current settings values.

??? Example 

    ```python
    MegamicrosWS mu32ws( 'your_server_address.com', '9002' )
    mu32ws.run()
    ```

You may have to provide some parameters yourself. All parameters can be passed as arguments to the method.

??? Example "Example: Passing settings to the run method"

    ```python
    MegamicrosWS mu32ws( 'your_server_address.com', '9002' )
    mu32ws.run(
        duration = 1,
        sampling_frequency = 10000 
    )
    ```