from __future__ import annotations

import os
from pathlib import Path


def atomic_write_text(target: Path, text: str) -> None:
    """Schreibt erst in eine temporäre Datei und ersetzt dann atomar; ein Abbruch lässt die alte Datei gültig."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, target)


def repair_partial_last_line(target: Path) -> None:
    """Schneidet eine abgebrochene letzte Zeile (ohne Zeilenende) ab, bevor angehängt wird."""
    if not target.exists():
        return
    data = target.read_bytes()
    if not data or data.endswith(b"\n"):
        return
    cut = data.rfind(b"\n") + 1
    with target.open("r+b") as handle:
        handle.truncate(cut)
