# Master Thesis Crawler

Finds master thesis / exjobb listings and ranks them against my profile
(MSc Data-driven Health, KTH) and the programme's thesis guidelines: engineering
novelty (new ML methods, integrating sensors/models/systems) or scientific novelty,
**not** "compare 4 models on a dataset".

It crawls:

- **Company career pages**: the companies from the Data-driven Health kick-off
  (Elekta, RaySearch, Doctrin, SciLifeLab, AI Sweden, Modulai, ...) plus Saluto
- **KTH Degree Project Portal**
- **Job boards**: Platsbanken (JobTech API) and dittexjobb.se

Each listing gets a 0–100 score from weighted keywords plus (optionally) local
sentence-embedding similarity to a profile text. You get a ranked CSV and an HTML
report, and listings that are new since the last run are flagged.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
```

```bash
pip install -e ".[embeddings,dev]"
```

`embeddings` pulls in `sentence-transformers` (and PyTorch) so it can compute
similarity locally. No API key is needed. Leave it out (`pip install -e ".[dev]"`)
for keyword-only scoring.

## Run

```bash
thesis-crawler run
```

The command writes `out/report.html` and `out/listings.csv` and prints the top matches.
Useful flags:

| flag | what it does |
| --- | --- |
| `--only Doctrin Platsbanken` | run only some sources (names from `config/sources.yaml`) |
| `--no-embeddings` | keyword scoring only (fast, no model download) |
| `--min-score 30` | drop weak matches from the report |
| `--no-cache` | refetch pages (default: cached for 6 h in `cache/`) |
| `-v` | debug logging (shows skipped pages) |

To try it without network, run it on the bundled fixtures:

```bash
thesis-crawler run --sources tests/fixtures/sources.yaml --no-embeddings
```

Run it again every few days. `data/listings.db` remembers what you've seen, so
the **NEW** badge and the "Only new" filter show what appeared since the last run.

## Tuning

- **`config/profile.yaml`** is what "a good fit" means. `profile_text` is used
  for embedding similarity. The `keywords` groups each have a weight, and the
  `penalties` group has negative weights for things the guidelines warn against
  (comparing algorithms) and fields that don't fit (mechanical, finance, ...).
  Terms can be phrases, `prefix*` or `/regex/`. The report lists the matched
  terms for each listing, so you can see why it scored the way it did.
- **`config/sources.yaml`** lists where to look. To add a company, add
  `- {name: Foo, url: https://foo.se/careers}`. The `generic_html` crawler starts
  there, follows links that look thesis related (thesis, exjobb, students, degree
  project), and crawls hub pages such as "Thesis opportunities" one level deeper.
  If the site runs on Teamtailor, use `type: teamtailor` instead.

> The company URLs in `sources.yaml` are best guesses: they were written without
> a live connection. After the first run, look at **Sources that failed** at the
> bottom of the report, then point those entries at the company's real
> careers/students page or set `enabled: false`.

## How it works

```
sources/*.py  ->  filter.is_thesis  ->  dedupe  ->  scoring  ->  store (SQLite)  ->  report
```

- `fetch.py`: httpx client with a polite user agent, robots.txt checks, a delay
  per host, retries and an on-disk cache. It also reads `file://` URLs, which
  the fixtures use.
- `sources/`: one adapter per kind of site. Each adapter returns `Listing` objects.
  A source that fails is logged and skipped, and the rest of the run continues.
- `scoring.py`: total = `keyword_weight` × keyword score + the rest × embedding
  score. Without embeddings, total = keyword score.

## Tests

```bash
pytest
```
