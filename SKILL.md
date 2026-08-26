---
name: jobxhunter
description: >-
  Job-hunting skill for the UK and Canada (more markets coming). Core is CV tailoring: read a master profile plus a job description
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

# jobxhunter — the job-hunting skill for the UK and Canada (CV tailoring at its core)

CV tailoring at the core; cover letters, a recruiter loop, an alternative-world mode, and
application tracking around it. UK and Canada both ship (market-driven — see below). Works in
chat and in Claude Code.

## The one rule everything hangs on

**The master profile is the authority for any submittable document.** The skill
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
  `profiles/` + `applications/`. Resolve it once per run: **explicit path → `JOBXHUNTER_DIR` env →
  discovery → none ⇒ Setup mode** (`python "${CLAUDE_PLUGIN_ROOT}/scripts/_lib.py" resolve`). All paths derive from it. Full
  contract + Setup/Daily-run: `references/daily-hunt.md`.

## Two ways to run

- **On-demand (classic):** the user hands over one JD → run TAILOR (+ recruiter loop, cover letter).
- **Autonomous daily hunt:** point the skill at a workspace → it sources, triages, tailors every new
  live match, files everything, and builds the day's apply-from-here bundle. If no workspace resolves, it **scaffolds**
  one and stops for the user to fill their profile. See `references/daily-hunt.md` (SETUP + DAILY RUN).

## Running in Cowork (Claude Desktop) — read if the surface isn't Claude Code

jobxhunter runs in **Cowork**, not only Claude Code. The whole pipeline works; one piece routes
differently:

- **Fully supported:** the skill and every `/jobxhunter:*` command, the subagents (`recruiter-critic`,
  `role-tailorer`), tailoring, the recruiter loop, cover letters, discovery, L2, interview prep, and
  tracking. **Rendering** uses Cowork's native `docx` / `pdf` / `xlsx` file skills (see surface-aware
  routing below), so no local `render_docx.py` is needed.
- **Sourcing routes differently.** The bundled **Reed / Adzuna / Firecrawl** connectors are local
  **stdio** servers and **do not connect in Cowork** (it executes in an isolated VM that cannot reach a
  stdio process on your machine). In Cowork, SOURCE uses the **remote claude.ai connectors** (`Indeed`,
  `Dice`) plus **WebSearch** / **WebFetch**, and captures JDs with `WebFetch` or the **`/scrape`** skill.
- **Scripts:** `${CLAUDE_PLUGIN_ROOT}` resolves inside the Cowork VM, and the stdlib-only scripts
  (`dashboard.py`, `keyword_coverage.py`) run there as-is. `tracker.py` needs `openpyxl`; if it isn't
  present, the script prints the one-line fix, or use the native `xlsx` skill for the tracker.
- **Nothing silently breaks:** no `hooks/` or `monitors/` ship (both are Cowork-incompatible), so
  there's nothing to gray out.

**Do this in Cowork:** treat the bundled connectors as absent, prefer `Indeed`/`Dice` + WebSearch for
SOURCE, and let the native file skills render. Everything else is identical.

## Running the bundled scripts (shell note — read before the first `python …`)

The commands below write the plugin root as `${CLAUDE_PLUGIN_ROOT}` (the folder holding
this `SKILL.md`, `scripts/`, `references/`). **That token is not always exported to your
shell:** in the Claude Code Bash tool it can expand to empty, and PowerShell reads it as
`$env:CLAUDE_PLUGIN_ROOT`, not `${CLAUDE_PLUGIN_ROOT}`. Don't paste it blind — resolve it once:

- **Capture the root, then use it.** Find the directory this skill loaded from (it contains
  `scripts/`). POSIX/bash: `root="${CLAUDE_PLUGIN_ROOT:-<real path>}"`; PowerShell:
  `$root = $env:CLAUDE_PLUGIN_ROOT`. Then call `python "$root/scripts/tracker.py" …`.
- **Or `cd` into the plugin root** and run scripts by relative path: `python scripts/tracker.py …`.
  SETUP also copies the scripts into `<workspace>/scripts/`, so you can run them from the
  workspace too.

If a `python "${CLAUDE_PLUGIN_ROOT}/…"` line ever errors with `can't open file '/scripts/…'`,
the token expanded empty — resolve the root as above and re-run.

## Market (which country's path) — read from the profile, not hard-coded

