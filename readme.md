# Funzionamento

### TX (Trasmettitore)

- Si collega ad una rete WiFI
- Dopo essersi connesso al Server aspetta di ricevere vlaori validi per il _Coding Rate_ e per il _Data Rate_ da cui iniziare a trasmettere

### RX (Ricevitore)

- Si collega ad una rete WiFI
- Aspetta che TX sia pronto
- Si sincronizza con i valori di _Coding Rate_ e _Data Rate_

### INT (Interferenza)

- il file controller.py si occupa della sincronizzazione con il server, usa la connessione del PC e comunica con Arduino via porta USB
- Arduino aspetta che TX e RX siano pronti, si sincronizza ed inizia ad inviare pacchetti a sua volta

### Server

- mantiene i parametri relativi allo stato dei vari device
- permette monitorare lo stato dei device tramite un'interfaccia
- permette di resettare il trasmettitore se necessario e di impostare i parametri per la misurazione successiva
