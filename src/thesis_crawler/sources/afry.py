"""AFRY's own job list: afry.com loads every open job from one JSON file.

Thesis ads are in the "Student Assignment and Thesis Work" competence area.
"""

from __future__ import annotations

import json
import logging
import re

from ..fetch import FetchError, Fetcher
from ..filter import is_thesis
from ..models import Listing
from .base import Source, find_deadline, main_text, register, soup_of

log = logging.getLogger(__name__)

THESIS_AREA = re.compile(r"thesis|student assignment|examensarbete", re.IGNORECASE)
SITE = "https://afry.com"


def _first(job: dict, *keys: str) -> str:
    for key in keys:
        value = job.get(key)
        if isinstance(value, list):
            value = ", ".join(v.get("Name", "") if isinstance(v, dict) else str(v) for v in value)
        if value:
            return str(value).strip()
    return ""


def _jobs(data) -> list[dict]:
    """The list may be the whole document or sit under one key."""
    if isinstance(data, list):
        return data
    for value in data.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value
    return []


@register("afry")
class AfrySource(Source):
    def __init__(self, name: str, url: str, company: str | None = None, fetch_details: bool = True, **options):
        super().__init__(name, url, company or "AFRY", **options)
        self.fetch_details = fetch_details and not url.startswith("file://")

    def fetch(self, fetcher: Fetcher) -> list[Listing]:
        listings: dict[str, Listing] = {}
        for job in _jobs(json.loads(fetcher.get(self.url))):
            areas = [a.get("Name", "") for a in job.get("CompetenceAreas") or [] if isinstance(a, dict)]
            title = _first(job, "Title", "Name", "JobTitle", "Headline")
            if not (any(THESIS_AREA.search(a) for a in areas) or is_thesis(title)):
                continue
            detail = _first(job, "DetailUrl", "Url", "Link")
            url = detail if detail.startswith("http") else SITE + detail
            description = _first(job, "Description", "Summary", "Introduction", "Ingress")
            if self.fetch_details and len(description) < 200:
                try:
                    page = main_text(soup_of(fetcher.get(url)))
                    if len(page) > len(description):
                        description = page
                except FetchError as e:
                    log.debug("detail failed for %s: %s", url, e)
            listing = Listing(
                title=title,
                url=url,
                company=self.company,
                source=self.name,
                location=_first(job, "City", "Location", "LocationName", "Locations", "Cities"),
                deadline=find_deadline(description),
                description=description,
            )
            listings[listing.id] = listing
        return list(listings.values())
