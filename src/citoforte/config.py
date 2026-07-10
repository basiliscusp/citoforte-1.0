from dataclasses import dataclass


@dataclass(slots=True)
class MonitorConfig:
    device_name_hint: str | None = None
    auto_discover: bool = True
    poll_interval_seconds: float = 2.0
