from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    """Drop fragments and trailing slashes so the same ad maps to one id."""
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


@dataclass
class Listing:
    title: str
    url: str
    company: str
    source: str
    location: str = ""
    deadline: str = ""
    description: str = ""

    # Filled in by scoring / storage.
    score: float = 0.0
    keyword_score: float = 0.0
    embedding_score: float | None = None
    matched_terms: list[str] = field(default_factory=list)
    bonuses: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)  # requirements the listing doesn't meet
    first_seen: str = ""
    is_new: bool = False

    @property
    def id(self) -> str:
        return hashlib.sha1(normalize_url(self.url).encode()).hexdigest()[:16]

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.description}"
