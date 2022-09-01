from network import WLAN
from time import sleep
import pycom

# lista delle reti a cui prova a connettersi

wlans = [('SSID_1', 'Password_1')]
wlan = WLAN(mode=WLAN.STA)  # Default is AP mode

pycom.heartbeat(False)
pycom.rgbled(0x220022)

print("Scanning WLAN networks...")
connected = False

while not connected:
    nets = wlan.scan()
    for net in nets:
        if connected:
            break
        for nwk in wlans:
            if connected:
                break
            if net.ssid == nwk[0]:
                print('Network found, connecting to', nwk[0])
                wlan.connect(nwk[0], auth=(net.sec, nwk[1]), timeout=10000)
                while not wlan.isconnected():
                    sleep(0.5)
                print('WLAN connection succeeded.')
                connected = True
