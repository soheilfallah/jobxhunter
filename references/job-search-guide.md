# Job-search guide — sourcing, connectors & boards (UK-first)

The rest of the skill starts from "here is a job description." This doc covers the step *before*
that: **finding the jobs** — which tools and connectors to use, which UK boards cover which
families, how to search well, and how a found listing flows into the tailoring pipeline. Generic and
profile-agnostic: it works for any candidate; match the search terms to the target family, not to a
person.

## Where sourcing sits

```
SOURCE (this doc)  →  CAPTURE  →  TAILOR  →  RECRUITER LOOP  →  TRACK & FILE
find live JDs          save JD     CV/letter    score/revise      folder + tracker row
```

Every listing you surface — even ones you decide against — should be captured with a status
(`Drafted` or `Skipped`) so the tracker records the whole search, not just the wins.

## Source-effort dial — `full` (default) vs `budget`

How hard to search is a **user choice** about coverage vs cost. Default to `full`; switch to `budget`
when the user asks to "save tokens", "quick hunt", or "just a quick look". Either way, **Firecrawl
captures each survivor's full JD** (never tailor off a snippet).

- **`full` (default) — maximum coverage.** Fan out across **all four job connectors at once**
  (Indeed, Reed, Adzuna, Dice), one search per title variant, dedupe by company+role, **then** run the
  deep-crawl net (`WebSearch` → **Firecrawl**) so niche/company-careers roles aren't missed. Nothing is
  skipped for cost. This is the behaviour the rest of this doc describes.
- **`budget` — tiered with early-stop.** Search in cost order and **stop climbing once you have enough**
  good live matches for the family (rough target: ~8–10 solid, un-knocked-out hits; the user can set
  their own number). Cap the title-variants and boards per tier.
  1. **Tier 1 — claude.ai job connectors:** **Indeed** + **Dice** (Dice only for AI/data families).
     These are already on and cheap to query.
  2. **Tier 2 — MCP job servers:** **Reed** + **Adzuna** (`gb`). Add these when Tier 1 is thin or you
     want salary context.
  3. **Tier 3 — web-search net:** `WebSearch` → **Firecrawl** deep-crawl for boards/companies no
     connector covers — run this last, as the completeness net, only if the earlier tiers came up short
     for a family. Skipping it is the main saving.

Record which mode ran in the run summary so a later, fuller pass knows what wasn't covered. In `budget`
mode, if a tier is skipped for cost, **say so** — don't imply the search was exhaustive.

## Connectors available in this environment

Use these first; they return structured data you can act on directly. **Fan out across all four job
connectors** for every search — each indexes different roles — then dedupe hits by company+role.

> **Tool-name convention (both surfaces).** Tool names below are written bare (`reed_search_jobs`).
> Resolve each to your surface's prefix: **Claude Code** uses `mcp__<server>__<tool>` (e.g.
> `mcp__reed__reed_search_jobs`, `mcp__claude_ai_Indeed__search_jobs`); **Claude Desktop / cowork**
> uses `<server>:<tool>` (e.g. `reed:reed_search_jobs`, `Indeed:search_jobs`). Server names:
> `Indeed`, `reed`, `adzuna`, `Dice`, `firecrawl`. If a name doesn't resolve, list available tools
> and match by the `<server>` + `<tool>` pair.

- **Indeed** (`Indeed` connector) — the broad UK workhorse. Verified working.
  - `search_jobs(search, location, country_code='GB', job_type?)` — list live UK roles. Keep the
    returned apply URLs intact.
  - `get_job_details(job_id)` — full JD text (requirements, knockouts, salary). This is the CAPTURE
    source: feed its text straight into `new_application.py --jd-file`.
  - `get_company_data(companyName, location{country:'GB'}, ...)` — employee reviews, ratings,
    salary bands. Use to vet an employer and to infer a salary band the JD omits.
  - `get_resume()` — reads any resume the user has on Indeed; a shortcut to seed a profile.
