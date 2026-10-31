from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

from .fetch import Fetcher
from .models import Listing
from .report import write_reports
from .scoring import Embedder, Profile, score_listings
from .sources import load_sources
from .store import Store

log = logging.getLogger("thesis_crawler")


def dedupe(listings: list[Listing]) -> list[Listing]:
    """The same ad often appears on a company site and a job board; keep the richest copy."""
    best: dict[str, Listing] = {}
    for l in listings:
        key = re.sub(r"\W+", " ", f"{l.company} {l.title}".lower()).strip()
        if key not in best or len(l.description) > len(best[key].description):
            best[key] = l
    return list(best.values())


def crawl(sources, fetcher: Fetcher) -> tuple[list[Listing], dict[str, str]]:
    listings: list[Listing] = []
    errors: dict[str, str] = {}
    for source in sources:
        try:
            found = source.fetch(fetcher)
        except Exception as e:  # one broken site shouldn't stop the run
            log.warning("%-28s FAILED: %s", source.name, e)
            errors[source.name] = str(e)
            continue
        log.info("%-28s %3d thesis listings", source.name, len(found))
        listings.extend(found)
    return dedupe(listings), errors


def run(args: argparse.Namespace) -> int:
    profile = Profile.load(args.profile)
    sources = load_sources(args.sources, only=args.only)
    if not sources:
        log.error("no sources selected from %s", args.sources)
        return 1

    fetcher = Fetcher(
        cache_dir=None if args.no_cache else args.cache_dir,
        delay=args.delay,
        respect_robots=not args.ignore_robots,
    )
    with fetcher:
        listings, errors = crawl(sources, fetcher)

    embedder = None if args.no_embeddings else Embedder(profile.embedding_model)
    ranked = score_listings(listings, profile, embedder)
    if args.min_score is not None:
        ranked = [l for l in ranked if l.score >= args.min_score]

    store = Store(args.db)
    try:
        store.record(ranked)
    finally:
        store.close()

    csv_path, html_path = write_reports(ranked, args.out, errors)
    new = sum(l.is_new for l in ranked)
    log.info("%d listings (%d new), %d sources failed", len(ranked), new, len(errors))
    log.info("wrote %s and %s", csv_path, html_path)
    for l in ranked[: args.top]:
        flag = "NEW " if l.is_new else "    "
        print(f"{l.score:5.1f} {flag}{l.title[:70]:70}  {l.company[:25]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thesis-crawler", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run", help="crawl all sources, score and write the report")
    p.add_argument("--sources", type=Path, default=Path("config/sources.yaml"))
    p.add_argument("--profile", type=Path, default=Path("config/profile.yaml"))
    p.add_argument("--out", type=Path, default=Path("out"))
    p.add_argument("--db", type=Path, default=Path("data/listings.db"))
    p.add_argument("--cache-dir", type=Path, default=Path("cache"))
    p.add_argument("--no-cache", action="store_true", help="always refetch pages")
    p.add_argument("--only", nargs="+", metavar="NAME", help="run only these sources")
    p.add_argument("--no-embeddings", action="store_true", help="keyword scoring only")
    p.add_argument("--min-score", type=float, default=None, help="drop listings scoring below this")
    p.add_argument("--top", type=int, default=15, help="print this many top matches")
    p.add_argument("--delay", type=float, default=1.0, help="seconds between requests per host")
    p.add_argument("--ignore-robots", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)-7s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return run(args)
