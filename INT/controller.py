import serial
import time
import requests

BASE_URL = 'http://'+''+'.herokuapp.com'  # indirizzo del server (app heroku)


def notifyServer(message):
    str(message)
    requests.post(BASE_URL + '/messages',
                  data='{"sender": "INT", "message": " ' + message + ' "}',
                  headers={'content-type': 'application/json'})


def setupConfig():
    print("Config setup....")
    global initial_CR, initial_DR, pr_int, arduino
    while True:
        time.sleep(1)
        r = requests.get(BASE_URL + '/tx_status')
        res = r.json()
        if res["dr"] != -1:  # TX started
            initial_DR = res["dr"]
            if res["cr"]:
                initial_CR = res["cr"]
                if res["pr_int"]:
                    pr_int = res["pr_int"]
                    notifyServer(
                        f'new config received! DR: {initial_DR}, CR: {initial_CR}, pr_int: {pr_int}')
                    # Valid config received, setup arduino via serial
                    arduino.setDTR(False)
                    time.sleep(0.5)
                    arduino.flushInput()
                    arduino.setDTR(True)
                    notifyServer("Serial Ready! setting up Draghino...")

                    # wait for aroduino feedback
                    data = arduino.read_all()
                    while len(data) < 1:
                        time.sleep(1)
                        data += arduino.read_all()
                    print(data.decode())  # waiting for configs
                    notifyServer(data.decode())
                    # send config params to arduino
                    arduino.write(str.encode(
                        f'{initial_DR},{initial_CR},{pr_int};'))
                    time.sleep(1)
                    data = arduino.read_all()
                    while len(data) < 2:
                        time.sleep(1)
                        data = arduino.read_all()
                    print("From Arduino: "+data.decode())
                    notifyServer("From Arduino: "+data.decode())
                    notifyServer("waiting for RX")
                    # TX Ready, INT ready, waiting for RX
                    for i in range(30):
                        r = requests.get(BASE_URL + '/rx_status')
                        res = r.json()

                        if res["dr"] != -1:
                            notifyServer("RX ready! stsrting interf.")
                            return interfere()
                        time.sleep(1)


def interfere():
    global initial_CR, initial_DR, pr_int, arduino
    while True:
        r = requests.get(BASE_URL + '/rx_status')
        res = r.json()
        # Reset if TX resets itself
        if res["dr"] == -1:  # TX restarted... new config
            notifyServer("TX restarted, setting up new config...")
            return setupConfig()
            initial_CR = 1
            initial_DR = 0
        else:
            r = requests.get(BASE_URL + '/tx_status')
            res = r.json()
            if res["cr"] != initial_CR:
                initial_CR = res["cr"]
                initial_DR = res["dr"]
                # skip to the next config on Arduino (firmware.ino:check_state())
                arduino.write('a'.encode())
                notifyServer("Updating config....")
                time.sleep(1)
                data = arduino.read_all()
                if len(data) > 2:
                    print(data.decode())
                    notifyServer(data.decode())
            else:
                time.sleep(1)


cr = 1
initial_DR = 0
initial_CR = 0
pr_int = 0
# /dev/ttyACM0 default usb port su linux
# per windows COM1
arduino = serial.Serial('/dev/ttyACM0', 9600)


setupConfig()
