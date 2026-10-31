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


# Titles of ordinary (mostly academic) jobs whose ads mention theses in passing,
# e.g. a lecturer who will supervise "examensarbeten".
NOT_THESIS_TITLE_RE = re.compile(
    r"\b(?:doktorand\w*|ph\.?\s?d\b|postdoc\w*|post-doc\w*|\w*lektor\w*|\w*adjunkt\w*|"
    r"professor\w*|\w*forskare|forskningsassistent\w*|research\s+(?:assistant|engineer|scientist)|"
    r"\w*lärare|sjuksköterska\w*|teacher|lecturer)\b",
    re.IGNORECASE,
)

# How far into a description a thesis mention still counts as being about the ad itself.
LEAD_CHARS = 600


def is_thesis(text: str) -> bool:
    return bool(THESIS_RE.search(text or ""))


def is_thesis_listing(title: str, description: str = "") -> bool:
    """A thesis ad says so in its title, or early in the text of a non-job title."""
    if is_thesis(title):
        return True
    if NOT_THESIS_TITLE_RE.search(title or ""):
        return False
    return is_thesis((description or "")[:LEAD_CHARS])


def looks_like_thesis_link(text: str) -> bool:
    return bool(LINK_RE.search(text or ""))
