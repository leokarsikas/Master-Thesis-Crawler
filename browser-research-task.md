# Browser task: find master thesis listings the crawler can't reach

You have a real browser (Claude in Chrome or the Claude desktop app's built-in
browser). Please use it to visit the company career pages below, which my automated
crawler couldn't read, and report back in the format at the end.

**Only read pages.** Don't log in, create accounts, apply, or submit any form. If you
get a cookie banner, choose "necessary only" or close it. If a site asks for a
CAPTCHA or a login, skip it and note that.

## Who this is for

Leo Karsikas is an MSc student in **Data-Driven Health at KTH** in Stockholm (2025–2027),
with a BSc in Computer Engineering. He wants a **30-credit master thesis in spring 2027**
(January–May, 20 weeks full time). The project description must be approved by
**15 December 2026**, so he's applying now.

His background:
- AI developer at Saluto (digital health): triage workflows combining an in-house ML
  model with frontier LLMs
- Bachelor thesis on generative AI (AWS Bedrock) in a digital health platform
- Python, Java, SQL, C, React/TypeScript, AWS, Azure; interested in transparent,
  explainable and secure AI

**What his programme accepts** (KTH Data-driven Health guidelines):
- Engineering novelty (developing an ML method, or integrating sensors, models
  and systems), and/or scientific novelty (finding an unknown relationship, unexpected
  effects, new empirical knowledge)
- **Not accepted:** "fit 3–4 models on a dataset and compare them" theses
- Good example: *Learning personalized treatment strategies from longitudinal clinical data*

**Extra-interesting ads:** ones from companies (not universities), ads that mention a
possible **job after the thesis**, and ads that mention **compensation** (ersättning,
stipend, salary or a kr/SEK amount).

## Pages to visit

### A. Sites that failed for the crawler

| Company | URL the crawler tried | What went wrong |
| --- | --- | --- |
| RaySearch Laboratories | https://raysearchlabs.workbuster.com/ | Host not found. Find the real careers page from https://www.raysearchlabs.com/ |
| AstraZeneca (Sweden) | https://www.astrazeneca.com/content/az-se/karriar/early-talent-careers.html | HTTP 403 (blocks bots) |
| AstraZeneca careers | https://careers.astrazeneca.com/students | HTTP 404. Find the job search and search for "thesis" in Sweden (Gothenburg, Södertälje) |
| AFRY | https://careers.smartrecruiters.com/afry | Its API is blocked by robots.txt. Use the job board, filter on "Student Assignments & Thesis Work" or search "thesis" in Sweden |

### B. Sites that loaded but showed 0 thesis listings

These pages may build their listings with JavaScript, the thesis page may be somewhere
else on the site, or there may really be no theses posted. For each one, find the
careers/students/thesis page and check for open thesis or exjobb positions.

| Company | Start here |
| --- | --- |
| Elekta | https://www.elekta.com/careers/ |
| Doctrin | https://www.doctrin.se/ |
| Modulai | https://modulai.teamtailor.com/jobs |
| LUMA Vision | https://luma-vision.hirehive.com/ |
| Devyser Diagnostics | https://devyser.weselect.com/ |
| Karolinska Institutet | https://ki.varbi.com/en/ (also search KI's site for "examensarbete" / "degree project") |
| SciLifeLab | https://www.scilifelab.se/careers/ |
| Knightec | https://knightec.se/en/career/thesis-work/ |
| AFRY thesis projects | https://afry.com/en/thesis-projects |
| AI Sweden thesis program | https://www.ai.se/en/adoption/talent-programs/master-thesis-program |
| Atea Sverige | https://www.atea.se/ |
| Acorai | https://www.acorai.com/ |
| EverySport Group | https://www.everysportgroup.com/ |
| OneTwo Analytics | https://www.onetwoanalytics.com/ |
| SensoDetect | https://www.sensodetect.com/ |
| Saluto | https://www.saluto.se/ |
| KTH MoveAbility Lab | https://www.kth.se/moveabilitylab |

### C. Sites the crawler never reached

| Site | URL |
| --- | --- |
| KTH Degree Project Portal | Start at https://www.kth.se/en/samverkan/exjobb/studenter, follow the link to the portal, and filter on **Degree project** and health, ML, AI or data subjects |
| dittexjobb.se | https://www.dittexjobb.se/hitta-examensarbete-exjobb (search: health, medtech, machine learning, AI, data) |
| Coala Solutions | Its old domain doesn't resolve. Search for the company's current site |
| Digital Diabetes Analytics Sweden | Its old domain doesn't resolve. Search for the company's current site |

## What to report

### 1. Thesis listings found

One row per open thesis/exjobb ad. Skip expired ads, and list everything open, even poor fits.

| Company | Title | Link | Location | Deadline | Fit (1–5) | Job after thesis? | Paid? | Why it fits / doesn't |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

Rate **fit** against the guidelines above. 5 = clear method or integration novelty in
health/medtech with ML/AI, and 1 = unrelated field or a "compare models" thesis. Quote the
ad's own words for "job after thesis" and "paid", or write "not mentioned".

### 2. How each careers site works

This is so the crawler can be fixed. One row per company:

| Company | Real careers / thesis page URL | Platform | Listings in page HTML or loaded by JS? | Job ad URL pattern | Notes |
| --- | --- | --- | --- | --- | --- |

- **Platform:** Teamtailor, Workday, SmartRecruiters, Varbi, HireHive, WeSelect,
  Workbuster, Radancy/TalentBrew, own site, or "no careers page"
- **HTML or JS:** if you can, view the page source (Ctrl+U / Cmd+Option+U) and check
  whether a job title appears in it. If it does, the listings are in the HTML; if not, JS loads them.
- **Job ad URL pattern:** e.g. `/jobs/123456-slug`
- **JSON endpoint:** if you can see a JSON URL the page loads (DevTools → Network → Fetch/XHR),
  put it in Notes. That's the easiest thing for the crawler to read.

### 3. Suggested `config/sources.yaml` entries

For each company you could reach, suggest an entry like:

```yaml
- name: Elekta
  url: https://<real careers url>
  # type: teamtailor | smartrecruiters | generic_html (default)
```

Mark any that need a new adapter (e.g. Workday or JS-only sites) with a comment.
