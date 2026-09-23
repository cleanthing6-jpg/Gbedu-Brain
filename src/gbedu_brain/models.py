from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class VocalAnalysis:
    bpm: float
    key: str
    scale: str
    key_strength: float
    duration: float
    energy: float
    pitch_contour: List[float] = field(default_factory=list)


@dataclass
class SongSpec:
    genre: str = "afrobeats"
    bpm: float = 105.0
    key: str = "C"
    scale: str = "minor"
    mood: str = "energetic"
    duration: float = 180.0
    instruments: List[str] = field(default_factory=lambda: [
        "log_drum", "shaker", "conga", "rimshot", "guitar_skank"
    ])
    arrangement: List[str] = field(default_factory=lambda: [
        "intro", "verse", "hook", "verse", "hook", "bridge", "hook", "outro"
    ])
    energy_curve: List[float] = field(default_factory=lambda: [
        0.3, 0.5, 0.9, 0.5, 0.9, 0.6, 1.0, 0.4
    ])
    swing: float = 0.15


def analysis_to_dict(a: VocalAnalysis) -> dict:
    return asdict(a)


def spec_to_dict(s: SongSpec) -> dict:
    return asdict(s)
