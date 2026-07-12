from __future__ import annotations

import argparse
from pathlib import Path

from citoforte.config import MonitorConfig
from citoforte.midi.monitor import run_monitor
from citoforte.runtime_settings import RuntimeSettingsStore
from citoforte.web.server import start_config_servers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CITOFORTE MIDI monitor")
    parser.add_argument(
        "--device",
        dest="device_name_hint",
        default=None,
        help="Filtro nome dispositivo (substring, case-insensitive)",
    )
    parser.add_argument(
        "--auto",
        dest="auto_discover",
        action="store_true",
        default=None,
        help="Abilita auto discovery (default true)",
    )
    parser.add_argument(
        "--poll-interval",
        dest="poll_interval_seconds",
        type=float,
        default=None,
        help="Intervallo polling secondi",
    )
    parser.add_argument(
        "--settings-file",
        default="config/runtime_settings.json",
        help="Percorso file impostazioni persistenti",
    )
    parser.add_argument(
        "--http-port",
        type=int,
        default=80,
        help="Porta server HTTP configurazione",
    )
    parser.add_argument(
        "--https-port",
        type=int,
        default=443,
        help="Porta server HTTPS configurazione",
    )
    parser.add_argument(
        "--bind-host",
        default="0.0.0.0",
        help="Host di bind per server configurazione",
    )
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Disabilita il server web di configurazione",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    defaults = MonitorConfig()
    store = RuntimeSettingsStore(Path(args.settings_file), defaults)
    persisted = store.load_or_create()

    config = MonitorConfig(
        device_name_hint=(
            args.device_name_hint
            if args.device_name_hint is not None
            else persisted.device_name_hint
        ),
        auto_discover=(args.auto_discover if args.auto_discover is not None else persisted.auto_discover),
        poll_interval_seconds=(
            args.poll_interval_seconds
            if args.poll_interval_seconds is not None
            else persisted.poll_interval_seconds
        ),
    )

    store.save(config)

    if not args.no_web:
        start_config_servers(
            store,
            host=args.bind_host,
            http_port=args.http_port,
            https_port=args.https_port,
        )

    run_monitor(config, config_provider=store.refresh_if_changed)


if __name__ == "__main__":
    main()
