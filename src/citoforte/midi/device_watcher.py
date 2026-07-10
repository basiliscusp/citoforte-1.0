from __future__ import annotations

import time
from collections.abc import Iterator

import mido


def list_input_ports() -> list[str]:
    return list(mido.get_input_names())


def pick_port(device_name_hint: str | None) -> str | None:
    ports = list_input_ports()
    if not ports:
        return None

    if device_name_hint:
        hint = device_name_hint.lower()
        for name in ports:
            if hint in name.lower():
                return name

    return ports[0]


def wait_for_port(device_name_hint: str | None, poll_interval_seconds: float) -> Iterator[str]:
    """Yield the selected port whenever a compatible MIDI input is available."""
    last_name: str | None = None

    while True:
        selected = pick_port(device_name_hint)
        if selected is not None and selected != last_name:
            last_name = selected
            yield selected

        if selected is None:
            last_name = None

        time.sleep(poll_interval_seconds)
