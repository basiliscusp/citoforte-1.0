from dataclasses import dataclass
from typing import Literal


OctaveMappingMode = Literal["controller_octave", "fold_all_octaves"]


@dataclass(slots=True)
class MonitorConfig:
    device_name_hint: str | None = None
    selected_device_name: str | None = None
    auto_discover: bool = True
    poll_interval_seconds: float = 2.0
    octave_mapping_mode: OctaveMappingMode = "controller_octave"
    controller_octave: int = 4
    instrument_octave: int = 4
    instrument_start_note: int = 0
    note_offset_semitones: int = 0
