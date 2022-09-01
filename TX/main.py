from network import LoRa
import socket
import time
import pycom
import urequests
import ujson
import struct
import gc
import machine

BASE_URL = 'http://'+''+'.herokuapp.com'  # indirizzo del server (app heroku)
# Led colors
BLACK = 0x000000
PURPLE = 0x220000
GREEN = 0x006600
YELLOW = 0xcccc00
BLUE = 0x0000ff
# Set up radio in LoRa mode
lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)

data_rates = [
    # (SpreadingFactor, BandWidth) possibili (DataRate [1...7])
    (12, LoRa.BW_125KHZ),
    (11, LoRa.BW_125KHZ),
    (10, LoRa.BW_125KHZ),
    (9,  LoRa.BW_125KHZ),
    (8,  LoRa.BW_125KHZ),
    (7,  LoRa.BW_125KHZ),
    (7,  LoRa.BW_250KHZ),
]

# Number of packets to send per setting
PKT_N = 250
pkt_id = 0
msg = [0]*16
time_stats = []
send_stat_threshold = 25  # After this many packets, send stats to server
initialDR = 0
initialCR = 1


# invia un messaggio al server tramite l'interfaccia Wifi, con mittente 'Tx'
def send_to_server(message):
    print(message)
    urequests.post(
        BASE_URL + "/messages",
        data='{"sender": "Tx", "message": " ' + message + ' "}',
        headers={'content-type': 'application/json'}).close()
    gc.collect()


# inizio del loop di sincronizzazione col server
send_to_server("Getting configs from server...")

while True:
    try:  # se le cose vanno male aspetta e riprova
        resp = urequests.get(BASE_URL + "/reset_stats")
        # invio una richiesta al server per parametri di config. iniziali
        if not resp or not resp.json():
            # controllo la risposta
            raise ValueError("nessuna risposta valida dal server")
        elif 'dr' not in resp.json():
            raise ValueError("campo 'dr' non trovato")
        else:
            # setup DataRate ->(bw, sf) e CodeRate iniziale

            if resp.json()['dr'] != -1:
                # controllo dal server da che data rate iniziare
                initialDR = int(resp.json()['dr'])
                initialCR = int(resp.json()['cr'])
                time.sleep(1)
                break
            # se 'dr' == -1 la config  non e' valida
            send_to_server("Server sent no config, retrying in 5 secs...")
            time.sleep(5)

    except Exception as e:
        # gestione dell'errore nel caso di nessuna risposta dal server o nessun dr
        for i in range(10):
            pycom.rgbled(0x0000ff)
            time.sleep(1)
            pycom.rgbled(PURPLE)  # PURPLE
            time.sleep(1)
            pycom.rgbled(BLACK)
            time.sleep(28)


send_to_server("Setup finished, start sending...")


try:  # se va male qualcosa resetta il device e riprova
    # -> [(0, (12, LoRa.BW_125KHZ)), (dr_idx,dr),...]
    for dr_idx, dr in enumerate(data_rates):
        if dr_idx < initialDR:
            print("[*] Skipping DR", dr_idx)
            continue

        send_to_server("[*] Setting up DR" + str(dr_idx))
        lora.sf(dr[0])
        lora.bandwidth(dr[1])
        # aggiorna il server sullo stato del device
        urequests.post(
            BASE_URL + "/tx_status",
            data='{"dr":'+str(dr_idx)+'}',
            headers={'content-type': 'application/json'}
        ).close()

        send_to_server("    > Waiting for receiver to be ready...")
        while True:  # Recv not ready
            pycom.rgbled(YELLOW)  # ??
            # controlla lo stato del ricevitore sul server
            resp = urequests.get(BASE_URL + "/rx_status")
            # attendi che il ricevitore sia pronto e sincronizzato
            if resp.json()['dr'] == dr_idx:
                break
            del resp
            pycom.rgbled(GREEN)
            time.sleep(3)

        for cr in [LoRa.CODING_4_5, LoRa.CODING_4_6, LoRa.CODING_4_7, LoRa.CODING_4_8]:

            if cr < initialCR:  # salta i cr non richiesti nella configurazione iniziale
                send_to_server("[*] Skipping CR: {}".format(cr))
                continue
            # imposta il 'cr'
            send_to_server("    > Coding Rate: {}".format(cr))
            lora.coding_rate(cr)
            msg[0] = cr
            # crea un socket lora, controllare documentazione per maggiori info...
            s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
            s.setblocking(False)
            s.settimeout(2)

            for i in range(PKT_N):

                #pack(format, val,)
                # Return a bytes object containing the values v1, v2, … packed according
                # to the format string format. format = 'i' -> int

                # impacchetta in byte i miei dati
                tmp = struct.pack('i', pkt_id)
                msg[1] = tmp[0]
                msg[2] = tmp[1]
                msg[3] = tmp[2]
                msg[4] = tmp[3]

                # timing invio pkt
                t_start = time.ticks_us()
                try:
                    s.send(bytes(msg))
                except:
                    send_to_server("sending packet failed!")

                t_end = time.ticks_us()
                # array che periodicamente viene inviato al server per un riscontro dei pacchetti inviati
                time_stats.append({
                    'id': pkt_id,
                    'cr': cr,
                    'dr': dr_idx,
                    'size': len(msg),
                    'time_ms': time.ticks_diff(t_end, t_start)/1000
                })

                if i % 10 == 0:
                    # periodicamente aggiorno il server sull'avanzamento
                    send_to_server("Sent {}/{}, available heap RAM = {} Kb with cr: {}".format(i +
                                                                                               1, PKT_N, gc.mem_free()//1024, cr))
                    # e controllo che non sia richiesto un reset
                    resp = urequests.get(BASE_URL + "/reset")
                    reset = resp.json()['reset']
                    if reset:
                        send_to_server("Restarting TX")
                        urequests.post(BASE_URL + "/reset")
                        machine.reset()

                # Show that a packet was sent
                pkt_id += 1
                pycom.rgbled(BLACK)  # BLACK
                time.sleep(0.1)
                pycom.rgbled(PURPLE)  # PURPLE

                # aggiorna il server: manda il json al server con i paccketti gia' inviati
                if pkt_id % send_stat_threshold == 0:
                    print(
                        "\n      [Sending partial timing stats to server...]")
                    gc.collect()  # Make room in memory for big JSON request...

                    urequests.post(
                        BASE_URL + "/tx_status",
                        data='{"time_stats": ' + ujson.dumps(time_stats) + '}',
                        headers={'content-type': 'application/json'}
                    ).close()

                    del time_stats
                    time_stats = []

            print()

            s.close()
            del s
            gc.collect()

        initialCR = 0
        # Show end of DR
        pycom.rgbled(GREEN)

    print("\nFinished")
    send_to_server("Finished")
    gc.collect()

    # Show idle
    urequests.post(
        BASE_URL + "/tx_status",
        data='{"dr":-1, "time_stats": ' + ujson.dumps(time_stats) + '}',
        headers={'content-type': 'application/json'}
    ).close()

    time.sleep(2)
    machine.reset()

except:
    print("TX FATAL ERROR, RESTARTING!")
    send_to_server("TX FATAL ERROR, RESTARTING...")
    time.sleep(3)
    machine.reset()