- **Reed** (`reed` connector) — Reed.co.uk, a top UK aggregator. Strong on security, data, admin and
  agency roles. Verified working (2026-07-17).
  - `reed_search_jobs(params={"keywords": …, "location_name": …, "distance_from_location": …,
    "results_to_take": …})` — live UK roles. **Distance is in MILES** (not km); default 10. Returns
    only a SHORT description.
  - `reed_get_job_details(params={"job_id": …})` — full JD text **plus** normalised yearly salary,
    salary type, contract type and the external apply URL. This is the Reed CAPTURE source — always
    call it before tailoring. Salary can be hidden by the employer; an absent salary is "Not
    disclosed", never £0.
- **Adzuna** (`adzuna` connector) — wide UK aggregator + labour-market data. Verified working.
  - `adzuna_search_jobs(params={"what": …, "where": …, "country": "gb", "results_per_page": …})` —
    live roles; returns only a SNIPPET of each JD. For the full text, fetch the result's
    `redirect_url` (via Firecrawl/WebFetch).

> **CALLING CONVENTION — Reed and Adzuna only.** Both wrap every argument in a single `params`
> object and use `snake_case`. Flat args fail with `Field required [params]`; camelCase fails with
> `Extra inputs are not permitted`. Neither error is recoverable by retrying the same shape, and
> each wasted call is a wasted round trip. **Indeed and Dice are the opposite** — flat top-level
> arguments, no wrapper. (Confirmed live 2026-08-03.)
  - Labour-market context to fill a salary band the JD omits: `adzuna_salary_histogram`,
    `adzuna_salary_history`, `adzuna_regional_breakdown`, `adzuna_top_companies`. All salaries are
    ANNUAL, GBP for `gb`.
- **Dice** (`Dice` connector, `search_jobs`) — tech/IT roles, **US-centric** (weak UK coverage).
  Worth a pass for the AI/data families only; note its useful filters: `workplace_types=['Remote']`,
  `willing_to_sponsor=true`, `posted_date`. Don't rely on it for UK plant-science/research/security.
- **Adjacent tools that help the search:**
  - **Clay** (`find-and-enrich-contacts-at-company`) — find the hiring manager / team lead at a
    target employer for a speculative or follow-up approach.
  - **Gmail** (`search_threads`, `create_draft`) — track recruiter replies and draft outreach.
  - **Google Calendar** (`create_event`) — book interviews the moment they're offered.
  - **Claude-in-Chrome** (browser automation) — drive ANY board that has no connector (LinkedIn,
    jobs.ac.uk, Reed, NHS Jobs, institute career pages). Load the browser tools, search the site,
    read the JD, and capture it into the pipeline. Use this for the specialist boards below.

**AI-disclosure note:** when presenting connector results to the user, include a short line that the
listings were retrieved via AI-powered search and details should be verified with the employer.

## Deep search without a connector (crawl the web)

When the connectors don't cover a role — a niche board, an institute careers page, a company's own
vacancies, a role that never hits the aggregators — or when a connector returns only a snippet and
you need the full JD, fall back to a **crawl-then-distil** stack. **Firecrawl is now connected**
(the `firecrawl` connector) and is the preferred crawler:

1. **`WebSearch`** — cast wide: `"<title variant>" <location> job site:jobs.ac.uk`, or
   `"<company>" careers <role>`, or `"<niche skill>" vacancy UK`. Get candidate URLs.
2. **Firecrawl** (`firecrawl` connector) — the primary crawler; returns clean markdown at scale and
   renders JS, so it handles most modern careers sites and ATS pages that `WebFetch` can't:
   - `firecrawl_scrape(url)` — one page → clean markdown. Use to pull the full JD from an Indeed
     apply URL, an Adzuna `redirect_url`, a Greenhouse/Workday/Lever posting, or a PDF.
   - `firecrawl_extract(urls, schema/prompt)` — pull structured JD fields (title, requirements,
     salary, location) straight into the pipeline.
   - `firecrawl_crawl(url)` / `firecrawl_map(url)` — multi-page crawl of a whole careers site to
     enumerate its live vacancies before scraping each.
   - `firecrawl_search(query)` — web search with the results scraped in one call.
3. **`WebFetch` or the `/scrape` skill** — lightweight single-page fallback when Firecrawl isn't
   connected on this surface. `/scrape` (installed here) pulls one page's content; `WebFetch` suits
   simple static pages/PDFs. Use either to grab a JD you already have the URL for.
4. **`Claude-in-Chrome`** (browser automation) — last resort for login-gated flows Firecrawl can't
   reach (LinkedIn search behind auth, portals needing a signed-in session): navigate, run the
   search, read the results, open each JD, capture the text.

