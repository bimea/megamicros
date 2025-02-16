import usb.core
import usb.util
import usb.backend.libusb1
import time

backend = usb.backend.libusb1.get_backend()
dev = usb.core.find(idVendor=0x0483, idProduct=0x5740, backend=backend)

if dev is None:
    print("Device not found! \n")
else:
    print("SLBP détectée! \n")

dev.set_configuration()
time.sleep(2)  # Attendre 1 seconde


for cfg in dev:
    print(f'Configuration {cfg.bConfigurationValue}')
    for intf in cfg:
        print(f'  Interface {intf.bInterfaceNumber}, AltSetting {intf.bAlternateSetting}')
        for ep in intf:
            print(f'    Endpoint {ep.bEndpointAddress}')

usb.util.claim_interface(dev, 0)  # Revendiquer l'interface 0
time.sleep(2)  # Attendre 1 seconde

# Envoi de la commande C_Reset B0
#bmRequestType = (0x02 << 5)
bmRequestType = 0x40  # Host to device
bRequest = 0xB0       # Commande spécifique
wValue = 0x0000       # Valeur de la commande
wIndex = 0x0000       # Index de la commande
data = b''            # Données vides

dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data,10000)
#libusb_control_transfer(dev,bmRequestType, bRequest, wValue, wIndex, data, 0, 10000)
usb.util.release_interface(dev, 0)  # Libérer l'interface
#try:
#    dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data,10000)
#    libusb_control_transfer(dev,bmRequestType, bRequest, wValue, wIndex, data, 0, 10000)
#    print("Commande envoyée !")
#except usb.core.USBError as e:
#    print(f"Erreur USB : {e}")
#finally:
#    usb.util.release_interface(dev, 0)  # Libérer l'interface
