from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    data_dir: Path
    auto_register_threshold: float = 0.85

    @classmethod
    def default(cls) -> "AppConfig":
        project_root = Path(__file__).resolve().parents[2]
        return cls(data_dir=project_root / "data")

