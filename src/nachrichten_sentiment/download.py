from __future__ import annotations

import time
from pathlib import Path

import requests


class MissingGkgError(Exception):
    def __init__(self, batch_id: str) -> None:
        super().__init__(f"missing GKG file {batch_id}")
        self.batch_id = batch_id


class DownloadError(Exception):
    def __init__(self, batch_id: str, message: str) -> None:
        super().__init__(f"{batch_id}: {message}")
        self.batch_id = batch_id
        self.message = message


def gkg_url(batch_id: str) -> str:
    return f"https://data.gdeltproject.org/gdeltv2/{batch_id}.gkg.csv.zip"


def _default_fetcher(url: str) -> bytes:
    response = requests.get(url, timeout=60)
    if response.status_code == 404:
        batch_id = url.rsplit("/", 1)[-1].split(".")[0]
        raise MissingGkgError(batch_id)
    response.raise_for_status()
    return response.content


def download_gkg_zip(
    batch_id: str,
    dest_dir: Path,
    retries: int = 3,
    backoff_seconds: float = 2.0,
    fetcher=None,
) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / f"{batch_id}.gkg.csv.zip"
    url = gkg_url(batch_id)
    fetch = fetcher or _default_fetcher
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            data = fetch(url)
            target.write_bytes(data)
            return target
        except MissingGkgError:
            last_error = MissingGkgError(batch_id)
        except Exception as exc:  # noqa: BLE001
            last_error = DownloadError(batch_id, str(exc))
        if attempt < retries and backoff_seconds:
            time.sleep(backoff_seconds * attempt)
    if isinstance(last_error, MissingGkgError):
        raise last_error
    raise last_error or DownloadError(batch_id, "unknown error")
