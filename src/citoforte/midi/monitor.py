from __future__ import annotations

import time
import rtmidi

from citoforte.config import MonitorConfig


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _note_label(note: int) -> str:
    octave = (note // 12) - 1
    name = NOTE_NAMES[note % 12]
    return f"{name}{octave}"


def _decode_note_event(status: int, data1: int, data2: int) -> tuple[str, int, int] | None:
    message_type = status & 0xF0
    channel = status & 0x0F

    if message_type == 0x90 and data2 > 0:
        return ("NOTE_ON", channel, data2)

    if message_type == 0x80 or (message_type == 0x90 and data2 == 0):
        return ("NOTE_OFF", channel, data2)

    return None


def _wait_for_first_alsa_port(poll_interval_seconds: float) -> tuple[rtmidi.MidiIn, int, str]:
    print("In attesa di controller MIDI USB (ALSA)...")

    while True:
        midi_in = rtmidi.MidiIn(rtmidi.API_LINUX_ALSA)
        ports = midi_in.get_ports()

        if ports:
            candidate_indexes = [
                idx for idx, name in enumerate(ports) if "midi through" not in name.lower()
            ]

            if not candidate_indexes:
                candidate_indexes = [0]

            selected_index = candidate_indexes[0]
            selected_name = ports[selected_index]
            print(f"Controller MIDI trovati: {ports}")
            print(f"Uso il primo della lista: {selected_name}")
            return midi_in, selected_index, selected_name

        time.sleep(poll_interval_seconds)


def run_monitor(config: MonitorConfig) -> None:
    print("CITOFORTE monitor ALSA avviato")

    while True:
        midi_in, port_index, port_name = _wait_for_first_alsa_port(config.poll_interval_seconds)

        try:
            midi_in.open_port(port_index)
            print(f"Ascolto su ALSA port: {port_name}")
            print("Premi Ctrl+C per uscire")

            while True:
                message = midi_in.get_message()
                if message is None:
                    time.sleep(0.01)
                    continue

                midi_bytes, _delta_time = message
                if len(midi_bytes) < 3:
                    continue

                status, data1, data2 = midi_bytes[0], midi_bytes[1], midi_bytes[2]
                decoded = _decode_note_event(status, data1, data2)
                if decoded is None:
                    continue

                event_name, channel, velocity = decoded
                note = data1
                note_name = _note_label(note)

                if event_name == "NOTE_ON":
                    print(f"{event_name} note={note} ({note_name}) velocity={velocity} channel={channel}")
                else:
                    print(f"{event_name} note={note} ({note_name}) channel={channel}")

        except (OSError, RuntimeError, rtmidi.SystemError) as exc:
            print(f"Connessione MIDI persa o non disponibile ({exc}). Riprovo...")
            time.sleep(config.poll_interval_seconds)
        finally:
            try:
                if midi_in.is_port_open():
                    midi_in.close_port()
            except Exception:
                pass
