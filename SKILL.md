---
name: job-hunt
description: >-
  UK-first job-hunt skill. Core is CV tailoring: read a master profile plus a job description
  and produce an ATS-friendly, slop-free CV that survives both the ATS parser and the
  six-second recruiter scan. Also finds and deep-crawls roles (Indeed/Reed/Adzuna/Dice connectors,
  with a Firecrawl/WebSearch crawl fallback), discovers target companies and cold-emails the right
  contact, writes cover letters and cold emails from the user's own spoken words, runs a
  recruiter-persona scoring loop, generates an "alternative world" ideal-candidate CV plus the
  gap-to-close, and tracks every application (applied rows locked). The master profile is a
  decoupled data feed — swap the path for any profile; skill logic never changes. Use whenever the
  user wants to find, search, or crawl for jobs, tailor a CV or résumé, write a cover letter or cold
  email, find companies to cold-email, score a CV against a job description, see the ideal candidate
  for a role, or track job applications.
---

# job-hunt — the UK-first job-hunt skill (CV tailoring at its core)

CV tailoring at the core; cover letters, a recruiter loop, an alternative-world mode, and
application tracking around it. UK-first, with Canada built in (market-driven — see below). Works in
chat and in Claude Code.

## The one rule everything hangs on

**The master profile is the only source of truth for any submittable document.** The skill
*selects, reframes, reorders, and emphasises* — it never invents a fact. If evidence for a JD
requirement isn't in the profile, that's a **gap to surface, not a blank to fill**. Only the L2
alternative-world persona may generate beyond the profile, and it is never submittable. Hold this
line in every command below.

## Inputs

- **Profile** (the data feed): a markdown file conforming to `references/master-profile-schema.md`.
  A demo fixture ships at `assets/sample-profile.md` (a sample persona). For real use, point at your
  own profile (e.g. a private file under `career/job-hunt/profiles/`). Point at any conforming file to
  tailor for anyone — skill logic is identical regardless of whose profile it is.
- **Job description**: pasted text, a file, or an Indeed/URL the skill captures.
- **Level** (CV only): `L0` / `L1` (default) / `L2`, with an optional `%` knob within L1. See
  `references/tailoring-levels.md`.
- **Workspace** (the unit of state — path-agnostic, never hard-coded): a directory holding
  `profiles/` + `applications/`. Resolve it once per run: **explicit path → `JOBHUNT_DIR` env →
  discovery → none ⇒ Setup mode** (`python "${CLAUDE_PLUGIN_ROOT}/scripts/_lib.py" resolve`). All paths derive from it. Full
  contract + Setup/Daily-run: `references/daily-hunt.md`.

## Two ways to run

- **On-demand (classic):** the user hands over one JD → run TAILOR (+ recruiter loop, cover letter).
- **Autonomous daily hunt:** point the skill at a workspace → it sources, triages, tailors every new
  live match, files everything, and writes a dated summary. If no workspace resolves, it **scaffolds**
  one and stops for the user to fill their profile. See `references/daily-hunt.md` (SETUP + DAILY RUN).

## Market (which country's path) — read from the profile, not hard-coded

The profile's **market** field (`## Career targets & market` — `uk` / `ca` / …) is the switch that
selects three things; resolve it once per run (if unset, infer from `location` + work authorisation and
confirm with the user):
- **CV conventions:** `uk` → `references/uk-conventions.md`; `ca` → `references/ca-conventions.md`
  (résumé not CV, US-Letter, Canadian spelling, YYYY-MM-DD, French-as-asset, PR/work-permit phrasing).
- **Job boards & sourcing lanes:** see `references/job-search-guide.md` (UK boards vs Canada boards).
- **Connectors:** `uk` → Reed + Adzuna(`gb`) + Indeed; `ca` → **Adzuna(`ca`) + Indeed(`CA`)** (Reed is
  UK-only, skip it for `ca`) + Firecrawl for everything else. All optional; missing ones fall back.
