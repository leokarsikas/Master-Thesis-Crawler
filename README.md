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

## Run it automatically (GitHub Actions + Pages)

`.github/workflows/crawl.yml` runs the crawler every day at 05:17 UTC and
publishes the report to GitHub Pages at
`https://<your-username>.github.io/Master-Thesis-Crawler/`. The CSV is at
`listings.csv` on the same site.

One-time setup:

1. **Settings → Pages → Build and deployment → Source:** choose "GitHub Actions".
2. **Actions → Crawl and publish report → Run workflow** to start the first run
   instead of waiting for the schedule. Untick "embeddings" for a faster keyword-only run.

To test a few sources without touching the public report, run the workflow with
**only** set to comma-separated source names (e.g. `RaySearch Laboratories, AFRY`)
and **deploy** unticked.

To change the time, edit the `cron` line in the workflow (it's in UTC).
The listing history (`data/listings.db`) is kept in the Actions cache between
runs, so the NEW badges work. If the cache is evicted, the next run marks every
listing as new once.

**Cost.** Public repos get unlimited Actions minutes on standard runners. A
private repo uses your monthly allowance: GitHub Pro (free with the Student
Developer Pack) includes 3,000 minutes. A run takes about 3–10 minutes
(installing PyTorch plus crawling about 20 sites with a 1 s delay per host),
which comes to roughly 100–300 minutes a month.
The site published by Pages is **public** even from a private repo on Pro.
It only contains the ranked listings, not your CV.

## Tuning

- **`config/profile.yaml`** is what "a good fit" means. `profile_text` is used
  for embedding similarity. The `keywords` groups each have a weight, and the
  `penalties` group has negative weights for things the guidelines warn against
  (comparing algorithms) and fields that don't fit (mechanical, finance, ...).
  Terms can be phrases, `prefix*` or `/regex/`. The report lists the matched
  terms for each listing, so you can see why it scored the way it did.
- **`bonuses`** in `config/profile.yaml` add flat points on top of the 0–100 score
  and appear as chips in the report:

  | bonus | points | when |
  | --- | --- | --- |
  | company | +8 | the employer isn't a university, research institute or public body |
  | preferred company | +7 | the employer is on my list (course PDF companies, RaySearch, AstraZeneca, Saluto) |
  | job after thesis | +12 | the ad mentions possible employment after the thesis (EN/SV) |
  | paid | +8 | the ad mentions compensation, a stipend, salary or an amount in kr/SEK |

- **`config/sources.yaml`** lists where to look. To add a company, add
  `- {name: Foo, url: https://foo.se/careers}`. The `generic_html` crawler starts
  there, follows links that look thesis related (thesis, exjobb, students, degree
  project), and crawls hub pages such as "Thesis opportunities" one level deeper.
  If the site runs on Teamtailor, use `type: teamtailor` instead; for SmartRecruiters
  (e.g. AFRY), use `type: smartrecruiters` with `company_id`.

> Check **Sources that failed** at the bottom of the report now and then: companies
> move their careers pages. Point a failing entry at the new page or set
> `enabled: false`.

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
