from __future__ import annotations

import argparse
import signal
from datetime import date, datetime
from pathlib import Path

from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.paths import ProjectPaths, default_root
from nachrichten_sentiment.pipeline import DEFAULT_WORKERS, run_daily, run_deferred, run_initial, run_trial
from nachrichten_sentiment.titles import http_title_opener


def batch_id_arg(value: str) -> str:
    """Satzkennung YYYYMMDDHHMMSS auf einer Viertelstunde (UTC)."""
    try:
        moment = datetime.strptime(value, "%Y%m%d%H%M%S")
    except ValueError:
        raise argparse.ArgumentTypeError(f"erwartet YYYYMMDDHHMMSS, erhalten: {value}") from None
    if moment.minute % 15 or moment.second:
        raise argparse.ArgumentTypeError(f"Satz muss auf einer Viertelstunde liegen: {value}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nachrichten-sentiment")
    sub = parser.add_subparsers(dest="command", required=True)
    erstlauf = sub.add_parser("erstlauf", help="alle GKG-Sätze ab 20150218230000 fortsetzbar verarbeiten")
    erstlauf.add_argument("--until", default=None, type=batch_id_arg, help="letzter Satz YYYYMMDDHHMMSS")
    bereich = erstlauf.add_mutually_exclusive_group()
    bereich.add_argument(
        "--start",
        default=None,
        type=batch_id_arg,
        help="erst ab diesem Satz YYYYMMDDHHMMSS sammeln; der übersprungene Bereich wird zum Nachholen vorgemerkt",
    )
    bereich.add_argument(
        "--nachholen",
        action="store_true",
        help="vorgemerkte Bereiche eines früheren --start nachholen (fertige Sätze werden übersprungen)",
    )
    tageslauf = sub.add_parser("tageslauf", help="Vortag in Europe/Berlin plus offene Lücken")
    tageslauf.add_argument("--day", default=None, help="Zieltag YYYY-MM-DD")
    for command in (erstlauf, tageslauf):
        command.add_argument(
            "--luecken-erneut",
            action="store_true",
            help="auch an der Quelle fehlende Sätze (GDELT 404) älter als 7 Tage erneut abrufen",
        )
        command.add_argument(
            "--voll-neuaufbau",
            action="store_true",
            help="Nahduplikate, Monatsdateien und Schlagzeilen für alle Tage neu berechnen statt nur betroffene",
        )
        command.add_argument(
            "--parallel",
            type=int,
            default=DEFAULT_WORKERS,
            help=f"Anzahl paralleler Downloads (Standard {DEFAULT_WORKERS}, 1 = nacheinander)",
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


def _exit_on_sigterm(signum, frame):
    # SIGTERM wie Strg+C behandeln: laufende Downloads sauber beenden, gespeicherter Stand bleibt konsistent.
    raise SystemExit(128 + signum)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    signal.signal(signal.SIGTERM, _exit_on_sigterm)
    root = default_root()
    paths = ProjectPaths(root)
    company = load_company("NVDA")
    model = _model()
    if args.command == "erstlauf" and args.nachholen:
        run_deferred(
            paths,
            company,
            model,
            http_title_opener,
            full_rebuild=args.voll_neuaufbau,
            workers=max(1, args.parallel),
        )
    elif args.command == "erstlauf":
        run_initial(
            paths,
            company,
            model,
            http_title_opener,
            until_id=args.until,
            retry_missing=args.luecken_erneut,
            full_rebuild=args.voll_neuaufbau,
            workers=max(1, args.parallel),
            start_id=args.start,
        )
    elif args.command == "tageslauf":
        day = date.fromisoformat(args.day) if args.day else None
        run_daily(
            paths,
            company,
            model,
            http_title_opener,
            day=day,
            retry_missing=args.luecken_erneut,
            full_rebuild=args.voll_neuaufbau,
            workers=max(1, args.parallel),
        )
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
