# Dash-websocket

*dash-websocket* is a javascript component for Dash inspired by the [Dash-extension:websocket](https://www.dash-extensions.com/components/websocket).

## Properties

### state (object of string)

The websocket state and associated informations. 
It is populated at websocket opening:

```javascript
    state: {
        // Mandatory props.
        readyState,
        isTrusted,
        timeStamp,
        // Extra props.
        origin
    }
```

`readyState` can be either:

```
    WebSocket.CONNECTING: 0;
    WebSocket.OPEN: 1;
    WebSocket.CLOSING: 2;
    WebSocket.CLOSED: 3;
```


### message (object) 

This property is updated with the message content when receiving text messages 

```javascript
    message: {
        data,
        isTrusted,
        origin,
        timeStamp
    }
```

### binary (ArrayBuffer)

When receiving binary messages that can be of `Blob` type or `ArrayBuffer`, converts them as `ArrayBuffer` and update the `binary` property:

```javascript
    binary: {
        data: e.data,
        isTrusted: e.isTrusted,
        origin: e.origin,
        timeStamp: e.timeStamp
    }
```

### error (json string)

This property is set with the json content of the onerror event.

### send (object or string)

When this property is set, a message is sent with its content.

### url (string)

Create the websocket object and set the websocket endpoint. 
If no websocket is active, creates ones. 
Otherwise destroys the current socket and creates a new one.
If a protocol is specified, sets at websocket creation.

### protocols (string)

Supported websocket protocols (optional).


### id (string)

The ID used to identify this component in Dash callbacks.

### close (string)

Close the websocket




# Documentation

* [Dash-extension: websocket](https://www.dash-extensions.com/components/websocket)
* [Dash-extension: websocket (GitHub)](https://github.com/thedirtyfew/dash-extensions)
* [Javascript WebSocket](https://javascript.info/websocket) [(fr)](https://fr.javascript.info/websocket)
* [Streaming in javascript](https://plotly.com/javascript/streaming/#30-points-using-update)
* [Typed arrays - Binary data in the browser](https://web.dev/webgl-typed-arrays/)