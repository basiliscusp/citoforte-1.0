# CITOFORTE

Progetto per Orange Pi Zero su Armbian pensato per ascoltare controller MIDI USB e preparare una base stabile per automazioni future.

L'idea e semplice:
- collego un controller MIDI via USB
- il sistema lo riconosce
- lo script si mette in ascolto sulla porta MIDI disponibile
- i messaggi vengono stampati a schermo

## Capitoli

- [Setup hardware](docs/setup-hardware.md)
- [Setup software](docs/setup-software.md)
- [Uso quotidiano](docs/uso.md)

## Cosa contiene il repository

- `scripts/check_system.sh`: controlli rapidi su USB, ALSA e MIDI
- `scripts/bootstrap_orangepi.sh`: bootstrap automatico della scheda
- `src/citoforte/main.py`: entrypoint CLI
- `src/citoforte/midi/monitor.py`: monitor MIDI ALSA
- `deploy/systemd/citoforte.service`: avvio automatico con systemd

## Stato attuale

La prima versione del progetto serve per verificare che:
- la scheda veda il controller USB
- ALSA esponga la porta MIDI
- lo script legga i messaggi correttamente

## Come partire in breve

Se hai già clonato il repository, il flusso base è:

```bash
cd CITOFORTE
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
citoforte-monitor --auto
```

Per il bootstrap automatico della macchina, vedi [Setup software](docs/setup-software.md).
