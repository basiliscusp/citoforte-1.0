# Setup software

Questa pagina descrive come installare e avviare CITOFORTE sulla Orange Pi.

## Manual installation

Questa e la procedura da fare a mano via SSH, passo dopo passo.

### 1. Aggiornare il sistema

```bash
sudo apt update
```

### 2. Installare i pacchetti necessari

```bash
sudo apt install -y git python3 python3-venv python3-pip alsa-utils usbutils
```

### 3. Clonare il repository

```bash
git clone https://github.com/<user>/CITOFORTE.git
cd CITOFORTE
```

### 4. Creare il virtual environment

```bash
python3 -m venv .venv
```

Se hai installato una versione specifica come `python3.11`, puoi usare anche quella.

### 5. Attivare il virtual environment

```bash
source .venv/bin/activate
```

### 6. Installare il progetto

```bash
pip install -e .
```

### 7. Avviare il monitor MIDI

```bash
citoforte-monitor --auto
```

### 8. Verificare il funzionamento

Quando colleghi il controller MIDI e premi un tasto, lo script deve stampare a schermo la nota premuta o rilasciata.

## Auto installation

Questa e la futura installazione automatica da eseguire quando il bootstrap sara completo.

L'obiettivo e avere un solo comando che faccia tutto:
- installa i pacchetti di sistema
- clona o aggiorna il repository
- crea l'ambiente Python
- installa le dipendenze
- configura il servizio systemd
- avvia il monitor in automatico

Esempio di esecuzione finale:

```bash
sudo bash scripts/bootstrap_orangepi.sh
```

## Avvio come servizio

L'obiettivo finale e installare un servizio systemd che:
- parte all'avvio
- si riavvia in caso di errore
- usa l'eseguibile installato nella virtualenv

La unit prevista si trova in `deploy/systemd/citoforte.service`.