The profile's **market** field (`## Career targets & market` — `uk` / `ca` / …) is the switch that
selects three things; resolve it once per run (if unset, infer from `location` + work authorisation and
confirm with the user):
- **CV conventions:** `uk` → `references/uk-conventions.md`; `ca` → `references/ca-conventions.md`
  (résumé not CV, US-Letter, Canadian spelling, YYYY-MM-DD, French-as-asset, PR/work-permit phrasing).
- **Job boards & sourcing lanes:** see `references/job-search-guide.md` (UK boards vs Canada boards).
- **Connectors:** `uk` → Reed + Adzuna(`gb`) + Indeed; `ca` → **Adzuna(`ca`) + Indeed(`CA`)** (Reed is
  UK-only, skip it for `ca`) + Firecrawl for everything else. All optional; missing ones fall back.
The UK is only the default, not a limit — the logic is market-driven, so adding a market = add a
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
| writing for a research / PhD / fellowship target | `references/academic-register.md` (on top of the writing model) |
| finding jobs to apply to (sourcing) | `references/job-search-guide.md` |
| finding target companies + cold-emailing them | `references/company-discovery-cold-outreach.md` |
| running the autonomous daily hunt / scaffolding a workspace | `references/daily-hunt.md` |
| which tool/connector/skill to use (the manifest) | `references/tools-and-connectors.md` |
| onboarding a new user's connectors + API keys | `references/connector-setup.md` |
| prepping for the interview after applying | `references/interview-prep.md` |
| answering application-form / screening questions | `references/application-answers.md` |

Keyword families: `plant-science-research`, `research-assistant-lead`, `ai-technician-junior-ai`,
`data-research-analysis`, `pa-ea-private-office`, `security-frontline`. Pick the closest; if none
fit, decompose the JD directly with `jd-analysis.md` and note the taxonomy gap.

## Tools & external skills (surface-aware routing)

The skill leans on other skills/tools for prose voice, rendering, and JD capture. **Detect what this
surface exposes** (list your skills/tools if unsure) and route accordingly — every route has a
self-sufficient fallback, so the skill never hard-depends on an optional tool.

- **Prose voice (the de-slop pass).** `references/writing-voice.md` is the skill's own **writing model** —
  a register-aware (CV / cover letter / cold email) standard for stripping AI tells and hitting the right
  formality. It's fully self-contained: the agent applies it **inline** on every final draft, together with
  the `cv-mistakes.md` banned-buzzword catalogue. No external tools or plugins required — never ship prose
  that hasn't been through it.
- **Humanizer pass (mandatory in TAILOR and COVER LETTER).** After the writing model, apply the
  installed **`humanizer`** skill's checklist, if present, to the summary, every bullet and the whole
  letter. It supplements `writing-voice.md`; it never replaces it. If it is not installed,
  `writing-voice.md` §"AI tells" is the whole pass, and `scripts/validate_profile.py`'s AI-tell WARN
  is the mechanical backstop either way.
- **What is and is not bundled.** This plugin ships its scripts, references and two agents. It does
  **not** bundle `humanizer`, `/make-pdf`, `/scrape`, the native `docx`/`pdf`/`xlsx` file skills, or
  any `academic-prose` skill — detect each on your surface and use the fallback named here when it is
  absent. Never wire a skill name that resolves to nothing.
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

