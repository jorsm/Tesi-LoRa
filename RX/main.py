from network import LoRa
import socket
import time
import pycom
import urequests
import _thread
import ujson
import struct
import gc


# "http://lora-evaluation-mediator.herokuapp.com"
BASE_URL = "http://lorapy.herokuapp.com"
urequests.post(
    BASE_URL + "/rx_status",
    data='{"dr":-1}',
    headers={'content-type': 'application/json'}
).close()

data_rates = [
    # (SF, BW)
    (12, LoRa.BW_125KHZ),
    (11, LoRa.BW_125KHZ),
    (10, LoRa.BW_125KHZ),
    (9,  LoRa.BW_125KHZ),
    (8,  LoRa.BW_125KHZ),
    (7,  LoRa.BW_125KHZ),
    (7,  LoRa.BW_250KHZ),
]

dr = -1

thread_running = False
recv_ids = []
recv_ids_lock = _thread.allocate_lock()
send_stat_threshold = 25  # After this number of packets, send stats to server


def send_to_server(message):
    urequests.post(
        BASE_URL + "/messages",
        data='{"sender": "Rx", "message": " ' + message + ' "}',
        headers={'content-type': 'application/json'}).close()

#inizia prima a riga 90
#thread per la ricezione dei pacchetti
def thread_recv_lora():
    global BASE_URL, data_rates, dr, recv_ids, recv_ids_lock, thread_running
    thread_running = True

    print("[RX.LoRa] Initializing radio...")
    send_to_server("[RX.LoRa] Initializing radio...")
    lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)

    while dr <= 6 and dr != -1:#dr viene aggiornato dalla thread main
        curr_dr = dr  # To compare with dr if it gets updated
        lora.sf(data_rates[curr_dr][0])
        lora.bandwidth(data_rates[curr_dr][1])
        s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
        s.setblocking(False)

        # Tell TX we're ready
        urequests.post(
            BASE_URL + "/rx_status",
            data='{"dr":'+str(curr_dr)+'}',
            headers={'content-type': 'application/json'}
        ).close()
        print("[RX.LoRa] Switched to DR", curr_dr)
        send_to_server("[RX.LoRa] Switched to DR " + str(curr_dr))
       #loop di ricezione
        while True:
            tmp = s.recv(16)

            if tmp:#interferenze
                if tmp[0] not in [1, 2, 3, 4]:
                    print("[RX.LoRa] Unknown target CR, dropping message")
                    send_to_server(
                        "[RX.LoRa] Unknown target CR, dropping message")
                else:
                    #spacchetta i byte ricevuti -> restituisci l'intero che identifica il pacchetto
                    pkt_id = struct.unpack('i', tmp[1:5])[0]
                    with recv_ids_lock:
                        recv_ids.append(pkt_id)
            else:
                time.sleep(0.1)#sleep fino a che non ricevi 16 bytes

            if curr_dr != dr:  # TX has changed dr
                break
    print("[RX.LoRa] Finished")
    send_to_server("[RX.LoRa] Finished")


print("[RX.Main] Waiting for TX to come up...")
send_to_server("[RX.Main] Waiting for TX to come up...")

#nel while aspetto che tx aggiorni il server poi inizia la thread di ricezione

while True:
    pycom.rgbled(0x000022)
    resp = urequests.get(BASE_URL + "/tx_status").json()

    if int(resp['dr']) != dr:  # TX has changed
        dr = int(resp['dr'])
        print("[RX.Main] TX switched to DR", dr)
        send_to_server("[RX.Main] TX switched to DR " + str(dr))

        if dr != -1 and not thread_running:  # First DR, start lora recv loop
            _thread.start_new_thread(thread_recv_lora, ())
        elif dr == -1:  # TX dr is -1 but ours wasn't -> finished
            print("[RX.Main] Finished", dr)
            send_to_server("[RX.Main] Finished DR: " + str(dr))
            break
        pycom.rgbled(0x006600)

    time.sleep(5)
#aggiorna il server sui pacchetti ricevuti
    if len(recv_ids) >= send_stat_threshold:
        print("[RX.Main]", len(recv_ids),
              "messages queued, sending recv_ids to server...")
        send_to_server("[RX.Main] " + str(len(recv_ids)) +
                       " messages queued, sending recv_ids to server...")
        with recv_ids_lock:
            urequests.post(
                BASE_URL + "/rx_status",
                data='{"recv_ids": ' + ujson.dumps(recv_ids) + '}',
                headers={'content-type': 'application/json'}
            ).close()
            send_to_server("Sending pckets confirm")

            del recv_ids
            recv_ids = []

        gc.collect()

# Show idle
urequests.post(
    BASE_URL + "/rx_status",
    data='{"dr":-1, "recv_ids": ' + ujson.dumps(recv_ids) + '}',
    headers={'content-type': 'application/json'}
).close()

while True:
    time.sleep(0.5)
    pycom.rgbled(0x222200)
    time.sleep(0.5)
    pycom.rgbled(0x000022)
