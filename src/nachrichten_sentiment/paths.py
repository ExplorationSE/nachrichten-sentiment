from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def default_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def company_config_path(self) -> Path:
        return self.root / "config" / "companies.json"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def state_dir(self) -> Path:
        return self.data_dir / "state"

    @property
    def progress_path(self) -> Path:
        return self.state_dir / "progress.json"

    @property
    def gaps_log_path(self) -> Path:
        return self.state_dir / "gaps.log"

    def articles_dir(self, ticker: str) -> Path:
        return self.data_dir / "articles" / ticker.lower()

    @property
    def site_dir(self) -> Path:
        return self.root / "site"

    @property
    def site_data_dir(self) -> Path:
        return self.site_dir / "data"

    @property
    def tmp_dir(self) -> Path:
        return self.data_dir / "tmp"
