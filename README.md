# job-hunt — a UK-first job-hunt skill

A general-purpose, UK-first **job-hunt skill** for Claude (Claude Code / chat, via a `SKILL.md`
skill). Its core is **CV tailoring** — read a master profile plus a job description and produce an
ATS-friendly, slop-free CV that survives both the machine parser and the six-second recruiter scan —
and it extends outward into the whole hunt: sourcing roles, discovering companies, cold outreach,
cover letters, a recruiter-persona scoring loop, an "alternative-world" ideal-candidate mode, and
application tracking.

It is deliberately **generic**: a dropped-in master profile makes it personal. The skill logic and
knowledge base never change based on whose profile they read.

---

## The problem it solves

Job applications fail in two places at once. An **ATS parser** (Workday, Greenhouse, Taleo, …) has to
read the CV as a clean text stream and match it to the posting's keywords; a **human recruiter** then
spends about six seconds deciding whether to keep reading. A CV optimised for one usually fails the
other — keyword-stuffing reads as spam to the human; beautiful prose in a two-column layout is
scrambled by the parser. On top of that, generic "corporate slop" ("results-driven team player,
passionate about synergy") is actively discounted by recruiters and adds no parser value.

This skill optimises for both audiences at once, enforces a hard **truth rule** (it never invents
facts — it selects, reframes, reorders, emphasises), and applies UK conventions by default.

---

## Design principles (the non-negotiables)

1. **The master profile is the only source of truth.** For any submittable CV, the skill selects,
   reframes, reorders and emphasises — it never invents a role, skill, number, date, or qualification.
2. **The profile is a decoupled data feed; the skill is the product.** The profile is inert data at a
   path you point the skill at. It can be anyone (yours, a friend's, an invented persona). Swap the
   path — skill logic is identical.
3. **Two audiences, one document.** Every CV must survive the ATS parser *and* the six-second scan.
4. **No slop.** Corporate filler is banned, enforced against a researched catalog of failure modes.
5. **The recruiter agent is critic *and* test harness.** The same JD-adapted persona that scores a
   draft during tailoring is the backbone of the skill's own evaluation.
6. **The dial goes from true to aspirational.** Tailoring runs on levels (below); only the top level
   generates beyond the profile, and only as a labelled, never-submittable learning artifact.
7. **Gaps are surfaced, not faked — but real experience isn't dropped either.** A profile is rarely a
   complete record of a person, so unmatched requirements are triaged: hard gaps are surfaced
   honestly; skills that plausibly exist under another name (or that a listed role obviously implies)
   are *provisionally* included and confirmed in one neutral yes/no batch at the end — a memory-jog,
   never an accusation.

---

## What it does — the commands

The skill spans the full pipeline: **SOURCE / DISCOVER → CAPTURE → TAILOR → RECRUITER LOOP →
COVER LETTER / COLD MAIL → TRACK & FILE.**

| Command | What it does |
|---|---|
| **SETUP / DAILY HUNT** | Scaffolds a job-hunt **workspace** for a new user (profile template + tracker + playbook) then stops; or, on a populated workspace, runs an autonomous **daily hunt** — sources, triages, tailors every new live match, files everything, and writes a dated summary. See `references/daily-hunt.md`. |
| **SOURCE** | Finds live roles via job connectors (Indeed, Reed, Adzuna, Dice — bring your own keys) and, when they don't cover a board, a deep-crawl fallback (Firecrawl → `WebSearch` → browser automation). Triages each hit against hard knockouts before tailoring. |
| **DISCOVER + COLD MAIL** | The hidden job market: builds a ranked target-company list (web search + Clay enrichment + Ahrefs "related companies"), finds the *named* hiring contact and a verified email, and drafts a short, human cold email — written from the user's own **spoken/verbal narrative**, voice preserved. |
| **TAILOR** (core) | Parse JD → build a coverage matrix → select & order evidence → draft (verb + task + method + outcome, keywords woven in, acronyms paired) → voice pass + integrity checks → render ATS-safe `.docx` + plain-text. |
| **RECRUITER LOOP** | Adopts a JD-specific recruiter persona (a fintech manager reads differently from an NHS panel) and scores the draft on five dimensions, returning a scorecard + ranked, actionable fixes. Loops until it passes a threshold or a pass limit. |
| **L2 — alternative world** | Generates a *realistic* stronger candidate who would win the interview, plus the **delta** — the specific experience/skills/certs between the real candidate and that persona. A learning roadmap; clean artifact, never presented as submittable. |
| **COVER LETTER** | Written from the user's own brain-dump (spoken narrative invited), preserving their voice while removing slop. Asks for the brain-dump first and waits — never cold-generates. |
| **TRACK & FILE** | Files every job into `applications/<category>/<date>_<company>_<role>/` (JD, CV, notes) and logs a tracker row. Applied rows turn green and lock; skipped/considered jobs are recorded too. |

### The tailoring dial (levels)

- **L0 — true, reframed.** Same facts, optimally worded and ordered. Always submittable.
- **L1 — aggressive but true (default).** Maximal *honest* emphasis; a `%` knob sets how aggressive.
  Still fully submittable — never fiction.
- **L2 — the alternative world.** A different realistic person who already holds what the JD wants,
  delivered alongside the delta-to-close. For learning/targeting only; never submitted.

---

## Architecture

```
job-hunt/
├── SKILL.md                     # the skill: workflow map + commands + non-negotiables
├── references/                  # the distilled knowledge base (progressive disclosure)
│   ├── cv-craft.md              # bullet anatomy, section design, quantification
│   ├── career-narrative.md      # turning a non-linear history into one coherent story
│   ├── cover-letter.md          # UK cover-letter craft + tone preservation
│   ├── ats-mechanics.md         # how Workday/Greenhouse/Taleo/… parse; format traps
│   ├── cv-mistakes.md           # researched catalog of failure modes; slop ban-list
│   ├── uk-conventions.md        # UK norms + per-sector deltas
│   ├── jd-analysis.md           # decompose a JD into knockouts/must/nice/level/salary
│   ├── recruiter-rubric.md      # the recruiter-critic's scoring brain
│   ├── tailoring-levels.md      # the L0/L1/L2 dial + gap classes + provisional rule
│   ├── master-profile-schema.md # the loose data contract for the profile feed
│   ├── job-search-guide.md      # sourcing: connectors, boards by family, deep crawl
│   ├── company-discovery-cold-outreach.md  # company search + cold-mail pipeline
│   └── keyword-taxonomy/        # weighted keyword maps per job family
├── assets/                      # CV markdown-input template, render contract, sample-profile.md (demo)
├── scripts/                     # deterministic Python helpers
│   ├── _lib.py                  # workspace resolution + dependency preflight
│   ├── init_workspace.py        # scaffold a new workspace (Setup mode)
│   ├── setup_connectors.py      # connector doctor — configured vs missing + bring-your-own-key guide
│   ├── render_docx.py           # markdown CV → ATS-safe .docx + .txt
│   ├── tracker.py               # xlsx + csv tracker; green/lock on Applied; dedupe; priority-view
│   ├── new_application.py       # create per-job folder + tracker row
│   └── build_seen_ledger.py     # canonical-key dedupe ledger for the daily hunt
├── kb-build/                    # provenance: live JD captures + raw research notes
└── evals/                       # validation runs (self-contained)
```

**Progressive disclosure:** `SKILL.md` stays lean (a workflow map); the heavy knowledge lives in
`references/` and loads only when a step needs it.

**The data feed is decoupled.** The skill ships one **demo fixture** — `assets/sample-profile.md` (an
anonymised sample persona) — so it runs out of the box. Your **real** profile and all application
outputs live in a separate, private location outside the skill, so the tool and the personal data stay
decoupled. To use the skill for anyone, point it at a different profile path.

---

## How it was built

- **Knowledge base (Phase 0):** built by *scrape-then-distil* — raw web research (recruiter blogs,
  ATS-vendor guides, UK university careers services, O\*NET/ESCO/LinkedIn taxonomies) plus live UK job
  descriptions pulled through a job connector, then distilled by hand into tight, opinionated
  reference docs. Raw notes and source URLs are preserved under `kb-build/` so any doc can be
  refreshed later.
- **Keyword taxonomy** is seeded from *live* postings (which age slower than advice blogs) across the
  target families, then enriched from the standard skills taxonomies.
- **Scripts** are deterministic Python (`python-docx`, `openpyxl`) so state changes — rendering,
  tracker green/lock, folder creation — are reproducible rather than model-improvised.

---

## Validation (eval)

The full pipeline was run end-to-end on live UK job descriptions across several families, with an
**independent recruiter agent** scoring each CV (so the tailorer never grades its own work):

| Case | Level | Recruiter score | Outcome |
|---|---|---|---|
| Strong-match research placement | L1 | **4.0 / 5** | forward with caveats |
| Role needing a PhD + niche lab skills | L2 | n/a | alternative-world persona + delta roadmap; not submitted |
| Research assistant (partial fit) | L1 | 2.9 / 5 | revise; real qualitative-methods gap surfaced |
| Junior ML engineer (genuine stretch) | L1 + cover letter | 2.9 / 5 | honest stretch; missing stack *not* faked |

What it proved:

- **The truth invariant holds — and the loop enforces it.** In one case the recruiter caught the
  tailorer *drifting* into JD-echo phrases with no basis in the profile; they were removed. The
  recruiter loop functions as a **truth backstop**, not just polish. That lesson was hardened back
  into the skill (an anti-mirroring guard + a truth sweep).
- **Scores discriminate honestly.** A true match scored 4.0; genuine stretches scored 2.9 with clear
  reasons — the rubric isn't a rubber stamp.
- **Gaps are surfaced, not filled;** the L2 delta reads as a roadmap; the cover letter preserved the
  candidate's own voice and disclosed a real gap rather than papering over it.
- **Mechanics verified:** ATS-safe `.docx` (no tables/columns/text-boxes/images — checked in the
  document XML) + plain-text export; tracker green/lock/date-stamp; per-job folders; portability
  (a second profile renders through identical logic).

---

## Requirements

- Claude Code (or a `SKILL.md`-compatible Claude host).
- Python 3 with `python-docx` and `openpyxl` (`pip install python-docx openpyxl`). The scripts
  **preflight** these and fail with the exact fix if missing.
- Optional connectors that enhance sourcing/outreach — **bring your own** (see next section).

---

## Connectors & API keys — bring your own

**This skill ships with NO API keys, and none are committed to this repo.** The job connectors are
Model-Context-Protocol (MCP) servers that *you* register in *your own* Claude config, each with *your
own* key. The skill only ever calls tools **by name** (`reed_search_jobs`, `adzuna_search_jobs`,
`firecrawl_scrape`, …) — it never contains a credential. Your keys live in your MCP config
(`~/.claude.json` for Claude Code, or the Claude Desktop config) — a file **outside this repository**.
Never paste a key into a skill file, a profile, or a commit.

**The setup flow:** you sign up for a connector and get **your own free API key** (Firecrawl needs a
free account too), then **paste the key to Claude in chat** — and **Claude sets up the MCP server for
you** (backs up your config, adds the entry, tells you to restart). You never hand-edit JSON. Every
connector is **optional**: the skill detects what you've configured and degrades gracefully (each
sourcing lane has a fallback). Configure the ones you want:

| Connector | Get a key | Cost |
|---|---|---|
| **Reed** (UK jobs) | https://www.reed.co.uk/developers — free Jobseeker API key | free |
| **Adzuna** (UK jobs + salary data) | https://developer.adzuna.com — free `app_id` + `app_key` | free tier |
| **Firecrawl** (JD crawling) | https://www.firecrawl.dev — API key (`fc-…`) | free tier + paid |
| **Indeed / Dice** (jobs) | via their claude.ai connectors (OAuth — no manual key) | per host |
| **Clay / Ahrefs / Gmail / Calendar** (discovery + outreach) | your own accounts / connectors | per service |

**How to register (example — Reed, Claude Code `~/.claude.json`):**
```jsonc
"mcpServers": {
  "reed": {
    "command": "python",
    "args": ["path/to/reed-mcp/server.py"],
    "env": { "REED_API_KEY": "YOUR_OWN_KEY_HERE" }   // your key, never committed
  },
  "firecrawl": {
    "command": "npx",
    "args": ["-y", "firecrawl-mcp"],
    "env": { "FIRECRAWL_API_KEY": "YOUR_OWN_KEY_HERE" }
  }
}
```
Keep `.env` files and MCP configs out of git (this repo's `.gitignore` already excludes `.env`). If a
connector isn't configured, the skill falls back to `WebSearch`/browser crawling for that lane —
nothing breaks, it's just less structured. See `references/tools-and-connectors.md` for the full map.

**Recommended companion skills (keyless, optional).** For the CV/cover-letter voice pass the skill
routes to `/humanizer`, then `/academic-prose`. A good MIT-licensed `/humanizer` is
[blader/humanizer](https://github.com/blader/humanizer) — `npx skills add blader/humanizer`.
`/academic-prose` is optional and has no public default the skill assumes — bring your own if you have
one. For a polished human-facing PDF, `/make-pdf` if available. All are optional — the skill de-slops
inline (`references/cv-mistakes.md`) and renders via its bundled scripts when they're absent.

**First-run setup.** New users don't have the connectors yet. Run
`python scripts/setup_connectors.py` for a report of what's configured and step-by-step guidance to
get your own free keys and register the ones you want. Full walkthrough:
`references/connector-setup.md`.

## Using it

1. Point the skill at a profile that conforms to `references/master-profile-schema.md`.
2. Give it a job description (pasted, a file, or captured via a connector) and a level (L0 / L1 / L2).
3. It parses the JD, builds a coverage matrix against real evidence, drafts and de-slops an ATS-safe
   CV, runs the recruiter loop, renders `.docx` + `.txt`, and files everything with a tracker row.
4. Say "I applied to this one" to turn the row green and lock it.

A sample profile is included so the skill can be tried without supplying real data.

---

## Privacy note (if publishing)

The **skill itself** (this folder) is the publishable artifact. The **personal data feed** — real
profiles and filed applications — is intentionally kept separate and should not be committed. The
included sample profile and eval outputs use a **sample persona** for demonstration; scrub or replace
them before publishing if you prefer. A suggested `.gitignore` for a personal deployment excludes the
profiles/applications directory entirely.

---

## Roadmap

- **One-command connector install** — publish the Reed/Adzuna MCP servers (npm/pip) so setup is
  `npx`/`pip install` + your key, instead of pointing at a local clone.
- **CLI packaging** — install the skill + scripts via a single command.
- **Plugin marketplace** — bundle as a Claude plugin so it installs from the marketplace with its
  companion skills and connector prompts wired in.

## Status

Built and validated across the target job families. The knowledge base, scripts, and command set are
complete; plugging in a production profile is a straightforward, non-code step (change one path).

*Built with Claude. UK-first by design; the conventions layer can be swapped for another market.*
