from .base import Source, build_source, load_sources

# Import adapters so they register themselves.
from . import afry, generic_html, jobtech, kth_portal, teamtailor, workday  # noqa: E402,F401

__all__ = ["Source", "build_source", "load_sources"]
