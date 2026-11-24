import json
import pickle
import threading
import time
from pathlib import Path

import pytest

from nachrichten_sentiment.cli import build_parser
from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.download import MissingGkgError
from nachrichten_sentiment.paths import ProjectPaths
from nachrichten_sentiment.pipeline import prefetch_batch, run_batches, use_process_pool
from nachrichten_sentiment.progress import load_progress, processed_batch_ids
from nachrichten_sentiment.timeutil import iter_batch_ids
from nachrichten_sentiment.titles import http_title_opener
from tests.fixtures.build_week import gkg_zip_bytes, nvidia_line

IDS = list(iter_batch_ids("20190930000000", "20190930043000"))  # 19 Sätze
MISSING = IDS[3]
BROKEN = IDS[7]


class _Model:
    def predict_proba(self, title: str) -> tuple[float, float, float]:
        return (0.5, 0.3, 0.2)


class _Abort(BaseException):
    """Simuliert einen harten Abbruch (wie KeyboardInterrupt) mitten im Lauf."""


def _body(batch_id: str) -> str:
    n = int(batch_id[8:12])
    lines = [nvidia_line(batch_id, f"r{batch_id}", f"NVIDIA headline number {n}")]
    if n % 2 == 0:
        lines.append(nvidia_line(batch_id, f"s{batch_id}", "NVIDIA raises full-year revenue forecast"))
    return "".join(lines)


def _make_fetcher(abort_at: str | None = None, seen: list | None = None, jitter: bool = False):
    lock = threading.Lock()

    def fetcher(url: str) -> bytes:
        batch_id = url.rsplit("/", 1)[-1].split(".")[0]
        if jitter:
            # Spätere Sätze werden zuerst fertig: die Reihenfolge der Ergebnisse muss trotzdem stabil sein.
            time.sleep(0.002 * (len(IDS) - IDS.index(batch_id)))
        with lock:
            if seen is not None:
                seen.append(batch_id)
        if batch_id == MISSING:
            raise MissingGkgError(batch_id)
        if batch_id == BROKEN:
            raise RuntimeError("Verbindung abgebrochen")
        if batch_id == abort_at:
            raise _Abort()
        return gkg_zip_bytes(batch_id, _body(batch_id))

    return fetcher


def _kwargs(paths: ProjectPaths, fetcher, workers: int) -> dict:
    return dict(
        company=load_company("NVDA"),
        paths=paths,
        model=_Model(),
        title_opener=lambda u, t: "",
        fetcher=fetcher,
        workers=workers,
    )


def _snapshot(root: Path) -> dict[str, str]:
    files = {}
    for sub in ("site/data", "data/articles"):
        for file in sorted((root / sub).rglob("*")):
            if file.is_file():
                files[str(file.relative_to(root))] = file.read_text(encoding="utf-8")
    return files


def _gap_ids(paths: ProjectPaths) -> list[str]:
    return [line.split()[1] for line in paths.gaps_log_path.read_text(encoding="utf-8").splitlines()]


def test_parallel_run_equals_sequential_run(tmp_path: Path):
    seq = ProjectPaths(tmp_path / "seq")
    run_batches(IDS, **_kwargs(seq, _make_fetcher(), workers=1))
    par = ProjectPaths(tmp_path / "par")
    run_batches(IDS, **_kwargs(par, _make_fetcher(jitter=True), workers=6))
    assert _snapshot(par.root) == _snapshot(seq.root)
    for paths in (seq, par):
        progress = load_progress(paths.progress_path)
        assert progress.cursor_batch_id == IDS[-1]
        assert MISSING in progress.missing_at_source  # 404 bleibt "Quelle fehlt"
        assert BROKEN in progress.open_gaps
    # gaps.log in Satzreihenfolge, 404 weiter protokolliert
    assert _gap_ids(par) == _gap_ids(seq) == [MISSING, BROKEN]
    assert "Quelle fehlt (404)" in par.gaps_log_path.read_text(encoding="utf-8")
    lines = (par.articles_dir("NVDA") / "2019-09.jsonl").read_text(encoding="utf-8").splitlines()
    batches = [json.loads(line)["batch_id"] for line in lines]
    assert batches == sorted(batches)  # stabile Reihenfolge


def test_abort_leaves_cursor_at_last_contiguous_batch_and_resume_completes(tmp_path: Path):
    abort_at = IDS[12]
    paths = ProjectPaths(tmp_path / "abort")
    seen: list[str] = []
    with pytest.raises(_Abort):
        run_batches(IDS, **_kwargs(paths, _make_fetcher(abort_at=abort_at, seen=seen, jitter=True), workers=6))
    progress = load_progress(paths.progress_path)
    # Kein Fortschritt über den abgebrochenen Satz hinaus, auch wenn spätere schon geladen waren.
    assert progress.cursor_batch_id == IDS[11]
    done = processed_batch_ids(progress) | set(progress.open_gaps) | set(progress.missing_at_source)
    assert done == set(IDS[:12])
    assert any(batch_id > abort_at for batch_id in seen)  # es wurde tatsächlich vorausgeladen
    assert not list(paths.tmp_dir.glob("*.zip"))  # keine ZIP-Reste
    stored = [json.loads(line)["batch_id"] for line in
              (paths.articles_dir("NVDA") / "2019-09.jsonl").read_text(encoding="utf-8").splitlines()]
    assert max(stored) < abort_at

    # Wiederaufnahme vom gespeicherten Stand ergibt dasselbe wie ein ununterbrochener Lauf.
    remaining = [b for b in IDS if b > progress.cursor_batch_id]
    run_batches(remaining, **_kwargs(paths, _make_fetcher(), workers=6))
    reference = ProjectPaths(tmp_path / "ref")
    run_batches(IDS, **_kwargs(reference, _make_fetcher(), workers=1))
    assert _snapshot(paths.root) == _snapshot(reference.root)
    assert load_progress(paths.progress_path).cursor_batch_id == IDS[-1]


def test_leftover_zip_files_from_an_aborted_run_are_removed(tmp_path: Path):
    paths = ProjectPaths(tmp_path)
    paths.tmp_dir.mkdir(parents=True)
    (paths.tmp_dir / "20190101000000.gkg.csv.zip").write_bytes(b"rest")
    run_batches(IDS[:2], **_kwargs(paths, _make_fetcher(), workers=2))
    assert not list(paths.tmp_dir.glob("*.zip"))


def test_process_pool_only_for_real_downloads_and_worker_is_picklable():
    assert use_process_pool(workers=8, fetcher=None, extract_zip=None, title_opener=http_title_opener)
    assert not use_process_pool(workers=1, fetcher=None, extract_zip=None, title_opener=http_title_opener)
    assert not use_process_pool(workers=8, fetcher=lambda u: b"", extract_zip=None, title_opener=http_title_opener)
    assert not use_process_pool(workers=8, fetcher=None, extract_zip=None, title_opener=lambda u, t: "")
    pickle.dumps(prefetch_batch)
    pickle.dumps(load_company("NVDA"))


def test_cli_parallel_option_defaults_to_eight():
    parser = build_parser()
    assert parser.parse_args(["erstlauf"]).parallel == 8
    assert parser.parse_args(["erstlauf", "--parallel", "3"]).parallel == 3
    assert parser.parse_args(["tageslauf"]).parallel == 8
