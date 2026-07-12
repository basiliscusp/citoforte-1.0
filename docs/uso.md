# Uso quotidiano

Questa pagina raccoglie i comandi base per usare CITOFORTE dopo l'installazione.

## Avvio manuale

```bash
cd CITOFORTE
source .venv/bin/activate
citoforte-monitor --auto
```

Apri poi la pagina di configurazione da browser:

- `http://<ip-device>:80`
- `https://<ip-device>:443`

Usa il bottone `Salva` per rendere permanenti le impostazioni e applicarle subito.

## Aggiornamento dopo un git clone

```bash
cd CITOFORTE
git pull origin main
```

Se hai modifiche locali e vuoi conservarle:

```bash
git stash
git pull origin main
git stash pop
```

## Diagnostica rapida

```bash
bash scripts/check_system.sh
```

## Cosa aspettarsi

Quando il controller viene rilevato, il monitor stampa a schermo le note premute e rilasciate.
