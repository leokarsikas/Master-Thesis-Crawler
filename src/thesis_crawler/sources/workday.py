"""Workday career sites (e.g. Elekta), read through the JSON the site itself loads.

https://<tenant>.wdN.myworkdayjobs.com/<lang>/<site> lists jobs from
POST /wday/cxs/<tenant>/<site>/jobs and each ad from GET /wday/cxs/<tenant>/<site><externalPath>.
"""

from __future__ import annotations

import json
import logging
from urllib.parse import urlsplit

from ..fetch import FetchError, Fetcher
from ..filter import is_thesis
from ..models import Listing
from .base import Source, find_deadline, main_text, register, soup_of

log = logging.getLogger(__name__)

DEFAULT_QUERIES = ["thesis", "examensarbete", "exjobb"]
PAGE_SIZE = 20


@register("workday")
class WorkdaySource(Source):
    def __init__(
        self,
        name: str,
        url: str,
        company: str | None = None,
        queries: list[str] | None = None,
        max_results: int = 200,
        **options,
    ):
        super().__init__(name, url, company, **options)
        self.queries = queries or DEFAULT_QUERIES
        self.max_results = max_results
        parts = urlsplit(url)
        segments = [s for s in parts.path.split("/") if s]
        self.offline = parts.scheme == "file"
        self.base = f"{parts.scheme}://{parts.netloc}"
        self.lang = segments[0] if len(segments) > 1 else "en-US"
        self.site = segments[-1] if segments else ""
        self.api = f"{self.base}/wday/cxs/{parts.netloc.split('.')[0]}/{self.site}"

    def fetch(self, fetcher: Fetcher) -> list[Listing]:
        listings: dict[str, Listing] = {}
        for query in self.queries:
            offset = 0
            while offset < self.max_results:
                if self.offline:
                    data = json.loads(fetcher.get(self.url))
                else:
                    body = {"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": query}
                    data = json.loads(fetcher.post_json(f"{self.api}/jobs", body))
                postings = data.get("jobPostings") or []
                for posting in postings:
                    if is_thesis(posting.get("title", "")):
                        listing = self._to_listing(posting, fetcher)
                        listings[listing.id] = listing
                offset += PAGE_SIZE
                if self.offline or not postings or offset >= data.get("total", 0):
                    break
            if self.offline:
                break
        return list(listings.values())

    def _to_listing(self, posting: dict, fetcher: Fetcher) -> Listing:
        path = posting.get("externalPath", "")
        description, location = "", posting.get("locationsText", "")
        if not self.offline and path:
            try:
                info = json.loads(fetcher.get(f"{self.api}{path}")).get("jobPostingInfo") or {}
                description = main_text(soup_of(info.get("jobDescription", "")))
                location = info.get("location") or location
            except (FetchError, ValueError) as e:
                log.debug("detail failed for %s: %s", path, e)
        return Listing(
            title=posting.get("title", "").strip(),
            url=f"{self.base}/{self.lang}/{self.site}{path}",
            company=self.company,
            source=self.name,
            location=location,
            deadline=find_deadline(description),
            description=description,
        )
