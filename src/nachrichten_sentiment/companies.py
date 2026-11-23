from __future__ import annotations

import json
from pathlib import Path

from nachrichten_sentiment.models import CompanyConfig
from nachrichten_sentiment.paths import default_root


def load_company(ticker: str, path: Path | None = None) -> CompanyConfig:
    config_path = path or (default_root() / "config" / "companies.json")
    data = json.loads(config_path.read_text(encoding="utf-8"))
    key = ticker.upper()
    if key not in data:
        raise KeyError(ticker)
    raw = data[key]
    return CompanyConfig(
        ticker=raw["ticker"],
        display_name=raw["display_name"],
        name_substrings=tuple(s.lower() for s in raw["name_substrings"]),
        ticker_word=str(raw["ticker_word"]).lower(),
    )
