# Setup Hardware

## Lista materiali

Per la realizzazione di questo progetto è stata utilizzata una **Orange Pi Zero** basata su processore **Allwinner H3**, scelta per il basso consumo energetico, le dimensioni compatte e la disponibilità di una distribuzione Linux completa tramite Armbian.

La scheda utilizzata è stata acquistata dal seguente link:

https://it.aliexpress.com/item/1005003510088478.html

L'Orange Pi Zero costituisce il cuore del sistema e si occupa della gestione del controller MIDI USB, dell'esecuzione dell'applicazione e dell'interfacciamento con il sistema operativo Linux tramite i driver ALSA.

### Componenti utilizzati

- Orange Pi Zero (Allwinner H3)
- Alimentatore 5V
- Scheda microSD
- Controller MIDI USB
- Connessione di rete (Ethernet o Wi-Fi)
- Sistema operativo Armbian

---

## Obiettivo

Verificare che:

- la porta USB funzioni correttamente
- il controller MIDI venga visto dal sistema
- ALSA esponga una porta MIDI utilizzabile

---

## Verifiche utili da SSH

Una volta effettuato l'accesso alla Orange Pi tramite SSH è possibile eseguire una serie di controlli diagnostici per verificare il corretto riconoscimento dell'hardware.

### Verifica dispositivi USB

```bash
lsusb