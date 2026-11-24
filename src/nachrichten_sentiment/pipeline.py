from __future__ import annotations

import multiprocessing
import time
import zipfile
from collections import deque
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from nachrichten_sentiment.daily import aggregate_daily
from nachrichten_sentiment.dedup import UrlIndex, group_by_day, mark_near_duplicates
from nachrichten_sentiment.download import DownloadError, MissingGkgError, download_gkg_zip
from nachrichten_sentiment.filter_company import matches_company
from nachrichten_sentiment.gkg import parse_gkg_line
from nachrichten_sentiment.models import Article, CompanyConfig, DailyRow, ProgressState
from nachrichten_sentiment.paths import ProjectPaths
from nachrichten_sentiment.progress import (
    append_gap_log,
    batches_to_process,
    load_progress,
    mark_gap,
    mark_missing_at_source,
    mark_pending_rebuild,
    mark_success,
    processed_batch_ids,
    save_progress,
)
from nachrichten_sentiment.sentiment import SentimentModel, score_title
from nachrichten_sentiment.store import (
    append_articles,
    load_articles,
    rewrite_month_articles,
    write_daily,
    write_headlines,
)
from nachrichten_sentiment.timeutil import (
    FIRST_BERLIN_DAY,
    batch_id_from_datetime,
    berlin_day_from_batch_id,
    datetime_from_batch_id,
    expected_batch_ids_for_berlin_day,
    previous_berlin_day,
)
from nachrichten_sentiment.titles import fetch_title, http_title_opener
from nachrichten_sentiment.urls import normalize_url


DEFAULT_WORKERS = 8
PREFETCH_FACTOR = 2  # vorausgeladene Sätze je Worker (begrenzt Speicher und Plattenbedarf)
PROGRESS_EVERY = 96  # Fortschrittszeile etwa einmal je Tag an Sätzen


class EmptyGkgZipError(Exception):
    """Die ZIP-Datei ist lesbar, enthält aber keine Datei."""


