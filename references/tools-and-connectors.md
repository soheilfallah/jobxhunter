# Tools & connectors this skill uses (the manifest)

One place that names every external tool/skill `/jobxhunter` orchestrates, what it's for, and its
fallback. **Detect what the surface exposes** (list your tools/skills if unsure) and route
accordingly — every route has a self-sufficient fallback, so the skill never hard-depends on an
optional tool.

> **Bring your own keys.** No API keys ship with this skill and none are in the repo. Two kinds of
> connector exist: **built-in claude.ai connectors** (Indeed, Dice — OAuth, the user clicks
> *Connect* in claude.ai, nothing to copy) and **bring-your-own-key MCP servers** bundled in
> `.mcp.json` (Reed, Adzuna, Firecrawl — keys go into the plugin's user-config). The skill only
> calls tools by name; it never holds a credential. Every connector is optional — absent ones fall
> back to WebSearch/browser.

## The canonical connector table

This is the single source for "what do I need and how do I get it". `SETUP.md`, the README and
`scripts/setup_connectors.py` point here; do not fork the instructions elsewhere.

| Connector | What it gives | Type | Sign up | Get the credential | Register it | Verify |
|---|---|---|---|---|---|---|
| **Indeed** ⭐ | UK + Canada search, **full JD** via `get_job_details`, company data, `get_resume` | built-in claude.ai (OAuth, no key, free) | <https://claude.ai/settings/connectors> | none — click **Connect** on the Indeed card and authorise | nothing to register; tools appear as `mcp__claude_ai_Indeed__*` (Claude Code) / `Indeed:*` (Desktop/Cowork) once the account has it | `search_jobs(query="analyst", location="London", country_code="GB")` returns rows |
| **Adzuna** ⭐ | UK **and Canada** search (snippet only; full JD via `redirect_url`), **salary data** (histogram, history, regional, top companies, estimate) | bring-your-own-key, bundled MCP `adzuna` | <https://developer.adzuna.com/signup> | Register (separate from a jobseeker login) → **Create app** → copy **App ID** (8 chars) and **App Key** (32 chars) | `/plugin configure jobxhunter@soheil-jobxhunter` → `adzuna_app_id` + `adzuna_app_key`; or paste both to Claude Code | `python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_connectors.py" doctor` shows both `[OK]`; `adzuna_search_jobs(params={"what":"analyst","where":"London"})` returns rows |
| **Firecrawl** ⭐ | **Full JD** behind any link — Workday/Greenhouse/Lever, PDFs, careers pages; crawl/map a site | bring-your-own-key, bundled MCP `firecrawl` (`npx firecrawl-mcp`) | <https://www.firecrawl.dev> (free tier) | Sign up → dashboard → **API Keys** → copy the key (starts `fc-`) | `/plugin configure …` → `firecrawl_api_key`; or paste it to Claude Code | doctor shows `[OK] firecrawl_api_key`; `firecrawl_scrape(url=<any job URL>)` returns markdown |
| **Reed** | **UK-only** search + full JD, normalised salary, apply URL | bring-your-own-key, bundled MCP `reed` | <https://www.reed.co.uk/developers/jobseeker> | Register → **Jobseeker API** → copy the API key (36 chars). It is the HTTP Basic *username*; the server handles that | `/plugin configure …` → `reed_api_key`; or paste it to Claude Code | doctor shows `[OK] reed_api_key`; `reed_search_jobs(params={"keywords":"analyst","location_name":"London"})` returns rows |
| **Dice** (optional) | US-leaning tech roles; AI/data/software only | built-in claude.ai (OAuth, no key) | <https://claude.ai/settings/connectors> | none — **Connect** on the Dice card | nothing; tools appear as `mcp__claude_ai_Dice__*` / `Dice:*` | `search_jobs(q="machine learning")` returns rows |

⭐ = the three that buy the most. **Indeed costs nothing and needs no key**, so it comes first.

**How "paste it to Claude Code" works.** The user says *"here's my Adzuna app id … and key …"*.
As a plugin the values belong in the plugin's user-config: run
`claude plugin install jobxhunter@soheil-jobxhunter --config adzuna_app_id=… --config adzuna_app_key=…`
(repeatable; it applies the values even when it answers "already installed") or tell the user to run
`/plugin configure jobxhunter@soheil-jobxhunter`. Standalone (cloned skill folder, no plugin):
`python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_connectors.py" --emit <name>` prints the `mcpServers`
snippet; back up the config, merge it with the real key, tell the user to restart. Never write a key
into a skill file or a commit. **A key only reaches a connector at startup — restart Claude Code
after setting one.**

**Verify from a terminal:** `python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_connectors.py" doctor`
lists each key-based connector and whether its key is set (lengths only, never values), and prints
the enable steps for Indeed/Dice. It cannot see claude.ai connectors — `[? ]` there means *unknown*,
not missing; check the tool list or ask the user.

## Agent script — what to say, in this order

Rules: **one connector per message**, never the whole list at once. **Never block** — if the user
says "later", move on; everything still works on web search. Always say what still works without it.
Skip a connector the doctor already shows as set, and skip Reed for a Canada-market profile.

1. **Indeed** (first: free, no key)
   > "The best free job source is Indeed, and it needs no key. Open **claude.ai → Settings →
   > Connectors → Indeed → Connect**, then come back and say 'done'. Without it I search Adzuna,
   > Reed and the web instead."
   After "done": if `mcp__claude_ai_Indeed__search_jobs` (or `Indeed:search_jobs`) is not in the
   tool list, say *"Restart Claude Code once so the Indeed tools load, then tell me."*

2. **Adzuna**
   > "Next, Adzuna — the only board covering both the UK and Canada, plus salary data. Sign up at
   > **developer.adzuna.com/signup** (it's a separate developer account), create an app, and paste
   > me the **App ID** and **App Key**. Or say 'later' — I'll use web search for those roles."
   On receipt: register via `--config adzuna_app_id=… --config adzuna_app_key=…` (or
   `/plugin configure`), tell them to restart Claude Code, run the doctor.

3. **Firecrawl**
   > "Firecrawl reads the full job advert behind Workday, Greenhouse and Lever links and PDFs, so
   > the CV is tailored to the real text, not a snippet. Sign up at **firecrawl.dev**, open
   > **API Keys** in the dashboard, and paste me the key that starts `fc-`. Or 'later' — I'll fall
   > back to WebFetch, which misses some JavaScript-rendered pages."

4. **Reed** (UK profiles only)
   > "Reed is a UK-only board with full job descriptions. Get a free Jobseeker API key at
   > **reed.co.uk/developers/jobseeker** and paste it here. Or 'later'."

5. **Dice** (only if the profile is AI/data/software)
   > "Optional: Dice covers US-leaning tech roles. If you want it, **claude.ai → Settings →
   > Connectors → Dice → Connect**. Fine to skip."

Close with one line: *"Live now: … . Missing: … (web-search fallback covers them). Say the name any
time to add one."*

## Tool-name convention (both surfaces)
Tool names are written **bare** (`reed_search_jobs`). Resolve each to your surface's prefix:
- **Claude Code:** `mcp__<server>__<tool>` — e.g. `mcp__plugin_jobxhunter_reed__reed_search_jobs`
  for the bundled servers, `mcp__claude_ai_Indeed__search_jobs` for claude.ai connectors
  (standalone installs: `mcp__reed__reed_search_jobs`).
- **Claude Desktop / cowork:** `<server>:<tool>` — e.g. `reed:reed_search_jobs`, `Indeed:search_jobs`.
Server names: `Indeed`, `reed`, `adzuna`, `Dice`, `firecrawl`. If a name doesn't resolve, list
available tools and match by the `<server>` + `<tool>` pair.

## Job connectors (SOURCE fans out across all four)
| Connector | Tools | Use for | Notes |
|---|---|---|---|
| **Indeed** | `search_jobs`, `get_job_details`, `get_company_data`, `get_resume` | broad UK sourcing + employer vetting | `country_code='GB'` |
| **Reed** | `reed_search_jobs`, `reed_get_job_details` | UK security/data/admin/agency | distance in **MILES**; hidden salary = "Not disclosed", never £0 |
| **Adzuna** | `adzuna_search_jobs` + `adzuna_salary_histogram`/`salary_history`/`regional_breakdown`/`top_companies`/`list_categories` | wide UK aggregator + labour-market salary context | salaries ANNUAL, GBP for `gb` |
| **Dice** | `search_jobs` | US-leaning tech; AI/data families only | filters: `willing_to_sponsor`, `workplace_types`, `posted_date` |

**Full-JD capture (never tailor off a snippet):** Indeed `get_job_details` · Reed `reed_get_job_details`
(also normalised salary + apply URL) · Adzuna → fetch `redirect_url`. If none yield full text → crawl
with Firecrawl.

## JD capture / deep-crawl fallback
- **Firecrawl** (`firecrawl_scrape`, `firecrawl_extract`, `firecrawl_crawl`, `firecrawl_map`,
  `firecrawl_search`) — primary crawler; renders JS, clean markdown. Use for external ATS (Workday/
  Greenhouse/Lever), PDFs, company careers portals, and whole-site vacancy enumeration.
- **`/scrape`** skill (if installed) — single-page JD pull when Firecrawl isn't on the surface.
- **WebSearch / WebFetch** — lightweight; WebFetch needs a URL already in scope (WebSearch first).
- **Claude-in-Chrome** — last resort for login-gated flows (LinkedIn behind auth).

## Company discovery + cold outreach (DISCOVER + COLD MAIL)
- **Clay**: `find-and-enrich-company`, `find-and-enrich-contacts-at-company`, `query-objects`.
- **Ahrefs**: `site-explorer-organic-competitors` — surface same-sector companies from a known domain.
- **Gmail**: `create_draft`, `search_threads` — draft outreach, track replies.
- **Google Calendar**: `create_event` — book interviews.

## Prose voice + rendering
- **Writing model (built in)** — the voice/de-slop pass is the skill's own `references/writing-voice.md`,
  a register-aware standard covering ~33 AI-writing tells, plus the `cv-mistakes.md` banned-buzzword
  catalogue. Applied inline on every draft; no external skill, plugin, or key required.
- **`docx` / `pdf` / `xlsx`** skills — native rendering in cowork.
- **`/make-pdf`** (if installed) — human-facing / portfolio PDF. `.docx` stays the ATS submission.
- Bundled `scripts/` — the self-sufficient Claude Code path (see `scripts` in SKILL.md).

## Bundled scripts (part of the skill, in the workspace's `scripts/`)
`_lib.py` (workspace resolution + preflight) · `init_workspace.py` (scaffold) · `tracker.py`
(init/add/update/show/**dedupe**/**priority-view**) · `new_application.py` (folder + row, auto-inits
tracker) · `build_seen_ledger.py` (dedupe ledger) · `render_docx.py` (ATS-safe `.docx`+`.txt`).

## Availability reality (varies by surface — check, don't assume)
- **Claude Code:** the bundled Reed/Adzuna/Firecrawl servers (once keys are set) plus any claude.ai
  connector the account has (Indeed, Dice); `/make-pdf`, `/scrape` if installed.
- **Cowork / Claude Desktop:** the bundled stdio servers do not run in its sandbox — sourcing uses
  Indeed/Dice plus web search; Clay/Ahrefs/Gmail/Calendar and the `docx`/`pdf`/`xlsx` rendering
  skills live here and are often NOT in Claude Code. The skill's inline/bundled fallbacks cover
  their absence.
