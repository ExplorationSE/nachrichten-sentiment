from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_DROP_PARAMS = {"fbclid", "gclid"}


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _DROP_PARAMS and not key.lower().startswith("utm_")
    ]
    return urlunparse((scheme, netloc, path, "", urlencode(query, doseq=True), ""))
