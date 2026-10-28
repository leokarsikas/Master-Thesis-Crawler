"""Companies hiring through SmartRecruiters (e.g. AFRY), via its public postings API.

Docs: https://developers.smartrecruiters.com/docs/posting-api
"""

from __future__ import annotations

import json
import logging
import re

from ..fetch import FetchError, Fetcher
from ..filter import is_thesis
from ..models import Listing
from .base import Source, main_text, register, soup_of

log = logging.getLogger(__name__)

API = "https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
DEFAULT_QUERIES = ["thesis", "examensarbete", "exjobb"]


@register("smartrecruiters")
class SmartRecruitersSource(Source):
    def __init__(
        self,
        name: str,
        url: str | None = None,
        company: str | None = None,
        company_id: str | None = None,
        queries: list[str] | None = None,
        country: str | None = "se",
        **options,
    ):
        self.company_id = company_id or name
        super().__init__(name, url or API.format(company_id=self.company_id), company, **options)
        self.queries = queries or DEFAULT_QUERIES
        self.country = country

    def fetch(self, fetcher: Fetcher) -> list[Listing]:
        listings: dict[str, Listing] = {}
        offline = self.url.startswith("file://")
        for query in self.queries:
            params = None if offline else {"q": query, "limit": 100, **({"country": self.country} if self.country else {})}
            data = json.loads(fetcher.get(self.url, params=params))
            for posting in data.get("content", []):
                if not is_thesis(posting.get("name", "")):
                    continue
                listing = self._to_listing(posting, fetcher)
                listings[listing.id] = listing
            if offline:
                break
        return list(listings.values())

    def _to_listing(self, posting: dict, fetcher: Fetcher) -> Listing:
        slug = re.sub(r"[^a-z0-9]+", "-", posting.get("name", "").lower()).strip("-")
        url = f"https://jobs.smartrecruiters.com/{self.company_id}/{posting['id']}-{slug}"
        location = posting.get("location") or {}
        description = ""
        ref = posting.get("ref")
        if ref and not self.url.startswith("file://"):
            try:
                detail = json.loads(fetcher.get(ref))
                sections = (detail.get("jobAd") or {}).get("sections") or {}
                html = "\n".join((sections.get(k) or {}).get("text", "") for k in sections)
                description = main_text(soup_of(html))
            except (FetchError, ValueError) as e:
                log.debug("detail failed for %s: %s", url, e)
        return Listing(
            title=posting.get("name", "").strip(),
            url=url,
            company=(posting.get("company") or {}).get("name") or self.company,
            source=self.name,
            location=location.get("city") or location.get("country", "").upper(),
            description=description,
        )