The skill is UK-first only in its defaults — the logic is market-driven, so adding a market = add a
conventions doc + a board list + a connector map, nothing in the engine changes.

## Reference map (progressive disclosure — load only what the step needs)

| When you're… | Read |
|---|---|
| decomposing a JD | `references/jd-analysis.md` |
| matching keywords for a family | `references/keyword-taxonomy/<family>.md` |
| writing bullets, summary, sections | `references/cv-craft.md` |
| framing a non-linear / career-change story | `references/career-narrative.md` |
| enforcing voice + register (the writing model) | `references/writing-voice.md` (the self-contained de-slop + register standard) |
| de-slopping / choosing verbs | `references/cv-mistakes.md` (the CV-specific mistake + banned-buzzword catalogue) |
| ensuring the render parses | `references/ats-mechanics.md` |
| applying market CV norms | pick by the profile's **market**: `references/uk-conventions.md` (`uk`) · `references/ca-conventions.md` (`ca`) |
| building a profile from a user's dump folder (first run) | `references/profile-intake.md` |
| scoring as the recruiter | `references/recruiter-rubric.md` |
| choosing/operating the dial | `references/tailoring-levels.md` |
| reading the profile | `references/master-profile-schema.md` |
| writing a cover letter | `references/cover-letter.md` |
| finding jobs to apply to (sourcing) | `references/job-search-guide.md` |
| finding target companies + cold-emailing them | `references/company-discovery-cold-outreach.md` |
| running the autonomous daily hunt / scaffolding a workspace | `references/daily-hunt.md` |
| which tool/connector/skill to use (the manifest) | `references/tools-and-connectors.md` |
| onboarding a new user's connectors + API keys | `references/connector-setup.md` |

Keyword families: `plant-science-research`, `research-assistant-lead`, `ai-technician-junior-ai`,
`data-research-analysis`, `security-frontline`. Pick the closest; if none fit, decompose the JD
directly with `jd-analysis.md` and note the taxonomy gap.

## Tools & external skills (surface-aware routing)

The skill leans on other skills/tools for prose voice, rendering, and JD capture. **Detect what this
surface exposes** (list your skills/tools if unsure) and route accordingly — every route has a
self-sufficient fallback, so the skill never hard-depends on an optional tool.

- **Prose voice (the de-slop pass).** `references/writing-voice.md` is the skill's own **writing model** —
  a register-aware (CV / cover letter / cold email) standard for stripping AI tells and hitting the right
  formality. It's fully self-contained: the agent applies it **inline** on every final draft, together with
  the `cv-mistakes.md` banned-buzzword catalogue. No external tools or plugins required — never ship prose
  that hasn't been through it.
- **Rendering the CV / cover letter.**
  - **cowork / Claude Desktop:** the native `docx`, `pdf`, and `xlsx` file-creation skills produce the
    CV `.docx`, an optional recruiter-facing `.pdf`, and the `tracker.xlsx`. Hold the ATS rules
    regardless of renderer (no tables/columns/text-boxes/graphics — `references/ats-mechanics.md`).
  - **Claude Code:** the bundled `scripts/` are the default and self-sufficient (`render_docx.py` →
    ATS-safe `.docx` + `.txt`; `tracker.py` → `tracker.xlsx`).
  - **Polished PDF (either surface):** `render_docx.py`/the `docx` skill do NOT emit PDF. For a
    human-facing / portfolio PDF, route the CV markdown through the installed **`/make-pdf`** skill.
    Use it only for the human copy — **submit the `.docx` to ATS**, never a make-pdf PDF (it isn't
    guaranteed ATS-parseable). Use PDF for direct-to-human sends or when a JD explicitly asks for PDF.
- **JD capture fallback.** SOURCE prefers the job connectors + Firecrawl. Where Firecrawl isn't
  connected on this surface, the installed **`/scrape`** skill is an alternative single-page JD puller
  before dropping to WebFetch/Claude-in-Chrome.

---

## Command: INTAKE (build the profile from a dump folder — the true first run)

