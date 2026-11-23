from __future__ import annotations

import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from nachrichten_sentiment.daily import aggregate_daily
from nachrichten_sentiment.dedup import UrlIndex, mark_near_duplicates
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
    mark_success,
    processed_batch_ids,
    save_progress,
)
from nachrichten_sentiment.sentiment import SentimentModel, score_title
from nachrichten_sentiment.store import append_articles, load_articles, write_daily, write_headlines
from nachrichten_sentiment.timeutil import (
    FIRST_BERLIN_DAY,
    batch_id_from_datetime,
    berlin_day_from_batch_id,
    datetime_from_batch_id,
    expected_batch_ids_for_berlin_day,
    previous_berlin_day,
)
from nachrichten_sentiment.titles import fetch_title
from nachrichten_sentiment.urls import normalize_url


class EmptyGkgZipError(Exception):
    """Die ZIP-Datei ist lesbar, enthält aber keine Datei."""


def _extract_zip(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        if not names:
            raise EmptyGkgZipError(zip_path.name)
        return archive.read(names[0]).decode("utf-8", errors="replace")


def _record_gap(batch_id: str, message: str, *, paths: ProjectPaths, progress: ProgressState) -> list[Article]:
    mark_gap(progress, batch_id)
    append_gap_log(paths.gaps_log_path, f"{batch_id} {message}")
    save_progress(paths.progress_path, progress)
    return []


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
    try:
        zip_path = download_gkg_zip(
            batch_id,
            paths.tmp_dir,
            fetcher=fetcher,
            backoff_seconds=0.0 if fetcher else 2.0,
        )
        text = (extract_zip or _extract_zip)(zip_path)
    except (MissingGkgError, DownloadError) as exc:
        return _record_gap(batch_id, str(exc), paths=paths, progress=progress)
    except zipfile.BadZipFile as exc:
        return _record_gap(batch_id, f"defekte ZIP-Datei: {exc}", paths=paths, progress=progress)
    except EmptyGkgZipError:
        return _record_gap(batch_id, "leere ZIP-Datei ohne Inhalt", paths=paths, progress=progress)
    finally:
        leftover = paths.tmp_dir / f"{batch_id}.gkg.csv.zip"
        if leftover.exists():
            leftover.unlink()

    articles: list[Article] = []
    batch_utc = datetime_from_batch_id(batch_id).strftime("%Y-%m-%dT%H:%M:%SZ")
    day = berlin_day_from_batch_id(batch_id).isoformat()
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
        if not url_index.keep(record.url, record.gkg_record_id):
            continue
        if record.page_title:
            title, title_source = record.page_title, "gkg"
        else:
            fetched = fetch_title(record.url, title_opener, progress.failed_title_fetches)
            title, title_source = (fetched.title or ""), fetched.source
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
    save_progress(paths.progress_path, progress)
    return articles


def rebuild_outputs(paths: ProjectPaths, company: CompanyConfig, progress: ProgressState) -> list[DailyRow]:
    """Baut Tageswerte und Schlagzeilen vollständig aus allen gespeicherten Artikeln neu auf."""
    articles = mark_near_duplicates(load_articles(paths, company.ticker))
    processed = processed_batch_ids(progress)
    end_day = berlin_day_from_batch_id(progress.cursor_batch_id) if progress.cursor_batch_id else FIRST_BERLIN_DAY
    rows: list[DailyRow] = []
    day = FIRST_BERLIN_DAY
    while day <= end_day:
        rows.append(aggregate_daily(articles, day, processed))
        day += timedelta(days=1)
    write_daily(paths, company.ticker, rows, company.display_name)
    write_headlines(paths, company.ticker, articles)
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
) -> None:
    progress = load_progress(paths.progress_path)
    url_index = UrlIndex()
    url_index.load_from_articles(load_articles(paths, company.ticker))
    already = processed_batch_ids(progress)
    for batch_id in batch_ids:
        if batch_id in already:
            continue
        process_batch(
            batch_id,
            company=company,
            paths=paths,
            url_index=url_index,
            model=model,
            title_opener=title_opener,
            progress=progress,
            fetcher=fetcher,
            extract_zip=extract_zip,
        )
    rebuild_outputs(paths, company, progress)


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
) -> None:
    progress = load_progress(paths.progress_path)
    target = until_id or _latest_published_batch_id()
    run_batches(
        batches_to_process(progress, target),
        company=company,
        paths=paths,
        model=model,
        title_opener=title_opener,
        fetcher=fetcher,
        extract_zip=extract_zip,
    )


def run_daily(
    paths: ProjectPaths,
    company: CompanyConfig,
    model: SentimentModel | None,
    title_opener,
    day: date | None = None,
    fetcher=None,
    extract_zip=None,
) -> None:
    target = day or previous_berlin_day()
    until_id = expected_batch_ids_for_berlin_day(target)[-1]
    progress = load_progress(paths.progress_path)
    run_batches(
        batches_to_process(progress, until_id),
        company=company,
        paths=paths,
        model=model,
        title_opener=title_opener,
        fetcher=fetcher,
        extract_zip=extract_zip,
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
