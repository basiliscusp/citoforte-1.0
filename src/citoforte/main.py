from __future__ import annotations

import argparse

from citoforte.config import MonitorConfig
from citoforte.midi.monitor import run_monitor


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
        action="store_true",
        help="Abilita auto discovery (default true)",
    )
    parser.add_argument(
        "--poll-interval",
        dest="poll_interval_seconds",
        type=float,
        default=2.0,
        help="Intervallo polling secondi",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = MonitorConfig(
        device_name_hint=args.device_name_hint,
        auto_discover=True if args.auto else True,
        poll_interval_seconds=args.poll_interval_seconds,
    )
    run_monitor(config)


if __name__ == "__main__":
    main()