def _extract_zip(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        if not names:
            raise EmptyGkgZipError(zip_path.name)
        return archive.read(names[0]).decode("utf-8", errors="replace")


def _record_gap(
    batch_id: str,
    message: str,
    *,
    paths: ProjectPaths,
    progress: ProgressState,
    missing_at_source: bool = False,
) -> list[Article]:
    if missing_at_source:
        mark_missing_at_source(progress, batch_id)
    else:
        mark_gap(progress, batch_id)
    mark_pending_rebuild(progress, batch_id)
    append_gap_log(paths.gaps_log_path, f"{batch_id} {message}")
    save_progress(paths.progress_path, progress)
    return []


@dataclass
class PrefetchedBatch:
    """Ergebnis von Download, Entpacken, Filtern und Titelabruf eines Satzes (ohne Zustandsänderung)."""

    batch_id: str
    status: str  # "ok" | "missing" | "error"
    message: str = ""
    records: list = field(default_factory=list)  # (GkgRecord, Titel, Titelquelle)
    failed_titles: dict = field(default_factory=dict)


def prefetch_batch(
    batch_id: str,
    tmp_dir: Path,
    company: CompanyConfig,
    title_opener,
    fetcher=None,
    extract_zip=None,
    failed_cache: dict[str, str] | None = None,
) -> PrefetchedBatch:
    """Lädt und filtert einen Satz. Ändert keinen gespeicherten Zustand und darf parallel laufen."""
    try:
        zip_path = download_gkg_zip(
            batch_id,
            tmp_dir,
            fetcher=fetcher,
            backoff_seconds=0.0 if fetcher else 2.0,
        )
        text = (extract_zip or _extract_zip)(zip_path)
    except MissingGkgError as exc:
        return PrefetchedBatch(batch_id, "missing", f"Quelle fehlt (404): {exc}")
    except DownloadError as exc:
        return PrefetchedBatch(batch_id, "error", str(exc))
    except zipfile.BadZipFile as exc:
        return PrefetchedBatch(batch_id, "error", f"defekte ZIP-Datei: {exc}")
    except EmptyGkgZipError:
        return PrefetchedBatch(batch_id, "error", "leere ZIP-Datei ohne Inhalt")
    finally:
        leftover = tmp_dir / f"{batch_id}.gkg.csv.zip"
        if leftover.exists():
            leftover.unlink()

    cache = {} if failed_cache is None else failed_cache
    before = set(cache)
    records = []
    fetched: dict[str, tuple[str, str]] = {}
    # splitlines() behandelt auch CRLF-Zeilenenden.
    for line in text.splitlines():
        record = parse_gkg_line(line, batch_id)
        if record is None:
            continue
        if not matches_company(
            company,
            record.organizations,
            record.enhanced_organizations,
            record.url,
            record.page_title,
        ):
            continue
        if record.page_title:
            title, title_source = record.page_title, "gkg"
        else:
            key = normalize_url(record.url)
            if key not in fetched:
                result = fetch_title(record.url, title_opener, cache)
                fetched[key] = ((result.title or ""), result.source)
            title, title_source = fetched[key]
        records.append((record, title, title_source))
    failed = {key: cache[key] for key in cache if key not in before}
    return PrefetchedBatch(batch_id, "ok", records=records, failed_titles=failed)


def apply_prefetched(
    prefetched: PrefetchedBatch,
    *,
    company: CompanyConfig,
    paths: ProjectPaths,
    url_index: UrlIndex,
    model: SentimentModel | None,
    progress: ProgressState,
) -> list[Article]:
    """Übernimmt einen vorab geladenen Satz in strikter Satzreihenfolge in Artikel und Fortschritt."""
    batch_id = prefetched.batch_id
    if prefetched.status != "ok":
        return _record_gap(
            batch_id,
            prefetched.message,
            paths=paths,
            progress=progress,
            missing_at_source=prefetched.status == "missing",
        )
    for key, error in prefetched.failed_titles.items():
        progress.failed_title_fetches.setdefault(key, error)
    articles: list[Article] = []
    batch_utc = datetime_from_batch_id(batch_id).strftime("%Y-%m-%dT%H:%M:%SZ")
    day = berlin_day_from_batch_id(batch_id).isoformat()
    for record, title, title_source in prefetched.records:
        if not url_index.keep(record.url, record.gkg_record_id):
            continue
        sentiment = label = p_pos = p_neu = p_neg = None
        if title and model is not None and title_source != "missing":
            scored = score_title(title, model)
            sentiment, label = scored.sentiment, scored.label
            p_pos, p_neu, p_neg = scored.p_positive, scored.p_neutral, scored.p_negative
        articles.append(
            Article(
                gkg_record_id=record.gkg_record_id,
                url=record.url,
                url_normalized=normalize_url(record.url),
                source_domain=record.source_domain,
                title=title,
                title_source=title_source,
                batch_id=batch_id,
                batch_utc=batch_utc,
                day_berlin=day,
                sentiment=sentiment,
                sentiment_label=label,
                p_positive=p_pos,
                p_neutral=p_neu,
                p_negative=p_neg,
                is_near_duplicate=False,
                near_duplicate_of=None,
            )
        )
    if articles:
        append_articles(paths, company.ticker, articles)
    mark_success(progress, batch_id)
    mark_pending_rebuild(progress, batch_id)
    save_progress(paths.progress_path, progress)
    return articles


def process_batch(
    batch_id: str,
    *,
    company: CompanyConfig,
    paths: ProjectPaths,
    url_index: UrlIndex,
    model: SentimentModel | None,
    title_opener,
    progress: ProgressState,
    fetcher=None,
    extract_zip=None,
) -> list[Article]:
    prefetched = prefetch_batch(
        batch_id,
        paths.tmp_dir,
        company,
        title_opener,
        fetcher=fetcher,
        extract_zip=extract_zip,
        failed_cache=progress.failed_title_fetches,
    )
    return apply_prefetched(
        prefetched, company=company, paths=paths, url_index=url_index, model=model, progress=progress
    )


def use_process_pool(*, workers: int, fetcher, extract_zip, title_opener) -> bool:
    """Prozesse nur für echte Downloads (picklebare Standardfunktionen); sonst Threads."""
    return workers > 1 and fetcher is None and extract_zip is None and title_opener is http_title_opener


def _remove_leftover_zips(tmp_dir: Path) -> None:
    if tmp_dir.exists():
        for leftover in tmp_dir.glob("*.gkg.csv.zip"):
            leftover.unlink()


def rebuild_outputs(
    paths: ProjectPaths,
    company: CompanyConfig,
    progress: ProgressState,
    affected_days: set[str] | None = None,
) -> list[DailyRow]:
    """Baut Tageswerte neu auf; Nahduplikate, Monats-JSONL und Schlagzeilen nur für betroffene Tage/Monate.

    ``affected_days=None`` bedeutet vollständiger Neuaufbau aller Tage.
    """
    articles = load_articles(paths, company.ticker)
    by_day = group_by_day(articles)
    if affected_days is None:
        days_to_mark: set[str] = set(by_day)
    else:
        days_to_mark = set(affected_days)
    mark_near_duplicates(articles, days=days_to_mark)
    months = {day[:7] for day in days_to_mark}
    by_month: dict[str, list[Article]] = {}
    for article in articles:
        month = article.day_berlin[:7]
        if month in months:
            by_month.setdefault(month, []).append(article)
    for month, month_articles in by_month.items():
        rewrite_month_articles(paths, company.ticker, month, month_articles)

    processed = processed_batch_ids(progress)
    missing = set(progress.missing_at_source)
    end_day = berlin_day_from_batch_id(progress.cursor_batch_id) if progress.cursor_batch_id else FIRST_BERLIN_DAY
    rows: list[DailyRow] = []
    day = FIRST_BERLIN_DAY
    while day <= end_day:
        rows.append(aggregate_daily(by_day.get(day.isoformat(), []), day, processed, missing))
        day += timedelta(days=1)
    write_daily(paths, company.ticker, rows, company.display_name)
    write_headlines(paths, company.ticker, [a for items in by_month.values() for a in items], months=by_month.keys())
    return rows


def run_batches(
    batch_ids: list[str],
    *,
    company: CompanyConfig,
    paths: ProjectPaths,
    model: SentimentModel | None,
    title_opener,
    fetcher=None,
    extract_zip=None,
    full_rebuild: bool = False,
    workers: int = 1,
) -> None:
    progress = load_progress(paths.progress_path)
    url_index = UrlIndex()
    url_index.load_from_articles(load_articles(paths, company.ticker))
    already = processed_batch_ids(progress)
    todo = [batch_id for batch_id in batch_ids if batch_id not in already]
    # ZIP-Reste eines abgebrochenen Laufs entfernen.
    _remove_leftover_zips(paths.tmp_dir)
    apply_kwargs = dict(company=company, paths=paths, url_index=url_index, model=model, progress=progress)
    total = len(todo)
    started = time.monotonic()

    def report(done: int, batch_id: str) -> None:
        if done % PROGRESS_EVERY == 0 or done == total:
            rate = (time.monotonic() - started) / done
            print(f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} Satz {batch_id} ({done}/{total}, {rate:.2f} s/Satz)",
                  flush=True)

    if workers <= 1:
        for done, batch_id in enumerate(todo, start=1):
            # process_batch trägt den Berlin-Tag vor dem Speichern in pending_rebuild_days ein
            # (Erfolg wie Lücke), damit ein Abbruch keine betroffenen Tage verliert.
            process_batch(batch_id, title_opener=title_opener, fetcher=fetcher, extract_zip=extract_zip, **apply_kwargs)
            report(done, batch_id)
    else:
        if use_process_pool(workers=workers, fetcher=fetcher, extract_zip=extract_zip, title_opener=title_opener):
            executor = ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"))
        else:
            executor = ThreadPoolExecutor(max_workers=workers)
        pending: deque = deque()
        queue = iter(todo)

        def submit_next() -> None:
            batch_id = next(queue, None)
            if batch_id is not None:
                pending.append(
                    executor.submit(prefetch_batch, batch_id, paths.tmp_dir, company, title_opener, fetcher, extract_zip)
                )

        try:
            for _ in range(workers * PREFETCH_FACTOR):
                submit_next()
            done = 0
            while pending:
                # Ergebnisse strikt in Satzreihenfolge übernehmen: der Cursor rückt nur lückenlos vor.
                prefetched = pending.popleft().result()
                submit_next()
                apply_prefetched(prefetched, **apply_kwargs)
                done += 1
                report(done, prefetched.batch_id)
        finally:
            # Bei Abbruch nicht gestartete Sätze verwerfen, laufende sauber beenden (sie löschen ihre ZIPs).
            executor.shutdown(wait=True, cancel_futures=True)
            _remove_leftover_zips(paths.tmp_dir)
    daily_file = paths.site_data_dir / f"{company.ticker.lower()}-daily.json"
    # Ohne vorhandene Tagesdatei gibt es keinen gespeicherten Stand, auf dem inkrementell aufgebaut werden kann.
    full = full_rebuild or not daily_file.exists()
    rebuild_outputs(paths, company, progress, None if full else set(progress.pending_rebuild_days))
    # Erst nach erfolgreichem Schreiben von Tages- und Schlagzeilendateien leeren.
    progress.pending_rebuild_days = []
    save_progress(paths.progress_path, progress)


