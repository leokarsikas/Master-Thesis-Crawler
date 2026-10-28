"""Rank listings against the profile: weighted keywords plus embedding similarity."""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .models import Listing

log = logging.getLogger(__name__)


@dataclass
class Term:
    label: str
    pattern: re.Pattern
    weight: float


def _compile(term: str) -> re.Pattern:
    """`/regex/` is used as-is; `word*` is a prefix match; anything else is a whole phrase."""
    if len(term) > 2 and term.startswith("/") and term.endswith("/"):
        return re.compile(term[1:-1], re.IGNORECASE)
    prefix = term.endswith("*")
    body = re.escape(term.rstrip("*")).replace(r"\ ", r"[\s-]+")
    return re.compile(rf"(?<!\w){body}{r'\w*' if prefix else r'(?!\w)'}", re.IGNORECASE)


@dataclass
class Bonus:
    """Flat points added on top of the 0-100 score when a listing qualifies."""

    label: str
    points: float
    terms: list[re.Pattern]  # match title or description
    employers: list[re.Pattern]  # company must match one of these
    not_employers: list[re.Pattern]  # company must match none of these

    def applies(self, listing: Listing) -> bool:
        company = listing.company or ""
        if self.employers and not any(p.search(company) for p in self.employers):
            return False
        if any(p.search(company) for p in self.not_employers):
            return False
        if self.terms:
            return any(p.search(listing.title) or p.search(listing.description) for p in self.terms)
        return True


class Profile:
    def __init__(self, data: dict):
        self.text: str = data.get("profile_text", "").strip()
        self.terms: list[Term] = []
        for group in (data.get("keywords") or {}).values():
            weight = float(group.get("weight", 1))
            for term in group.get("terms", []):
                self.terms.append(Term(term, _compile(term), weight))
        self.bonuses: list[Bonus] = [
            Bonus(
                label=cfg.get("label", name.replace("_", " ")),
                points=float(cfg.get("points", 0)),
                terms=[_compile(t) for t in cfg.get("terms", [])],
                employers=[_compile(t) for t in cfg.get("employers", [])],
                not_employers=[_compile(t) for t in cfg.get("not_employers", [])],
            )
            for name, cfg in (data.get("bonuses") or {}).items()
        ]
        scoring = data.get("scoring") or {}
        self.keyword_saturation = float(scoring.get("keyword_saturation", 25))
        self.title_multiplier = float(scoring.get("title_multiplier", 2))
        self.keyword_weight = float(scoring.get("keyword_weight", 0.5))
        self.embedding_model = scoring.get(
            "embedding_model", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.similarity_range = tuple(scoring.get("similarity_range", [0.15, 0.6]))

    @classmethod
    def load(cls, path: Path) -> Profile:
        return cls(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def keyword_score(listing: Listing, profile: Profile) -> tuple[float, list[str]]:
    """0-100. Each term counts once; a hit in the title counts extra."""
    raw = 0.0
    matched: list[tuple[float, str]] = []
    for term in profile.terms:
        hit = term.pattern.search(listing.title)
        in_title = hit is not None
        hit = hit or term.pattern.search(listing.description)
        if hit is None:
            continue
        contribution = term.weight * (profile.title_multiplier if in_title else 1)
        raw += contribution
        # Show the text that matched, which reads better than a pattern.
        label = re.sub(r"\s+", " ", hit.group(0).lower())
        matched.append((contribution, label if term.weight > 0 else f"-{label}"))
    matched.sort(key=lambda m: -abs(m[0]))
    score = 100 * (1 - math.exp(-raw / profile.keyword_saturation)) if raw > 0 else 0.0
    return score, list(dict.fromkeys(label for _, label in matched))


class Embedder:
    """Lazy sentence-transformers wrapper. `available` is False if it can't load."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self.available = True

    def _load(self):
        if self._model is None and self.available:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            except Exception as e:  # ImportError, download failures, ...
                log.warning("embeddings disabled (%s); using keywords only", e)
                self.available = False
        return self._model

    def similarities(self, query: str, texts: list[str]) -> list[float] | None:
        model = self._load()
        if model is None:
            return None
        vecs = model.encode([query, *texts], normalize_embeddings=True, show_progress_bar=False)
        q = vecs[0]
        return [float((v * q).sum()) for v in vecs[1:]]


def score_listings(
    listings: list[Listing], profile: Profile, embedder: Embedder | None = None
) -> list[Listing]:
    for listing in listings:
        listing.keyword_score, listing.matched_terms = keyword_score(listing, profile)

    sims = None
    if embedder and profile.text and listings:
        sims = embedder.similarities(
            profile.text, [f"{l.title}\n{l.description[:3000]}" for l in listings]
        )

    lo, hi = profile.similarity_range
    for i, listing in enumerate(listings):
        if sims is None:
            listing.embedding_score = None
            listing.score = listing.keyword_score
        else:
            listing.embedding_score = max(0.0, min(100.0, 100 * (sims[i] - lo) / (hi - lo)))
            w = profile.keyword_weight
            listing.score = w * listing.keyword_score + (1 - w) * listing.embedding_score
        earned = [b for b in profile.bonuses if b.applies(listing)]
        listing.bonuses = [b.label for b in earned]
        listing.score += sum(b.points for b in earned)
        listing.score = round(listing.score, 1)

    return sorted(listings, key=lambda l: l.score, reverse=True)