The method is identical regardless of which crawler backs it: **crawl → extract → distil the JD →
capture**.

Treat raw crawl output as noisy: extract only the JD/vacancy content, discard nav/boilerplate, then
run it through the same triage (`jd-analysis.md` §0) and CAPTURE step as any connector result.

## Canada boards & connectors (market = `ca`)

For a Canadian profile, swap the UK boards for these and use `ca-conventions.md`. **You don't need a
new connector — Canada works out of the box:**

**Connectors (already integrable — bring your own key):**
- **Adzuna** with `country='ca'` — the tool's Adzuna connector already supports Canada (CAD salaries,
  same tools). This is the primary structured source for `ca`. *(A public community MCP also exists:
  `folathecoder/adzuna-job-search-mcp`, 12 countries.)*
- **Indeed** — Indeed.ca is Canada's #1 board by reach; use the Indeed connector with `country_code='CA'`.
  Indeed also publishes an official MCP (`docs.indeed.com/mcp`).
- **Firecrawl** — for any board without a connector (Job Bank, University Affairs, company careers).
- **Reed is UK-only — skip it for `ca`.**

**Optional add-on sources (integrable without building from scratch, if you want more Canada coverage):**
- **Government of Canada Job Bank** (jobbank.gc.ca) — free, national, bilingual, immigrant-friendly.
  No live per-query REST key, but its data is on the **Open Government CKAN API** (free; monthly
  CSV/JSON/XML datasets) plus a beta Labour-Market-Information API and XML job feeds. Good for bulk/
  cross-check; crawl individual postings with Firecrawl for live search.
- **JobSpy MCP** (`borgius/jobspy-mcp-server`) — free multi-board scraper MCP covering Indeed, LinkedIn,
  Glassdoor, ZipRecruiter, Google Jobs — gives broad Canadian coverage in one server.
- **Free no-key job APIs** (mostly remote/global): **Jobicy** (`jobicy.com/api/v2/remote-jobs`, no auth,
  salary data), **Arbeitnow** (no auth, ATS jobs), **Careerjet** / **Jooble** (public search APIs).

**Canadian boards by lane** (search via Indeed/Firecrawl):
| Lane | Primary | Specialist / highest-signal |
|---|---|---|
| general | **Indeed.ca**, **LinkedIn**, **Job Bank**, Glassdoor | **Eluta** (quality-listing aggregator) |
| academic / research | Job Bank, LinkedIn | **University Affairs** (universityaffairs.ca), **CAUT**, individual university career portals |
| healthcare | Job Bank, Indeed | provincial health-authority sites; HealthForceOntario etc. |
| tech / AI / data | LinkedIn, Indeed | **ITJobs.ca**, **MaRS**, company careers pages |
| students / grads / early-career | Indeed, Job Bank | **TalentEgg** |

Note bilingual/federal & Quebec roles often need French (see `ca-conventions.md`).

## UK boards by job family

No single board covers everything. Map the family to its real home:

| Family | Primary boards | Specialist / highest-signal |
|---|---|---|
| **plant-science-research** | Indeed, LinkedIn | **jobs.ac.uk** (academic/research — the main one); institute pages: **NIAB, John Innes Centre, Rothamsted, James Hutton, RHS**; **New Scientist Jobs**; agrirecruit / agricultural-specific agencies |
| **research-assistant-lead** | Indeed, LinkedIn | **jobs.ac.uk** (universities); **NHS Jobs** (jobs.nhs.uk) + **NIHR** for clinical research; **Find a PhD / Find a Job** university portals; **Guardian Jobs** (charity/research) |
| **ai-technician-junior-ai** | LinkedIn, Indeed | **Otta / Welcome to the Jungle** (startups), **Wellfound** (AngelList), **Dice** (US-tech), company careers pages, **Hacker News "Who is hiring"** |
| **data-research-analysis** | LinkedIn, Indeed | **Otta**, **Reed**, **CV-Library**, **Totaljobs**; sector-specific (media/bank) careers pages |
| **security-frontline** | Indeed, **Reed**, **Totaljobs** | **SecurityJobs.co.uk / security-specific boards**; local SIA-licensing agency listings; company sites (Bidvest Noonan, Securitas, G4S) |

