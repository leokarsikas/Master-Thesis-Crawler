from pathlib import Path

import pytest

from thesis_crawler.filter import is_thesis, is_thesis_listing
from thesis_crawler.sources import build_source, load_sources

from conftest import FIXTURES, ROOT


def source(cfg):
    return build_source(cfg, FIXTURES)


def titles(listings):
    return sorted(l.title for l in listings)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Master thesis: ML for health", True),
        ("Master's thesis in radiotherapy", True),
        ("Examensarbete inom AI", True),
        ("Exjobb: Hydraulic valve design", True),
        ("Thesis worker: XAI", True),
        ("Degree project, 30 hp", True),
        ("Senior backend developer", False),
        ("Lagerarbetare", False),
    ],
)
def test_is_thesis(text, expected):
    assert is_thesis(text) is expected


def test_generic_html_follows_hubs_and_skips_non_thesis(fetcher):
    listings = source({"name": "MedAI", "url": "company/careers.html"}).fetch(fetcher)
    assert titles(listings) == [
        "Exjobb: Hydraulic valve design",
        "Master thesis: Comparing four machine learning algorithms for sepsis prediction",
        "Master thesis: LLM-based patient triage with in-house models",
        "Master thesis: Learning personalized treatment strategies from longitudinal clinical data",
    ]
    good = next(l for l in listings if "personalized" in l.title)
    assert good.company == "MedAI"
    assert good.deadline == "2026-11-30"
    assert "Senior backend" not in good.description  # page text, not the whole site


def test_teamtailor_only_job_pages(fetcher):
    listings = source({"name": "Teamhealth", "type": "teamtailor", "url": "teamtailor/jobs.html"}).fetch(fetcher)
    assert titles(listings) == ["Thesis worker: Explainable AI for radiotherapy"]


def test_kth_portal_table_pagination_and_type_filter(fetcher):
    listings = source(
        {"name": "KTH", "type": "kth_portal", "company": "KTH", "url": "kth/info.html"}
    ).fetch(fetcher)
    by_title = {l.title: l for l in listings}
    assert set(by_title) == {
        "Master Thesis: Wearable sensor fusion for gait analysis",
        "Master Thesis, 30 hp: Kontinuerlig erfarenhetsåterföring",
    }
    gait = by_title["Master Thesis: Wearable sensor fusion for gait analysis"]
    assert gait.company == "KTH MoveAbility Lab"
    assert gait.location == "Stockholm"
    assert gait.deadline == "2026-12-01"
    assert "wearable sensors" in gait.description


def test_jobtech_keeps_only_thesis_ads(fetcher):
    listings = source({"name": "Platsbanken", "type": "jobtech", "url": "jobtech.json"}).fetch(fetcher)
    assert titles(listings) == [
        "Examensarbete: AI för klinisk beslutsstöd",
        "Master thesis: LLM-based patient triage with in-house models",
    ]
    ad = next(l for l in listings if l.company == "Region Stockholm")
    assert ad.deadline == "2026-11-20"
    assert ad.location == "Stockholm"


def test_shipped_sources_config_is_valid():
    sources = load_sources(ROOT / "config" / "sources.yaml")
    assert len(sources) > 15
    assert all(s.url.startswith("https://") for s in sources)
    assert {s.name for s in load_sources(ROOT / "config" / "sources.yaml", only=["doctrin"])} == {"Doctrin"}


@pytest.mark.parametrize(
    "title, description, expected",
    [
        ("Master Thesis: ML for triage", "", True),
        ("Doktorand i medicinsk vetenskap", "Du kommer att handleda examensarbeten.", False),
        ("Universitetsadjunkt i omvårdnad", "Undervisning och examensarbete 15 hp.", False),
        ("Forskningsassistent i medical management", "examensarbete", False),
        ("Personalized treatment from EHR data", "Master thesis, 30 hp, at our lab.", True),
        ("Personalized treatment from EHR data", "x" * 700 + " master thesis", False),
    ],
)
def test_is_thesis_listing(title, description, expected):
    assert is_thesis_listing(title, description) is expected


def test_smartrecruiters_keeps_thesis_postings(fetcher):
    listings = source(
        {"name": "AFRY", "type": "smartrecruiters", "company_id": "AFRY", "url": "smartrecruiters.json"}
    ).fetch(fetcher)
    [l] = listings
    assert l.title == "Master's Thesis Project at AFRY, Medical Device Software"
    assert l.url == "https://jobs.smartrecruiters.com/AFRY/743999937353932-master-s-thesis-project-at-afry-medical-device-software"
    assert (l.company, l.location) == ("AFRY", "Stockholm")
