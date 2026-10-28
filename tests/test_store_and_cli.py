import csv

from thesis_crawler.cli import main
from thesis_crawler.models import Listing
from thesis_crawler.store import Store

from conftest import FIXTURES, ROOT


def test_store_flags_new_only_once(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    l1 = Listing("Master thesis A", "https://x.se/a/", "X", "s")
    store.record([l1], now="2026-10-01T00:00:00")
    assert l1.is_new and l1.first_seen == "2026-10-01T00:00:00"

    again = Listing("Master thesis A (updated)", "https://x.se/a#apply", "X", "s")
    fresh = Listing("Master thesis B", "https://x.se/b", "X", "s")
    store.record([again, fresh], now="2026-10-02T00:00:00")
    assert not again.is_new and again.first_seen == "2026-10-01T00:00:00"
    assert fresh.is_new
    store.close()


def test_cli_end_to_end_on_fixtures(tmp_path, capsys):
    args = [
        "run", "--sources", str(FIXTURES / "sources.yaml"),
        "--profile", str(ROOT / "config" / "profile.yaml"),
        "--out", str(tmp_path / "out"), "--db", str(tmp_path / "db.sqlite"),
        "--no-cache", "--no-embeddings", "--delay", "0",
    ]
    assert main(args) == 0

    rows = list(csv.DictReader((tmp_path / "out" / "listings.csv").open(encoding="utf-8")))
    titles = [r["title"] for r in rows]
    assert titles[0].startswith("Master thesis: Learning personalized treatment")
    assert titles[-1] == "Exjobb: Hydraulic valve design"
    # Same MedAI ad on the company site and Platsbanken is listed once.
    assert titles.count("Master thesis: LLM-based patient triage with in-house models") == 1
    assert all(r["new"] == "yes" for r in rows)

    html = (tmp_path / "out" / "report.html").read_text(encoding="utf-8")
    assert "Broken site" in html  # failed sources are reported, not fatal
    assert "NEW" in html

    assert main(args) == 0
    rows = list(csv.DictReader((tmp_path / "out" / "listings.csv").open(encoding="utf-8")))
    assert not any(r["new"] for r in rows)