General UK aggregators worth a sweep for any family: **Indeed, LinkedIn, Reed, Totaljobs,
CV-Library, Glassdoor, Google Jobs, Adzuna**. Set up **email alerts / saved searches** on the two or
three that matter for the target family so new roles arrive without re-searching.

## Search strategy

1. **Pull search terms from the taxonomy.** Use the family's `TITLE VARIANTS` (in
   `references/keyword-taxonomy/<family>.md`) as your search keywords — e.g. for research-data, run
   "data analyst", "insight analyst", "research analyst" as separate searches, not one broad query.
2. **Search each title variant separately** — boards rank on title match, so one query per variant
   surfaces different roles.
3. **Filter for fit early:**
   - Location / remote / hybrid (match the candidate's constraints).
   - **Right-to-work / sponsorship** — the single biggest time-saver. On Dice use
     `willing_to_sponsor=true` when sponsorship is needed; on Indeed/LinkedIn filter by
     visa-friendly employers and read the JD's right-to-work line before investing.
   - Recency (`posted_date` — last 3–7 days) to avoid stale/filled roles.
   - Salary band where the board supports it.
4. **Triage before tailoring.** For each hit, do a fast knockout check (`jd-analysis.md` Section 0):
   right-to-work, licence (SIA), degree-field, years, immediate-start. If it fails a hard knockout,
   log it `Skipped` with the reason and move on — don't tailor a dead application.
5. **Vet the employer** with `get_company_data` (ratings, reviews, real salary bands) before
   spending effort — especially for agency-posted roles, which are often duplicated or thin.
6. **Capture the survivors** (below).

## From a found listing into the pipeline

Once a role passes triage:

1. Get the full JD text — never tailor off a search snippet: `get_job_details` (Indeed),
   `reed_get_job_details` (Reed), fetch the `redirect_url` (Adzuna), or crawl the apply/JD URL with
   **Firecrawl** (`firecrawl_scrape`/`firecrawl_extract`) for any other board, ATS or PDF.
2. Create the job folder + tracker row:
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/new_application.py" --root <apps> --category <family> --company "<Co>" \
       --role "<Role>" --date <YYYY-MM-DD> --jd-file <captured-jd.txt> \
       --link "<apply-url>" --source <Indeed|LinkedIn|jobs.ac.uk|…> --pay "<band>" \
       [--status Skipped]   # if triaged out but worth recording
   ```
3. Run TAILOR → RECRUITER LOOP → render into that folder (see `SKILL.md`).
4. On applying, flip the row to `Applied` (green + locked) via `tracker.py update`.

## Beyond boards — the higher-yield channels

Job boards are the floor, not the ceiling. For the research and AI families especially:

- **Speculative / direct:** email a target lab or team lead (find them with Clay or the institute
  page) with a tailored CV + short note. jobs.ac.uk roles often have a named "informal enquiries"
  contact — use it.
- **Referrals / network:** a LinkedIn message to someone in the team beats a cold portal
  application. Keep the CV tailored to the specific team.
- **Set alerts** on jobs.ac.uk, NHS Jobs, and the two general aggregators for the target family, and
  review them on a weekly cadence rather than re-searching from scratch.

## Weekly cadence (suggested)

- **Search** the family's title variants across its primary + specialist boards; skim alerts.
- **Triage** to a shortlist (knockout + employer vet); log everything (Drafted/Skipped).
- **Tailor + apply** to the shortlist; run the recruiter loop on each.
- **Follow up** on last week's applications; update tracker statuses (Interview/Rejected/Offer).

## Sources / connectors referenced
- Job connectors (server names): `Indeed`, `reed`, `adzuna`, `Dice`. Crawl fallback: `firecrawl`
  (added 2026-07-17), WebSearch/WebFetch, Claude-in-Chrome. Adjacent: Clay,
  Gmail, Google Calendar. Reed + Adzuna + Firecrawl connected 2026-07-17; the rest as of 2026-07-06.
- UK board landscape: jobs.ac.uk, NHS Jobs (jobs.nhs.uk), NIHR, Reed, Totaljobs, CV-Library, Otta,
  Wellfound, Glassdoor, Adzuna; institute career pages (NIAB, JIC, Rothamsted, James Hutton, RHS).
