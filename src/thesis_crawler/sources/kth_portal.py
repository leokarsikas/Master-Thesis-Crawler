"""KTH Degree Project Portal: an assignments table with headline, organisation,
location and assignment type columns, plus a detail page per assignment."""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from ..fetch import FetchError, Fetcher
from ..filter import is_thesis
from ..models import Listing
from .base import Source, find_deadline, main_text, register, soup_of

log = logging.getLogger(__name__)

_COLUMNS = {
    "title": re.compile(r"headline|title|rubrik", re.I),
    "company": re.compile(r"organi[sz]ation|company|företag", re.I),
    "location": re.compile(r"location|ort|plats", re.I),
    "type": re.compile(r"type|typ", re.I),
    "deadline": re.compile(r"deadline|last|sista|apply", re.I),
}
_DEGREE_TYPE = re.compile(r"degree|exjobb|examensarbete|thesis", re.I)
_PORTAL_LINK = re.compile(r"degree\s+project\s+portal|exjobbsportal|assignments|uppdrag", re.I)
_NEXT = re.compile(r"^\s*(next|nästa|›|»|>)\s*$", re.I)


@register("kth_portal")
class KthPortalSource(Source):
    def __init__(
        self,
        name: str,
        url: str,
        company: str | None = None,
        max_pages: int = 20,
        max_details: int = 300,
        **options,
    ):
        super().__init__(name, url, company, **options)
        self.max_pages = max_pages
        self.max_details = max_details

    def fetch(self, fetcher: Fetcher) -> list[Listing]:
        rows: list[dict] = []
        url: str | None = self.url
        for _ in range(self.max_pages):
            if not url:
                break
            soup = soup_of(fetcher.get(url))
            page_rows = self._parse_table(soup, url)
            if not rows and not page_rows:
                # Started on an info page: jump to the portal it links to.
                portal = next(
                    (a for a in soup.find_all("a", href=True)
                     if _PORTAL_LINK.search(a.get_text(" ", strip=True))),
                    None,
                )
                portal_url = urljoin(url, portal["href"]) if portal else None
                url = portal_url if portal_url and portal_url != url else None
                continue
            rows.extend(page_rows)
            url = self._next_page(soup, url)

        listings: list[Listing] = []
        for row in rows[: self.max_details]:
            if row.get("type") and not _DEGREE_TYPE.search(row["type"]):
                continue
            description = ""
            try:
                description = main_text(soup_of(fetcher.get(row["url"])))
            except FetchError as e:
                log.debug("detail page failed: %s", e)
            listing = Listing(
                title=row["title"],
                url=row["url"],
                company=row.get("company") or self.company,
                source=self.name,
                location=row.get("location", ""),
                deadline=row.get("deadline") or find_deadline(description),
                description=description,
            )
            # Typed rows are already known degree projects; untyped ones need the wording.
            if row.get("type") or is_thesis(listing.text):
                listings.append(listing)
        return listings

    def _parse_table(self, soup, base_url: str) -> list[dict]:
        out = []
        for table in soup.find_all("table"):
            headers = [th.get_text(" ", strip=True) for th in table.find_all("th")]
            colmap: dict[str, int] = {}
            for i, h in enumerate(headers):
                for key, pattern in _COLUMNS.items():
                    if key not in colmap and pattern.search(h):
                        colmap[key] = i
                        break
            if "title" not in colmap:
                continue
            for tr in table.find_all("tr"):
                cells = tr.find_all("td")
                if len(cells) <= colmap["title"]:
                    continue
                link = cells[colmap["title"]].find("a", href=True) or tr.find("a", href=True)
                if not link:
                    continue
                row = {"url": urljoin(base_url, link["href"])}
                for key, idx in colmap.items():
                    if idx < len(cells):
                        row[key] = cells[idx].get_text(" ", strip=True)
                out.append(row)
        return out

    def _next_page(self, soup, base_url: str) -> str | None:
        link = soup.find("a", rel="next", href=True)
        if not link:
            link = next(
                (a for a in soup.find_all("a", href=True) if _NEXT.match(a.get_text(strip=True))),
                None,
            )
        return urljoin(base_url, link["href"]) if link else None
