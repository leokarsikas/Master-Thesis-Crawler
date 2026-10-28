"""Write the ranked listings as CSV and a self-contained HTML page."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from .models import Listing

CSV_FIELDS = [
    "score", "new", "title", "company", "location", "deadline", "source",
    "keyword_score", "embedding_score", "matched_terms", "first_seen", "url",
]


def write_csv(listings: list[Listing], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for l in listings:
            writer.writerow({
                "score": l.score,
                "new": "yes" if l.is_new else "",
                "title": l.title,
                "company": l.company,
                "location": l.location,
                "deadline": l.deadline,
                "source": l.source,
                "keyword_score": round(l.keyword_score, 1),
                "embedding_score": "" if l.embedding_score is None else round(l.embedding_score, 1),
                "matched_terms": "; ".join(l.matched_terms),
                "first_seen": l.first_seen[:10],
                "url": l.url,
            })


def write_html(listings: list[Listing], path: Path, errors: dict[str, str]) -> None:
    env = Environment(
        loader=PackageLoader("thesis_crawler", "templates"),
        autoescape=select_autoescape(["html"]),
    )
    html = env.get_template("report.html").render(
        listings=listings,
        errors=errors,
        generated=datetime.now().strftime("%Y-%m-%d %H:%M"),
        new_count=sum(l.is_new for l in listings),
        embeddings=any(l.embedding_score is not None for l in listings),
    )
    path.write_text(html, encoding="utf-8")


def write_reports(listings: list[Listing], out_dir: Path, errors: dict[str, str]) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path, html_path = out_dir / "listings.csv", out_dir / "report.html"
    write_csv(listings, csv_path)
    write_html(listings, html_path, errors)
    return csv_path, html_path