def _latest_published_batch_id(now: datetime | None = None) -> str:
    """Letzter sicher veröffentlichter 15-Minuten-Satz: Viertelstunde vor der aktuellen, abgerundet."""
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc) - timedelta(minutes=15)
    rounded = current.replace(minute=(current.minute // 15) * 15, second=0, microsecond=0)
    return batch_id_from_datetime(rounded)


def run_initial(
    paths: ProjectPaths,
    company: CompanyConfig,
    model: SentimentModel | None,
    title_opener,
    until_id: str | None = None,
    fetcher=None,
    extract_zip=None,
    retry_missing: bool = False,
    full_rebuild: bool = False,
    workers: int = 1,
) -> None:
    progress = load_progress(paths.progress_path)
    target = until_id or _latest_published_batch_id()
    run_batches(
        batches_to_process(progress, target, retry_missing=retry_missing),
        company=company,
        paths=paths,
        model=model,
        title_opener=title_opener,
        fetcher=fetcher,
        extract_zip=extract_zip,
        full_rebuild=full_rebuild,
        workers=workers,
    )


def run_daily(
    paths: ProjectPaths,
    company: CompanyConfig,
    model: SentimentModel | None,
    title_opener,
    day: date | None = None,
    fetcher=None,
    extract_zip=None,
    retry_missing: bool = False,
    full_rebuild: bool = False,
    workers: int = 1,
) -> None:
    target = day or previous_berlin_day()
    until_id = expected_batch_ids_for_berlin_day(target)[-1]
    progress = load_progress(paths.progress_path)
    run_batches(
        batches_to_process(progress, until_id, retry_missing=retry_missing),
        company=company,
        paths=paths,
        model=model,
        title_opener=title_opener,
        fetcher=fetcher,
        extract_zip=extract_zip,
        full_rebuild=full_rebuild,
        workers=workers,
    )


def run_trial(
    paths: ProjectPaths,
    company: CompanyConfig,
    model: SentimentModel | None,
    title_opener,
    start_day: date,
    days: int = 7,
    fetcher=None,
    extract_zip=None,
) -> None:
    wanted: list[str] = []
    for offset in range(days):
        wanted.extend(expected_batch_ids_for_berlin_day(start_day + timedelta(days=offset)))
    run_batches(
        wanted,
        company=company,
        paths=paths,
        model=model,
        title_opener=title_opener,
        fetcher=fetcher,
        extract_zip=extract_zip,
    )
