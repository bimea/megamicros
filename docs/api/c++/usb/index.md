# mmic::Usb

```cpp
class mmic::Usb
```

The `Usb` class is devoted to data transfer handling between a Megamicros receiver and a PC via the usb port.

* [asyncBulkTransfer](async_bulk_transfer.md)

void Usb::asyncBulkTransfer( unsigned char bus_address, u_int64_t transfers_number, unsigned int timeout, bool blocking ) {
