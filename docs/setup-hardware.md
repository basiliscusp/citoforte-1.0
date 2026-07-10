# Setup hardware

Questa pagina raccoglie i controlli e le verifiche lato Orange Pi / Armbian prima di avviare il software.

## Obiettivo

Verificare che:
- la porta USB funzioni correttamente
- il controller MIDI venga visto dal sistema
- ALSA esponga una porta MIDI utilizzabile

## Verifiche utili da SSH

- `lsusb`
- `lsusb -t`
- `dmesg | tail -n 100`
- `cat /proc/asound/cards`
- `ls /dev/snd`
- `amidi -l`
- `aseqdump -l`

## Caso tipico

Se `lsusb` vede il controller ma `amidi -l` non mostra nulla, di solito il problema e nel riconoscimento ALSA o nel driver del device.

## Nota pratica

Prima di aggiungere logica applicativa conviene sempre validare che il controller compaia come porta MIDI reale e non solo come periferica USB generica.
