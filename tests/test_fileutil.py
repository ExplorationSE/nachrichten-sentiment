from pathlib import Path

from nachrichten_sentiment.fileutil import repair_partial_last_line


def _no_full_read(monkeypatch):
    def fail(self):
        raise AssertionError("ganze Datei gelesen")

    monkeypatch.setattr(Path, "read_bytes", fail)
    monkeypatch.setattr(Path, "read_text", fail)


def test_large_file_with_broken_last_line_is_cut_without_full_read(tmp_path: Path, monkeypatch):
    target = tmp_path / "big.jsonl"
    good = b"".join(b'{"n": %d, "pad": "%s"}\n' % (i, b"x" * 200) for i in range(20_000))  # ~4,3 MB
    broken = b'{"n": "abgebrochen", "pad": "' + b"y" * 300_000  # länger als mehrere Blöcke
    target.write_bytes(good + broken)
    _no_full_read(monkeypatch)
    repair_partial_last_line(target)
    monkeypatch.undo()
    assert target.stat().st_size == len(good)
    assert target.read_bytes().endswith(b"\n")


def test_intact_empty_and_newline_free_files(tmp_path: Path, monkeypatch):
    intact = tmp_path / "ok.jsonl"
    intact.write_bytes(b"a\nb\n")
    empty = tmp_path / "empty.jsonl"
    empty.write_bytes(b"")
    single = tmp_path / "single.jsonl"
    single.write_bytes(b'{"kaputt')
    _no_full_read(monkeypatch)
    for file in (intact, empty, single, tmp_path / "fehlt.jsonl"):
        repair_partial_last_line(file)
    monkeypatch.undo()
    assert intact.read_bytes() == b"a\nb\n"
    assert empty.read_bytes() == b""
    assert single.read_bytes() == b""
