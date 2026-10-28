from thesis_crawler.models import Listing
from thesis_crawler.scoring import _compile, keyword_score, score_listings


def make(title, description=""):
    return Listing(title=title, url=f"https://x.se/{abs(hash(title))}", company="X",
                   source="test", description=description)


GOOD = make(
    "Master thesis: Learning personalized treatment strategies from longitudinal clinical data",
    "Develop a novel machine learning method for personalized treatment from longitudinal "
    "electronic health records, using causal inference and explainable AI.",
)
COMPARE = make(
    "Master thesis: Comparing four machine learning algorithms for sepsis prediction",
    "Compare four machine learning algorithms (XGBoost, random forest) on a hospital dataset.",
)
MECH = make("Exjobb: Hydraulic valve design", "Examensarbete inom maskinteknik, mechanical engineering.")


def test_term_syntax():
    assert _compile("diagnos*").search("Diagnostik")
    assert _compile("AI").search("Using AI here") and not _compile("AI").search("maintain")
    assert _compile("machine learning").search("machine-learning")
    assert _compile("/compar\\w* models/").search("Comparing models")


def test_guideline_ordering(profile):
    ranked = score_listings([MECH, COMPARE, GOOD], profile, embedder=None)
    assert [l.title for l in ranked] == [GOOD.title, COMPARE.title, MECH.title]
    assert ranked[0].score > 60
    assert ranked[-1].keyword_score == 0


def test_matched_terms_explain_score(profile):
    _, terms = keyword_score(GOOD, profile)
    assert "longitudinal" in terms and "causal" in terms
    assert "develop a novel machine learning method" in terms
    _, terms = keyword_score(COMPARE, profile)
    assert any(t.startswith("-") for t in terms)  # the "compare algorithms" penalty


class FakeEmbedder:
    def __init__(self, sims):
        self.sims = sims

    def similarities(self, query, texts):
        return self.sims[: len(texts)]


def test_embeddings_blend_with_keywords(profile):
    a, b = make("Master thesis A"), make("Master thesis B")
    ranked = score_listings([a, b], profile, FakeEmbedder([0.15, 0.6]))
    assert ranked[0] is b
    assert b.embedding_score == 100 and a.embedding_score == 0
    assert b.score == round(0.5 * b.keyword_score + 50 + 8, 1)  # + company bonus


def test_embeddings_unavailable_falls_back_to_keywords(profile):
    class Broken:
        def similarities(self, query, texts):
            return None

    [l] = score_listings([make("Master thesis", "machine learning for health")], profile, Broken())
    assert l.embedding_score is None and l.score == round(l.keyword_score + 8, 1)  # + company bonus


def bonus_labels(listing, profile):
    [scored] = score_listings([listing], profile, embedder=None)
    return scored.bonuses


def with_company(company, description=""):
    l = make(f"Master thesis at {company}", description)
    l.company = company
    return l


def test_company_bonus_skips_academia_and_public_sector(profile):
    assert bonus_labels(with_company("Volvo Business Services AB"), profile) == ["company"]
    for employer in ["Umeå Universitet", "Högskolan Väst", "KTH", "Region Stockholm",
                     "Statistiska Centralbyrån", "Trafikverket"]:
        assert "company" not in bonus_labels(with_company(employer), profile), employer


def test_preferred_company_bonus(profile):
    assert bonus_labels(with_company("RaySearch Laboratories AB"), profile) == ["company", "preferred company"]
    assert bonus_labels(with_company("AstraZeneca AB"), profile) == ["company", "preferred company"]
    # On my list (from the course PDF) but academic: preferred only.
    assert bonus_labels(with_company("Karolinska Institutet"), profile) == ["preferred company"]


def test_job_after_thesis_bonus_en_and_sv(profile):
    for text in [
        "There is a possibility of future employment after the thesis.",
        "Many of our thesis students get a job offer after the thesis.",
        "Det finns möjlighet till fortsatt anställning.",
        "Goda chanser till anställning efter examensarbetet.",
    ]:
        assert "job after thesis" in bonus_labels(with_company("X AB", text), profile), text
    assert "job after thesis" not in bonus_labels(with_company("X AB", "Full-time employment."), profile)


def test_compensation_bonus(profile):
    for text in ["Compensation according to agreement.", "Ersättning utgår med 30 000 kr.",
                 "A thesis grant of 5 000 SEK is paid on completion.", "Stipendium vid godkänt arbete."]:
        assert "paid" in bonus_labels(with_company("X AB", text), profile), text


def test_bonuses_raise_ranking(profile):
    base = "Develop a machine learning method for patient triage."
    plain = with_company("Umeå Universitet", base)
    plain.url = "https://x.se/plain"
    perks = with_company("RaySearch Laboratories AB",
                         base + " Possibility of employment after the thesis. Compensation is paid.")
    perks.url = "https://x.se/perks"
    ranked = score_listings([plain, perks], profile, embedder=None)
    assert ranked[0] is perks
    assert perks.score - plain.score == 8 + 7 + 12 + 8
