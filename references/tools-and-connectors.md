# Tools & connectors this skill uses (the manifest)

One place that names every external tool/skill `/job-hunt` orchestrates, what it's for, and its
fallback. **Detect what the surface exposes** (list your tools/skills if unsure) and route
accordingly — every route has a self-sufficient fallback, so the skill never hard-depends on an
optional tool.

> **Bring your own keys.** No API keys ship with this skill and none are in the repo. Each connector
> below is an MCP server the user registers in their own Claude config with their own key (see the
> README, "Connectors & API keys — bring your own"). The skill only calls tools by name; it never
> holds a credential. Every connector is optional — absent ones fall back to WebSearch/browser.

## Tool-name convention (both surfaces)
Tool names are written **bare** (`reed_search_jobs`). Resolve each to your surface's prefix:
- **Claude Code:** `mcp__<server>__<tool>` — e.g. `mcp__reed__reed_search_jobs`.
- **Claude Desktop / cowork:** `<server>:<tool>` — e.g. `reed:reed_search_jobs`.
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
- **Registered/available now:** all four job connectors + Firecrawl (MCP); `/make-pdf`, `/scrape`
  (Claude Code); Clay/Ahrefs/Gmail/Calendar (cowork connectors).
- **Cowork-side, often NOT in Claude Code:** the `docx`/`pdf`/`xlsx` rendering skills. The skill's
  inline/bundled fallbacks cover their absence.
