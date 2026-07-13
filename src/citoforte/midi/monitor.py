from __future__ import annotations

import time
from collections.abc import Callable

import rtmidi

from citoforte.config import MonitorConfig


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _note_label(note: int) -> str:
    octave = (note // 12) - 1
    name = NOTE_NAMES[note % 12]
    return f"{name}{octave}"


def _hex_bytes(values: list[int]) -> str:
    return " ".join(f"{value:02X}" for value in values)


def _clamp_midi_note(value: int) -> int:
    return max(0, min(127, value))


def _remap_note(note: int, config: MonitorConfig) -> int | None:
    if config.octave_mapping_mode == "controller_octave":
        source_octave_start = (config.controller_octave + 1) * 12
        source_offset = note - source_octave_start
        if source_offset < 0 or source_offset > 11:
            return None
    else:
        source_offset = note % 12

    target_octave_start = (config.instrument_octave + 1) * 12
    mapped = (
        target_octave_start
        + config.instrument_start_note
        + source_offset
        + config.note_offset_semitones
    )
    return _clamp_midi_note(mapped)


def _format_note_mapping(note: int, config: MonitorConfig) -> str:
    mapped = _remap_note(note, config)
    original_label = _note_label(note)
    if mapped is None:
        return f"{note} ({original_label}) -> ignorata"

    mapped_label = _note_label(mapped)
    return f"{note} ({original_label}) -> {mapped} ({mapped_label})"


def _format_midi_message(midi_bytes: list[int], config: MonitorConfig) -> str | None:
    if not midi_bytes:
        return None

    status = midi_bytes[0]
    data1 = midi_bytes[1] if len(midi_bytes) > 1 else None
    data2 = midi_bytes[2] if len(midi_bytes) > 2 else None

    if status < 0xF0:
        message_type = status & 0xF0
        channel = (status & 0x0F) + 1

        if message_type == 0x80 and data1 is not None and data2 is not None:
            mapped_label = _format_note_mapping(data1, config)
            return f"NOTE_OFF ch={channel} note={mapped_label} velocity={data2}"

        if message_type == 0x90 and data1 is not None and data2 is not None:
            mapped_label = _format_note_mapping(data1, config)
            if data2 == 0:
                return f"NOTE_OFF ch={channel} note={mapped_label} velocity=0"
            return f"NOTE_ON ch={channel} note={mapped_label} velocity={data2}"

        if message_type == 0xA0 and data1 is not None and data2 is not None:
            mapped_label = _format_note_mapping(data1, config)
            return f"POLY_AFTERTOUCH ch={channel} note={mapped_label} pressure={data2}"

        if message_type == 0xB0 and data1 is not None and data2 is not None:
            return f"CONTROL_CHANGE ch={channel} cc={data1} value={data2}"

        if message_type == 0xC0 and data1 is not None:
            return f"PROGRAM_CHANGE ch={channel} program={data1}"

        if message_type == 0xD0 and data1 is not None:
            return f"CHANNEL_AFTERTOUCH ch={channel} pressure={data1}"

        if message_type == 0xE0 and data1 is not None and data2 is not None:
            raw_value = (data2 << 7) | data1
            centered_value = raw_value - 8192
            return f"PITCH_BEND ch={channel} value={centered_value} raw={raw_value}"

        return f"CHANNEL_MSG status=0x{status:02X} data=[{_hex_bytes(midi_bytes[1:])}]"

    if status == 0xF0:
        return f"SYSEX bytes={len(midi_bytes)} data=[{_hex_bytes(midi_bytes)}]"

    if status == 0xF1 and data1 is not None:
        return f"MTC_QUARTER_FRAME value={data1}"

    if status == 0xF2 and data1 is not None and data2 is not None:
        song_position = (data2 << 7) | data1
        return f"SONG_POSITION_POINTER value={song_position}"

    if status == 0xF3 and data1 is not None:
        return f"SONG_SELECT value={data1}"

    if status == 0xF6:
        return "TUNE_REQUEST"

    if status == 0xF8:
        return "TIMING_CLOCK"

    if status == 0xFA:
        return "START"

    if status == 0xFB:
        return "CONTINUE"

    if status == 0xFC:
        return "STOP"

    if status == 0xFE:
        return "ACTIVE_SENSING"

    if status == 0xFF:
        return "SYSTEM_RESET"

    return f"SYSTEM_MSG status=0x{status:02X} data=[{_hex_bytes(midi_bytes[1:])}]"


def _pick_port_index(ports: list[str], config: MonitorConfig) -> int:
    if not ports:
        raise ValueError("Lista porte vuota")

    if config.selected_device_name:
        selected_lower = config.selected_device_name.lower()
        for idx, name in enumerate(ports):
            if name.lower() == selected_lower:
                return idx

        for idx, name in enumerate(ports):
            if selected_lower in name.lower():
                return idx

        if not config.auto_discover:
            raise ValueError(f"Dispositivo selezionato non trovato: {config.selected_device_name}")

    if config.device_name_hint:
        hint = config.device_name_hint.lower()
        for idx, name in enumerate(ports):
            lowered = name.lower()
            if hint in lowered and "midi through" not in lowered:
                return idx

        for idx, name in enumerate(ports):
            if hint in name.lower():
                return idx

    candidate_indexes = [idx for idx, name in enumerate(ports) if "midi through" not in name.lower()]
    if candidate_indexes:
        return candidate_indexes[0]

    return 0


def _wait_for_first_alsa_port(config: MonitorConfig) -> tuple[rtmidi.MidiIn, int, str]:
    print("In attesa di controller MIDI USB (ALSA)...")

    while True:
        midi_in = rtmidi.MidiIn(rtmidi.API_LINUX_ALSA)
        ports = midi_in.get_ports()

        if ports:
            try:
                selected_index = _pick_port_index(ports, config)
            except ValueError as exc:
                print(f"{exc}. Riprovo...")
                time.sleep(config.poll_interval_seconds)
                continue

            selected_name = ports[selected_index]
            print(f"Controller MIDI trovati: {ports}")
            print(f"Uso la porta selezionata: {selected_name}")
            return midi_in, selected_index, selected_name

        time.sleep(config.poll_interval_seconds)


def run_monitor(
    config: MonitorConfig,
    config_provider: Callable[[], MonitorConfig] | None = None,
) -> None:
    print("CITOFORTE monitor ALSA avviato")
    active_config = config

    while True:
        if config_provider is not None:
            active_config = config_provider()

        midi_in, port_index, port_name = _wait_for_first_alsa_port(active_config)

        try:
            midi_in.open_port(port_index)
            print(f"Ascolto su ALSA port: {port_name}")
            print("Premi Ctrl+C per uscire")

            while True:
                if config_provider is not None:
                    latest = config_provider()
                    if latest != active_config:
                        active_config = latest
                        print("Configurazione aggiornata: riapro la porta con i nuovi parametri")
                        break

                message = midi_in.get_message()
                if message is None:
                    time.sleep(0.01)
                    continue

                midi_bytes, delta_time = message
                formatted = _format_midi_message(midi_bytes, active_config)
                if formatted is None:
                    continue

                print(f"{formatted} dt={delta_time:.6f}s")

        except (OSError, RuntimeError, rtmidi.SystemError) as exc:
            print(f"Connessione MIDI persa o non disponibile ({exc}). Riprovo...")
            time.sleep(active_config.poll_interval_seconds)
        finally:
            try:
                if midi_in.is_port_open():
                    midi_in.close_port()
            except Exception:
                pass
