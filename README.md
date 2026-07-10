# CITOFORTE

Base project per Orange Pi Zero (Armbian) per:
- bootstrap automatico della macchina
- monitoraggio dispositivi MIDI USB
- avvio come servizio systemd

## Obiettivi fase 1

- Rilevare controller MIDI USB collegati
- Intercettare i messaggi in ingresso
- Stampare a schermo Note On/Off e dati principali
- Preparare deployment automatico

## Struttura

- `scripts/bootstrap_orangepi.sh`: setup completo host + deploy app
- `scripts/check_system.sh`: diagnostica rapida USB/MIDI
- `src/citoforte/main.py`: entrypoint CLI
- `src/citoforte/midi/device_watcher.py`: discovery porte MIDI
- `src/citoforte/midi/monitor.py`: loop lettura messaggi MIDI
- `deploy/systemd/citoforte.service`: unit file service

## Setup locale veloce

1. Installa dipendenze:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -e .`
2. Avvia monitor:
   - `citoforte-monitor --auto`

## Bootstrap su Orange Pi

Esempio:

```bash
sudo bash scripts/bootstrap_orangepi.sh --repo-url https://github.com/<user>/<repo>.git
```

Lo script:
- installa pacchetti di sistema
- clona/aggiorna il repository in `/opt/citoforte`
- crea ambiente virtuale Python
- installa il progetto
- installa/abilita il servizio systemd

## Note

Il comportamento in fase iniziale e intenzionalmente semplice: output console per validare hardware e pipeline MIDI prima di introdurre regole applicative.
