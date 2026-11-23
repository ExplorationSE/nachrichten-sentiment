from __future__ import annotations

import re

from nachrichten_sentiment.models import CompanyConfig
from nachrichten_sentiment.urls import normalize_url


def _contains_name(text: str, company: CompanyConfig) -> bool:
    lowered = text.lower()
    return any(part in lowered for part in company.name_substrings)


def _contains_ticker_word(text: str, company: CompanyConfig) -> bool:
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(company.ticker_word)}(?![A-Za-z0-9])", text, re.IGNORECASE) is not None


def matches_company(
    company: CompanyConfig,
    organizations: str,
    enhanced_organizations: str,
    url: str,
    gkg_title: str | None,
) -> bool:
    if _contains_name(organizations, company) or _contains_name(enhanced_organizations, company):
        return True
    normalized = normalize_url(url)
    if _contains_name(normalized, company) or _contains_ticker_word(normalized, company):
        return True
    if gkg_title and (_contains_name(gkg_title, company) or _contains_ticker_word(gkg_title, company)):
        return True
    return False