The easiest on-ramp for a new user, ideal in **cowork**: instead of filling a blank template, the user
**dumps everything they have about themselves** into `<workspace>/dump/` — old CVs/résumés, a LinkedIn
PDF export, cover letters, certificates, transcripts, brag docs, freeform notes, even job ads they
liked — and the skill reads it all and **builds the master profile** for them. Then it detects the
market and hands off. Full method: `references/profile-intake.md`.

1. Ensure the workspace + `dump/` exist (SETUP/`init_workspace.py` creates `dump/` with a README).
2. **Scan the dump first — `python "${CLAUDE_PLUGIN_ROOT}/scripts/dump_manifest.py" scan --workspace <root>`.** This writes
   `dump/_manifest.csv` and tells you exactly what to read: **new/updated** text files to ingest,
   **unreadable** files (Word/PDF/image/binary) for which it auto-creates an empty **placeholder stub**
   under `profiles/_intake/placeholders/` so nothing is lost, and **ingested** files to skip. This is
   what makes a re-run incremental — only genuinely new material is processed.
3. **Read every actionable file** — in cowork the agent can read PDFs, DOCX, images, and text (PDFs and
   images also read in Claude Code). Extract real facts only (roles, dates, skills, education, licences,
   numbers, outputs, contact, location, work authorisation). As each file's facts land in the profile,
   record it: `dump_manifest.py mark --path "<rel>" --status ingested`, delete its placeholder, and log
   the delta to `profiles/_intake/CHANGELOG.md`.
4. **Synthesise / enrich the master profile** into `profiles/<name>.md` per
   `references/master-profile-schema.md` — a WAREHOUSE, not a CV. First run creates it; later runs
   **merge** (keep prior confirmations + the "never claim" list). Never invent; where the dump is
   silent, leave a gap and ask.
5. **Run the profile enrichment interview** (`references/profile-intake.md`) — ask targeted starter
   questions wherever a bullet is unquantified, a skill has no project behind it, a date is ambiguous,
   or a target is unset, and write answers straight into the profile. This kills vague statements at the
   source, so every downstream CV/cover letter stays concrete. Ask in small neutral memory-jog batches.
6. **Detect the market** (`## Career targets & market`) from location + work authorisation + target
   geography, and set it (`uk`/`ca`/…). This is what later picks the conventions/boards/connectors.
7. **Surface gaps and conflicts** for the user to confirm (missing dates, the "never claim" list,
   still-unreadable dump files, confidential-hold items) — one neutral batch, never an accusation.
8. Hand off to DAILY HUNT (or TAILOR) using the market path chosen in step 6.

