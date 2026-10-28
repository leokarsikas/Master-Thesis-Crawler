"""Crawl any career page for thesis listings.

Starting from the configured page, follow same-site links whose text or URL
looks thesis related. A fetched page that itself links to several thesis
pages is treated as a hub (e.g. a "Thesis opportunities" page) and crawled
further; any other page that mentions a thesis becomes a listing.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlsplit

from ..fetch import FetchError, Fetcher
from ..filter import is_thesis_listing, looks_like_thesis_link
from ..models import Listing, normalize_url
from .base import Source, find_deadline, main_text, page_title, register, soup_of

log = logging.getLogger(__name__)

HUB_MIN_LINKS = 3


@register("generic_html")
class GenericHtmlSource(Source):
    def __init__(
        self,
        name: str,
        url: str,
        company: str | None = None,
        link_pattern: str | None = None,
        max_depth: int = 2,
        max_pages: int = 40,
        **options,
    ):
        super().__init__(name, url, company, **options)
        # Optional regex an href must match to be a listing link (e.g. "/jobs/\\d+").
        self.link_re = re.compile(link_pattern) if link_pattern else None
        self.max_depth = max_depth
        self.max_pages = max_pages

    def fetch(self, fetcher: Fetcher) -> list[Listing]:
        listings: dict[str, Listing] = {}
        seen: set[str] = {normalize_url(self.url)}
        queue: list[tuple[str, int]] = [(self.url, 0)]
        pages = 0

        while queue and pages < self.max_pages:
            url, depth = queue.pop(0)
            try:
                html = fetcher.get(url)
            except FetchError as e:
                if depth == 0:
                    raise
                log.debug("skip %s", e)
                continue
            pages += 1
            soup = soup_of(html)
            links = self._candidate_links(soup, url, include_nav=depth == 0)

            # With an explicit link_pattern every followed page is a job page.
            is_hub = depth == 0 or (self.link_re is None and len(links) >= HUB_MIN_LINKS)
            if not is_hub:
                listing = self._to_listing(soup, url)
                if listing:
                    listings[listing.id] = listing
                continue

            if depth >= self.max_depth:
                continue
            for link in links:
                key = normalize_url(link)
                if key not in seen:
                    seen.add(key)
                    queue.append((link, depth + 1))

        return list(listings.values())

    def _candidate_links(self, soup, base_url: str, include_nav: bool = False) -> list[str]:
        host = urlsplit(base_url).netloc
        out: list[str] = []
        # Menus and footers link to "Students"/"Thesis" from every page; ignore them
        # so ordinary job pages aren't mistaken for hubs.
        content = soup
        if not include_nav:
            content = soup_of(str(soup))
            for tag in content(["nav", "header", "footer"]):
                tag.decompose()
        for a in content.find_all("a", href=True):
            href = urljoin(base_url, a["href"])
            parts = urlsplit(href)
            if parts.scheme not in ("http", "https", "file") or parts.netloc != host:
                continue
            if normalize_url(href) == normalize_url(base_url):
                continue
            text = a.get_text(" ", strip=True)
            if self.link_re:
                if not self.link_re.search(parts.path):
                    continue
            elif not (looks_like_thesis_link(text) or looks_like_thesis_link(parts.path)):
                continue
            if href not in out:
                out.append(href)
        return out

    def _to_listing(self, soup, url: str) -> Listing | None:
        title = page_title(soup)
        text = main_text(soup)
        if not is_thesis_listing(title, text):
            return None
        return Listing(
            title=title,
            url=url,
            company=self.company,
            source=self.name,
            deadline=find_deadline(text),
            description=text,
        )
