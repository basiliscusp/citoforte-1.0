from __future__ import annotations

import json
import threading
from dataclasses import asdict
from pathlib import Path

from citoforte.config import MonitorConfig


class RuntimeSettingsStore:
    def __init__(self, settings_path: Path, initial: MonitorConfig) -> None:
        self._settings_path = settings_path
        self._lock = threading.Lock()
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._config = initial
        self._mtime_ns = 0

    @property
    def settings_path(self) -> Path:
        return self._settings_path

    def load_or_create(self) -> MonitorConfig:
        with self._lock:
            if not self._settings_path.exists():
                self._write_unlocked(self._config)
                return self._config

            loaded = self._read_from_disk_unlocked()
            if loaded is None:
                self._write_unlocked(self._config)
                return self._config

            self._config = loaded
            return self._config

    def get(self) -> MonitorConfig:
        with self._lock:
            return MonitorConfig(**asdict(self._config))

    def save(self, config: MonitorConfig) -> MonitorConfig:
        with self._lock:
            self._config = config
            self._write_unlocked(config)
            return self._config

    def refresh_if_changed(self) -> MonitorConfig:
        with self._lock:
            if not self._settings_path.exists():
                return MonitorConfig(**asdict(self._config))

            stat = self._settings_path.stat()
            if stat.st_mtime_ns == self._mtime_ns:
                return MonitorConfig(**asdict(self._config))

            loaded = self._read_from_disk_unlocked()
            if loaded is not None:
                self._config = loaded
            return MonitorConfig(**asdict(self._config))

    def _read_from_disk_unlocked(self) -> MonitorConfig | None:
        try:
            payload = json.loads(self._settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        def _to_int(value: object, fallback: int, min_value: int, max_value: int) -> int:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                return fallback
            return max(min_value, min(max_value, parsed))

        normalized_poll = float(payload.get("poll_interval_seconds", self._config.poll_interval_seconds))
        if normalized_poll <= 0:
            normalized_poll = self._config.poll_interval_seconds

        raw_selected = payload.get("selected_device_name")
        selected_device_name: str | None
        if isinstance(raw_selected, str):
            selected_device_name = raw_selected.strip() or None
        else:
            selected_device_name = None

        raw_mode = payload.get("octave_mapping_mode", self._config.octave_mapping_mode)
        if raw_mode not in {"controller_octave", "fold_all_octaves"}:
            raw_mode = self._config.octave_mapping_mode

        stat = self._settings_path.stat()
        self._mtime_ns = stat.st_mtime_ns

        return MonitorConfig(
            device_name_hint=payload.get("device_name_hint") or None,
            selected_device_name=selected_device_name,
            auto_discover=bool(payload.get("auto_discover", self._config.auto_discover)),
            poll_interval_seconds=normalized_poll,
            octave_mapping_mode=raw_mode,
            controller_octave=_to_int(
                payload.get("controller_octave"),
                self._config.controller_octave,
                -1,
                9,
            ),
            instrument_octave=_to_int(
                payload.get("instrument_octave"),
                self._config.instrument_octave,
                -1,
                9,
            ),
            instrument_start_note=_to_int(
                payload.get("instrument_start_note"),
                self._config.instrument_start_note,
                0,
                11,
            ),
            note_offset_semitones=_to_int(
                payload.get("note_offset_semitones"),
                self._config.note_offset_semitones,
                -24,
                24,
            ),
        )

    def _write_unlocked(self, config: MonitorConfig) -> None:
        temp_path = self._settings_path.with_suffix(self._settings_path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(asdict(config), indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self._settings_path)
        self._mtime_ns = self._settings_path.stat().st_mtime_ns