Truth rule applies throughout: the profile may only contain what the dump (and the user's confirmations)
actually support.

## Command: SETUP (scaffold a workspace — first run / new user)

When no workspace resolves (no path, no `JOBHUNT_DIR`, discovery finds nothing), the user is new.
**Scaffold and stop** — do not hunt against an empty profile:
```
python "${CLAUDE_PLUGIN_ROOT}/scripts/init_workspace.py" --workspace <dir> [--name <who>]
```
This builds the workspace contract (`profiles/` + `profiles/_intake/`, `dump/` with its `_manifest.csv`,
`applications/`, `daily-hunt/`, `scripts/`), drops a rich **profile template** (a warehouse, not a CV) +
a starter `_RUN-PLAYBOOK.md` + empty dedupe ledger, generates a **`WORKSPACE-MAP.md`** documenting every
folder/tracker + the Word/PDF output contract, copies the scripts in, runs `tracker.py init`, then stops
for the user to fill the profile (or run INTAKE against `dump/`). It runs a dependency **preflight**
first (openpyxl + python-docx) so the tracker can never half-commit. Full detail: `references/daily-hunt.md`.

**Then onboard the connectors (bring-your-own-keys).** A new user has the skill but not the MCP
connectors. Run the doctor and guide them — never assume the connectors exist:
```
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_connectors.py"          # what's configured vs missing + how to add each
```
For each connector the user wants, point them to the free key (Firecrawl / Reed / Adzuna), then — once
they hand over a key — **offer to register it for them**: read their Claude config, back it up, merge
the `--emit`ted snippet under `mcpServers` with their real key, and tell them to restart. Every
connector is optional; missing ones fall back to WebSearch/browser. Full walkthrough:
`references/connector-setup.md`.

## Command: DAILY HUNT (autonomous run — populated workspace)

The repeatable daily hunt. Read `references/daily-hunt.md` and follow it: read the playbook → read the
profile fresh → concurrency lock + rebuild ledger → **source** the priority families (live connectors,
LIVE-only, new-since-last-run) → knockout sweep → **tailor every new live match (no cap)** → prep
cover-letter scaffolds and flag braindumps → **track & file** every job (Drafted/Skipped with reason +
link) → rebuild ledger + regenerate the priority view → write a dated `daily-hunt/<DATE>-summary.md`
(same-day re-run ⇒ `-run-b`). Never touch `Applied` rows; never claim a profile "never-claim" gap;
dedupe on the canonical link key, not folder slugs.

## Command: SOURCE (find jobs)

The discovery front-end that precedes tailoring — see `references/job-search-guide.md`. Given a
target family (and the candidate's location / right-to-work constraints), find live UK roles:

> **Tool names are written bare here** (`search_jobs`, `reed_search_jobs`, `firecrawl_scrape`) because
> the prefix depends on your surface. Your environment exposes the same tools under one of two
> conventions — resolve each name to whichever your surface uses:
> - **Claude Code / this CLI:** `mcp__<server>__<tool>` — e.g. `mcp__reed__reed_search_jobs`,
>   `mcp__adzuna__adzuna_search_jobs`, `mcp__firecrawl__firecrawl_scrape`.
> - **Claude Desktop / cowork:** `<server>:<tool>` — e.g. `reed:reed_search_jobs`,
>   `adzuna:adzuna_search_jobs`, `firecrawl:firecrawl_scrape`. The Indeed/Dice connectors surface as
>   `Indeed:*` / `Dice:*` here (vs `mcp__claude_ai_Indeed__*` in Code).
>
> If a name doesn't resolve, list your available tools and match by the `<server>` + `<tool>` pair —
> the connector server names are `Indeed`, `reed`, `adzuna`, `Dice`, `firecrawl`.

**Source-effort dial (user's choice — see `references/job-search-guide.md`).** Default is **`full`**:
fan out across all connectors, then the web-crawl net — maximum coverage. Switch to **`budget`** when the
user wants to save tokens ("quick hunt"): search in cost order and stop early — **Tier 1 claude.ai
connectors (Indeed/Dice) → Tier 2 MCP servers (Reed/Adzuna) → Tier 3 web-search net (WebSearch →
Firecrawl)**, climbing only while results are thin. Firecrawl captures each full JD in both modes; in
`budget` mode, note any tier skipped for cost so the search isn't implied exhaustive.

1. Pull search keywords from the family's `TITLE VARIANTS` in `references/keyword-taxonomy/<family>.md`.
2. **Fan out across every connected job connector — one search per title variant, per connector** (in
   `budget` mode, work the tiers above in order instead) — then dedupe hits by company+role. Don't stop
   at the first board; each covers different roles:
   - **Indeed** (`search_jobs`, `country_code='GB'`) — the broad UK workhorse.
   - **Reed** (`reed_search_jobs`, `locationName` + `distanceFromLocation` in **miles**) — strong on
     UK security, data, admin and agency roles.
   - **Adzuna** (`adzuna_search_jobs`, `country='gb'`) — wide UK aggregator; also gives labour-market
     salary context (`adzuna_salary_histogram`, `adzuna_top_companies`) to fill a band the JD omits.
   - **Dice** (`search_jobs` on the Dice connector) — US-leaning tech; worth a pass for the AI/data
     families only (weak UK coverage).
   When the connectors don't cover a role/board (niche board, institute page, company careers
   portal), run the **deep-crawl fallback** — see `references/job-search-guide.md`, "Deep search
   without a connector": `WebSearch` → **Firecrawl** (`firecrawl_scrape` / `firecrawl_crawl` /
   `firecrawl_extract`, now connected) → `WebFetch` / **Claude-in-Chrome** for JS- or login-gated
   pages — then extract and distil the JD.
3. **Triage** each hit with the knockout sweep (`jd-analysis.md` §0) and optionally vet the employer
   with Indeed's `get_company_data` (reviews, salary bands) or Adzuna salary tools. Drop
   hard-knockout fails.
4. **Capture** survivors — pull the FULL JD text before tailoring, never tailor off the search
   snippet: Indeed `get_job_details(job_id)`, Reed `reed_get_job_details(jobId)` (also returns
   normalised yearly salary + apply URL), Adzuna → fetch the result's `redirect_url`. If none of
   those yield the full text (external ATS, PDF, bare listing), **crawl the apply/JD URL with
   Firecrawl** (`firecrawl_scrape` for one page, `firecrawl_extract` to pull structured JD fields)
   and fall back to `WebFetch` / Claude-in-Chrome only if Firecrawl can't reach it. Hand off to
   TRACK & FILE + TAILOR; log triaged-out roles as `Skipped` so the search is fully recorded.

When presenting connector results to the user, add the AI-search disclosure (verify details with the
employer). Sourcing is profile-agnostic — match searches to the family, not to a person.

## Command: DISCOVER + COLD MAIL (the hidden job market)

For when there is no advert — target companies directly. See
`references/company-discovery-cold-outreach.md`. Pipeline:

1. **DISCOVER** — build a ranked target-company list for the family + location using several angles:
   `WebSearch`/`WebFetch`/browser for directories, association member lists and accelerator cohorts;
   **Clay** (`find-and-enrich-company`, `query-objects`) to enrich/filter; **Ahrefs**
   (`site-explorer-organic-competitors`) to surface same-sector "related companies" from a known
   domain; **Indeed** `get_company_data` to vet each. Rank by fit, location/right-to-work, and stage.
2. **ENRICH** — find the *named* owner of the hire/work (hiring manager, team lead, jobs.ac.uk
   "informal enquiries" contact) and a verified email via **Clay**
   (`find-and-enrich-contacts-at-company`) or **RocketReach** (`rocketreach_search_people` to find the
   profile, then `rocketreach_lookup_person` to get the verified email — a PAID lookup credit, so check
   `rocketreach_account` first and use it frugally, one confirmed target at a time). Never cold-mail
   `info@`.
3. **COLD MAIL** — **required input: the user's own spoken/verbal narrative** (a voice note or ramble)
   on why this company and what they'd bring. **If it isn't supplied, ask for it and wait — never
   cold-generate.** Write the email FROM their words: preserve the spoken cadence, strip only true
   filler, never corporatise it. 120–180 words, specific human subject line, one clear low-friction
   ask, tailored CV attached, truth rule applies (claims map to profile evidence). UK email etiquette
   ("Kind regards"). Draft via **Gmail** `create_draft` for the user to review/send.
4. **TRACK** — log each target with `new_application.py --category cold-outreach --status Cold-emailed`;
   flip to `Replied` on a response; one polite follow-up after ~5–7 working days, then stop. Companies
   researched but passed over are logged `Skipped`.

## Command: TAILOR (the core)

Given profile + JD + level, produce a tailored CV. Six steps:

1. **Parse the JD** → a JD-analysis object (must-haves, nice-to-haves, hard knockouts, seniority,
   tone, keywords, salary band). Follow `references/jd-analysis.md`. Capture the JD text for filing.
2. **Build the coverage matrix** — every requirement mapped to real profile evidence, marked
   **strong / partial / adjacent-provisional / hard-gap** (`tailoring-levels.md`, "Gap classes").
   This matrix is the spine: it drives selection, it's what the recruiter scores against, and its
   hard gaps define the L2 delta. *Hard gaps* (no plausible basis) are surfaced, never filled.
   *Adjacent-provisional* items (a skill under another name, or one a listed role obviously implies)
   are handled by the provisional mechanism — see step 4 and the end-of-run confirmation — not
   dropped and not treated as gaps.
3. **Select and order** — pull the matching skills cluster from the profile's warehouse using the
   family taxonomy as a *palette* (match to real evidence, never add a skill the profile lacks);
   drop weak/irrelevant material; order for this JD and this reader.
4. **Draft** — bullets as `strong verb + real task + method + quantified outcome` (`cv-craft.md`).
   Weave keywords naturally and in-context; pair every acronym with its expansion, e.g. "NLP
   (natural language processing)". Respect the level: L0 faithful, L1 aggressive-but-true (the `%`
   sets how aggressive), L2 the alternative-world persona (see its own section).
   - **Anti-mirroring guard (learned from eval — critical):** mirror the JD's *vocabulary* only onto
     *real profile evidence* or a **plausible basis**. It is fabrication to paste a JD term with
     nothing behind it — e.g. "quasi-experimental" when the profile only has true experimental
     designs, or "data security" when the profile says "detailed records": drop those or surface as
     a hard gap.
   - **Provisional inclusions (no interruption):** when a JD term has a *plausible basis* — an
     equivalent skill under a different name, or one a listed role obviously implies but doesn't
     state — you MAY provisionally include it rather than dropping it and underselling the candidate.
     Add it to the draft AND to a **"pending confirmation" list in the job's `notes.md`**, and keep
     going. Do not stop mid-draft. These are gated by the end-of-run confirmation (step 6). Full
     rules and tone in `tailoring-levels.md` ("Gap classes, provisional inclusions").
