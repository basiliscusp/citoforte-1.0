# Setup software

Questa pagina descrive come installare e avviare CITOFORTE sulla Orange Pi.

## Obiettivo

Preparare il sistema per:
- clonare il repository
- creare l'ambiente Python
- installare le dipendenze
- avviare il monitor MIDI
- eventualmente installare il servizio systemd

## Installazione manuale

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip alsa-utils usbutils

git clone https://github.com/<user>/CITOFORTE.git
cd CITOFORTE
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
citoforte-monitor --auto
```

## Bootstrap automatico

Quando il bootstrap sara completo, il flusso potra diventare:

```bash
sudo bash scripts/bootstrap_orangepi.sh
```

## Avvio come servizio

L'obiettivo finale e installare un servizio systemd che:
- parte all'avvio
- si riavvia in caso di errore
- usa l'eseguibile installato nella virtualenv

La unit prevista si trova in `deploy/systemd/citoforte.service`.
