"""Platsbanken (Arbetsförmedlingen) via the public JobTech JobSearch API.

Docs: https://jobsearch.api.jobtechdev.se/ — no API key needed.
"""

from __future__ import annotations

import json
import logging

from ..fetch import Fetcher
from ..filter import is_thesis
from ..models import Listing
from .base import Source, register

log = logging.getLogger(__name__)

DEFAULT_URL = "https://jobsearch.api.jobtechdev.se/search"
DEFAULT_QUERIES = ["examensarbete", "exjobb", "master thesis", "thesis worker"]


@register("jobtech")
class JobTechSource(Source):
    def __init__(
        self,
        name: str,
        url: str = DEFAULT_URL,
        company: str | None = None,
        queries: list[str] | None = None,
        limit: int = 100,
        max_results: int = 500,
        **options,
    ):
        super().__init__(name, url, company, **options)
        self.queries = queries or DEFAULT_QUERIES
        self.limit = limit
        self.max_results = max_results

    def fetch(self, fetcher: Fetcher) -> list[Listing]:
        listings: dict[str, Listing] = {}
        offline = self.url.startswith("file://")
        for query in self.queries:
            offset = 0
            while offset < self.max_results:
                params = None if offline else {"q": query, "limit": self.limit, "offset": offset}
                data = json.loads(fetcher.get(self.url, params=params))
                hits = data.get("hits", [])
                for hit in hits:
                    listing = self._to_listing(hit)
                    # Job-board thesis ads always name it in the headline; body mentions are
                    # usually PhD/lecturer jobs that supervise theses.
                    if listing and is_thesis(listing.title):
                        listings[listing.id] = listing
                total = (data.get("total") or {}).get("value", 0)
                offset += self.limit
                if offline or not hits or offset >= total:
                    break
            if offline:
                break
        return list(listings.values())

    def _to_listing(self, hit: dict) -> Listing | None:
        url = hit.get("webpage_url") or (hit.get("application_details") or {}).get("url")
        if not url:
            return None
        address = hit.get("workplace_address") or {}
        return Listing(
            title=hit.get("headline", "").strip(),
            url=url,
            company=(hit.get("employer") or {}).get("name") or "Unknown",
            source=self.name,
            location=address.get("municipality") or address.get("region") or "",
            deadline=(hit.get("application_deadline") or "")[:10],
            description=(hit.get("description") or {}).get("text", ""),
        )
