from pathlib import Path

import pytest

from thesis_crawler.fetch import Fetcher
from thesis_crawler.scoring import Profile

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fetcher():
    with Fetcher(cache_dir=None, delay=0) as f:
        yield f


@pytest.fixture
def profile():
    return Profile.load(ROOT / "config" / "profile.yaml")
