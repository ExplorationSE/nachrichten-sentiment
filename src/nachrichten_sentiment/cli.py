from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.paths import ProjectPaths, default_root
from nachrichten_sentiment.pipeline import run_daily, run_initial, run_trial
from nachrichten_sentiment.titles import http_title_opener


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nachrichten-sentiment")
    sub = parser.add_subparsers(dest="command", required=True)
    erstlauf = sub.add_parser("erstlauf", help="alle GKG-Sätze ab 20150218230000 fortsetzbar verarbeiten")
    erstlauf.add_argument("--until", default=None, help="letzter Satz YYYYMMDDHHMMSS")
    tageslauf = sub.add_parser("tageslauf", help="Vortag in Europe/Berlin plus offene Lücken")
    tageslauf.add_argument("--day", default=None, help="Zieltag YYYY-MM-DD")
    for command in (erstlauf, tageslauf):
        command.add_argument(
            "--luecken-erneut",
            action="store_true",
            help="auch an der Quelle fehlende Sätze (GDELT 404) älter als 7 Tage erneut abrufen",
        )
    probelauf = sub.add_parser("probelauf", help="einige Berlin-Tage zur Probe verarbeiten")
    probelauf.add_argument("--start", required=True, help="erster Tag YYYY-MM-DD")
    probelauf.add_argument("--days", type=int, default=7, help="Anzahl Berlin-Tage ab --start (Standard 7)")
    probelauf.add_argument("--fixture-dir", default=None, help="lokale GKG-ZIPs statt Download")
    probelauf.add_argument(
        "--root",
        default=None,
        help="eigener Projekt-Root für den Probelauf (Standard: probe/ im Repo), getrennt vom Echtbetrieb",
    )
    return parser


def _model():
    from nachrichten_sentiment.sentiment import FinBertModel

    return FinBertModel()


def _fixture_fetcher(fixture: Path):
    def fetcher(url: str) -> bytes:
        batch_id = url.rsplit("/", 1)[-1].split(".")[0]
        return (fixture / f"{batch_id}.gkg.csv.zip").read_bytes()

    return fetcher


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = default_root()
    paths = ProjectPaths(root)
    company = load_company("NVDA")
    model = _model()
    if args.command == "erstlauf":
        run_initial(paths, company, model, http_title_opener, until_id=args.until, retry_missing=args.luecken_erneut)
    elif args.command == "tageslauf":
        day = date.fromisoformat(args.day) if args.day else None
        run_daily(paths, company, model, http_title_opener, day=day, retry_missing=args.luecken_erneut)
    elif args.command == "probelauf":
        fetcher = _fixture_fetcher(Path(args.fixture_dir)) if args.fixture_dir else None
        # Eigener Zustand, damit der Cursor des Probelaufs den Erstlauf nicht verschiebt.
        trial_paths = ProjectPaths(Path(args.root) if args.root else root / "probe")
        run_trial(
            trial_paths,
            company,
            model,
            http_title_opener,
            date.fromisoformat(args.start),
            days=args.days,
            fetcher=fetcher,
        )
    return 0
