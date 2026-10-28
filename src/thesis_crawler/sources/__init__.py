from .base import Source, build_source, load_sources

# Import adapters so they register themselves.
from . import generic_html, jobtech, kth_portal, smartrecruiters, teamtailor  # noqa: E402,F401

__all__ = ["Source", "build_source", "load_sources"]