Profile rule applies throughout: the profile may only contain what the dump (and the user's confirmations)
actually support.

## Command: SETUP (scaffold a workspace — first run / new user)

When no workspace resolves (no path, no `JOBXHUNTER_DIR`, discovery finds nothing), the user is new.
**Scaffold and stop** — do not hunt against an empty profile:
```
python "${CLAUDE_PLUGIN_ROOT}/scripts/init_workspace.py" --workspace <dir> [--name <who>]
```
This builds the workspace contract (`profiles/` + `profiles/_intake/`, `dump/` with its `_manifest.csv`,
`applications/`, `daily-hunt/`, `scripts/`), drops a rich **profile template** (hold everything true
about the user, far more than one CV shows — tailoring selects from it) +
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
profile fresh → concurrency lock + rebuild ledger → **source with `run_hunt.py`** (every source across
the whole `SEARCH-KEYWORDS.md`, then the employers' own boards from `TARGET-COMPANIES.md`, consolidate,
rank, verify breadth, fetch the JDs → `to-tailor.csv`) → **triage every fetched advert on disk**
(`triage.py`, round-robin by lane, a reason on every skip) → **tailor every role you can defend (no
cap)** → **write each cover letter complete** (never a scaffold, never a request for a brain-dump —
the run has nobody to ask) → the L2 alternative-world CV + delta per role → **track & file** every job
(Drafted/Skipped with reason + link) → rebuild ledger + regenerate the priority view → **assemble the
dated apply-from-here bundle** (`daily_bundle.py --root <apps>` → one folder per role with the CV,
cover letter, L2 CV, advert and notes, plus a `<date>-roles.xlsx`) → `verify_run.py` (a FAIL means
search more, not write it up). The tracker, `queries.csv` and the bundle are the record of the day;
no separate summary file is written. Never touch `Applied` rows; never claim a profile "never-claim"
gap; dedupe on the canonical link key, not folder slugs.

**Keep quality flat across a long batch (Claude Code).** A no-cap hunt can tailor a dozen-plus roles
in one context, where later CVs quietly get less care. Where subagents are available, fan out **one
`role-tailorer` agent per surviving live role** (parallel), each tailoring + filing its role in a clean
context and returning a one-line result; the orchestrator only sources, dedupes, and synthesises the
summary — and scores each result with the independent `recruiter-critic` agent. Serial in-context
tailoring remains the fallback where subagents aren't exposed.

## Command: SOURCE (find jobs)

The discovery front-end that precedes tailoring — see `references/job-search-guide.md`. Given a
target family (and the candidate's location / right-to-work constraints), find live UK roles:

> **Tool names are written bare here** (`search_jobs`, `reed_search_jobs`, `firecrawl_scrape`) because
> both the prefix *and which connectors exist* depend on your surface. Resolve each name against the
> tools your surface actually exposes — never assume a connector is present:
> - **Claude Code / this CLI:** the bundled connectors load as `mcp__<server>__<tool>` — e.g.
>   `mcp__reed__reed_search_jobs`, `mcp__adzuna__adzuna_search_jobs`, `mcp__firecrawl__firecrawl_scrape`.
>   The claude.ai connectors are `mcp__claude_ai_Indeed__*` / `mcp__claude_ai_Dice__*`.
> - **Cowork / Claude Desktop:** the bundled **Reed / Adzuna / Firecrawl** connectors are local stdio
>   servers and **do NOT connect here** — Cowork runs in an isolated VM that can't reach a stdio server
>   on your machine. Source instead with the **remote claude.ai connectors** (`Indeed`, `Dice`, if you
>   have them connected) plus **WebSearch** / **WebFetch**, and capture full JDs with `WebFetch` or the
>   **`/scrape`** skill. Tailoring, tracking, and interview prep are identical to Claude Code.
>
> If a name doesn't resolve, list your available tools and match by the `<server>` + `<tool>` pair. The
> bundled (stdio, Claude-Code-only) server names are `reed`, `adzuna`, `firecrawl`; the always-remote
> ones are `Indeed`, `Dice`.

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
   - **Reed** (`reed_search_jobs`) — strong on UK security, data, admin and agency roles.
   - **Adzuna** (`adzuna_search_jobs`, `country='gb'`) — wide UK aggregator; also gives labour-market
     salary context (`adzuna_salary_histogram`, `adzuna_top_companies`) to fill a band the JD omits.

   > **Reed and Adzuna take every argument nested inside a single `params` object, in
   > `snake_case`.** Passing them flat, or in camelCase, is rejected outright by pydantic —
   > `Field required [params]` or `Extra inputs are not permitted`. So it is
   > `reed_search_jobs(params={"keywords": …, "location_name": "London",
   > "distance_from_location": 30, "results_to_take": 25})`, **not** `locationName` /
   > `distanceFromLocation` / `resultsToTake`, and `adzuna_search_jobs(params={"what": …,
   > "country": "gb", "results_per_page": 25})`. Reed distance is in **miles**, Adzuna's in km.
   > Indeed and Dice are the opposite — flat top-level args, no `params` wrapper.
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
   snippet: Indeed `get_job_details(job_id)`, Reed `reed_get_job_details(params={"job_id": …})` (also returns
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
   ask, tailored CV attached, profile rule applies (claims map to profile evidence). UK email etiquette
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
   Where the move is a career change or the history is non-linear, build the red thread first with
   `references/career-narrative.md` — the matrix is much stronger once the story is decided.
   This matrix is the spine: it drives selection, it's what the recruiter scores against, and its
   hard gaps define the L2 delta. *Hard gaps* (no plausible basis) are surfaced, never filled.
   *Adjacent-provisional* items (a skill under another name, or one a listed role obviously implies)
   are handled by the provisional mechanism — see step 4 and the end-of-run confirmation — not
   dropped and not treated as gaps.
3. **Select and order** — pull the matching skills cluster from the profile's warehouse using the
   family taxonomy (`references/keyword-taxonomy/<family>.md`; families listed under the reference
   map) as a *palette* (match to real evidence, never add a skill the profile lacks);
   drop weak/irrelevant material; order for this JD and this reader.
   **Never thin a CV because the role is junior.** A stretch-down advert gets the complete history,
   education and skills; only the *emphasis* changes. Where the role sits materially below level,
   soften rather than shorten — lead with hands-on and operational evidence and let the strongest
   academic credentials sit in Education rather than the summary. Nothing is removed or denied;
   note the softening in `notes.md` so it is reversible.
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
   responsibilities-not-achievements, tense/date drift). Then the **humanizer pass — mandatory**: the
   installed `humanizer` skill's checklist, if present, on the summary and every bullet (see "Tools &
   external skills" for the fallback when it is absent). Apply the **market conventions doc chosen by
   the profile's market — `references/uk-conventions.md` for `uk`, `references/ca-conventions.md` for
   `ca`** (for `uk`: CV not résumé, two pages, UK spelling/dates, no photo/DOB, right-to-work phrasing
   when a JD asks); academic/research targets also `references/academic-register.md`. Also run these
   three checks every time:
   - **Date consistency:** normalise all dates to one format ("Mon YYYY – Mon YYYY"). Overlapping
     roles: print exactly ONE, chosen by lane — the `overlap-print` menu in the profile's rules block
     is the authority (`references/master-profile-schema.md`). Never both, no "(concurrent)" label, no
     explanation on the page: an ATS cannot read it and a recruiter reads it as an error. Education is
     SELECTED per lane the same way (`education-for-lane`): only the listed degrees, in the listed
     order, grades only where the lane allows. Add the target-role headline line (`## <target>`
     immediately under the name, no blank line) for the six-second scan.
   - **Gap check:** scan the timeline for unexplained recent gaps (a common one: the tail between a
     course ending and "present"). Surface any gap to the user for an honest line — never paper it over.
     **In the autonomous daily run there is no user to ask: write the gap into `notes.md` and keep
     going.** Either way it never appears on the page.
   - **Profile check — RUN IT, do not eyeball it:**
     ```bash
     python "${CLAUDE_PLUGIN_ROOT}/scripts/validate_profile.py" --profile <profile.md> --folder <application dir>
     ```
     Exit 0 or the CV does not get rendered (exit 2 = the profile's rules block itself is broken —
     stop and report). The rules come from the profile's own `profile-rules` block, so the profile is
     the authority and the check is decidable — "does this line trace to the profile?" rather than
     "is this claim true?", which is not a question this skill can answer and which a plausible
     invention passes. Warnings list proper nouns the profile does not use: usually the employer's
     own name, occasionally something invented, so read them. Anything genuinely provisional goes on
     the pending-confirmation list and is gated by step 6.
6. **Render + end-of-run confirmation** — write the CV as markdown in the
   `assets/cv-markdown-template.md` convention, then render per surface (see "Tools & external
   skills"). The render must satisfy `references/ats-mechanics.md` §9 (the ATS-safe checklist) —
   check it there rather than from memory. In Claude Code — **pass `--page` by market** (`a4` default for `uk`; `letter` for `ca`/US):
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/render_docx.py" --in <cv.md> --outdir <job-folder> --page <a4|letter>
   ```
   produces ATS-safe `CV.docx` (no tables/columns/text-boxes/graphics) **and** `CV.txt`; in cowork use
   the native `docx` skill for the same ATS-safe output. **The `.docx` is the ATS submission.** If the
   user also wants a polished human-facing copy, additionally route the CV markdown through `/make-pdf`
   — label it the human/portfolio PDF, not the ATS file. Then run the recruiter loop and file it (below).
   - **Coverage read (deterministic).** After rendering, confirm the JD's must-have terms actually
     landed on the page: `python "${CLAUDE_PLUGIN_ROOT}/scripts/keyword_coverage.py" --cv <folder>/CV.txt
     --must "<must-haves from step 1>" [--nice "<nice-to-haves>"]`. It reports "N/M present (X%)" plus any
     acronym missing its expansion. This is a **parse diagnostic, not a match score** — fill a real miss
     only if the profile genuinely supports it (never mirror a term with nothing behind it). Drop the
     summary into `notes.md`.
   - **Before the CV is treated as final, run the pending-confirmation batch** if any provisional
     items were added (step 4). Present the whole list as ONE neutral yes/no memory-jog — *not* an
     accusation; the premise is the person likely did this and forgot to write it, or names it
     differently. On *yes*, keep it (offer to add it to the master profile); on *no*, remove it and
     re-render, and it may become a surfaced gap. Nothing provisional ships as "final" unconfirmed.
     Exact framing and tone: `tailoring-levels.md` ("Gap classes, provisional inclusions").
     **This batch is for the interactive commands only.** The autonomous daily run has nobody to
     answer it, and a run that pauses for confirmation produces no documents at all. There, the
     provisional list goes into `notes.md` under "pending confirmation" and the CV ships; the user
     reviews the list when they choose.

Output to the user: the CV, the coverage matrix (with hard gaps called out), the end-of-run
confirmation batch (if any provisional items), and — after the loop — the recruiter scorecard so they
see *why* it's strong.

## Command: RECRUITER LOOP (critic + test harness)

Adopt a **JD-specific recruiter persona** (`references/recruiter-rubric.md`) — a fintech hiring
manager, an NHS panel, a university PI, a security ops manager all read differently. Score the draft
on the five dimensions (ATS/keyword coverage, six-second scan, requirement coverage, authenticity/
slop, red flags). Return the structured scorecard: per-dimension score + justification, overall
score, PASS/REVISE verdict, and a short list of **specific, actionable fixes ranked by impact**.

**Make the critic genuinely independent.** Where the surface supports subagents (Claude Code), run
the scoring in the bundled **`recruiter-critic`** agent and hand it **only** the JD + the rendered
`CV.txt` — never the tailorer's notes or coverage matrix — so the grade can't be biased by the
writer's own rationale (self-scoring is how slop survives). Fall back to an in-context persona only
where subagents aren't available. **Point the critic at the writer's standard:** its authenticity
dimension is scored against `references/writing-voice.md` and `references/cv-mistakes.md` §1 — the
same banned list the tailorer worked from — not against the critic's own sense of what "reads like
AI". A critic and a writer holding different standards loop forever.

Loop: score → fixes → tailorer revises → re-score. Stop at **PASS** (default threshold: overall ≥
4.0/5 AND no dimension < 3, AND the "would I forward this?" test passes) or after **3 passes**.
Never "fix" a low score by inventing evidence — if the gap is real, surface it (and optionally offer
the L2 delta). The same rubric scores eval batches in `evals/`.

## Command: INTERVIEW PREP (carry the candidate past "filed")

Once a role is filed — and especially once it reaches `Interview` — turn the material already
on hand into an honest prep pack. See `references/interview-prep.md`. Read the job folder
(`job-description.md` + the `notes.md` coverage matrix) and the master profile, adopt the JD's
interviewer persona, and write `interview-prep.md` into that folder: a 30-second opener from the
CV headline, predicted questions grouped by the JD's must-have competencies with **STAR answers
built only from real profile evidence**, honest **gap-defence** answers for every hard-gap/partial
the matrix surfaced (the questions they *will* probe), sharp questions to ask them, and the likely
curveballs (salary anchored to the fetched Adzuna band, notice period, any timeline gap). Profile rule
holds — never invent experience; prepare a confident, honest way to handle a gap. Ties to the tracker:
`tracker.py update … {"status":"Interview"}` stamps the date and keeps the pack in the folder.

## Command: L2 — THE ALTERNATIVE WORLD

Produce a *different realistic person* who already holds what the JD wants and would win the
interview — realistic, not heavenly-perfect; a clean CV with **no watermark or disclaimer on the
artifact**. Deliver it **alongside the delta**: the specific experience, skills, and certs that
separate the real candidate (from the profile) from this persona. The delta is the point — it's the
user's roadmap. Never present L2 as submittable; state in-conversation/`notes.md` that it's a target
persona. Full rules: `references/tailoring-levels.md`.

## Command: COVER LETTER

Shares the JD analysis and profile feed but produces a letter, not a CV. **Draft first — never ask
for a brain-dump, a voice note, or the user's own words.** Write the letter complete from the JD +
profile: name the employer in the body, and build the "why this employer" paragraph from the advert
and verifiable public knowledge like any other paragraph (never fabricate familiarity; if research
turns up nothing specific, say less). No placeholders, no bracketed gaps, no "draft" label — the user
reviews the finished letter and says if something does not sound like them. If the user **volunteers**
their own words (typed, or a voice-note transcript), write the letter *from* them: preserve their voice
and cadence, strip slop but never de-voice them (a de-slopped letter that no longer sounds like them is
a failure). Claims map to real profile evidence (same profile rule). Run the same voice pass (the
writing model, `references/writing-voice.md`), then the **humanizer pass — mandatory**: the installed
`humanizer` skill's checklist, if present, on the whole letter (`validate_profile.py` WARNs on AI-tell
vocabulary as the mechanical backstop). For academic/research targets apply
`references/academic-register.md` on top.
Market conventions by the profile's market; render to `.docx` + plain text (bundled script or the
`docx` skill), and route through `/make-pdf` if the user wants a human-facing PDF to send directly.
The L0–L2 dial does NOT apply — a cover letter is inherently first-person and profile-grounded. Full
craft: `references/cover-letter.md`.

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
plant-science, data, security, …). Render the CV into that folder; put the coverage matrix, the
user's own words if they volunteered any, the recruiter scorecard, and any L2 delta into `notes.md`.
Pass `--link` always so the dedupe ledger key resolves. **If the application has screening/knockout
questions** (Workday/Greenhouse supplementals), also draft the profile-grounded **application answer
pack** into `notes.md`
per `references/application-answers.md` — a review-and-paste draft (never auto-submitted), with salary
anchored to the fetched Adzuna band and any profile-only answer flagged.

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

**Status vocabulary.** `Drafted` · `Skipped` · `Applied` · `Interview` / `Interviewed` · `Offer` ·
`Rejected` · `Cold-emailed` · `Replied` · `Not applied` · **`Archived`**. `Applied / Interview /
Interviewed / Offer / Rejected` are *committed*: status moves freely among them, but regressing out
of the set — or editing an identity field — needs `"_force": true`. **`Archived`** retires a row
from the active pipeline without deleting it: it renders pale grey and sinks below everything in
the priority view. Use it for a bulk reset, and keep an index of what was archived so the rows stay
reachable.

**Two things that bite (both fixed in the scripts, both worth knowing):** `update`/`add` now
**hard-fail on an unknown column name** instead of silently writing nothing — the real columns are
`ats_platform` and `level_used`, not `ats`/`level`; and the csv mirror is preflighted *before* the
xlsx commits, so a csv-only lock can no longer leave the two out of step. If they ever do diverge,
`tracker.py repair-mirror --root <apps>` regenerates the csv from the xlsx. Read a row back with
`tracker.py show --root <apps> --key <folder_path>`.

## Command: DASHBOARD (share the pipeline at a glance)

Turn the tracker into one self-contained HTML page — headline tiles, the apply→interview→offer
funnel with conversion, status and category breakdowns, and the recruiter-score spread:

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/dashboard.py" --root <apps> --out <workspace>/dashboard.html
```

Reads the `tracker.csv` mirror (no openpyxl needed), writes inline-CSS HTML that opens offline and
makes **no network requests** — safe to open or share without leaking the private workspace.
**Read-only** over the tracker; it never edits a row. `--sample` stamps a "sample data" badge for
demos (see `assets/sample-tracker.csv`).

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
- `scripts/keyword_coverage.py` — deterministic must-have/nice-to-have term check against the rendered
  `CV.txt`: "N/M present (X%)", missing terms, and acronyms lacking an expansion. A parse diagnostic,
  **not** a match score; `--min` makes it a pass/fail gate. Import or CLI.
- `scripts/dashboard.py` — tracker CSV → one self-contained HTML dashboard (funnel, status, category,
  recruiter-score spread). Stdlib only (no openpyxl); offline; no network requests. Read-only.
- `scripts/daily_bundle.py` — gathers one day's hunt into a dated apply-from-here folder:
  `CV_<Company>_<Role>.docx` + `CoverLetter_…` per role, a `<date>-roles.xlsx` sheet (status, pay,
  closing date, fit score, apply link; closing ≤7d red, ≤14d amber), and a `FINDINGS.md` scaffold.
  Selects on tracker `logged_date`, so it never depends on folder naming. Idempotent, and it
  **never overwrites an existing `FINDINGS.md`** — the written briefing is the one thing it will not
  touch. Read-only over the tracker.
- `scripts/run_hunt.py` — one command for the whole sourcing half: sweep every source → company
  boards (`--skip-companies` to skip the only credit-spending step) → consolidate → rank → verify →
  fetch JDs → `to-tailor.csv`. `--dry-run` prints the stages; `--stage <name>` runs one. Fails loudly
  (named FAIL, exit 3 on a rejected credential) rather than producing a confident thin day.
- `scripts/sweep.py` — drive the WHOLE `SEARCH-KEYWORDS.md` across one connector, broad-to-narrow,
  with novelty-based pagination (a query stops when a page adds nothing unseen this run). A 401 stops
  the source and is logged as `auth:`; exit 2 on an unknown `--source`.
- `scripts/harvest.py` — enumerate a whole result set (not page 1) for one query and reduce it to a
  triage row per advert; raises `DeadCredential` on 401 so the run fails by name.
- `scripts/harvest_companies.py` — read vacancies off employers' own boards for every company in
  `TARGET-COMPANIES.md` (Greenhouse / Workable / Lever / Ashby / SmartRecruiters / Recruitee, with an
  identity check, and a `| careers:<url>` pin to override it); rows go through `import_rows.py`.
- `scripts/rank.py` — judge the shortlist on the job TITLE against the keyword file's lists (aim-up >
  core > same-work); only clearance and the Global knockouts reject, an unmatched title scores 0. A
  bracketed keyword keeps its qualifier as a ranking signal (`references/job-search-guide.md`).
- `scripts/verify_run.py` — read `queries.csv` and fail the day by name when it was thin: platform
  floor, every lane in `JOB-LANES.md` queried, no reconstructed counts; auth-refused sources are
  excluded from the floor and named.
- `scripts/validate_profile.py` — validate a CV / letter against the profile's own `profile-rules`
  block (8 verbs, `role:` keys, `education-for-lane`, `overlap-print`): exit 0 clean, 1 violations,
  2 the rules are broken. `--folder <dir>` infers lane + JD; `--emit-template` prints a starter block.
  WARNs on AI-tell vocabulary and on proper nouns the profile never uses. Run it, do not eyeball it.
- `scripts/cvgen.py` — assemble a CV from shared blocks whose every fact is bound to the profile
  (lane blocks + JD-gated extras), so a batch cannot drift. `scripts/regen_batch.py` regenerates every
  Drafted application against the current profile — re-laned, re-rendered, re-validated, re-bundled —
  idempotently (`--priority` orders the batch).
- `scripts/triage.py` — the on-disk triage ledger for a day's fetched adverts: `--init`, `--next`
  (round-robin by lane), `--mark`, `--status` (non-zero while anything is pending).
- `scripts/import_rows.py` — bring rows from a source the scripts cannot reach (an OAuth MCP
  connector, a bot-walled board) through the same gate, ledger and query log as a harvester.

All CLIs force UTF-8 stdout so non-Latin-1 job data prints cleanly on a default Windows console, and
`tracker.py` saves atomically (never truncates; a clear message if the file is open in Excel).

**Agents (Claude Code).** `agents/recruiter-critic.md` scores a CV against a JD independently (give it
only the JD + `CV.txt`), and `agents/role-tailorer.md` tailors one role end-to-end in a clean context
for the daily-hunt fan-out. Both are optional — the routines fall back to in-context work where
subagents aren't exposed.

Requires Python with `python-docx` and `openpyxl`. The scripts **preflight** these and fail with the
exact `pip install` if missing — they never proceed into a half-commit.

## Hold-the-line invariants

1. The profile is the authority for L0/L1; gaps surfaced, never filled. **Never claim a technique the
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
   rows are never touched; same-day re-runs are deduped by the ledger and `done_queries`, never
   re-tailored.
10. **Ship complete, never ask.** Cover letters are written in full, first; the user volunteers their
   own words when they want to. Any step that would confirm with the user has an unattended branch
   (`notes.md`), so an autonomous run never pauses.