5. **Voice pass + integrity check** — apply the writing model (`references/writing-voice.md`) inline, and
   strip everything in the `cv-mistakes.md` catalog (buzzwords, unquantified claims,
   responsibilities-not-achievements, tense/date drift). Apply `uk-conventions.md` (CV not résumé, two pages, UK spelling/dates, no
   photo/DOB, right-to-work phrasing when a JD asks). Also run these three checks every time:
   - **Date consistency:** normalise all dates to one format ("Mon YYYY – Mon YYYY"); label genuinely
     concurrent roles "(concurrent…)" so overlaps don't read as errors; add the target-role headline
     line for the six-second scan.
   - **Gap check:** scan the timeline for unexplained recent gaps (a common one: the tail between a
     course ending and "present"). Surface any gap to the user for an honest line — never paper it over.
   - **Truth sweep:** re-read every line against the profile; any claim not traceable to it *and not
     on the pending-confirmation list* is a violation to fix before rendering. (Provisional items are
     allowed through here because they are gated by step 6's confirmation.)
6. **Render + end-of-run confirmation** — write the CV as markdown in the
   `assets/cv-markdown-template.md` convention, then render per surface (see "Tools & external
   skills"). In Claude Code — **pass `--page` by market** (`a4` default for `uk`; `letter` for `ca`/US):
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/render_docx.py" --in <cv.md> --outdir <job-folder> --page <a4|letter>
   ```
   produces ATS-safe `CV.docx` (no tables/columns/text-boxes/graphics) **and** `CV.txt`; in cowork use
   the native `docx` skill for the same ATS-safe output. **The `.docx` is the ATS submission.** If the
   user also wants a polished human-facing copy, additionally route the CV markdown through `/make-pdf`
   — label it the human/portfolio PDF, not the ATS file. Then run the recruiter loop and file it (below).
   - **Before the CV is treated as final, run the pending-confirmation batch** if any provisional
     items were added (step 4). Present the whole list as ONE neutral yes/no memory-jog — *not* an
     accusation; the premise is the person likely did this and forgot to write it, or names it
     differently. On *yes*, keep it (offer to add it to the master profile); on *no*, remove it and
     re-render, and it may become a surfaced gap. Nothing provisional ships as "final" unconfirmed.
     Exact framing and tone: `tailoring-levels.md` ("Gap classes, provisional inclusions").

Output to the user: the CV, the coverage matrix (with hard gaps called out), the end-of-run
confirmation batch (if any provisional items), and — after the loop — the recruiter scorecard so they
see *why* it's strong.

## Command: RECRUITER LOOP (critic + test harness)

Adopt a **JD-specific recruiter persona** (`references/recruiter-rubric.md`) — a fintech hiring
manager, an NHS panel, a university PI, a security ops manager all read differently. Score the draft
on the five dimensions (ATS/keyword coverage, six-second scan, requirement coverage, authenticity/
slop, red flags). Return the structured scorecard: per-dimension score + justification, overall
score, PASS/REVISE verdict, and a short list of **specific, actionable fixes ranked by impact**.

Loop: score → fixes → tailorer revises → re-score. Stop at **PASS** (default threshold: overall ≥
4.0/5 AND no dimension < 3, AND the "would I forward this?" test passes) or after **3 passes**.
Never "fix" a low score by inventing evidence — if the gap is real, surface it (and optionally offer
the L2 delta). The same rubric scores eval batches in `evals/`.

## Command: L2 — THE ALTERNATIVE WORLD

Produce a *different realistic person* who already holds what the JD wants and would win the
interview — realistic, not heavenly-perfect; a clean CV with **no watermark or disclaimer on the
artifact**. Deliver it **alongside the delta**: the specific experience, skills, and certs that
separate the real candidate (from the profile) from this persona. The delta is the point — it's the
user's roadmap. Never present L2 as submittable; state in-conversation/`notes.md` that it's a target
persona. Full rules: `references/tailoring-levels.md`.

## Command: COVER LETTER

Shares the JD analysis and profile feed but produces a letter, not a CV. **Best input: a short
brain-dump** of the user's own thoughts on *this* role (why they want it, their angle, any company
connection) — **always ask for it first and strongly encourage it**, and **invite a spoken/verbal
narrative** (a voice note or ramble; work from the transcript, keep the spoken cadence). Offer a quick
3–5 prompt brainstorm as the easy on-ramp ("What first caught your eye about them? Which of your
projects felt most like this job?"). **But the brain-dump is recommended, not required: if it isn't
supplied, draft anyway from the JD + profile** — build motivation only from what the profile/research
honestly support (never fabricate familiarity), keep it a touch shorter, and **flag the "why this
company" paragraph as profile-only** in your return note so the user fixes the input rather than
wordsmithing the output. Where the brain-dump exists, write the letter *from* the user's words: preserve
their voice and cadence, strip slop but never de-voice them (a de-slopped letter that no longer sounds
like them is a failure). Claims map to real profile evidence (same truth rule). Run the same voice pass
(the writing model, `references/writing-voice.md`).
UK conventions; render to `.docx` + plain text (bundled script or the `docx` skill), and route through
`/make-pdf` if the user wants a human-facing PDF to send directly. The L0–L2 dial does NOT
apply — a cover letter is inherently first-person and truthful. Full craft: `references/cover-letter.md`.

## Command: TRACK & FILE (every run)

Every job — including ones considered and skipped — is filed and logged. Nothing is lost.

**Create the job folder + tracker row** (status defaults to `Drafted`; use `Skipped` for
considered-but-passed):
```
python "${CLAUDE_PLUGIN_ROOT}/scripts/new_application.py" --root <apps> --category <cat> --company "<Co>" \
    --role "<Role>" --date <YYYY-MM-DD> --jd-file <jd.txt> \
    --location "<loc>" --link "<url>" --source <Indeed|LinkedIn|…> --ats <platform> \
    --pay "<band>" --level <L0|L1> [--status Skipped]
```
This makes `<category>/<date>_<company>_<role>/` with `job-description.md` and `notes.md`, and adds
one tracker row (it **auto-inits** the tracker on first use and **preflights** deps first, so the row
is never silently dropped). Categories are dynamic — create whatever fits (ai, research-assistant,
plant-science, data, security, …). Render the CV into that folder; put the brain-dump, coverage
matrix, recruiter scorecard, and any L2 delta into `notes.md`. Pass `--link` always so the dedupe
ledger key resolves.

**When the user says "I applied to this one":**
```
python "${CLAUDE_PLUGIN_ROOT}/scripts/tracker.py" update --root <apps> --key "<folder_path>" --data '{"status":"Applied"}'
```
This stamps `date_applied`, turns the row **green**, and **locks** it (sheet protection) so the
record can't be lost. Later updates (`Interview`/`Rejected`/`Offer`) stamp the matching date and
recolour. Applied rows are final — the script refuses silent overwrites (pass `"_force": true` to
override deliberately).

The tracker is `tracker.xlsx` + a `tracker.csv` mirror. **Always** change tracker state through
`scripts/tracker.py`, never by hand — it owns the green/lock/date logic deterministically. For the
day-to-day worklist, generate the prioritised view (`tracker.py priority-view` →
`tracker-priority.xlsx`: Drafted-first, soonest-closing next, closing ≤7d in red); the full tracker
stays the system of record. Clean duplicate rows with `tracker.py dedupe` (dry-run by default;
`--apply` to rewrite; it dedupes on the canonical link key and never drops `Applied` rows).

## Scripts (bundled, deterministic)

- `scripts/_lib.py` — workspace resolution (`resolve`) + dependency `preflight` (openpyxl +
  python-docx, fails loudly with the exact fix so the tracker never half-commits). Import or CLI.
- `scripts/init_workspace.py` — scaffold a new workspace (Setup mode): tree + profile template +
  playbook + empty ledger + tracker init, then stop. Idempotent; won't clobber a populated workspace.
- `scripts/render_docx.py` — markdown CV → ATS-safe `.docx` + `.txt`. Never emits tables/columns/
  text-boxes/images. `--page a4` (default, UK/world) or `--page letter` (Canada/US, market `ca`).
- `scripts/tracker.py` — `init` / `add` / `update` / `show` / **`dedupe`** / **`priority-view`**;
  green fill + lock on Applied; CSV mirror. Row key = `folder_path`; dedupe key = canonical link.
- `scripts/new_application.py` — per-job folder + tracker row in one call (auto-inits + preflights).
- `scripts/dump_manifest.py` — `scan` the `dump/` folder into `dump/_manifest.csv` (per-file status)
  and create placeholder stubs for unreadable formats; `mark` a file `ingested`. Makes INTAKE
  incremental and format-safe. Import or CLI.
- `scripts/build_seen_ledger.py` — rebuild `daily-hunt/seen-jobs.csv` (canonical job key → status)
  from the tracker; run at the start and end of every daily hunt.

Requires Python with `python-docx` and `openpyxl`. The scripts **preflight** these and fail with the
exact `pip install` if missing — they never proceed into a half-commit.

## Hold-the-line invariants

1. Master profile is truth for L0/L1; gaps surfaced, never filled. **Never claim a technique the
   profile lists under "never claim"; respect confidential holds** (capability, not protected specifics).
2. ATS-safe rendering — no tables, columns, or graphics in the CV.
3. No slop — enforced against `cv-mistakes.md`.
4. UK conventions on by default.
5. L2 is realistic-not-perfect, unwatermarked, delta stated in conversation/notes, never submittable.
6. Profile schema stays generic — the profile is swappable data; skill logic never keys off who it is.
7. Every job filed into a category folder and logged; applied rows green and locked; skipped jobs recorded.
8. **Path-agnostic** — resolve the workspace root at runtime; never hard-code a machine path.
9. **Daily hunt:** only LIVE roles, only NEW roles (dedupe on the canonical link key, never a folder
   slug), **no cap** on how many to tailor; the tracker is owned only by `tracker.py` and `Applied`
   rows are never touched; same-day re-runs append (`-run-b`), never overwrite.
