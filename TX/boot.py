# ******************************************************************************************
#
#   - boot.py = setup() per arduino: viene eseguito per primo all'accensione del device
#       qui si connette ad una rete Wifi nota oppure si riavvia in caso di errore
#
#   - main.py = loop() per arduino: ci metti un loop per leggere i sensori e cominicare
#     i dati, possibilmente in due thread diverse
#
# ******************************************************************************************

from network import WLAN
from time import sleep
import pycom


# lista delle reti a cui prova a connettersi

wlans = [('SSID_1', 'Password_1')]

wlan = WLAN(mode=WLAN.STA)  # Default AP mode

pycom.heartbeat(False)
pycom.rgbled(0x220022)

print("Scanning WLAN networks...")
connected = False


def connect():
    global connected
    while not connected:
        nets = wlan.scan()  # cerca reti disponibili
        for net in nets:

            if connected:
                break
            for nwk in wlans:
                if connected:
                    break
                # confromnta le reti note con quelle trovate
                print('Testing for', net.ssid, "on",  nwk[0])
                if net.ssid == nwk[0]:
                    print('Network found, connecting to', nwk[0])
                    # inizia tentativo di connessione
                    wlan.connect(nwk[0], auth=(net.sec, nwk[1]), timeout=10000)

                    while True:
                        try:
                            # attendi connessione effettuata o stato di errore
                            if not wlan.isconnected():
                                sleep(0.5)
                            else:
                                return()
                        except Exception as e:
                            print("Exeption while connecting")
                            machine.reset()  # se fallisce a connetersi reboot del device

                    print('WLAN connection succeeded.')
                    connected = True  # flag per terminare il ciclo di ricerca delle reti
                    return()  # finisce il file ed esegue main.py


connect()
