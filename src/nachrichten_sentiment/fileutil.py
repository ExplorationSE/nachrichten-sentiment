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


_BLOCK = 64 * 1024


def repair_partial_last_line(target: Path) -> None:
    """Schneidet eine abgebrochene letzte Zeile (ohne Zeilenende) ab, bevor angehängt wird.

    Liest nur das letzte Byte und bei Bedarf rückwärts blockweise bis zum letzten Zeilenende.
    """
    if not target.exists():
        return
    with target.open("r+b") as handle:
        size = handle.seek(0, os.SEEK_END)
        if size == 0:
            return
        handle.seek(-1, os.SEEK_END)
        if handle.read(1) == b"\n":
            return
        position = size
        cut = 0
        while position > 0:
            start = max(0, position - _BLOCK)
            handle.seek(start)
            block = handle.read(position - start)
            index = block.rfind(b"\n")
            if index != -1:
                cut = start + index + 1
                break
            position = start
        handle.truncate(cut)
