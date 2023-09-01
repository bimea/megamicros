# Station tracker

The *Station tracker* system is a MQTT C++ client running as a service on any computer which hosts a *megamicros broadcast server* (MBS).

## Configuration

```json
{
    "config": {
        "filename": "mbs-tracker.json"
    },
    "logging": {
        "file": "mbs-tracker.log",
        "level": "info"
    },
    "mqtt": {
        "broker": "parisparc.biimea.tech",
        "client_id": "STRACKER2023",
        "persist": "mbs-tracker.persist",
        "logging": {
            "topic": "STRACKER2023/log",
            "qos": 1
        }
    },
    "topic": "STRACKER2023/pub",
    "qos": 1,
    "period": 60
}
```

