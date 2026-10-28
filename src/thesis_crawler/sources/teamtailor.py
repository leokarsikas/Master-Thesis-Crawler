"""Teamtailor career sites (used by many Swedish companies).

Job pages live under /jobs/<id>-<slug>, so only those links are followed and
every job page is checked for thesis wording.
"""

from __future__ import annotations

from .base import register
from .generic_html import GenericHtmlSource


@register("teamtailor")
class TeamtailorSource(GenericHtmlSource):
    def __init__(self, name: str, url: str, company: str | None = None, **options):
        options.setdefault("link_pattern", r"/jobs/\d+")
        options.setdefault("max_depth", 1)
        options.setdefault("max_pages", 80)
        super().__init__(name, url, company, **options)
