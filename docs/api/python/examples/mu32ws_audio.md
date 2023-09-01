# mu32ws_audio.py

With this example, you can use the Mu32ws class for geting signals from a Megamicros remote server.

!!! Note "Note: before using"

    Before working with this example, you should have installed the PyAudio library. 
    On Mac OS systems:

    ```bash
        $ > brew install portaudio
        $ > pip install pyaudio
    ```

    See [PyAudio Python page](https://pypi.org/project/PyAudio/)
    and [PyAudio documentation](http://people.csail.mit.edu/hubert/pyaudio/ )

Program help:

```bash
    $ > python examples/mu32ws_audio.py -h
```

This example illustrates the blocking mode transfer.
The processing loop extracts the audio frames from the queue and send them to the output audio stream.
Reading and writing are synchroneous operations that stands one after the other.
As a direct consequence there is a minimum latency that cannot be avoided.
This latency is at least equal to the frame duration. 
For frames of 256 samples at a sampling frequency of 50kHz, the latency is greater or equal to 5ms.
All this stands provided the queue is not limited. 

## Using the PyAudio library

The PyAudio Library offers two modes for audio input/output performing:
* The blocking mode;
* The callback mode.

In *blocking mode*, each writing or reading call blocks until all frames have been played/recorded. 
The *callback mode * is an alternative approach in which PyAudio invokes a user-defined function to process recorded audio or generate output audio.


??? Example "Python program"

    ```python 
    # Instantiate Mu32ws and initialize Mu32 with host and port of remote server
    mu32 = MegamicrosWS( remote_host=host, remote_port=port )

    # Start running the remote Megamicros system
    mu32.run( 
        mems = (5, 6),                      # the microphones used
        duration = 0,                       # infinite acquisition loop      
        clockdiv = 9,                       # sampling frequency is 50kHz
        frame_length=256,                   # 256 samples per transfer frame
        counter = False,                    # counter is not acivated
        sync=False,                         # asynchronous mode
        signal_q_size=0                     # no limitation on the queue size
    )
    
    # Instantiate PyAudio and initialize PortAudio system resources (1)
    p = pyaudio.PyAudio()

    # Open stream (2)
    stream = p.open(
        format = pyaudio.paFloat32,         # data type: float 32
        channels = 2,                       # 2 mems
        rate = 50000,                       # sampling frequency is 50kHz 
        output=True,                        # output audio stream
        frames_per_buffer=256,              # 256 samples per transfer frame
    )

    # input-output loop
    # Frames are extracted from the queue and sent to the audio output stream
    # Since we use the blocking mode rather than the callback mode, there is a minimum latency that cannot be avoided (at least equal to the frame duration).
    # ALl this stands provided the queue is not limited (signal_q_size=0).
    # Use [Ctrl][C] to stop the loop
    transfers_counter = 0
    try:
        while( True ):
            data = mu32.signal_q.get()
            data = data.astype( np.float32 ).T * mu32.sensibility
            stream.write( data, num_frames = 256 )
            transfers_counter += 1

    except KeyboardInterrupt:
        print( f"Quitting loop !" )
    except Exception as e:
        print( f"Unexpected error: {e}" )
    
    print( f"Received transfers = {transfers_counter}" )

    stream.close()                          # Close audio output stream
    p.terminate()                           # Release PortAudio system resources
    mu32.stop()                             # Release mu32 
    ```
