# Job-search guide: where the adverts are

`references/search.md` is the method. This file is the map: which boards carry which kinds of role
in each market, and how to reach a board that has no connector. It is generic; the search terms come
from the user's own `master-cvs/TARGETS.md`, never from this file.

## The sources, by how they are reached

| Reached by | Sources | Full advert text |
|---|---|---|
| a connector with its own detail tool | Indeed, Reed (UK) | yes, from the detail tool |
| a connector that returns snippets | Adzuna (UK and Canada) | fetch the result's `redirect_url` |
| search and a page reader | every other board and every employer's own site | Firecrawl, then a plain fetch |
| a signed-in browser | LinkedIn and other login-walled boards | read in the browser, last resort |

Tool names and argument shapes: `references/tools-and-connectors.md`.

When showing results that came from a connector, add one line saying the listings were retrieved by
AI-powered search and details should be checked with the employer.

## Reaching a board with no connector

1. **Search for the listing pages.** `"<title>" <location> site:<board>`, or
   `"<employer>" careers <title>`, one query per title.
2. **Read the page.** A page reader that renders JavaScript (Firecrawl) handles most modern career
   sites and applicant-tracking pages. A plain fetch is enough for static pages and PDFs.
3. **Walk a whole careers site** when an employer is a target: map or crawl it to list the live
   vacancies, then read each one. Employers on the common applicant-tracking systems publish an open
   feed; `references/search.md` lists them.
4. **Signed-in browser** only for flows nothing else reaches.

Treat crawled pages as noisy. Keep the advert text, drop navigation and boilerplate.

## UK boards by kind of role

No single board covers everything. General aggregators worth a sweep for any role: **Indeed,
LinkedIn, Reed, Totaljobs, CV-Library, Adzuna, Google Jobs**.

| Kind of role | Where it is really advertised |
|---|---|
| academic and research | **jobs.ac.uk** (the main one), university vacancy portals, research-institute career pages, New Scientist Jobs |
| health and clinical research | **NHS Jobs** (jobs.nhs.uk), NIHR, trust career sites |
| public sector | **Civil Service Jobs**, local-authority sites, gov.uk Find a Job |
| charity and non-profit | **CharityJob**, Guardian Jobs |
| software, data and AI | LinkedIn, **Otta / Welcome to the Jungle**, Wellfound, employer career pages, Dice for remote US-leaning roles |
| admin, office, PA and EA | Reed, Totaljobs, CV-Library, specialist agencies |
| security, facilities and front of house | Reed, Totaljobs, Indeed, the large contractors' own sites |
| trades, technical and field roles | Indeed, CV-Library, Totaljobs, sector agencies |

Civil Service Jobs and some trust sites serve a bot check to automated readers. When a source cannot
be read, report it as failed and give the user the search link to open themselves.

## Canada boards (market `ca`)

Adzuna with `country: "ca"` and Indeed with `country_code: "CA"` both work unchanged. Reed is UK
only: skip it.

| Kind of role | Where it is really advertised |
|---|---|
| general | **Indeed.ca**, LinkedIn, **Job Bank** (jobbank.gc.ca), Glassdoor, Eluta |
| academic and research | **University Affairs**, CAUT, university career portals |
| health | provincial health-authority sites, Job Bank |
| software, data and AI | LinkedIn, ITJobs.ca, employer career pages |
| students and early career | TalentEgg, Job Bank |

Federal and Quebec roles often need French: `references/ca-conventions.md`.

## Choosing search titles

Boards rank on title match, so one query per title finds different roles. `TARGETS.md` holds four
lists per role and a scout runs all of them:

- **Core titles**: the role by its usual name.
- **Aim up**: the next level, which the candidate may be closer to than they think.
- **Same work, different name**: what other sectors call the same job. This list is where most of
  the missed adverts are.
- **Title knockouts**: titles that look similar and are a different job.

When a search returns little, the title lists are too narrow before the market is too thin. Ask
what the same work is called in the public sector, in agencies, in start-ups, and add those.

## Beyond the boards

- **Direct approach.** A short note to the person who owns the work, with the master CV attached.
  Academic adverts often name an "informal enquiries" contact: use it. See
  `references/company-discovery-cold-outreach.md`.
- **Referral.** A message to someone on the team beats a cold portal application.
- **Alerts.** Saved searches on the two or three boards that matter for the role, so new adverts
  arrive between searches.
