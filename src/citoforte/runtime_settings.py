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

        normalized_poll = float(payload.get("poll_interval_seconds", self._config.poll_interval_seconds))
        if normalized_poll <= 0:
            normalized_poll = self._config.poll_interval_seconds

        stat = self._settings_path.stat()
        self._mtime_ns = stat.st_mtime_ns

        return MonitorConfig(
            device_name_hint=payload.get("device_name_hint") or None,
            auto_discover=bool(payload.get("auto_discover", self._config.auto_discover)),
            poll_interval_seconds=normalized_poll,
        )

    def _write_unlocked(self, config: MonitorConfig) -> None:
        temp_path = self._settings_path.with_suffix(self._settings_path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(asdict(config), indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self._settings_path)
        self._mtime_ns = self._settings_path.stat().st_mtime_ns