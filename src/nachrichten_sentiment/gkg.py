from __future__ import annotations

import html
import re
from dataclasses import dataclass


COL_RECORD_ID = 0
COL_DATE = 1
COL_SOURCE_COLLECTION = 2
COL_SOURCE_NAME = 3
COL_URL = 4
COL_ORGANIZATIONS = 13
COL_ENHANCED_ORGANIZATIONS = 14
COL_EXTRAS = 26
GKG_MIN_COLUMNS = 27

_PAGE_TITLE = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class GkgRecord:
    gkg_record_id: str
    batch_id: str
    source_collection_id: int
    source_domain: str
    url: str
    organizations: str
    enhanced_organizations: str
    extras: str
    page_title: str | None


def unescape_gdelt_title(raw: str) -> str:
    return html.unescape(raw)


def extract_page_title(extras: str) -> str | None:
    match = _PAGE_TITLE.search(extras or "")
    if not match:
        return None
    title = unescape_gdelt_title(match.group(1)).strip()
    return title or None


def parse_gkg_line(line: str, batch_id: str) -> GkgRecord | None:
    parts = line.rstrip("\n").split("\t")
    if len(parts) < GKG_MIN_COLUMNS:
        return None
    if parts[COL_RECORD_ID] == "GKGRECORDID":
        return None
    try:
        collection = int(parts[COL_SOURCE_COLLECTION])
    except ValueError:
        return None
    if collection != 1:
        return None
    return GkgRecord(
        gkg_record_id=parts[COL_RECORD_ID],
        batch_id=batch_id,
        source_collection_id=collection,
        source_domain=parts[COL_SOURCE_NAME],
        url=parts[COL_URL],
        organizations=parts[COL_ORGANIZATIONS],
        enhanced_organizations=parts[COL_ENHANCED_ORGANIZATIONS],
        extras=parts[COL_EXTRAS],
        page_title=extract_page_title(parts[COL_EXTRAS]),
    )
