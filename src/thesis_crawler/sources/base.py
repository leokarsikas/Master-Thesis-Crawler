from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import yaml
from bs4 import BeautifulSoup

from ..fetch import Fetcher
from ..models import Listing

_REGISTRY: dict[str, Callable[..., "Source"]] = {}


def register(kind: str):
    def deco(cls):
        _REGISTRY[kind] = cls
        return cls

    return deco


class Source:
    """A place listings come from. Subclasses implement `fetch`."""

    def __init__(self, name: str, url: str, company: str | None = None, **options):
        self.name = name
        self.url = url
        self.company = company or name
        self.options = options

    def fetch(self, fetcher: Fetcher) -> list[Listing]:
        raise NotImplementedError


def build_source(cfg: dict, base_dir: Path | None = None) -> Source:
    cfg = dict(cfg)
    kind = cfg.pop("type", "generic_html")
    cfg.pop("enabled", None)
    if kind not in _REGISTRY:
        raise ValueError(f"unknown source type {kind!r} for {cfg.get('name')!r}")
    if base_dir is not None and cfg.get("url") and "://" not in cfg["url"]:
        # Plain paths in a sources file are local fixtures relative to that file.
        cfg["url"] = (base_dir / cfg["url"]).resolve().as_uri()
    return _REGISTRY[kind](**cfg)


def load_sources(path: Path, only: list[str] | None = None) -> list[Source]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    wanted = {o.lower() for o in only or []}
    sources = []
    for cfg in data.get("sources", []):
        if not cfg.get("enabled", True):
            continue
        if wanted and cfg["name"].lower() not in wanted:
            continue
        sources.append(build_source(cfg, path.parent))
    return sources


# --- shared HTML helpers -----------------------------------------------------

_DEADLINE_RE = re.compile(
    r"(?:deadline|apply\s+(?:by|before)|last\s+(?:day\s+to\s+apply|application\s+date)|"
    r"sista\s+ansökningsdag(?:en)?|ansök\s+senast)\s*[:\-]?\s*"
    r"(\d{4}-\d{2}-\d{2}|\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE,
)

_NOISE_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "form", "svg", "iframe"]


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def page_title(soup: BeautifulSoup) -> str:
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(" ", strip=True)
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return ""


def main_text(soup: BeautifulSoup, max_chars: int = 20000) -> str:
    soup = soup_of(str(soup))  # don't mutate the caller's tree
    for tag in soup(_NOISE_TAGS):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    text = root.get_text("\n", strip=True)
    text = re.sub(r"\n{2,}", "\n", text)
    return text[:max_chars]


def find_deadline(text: str) -> str:
    m = _DEADLINE_RE.search(text)
    return m.group(1) if m else ""

