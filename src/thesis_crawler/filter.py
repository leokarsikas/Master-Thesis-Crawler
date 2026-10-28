"""Decide whether a piece of text is about a master thesis / degree project."""

from __future__ import annotations

import re

# Strong signals: a listing must contain at least one of these.
THESIS_RE = re.compile(
    r"\b(?:"
    r"ex-?jobb\w*|examensarbet\w*|examensjobb\w*|"
    r"master'?s?\s+thes[ie]s|master\s+thesis|msc\s+thes[ie]s|"
    r"thesis\s+(?:work(?:er)?|project|student|position|opportunit\w*)|"
    r"degree\s+project|"
    r"30\s*(?:hp|ects|credits)"
    r")\b",
    re.IGNORECASE,
)

# Looser signal used when deciding which links to follow while crawling.
LINK_RE = re.compile(
    r"thes[ie]s|ex-?jobb|examensarbet|degree[\s_-]*project|students?\b|student[\s_-]*opportunit",
    re.IGNORECASE,
)


def is_thesis(text: str) -> bool:
    return bool(THESIS_RE.search(text or ""))


def looks_like_thesis_link(text: str) -> bool:
    return bool(LINK_RE.search(text or ""))
