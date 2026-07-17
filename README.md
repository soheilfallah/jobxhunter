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
| **SOURCE** | Finds live roles via job connectors (Indeed, Dice) and, when they don't cover a board, a deep-crawl fallback (`WebSearch` → `WebFetch` → browser automation; or a Firecrawl-style crawl MCP if connected). Triages each hit against hard knockouts before tailoring. |
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
│   ├── render_docx.py           # markdown CV → ATS-safe .docx + .txt
│   ├── tracker.py               # xlsx + csv tracker; green/lock on Applied
│   └── new_application.py       # create per-job folder + tracker row
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
- Python 3 with `python-docx` and `openpyxl` (`pip install python-docx openpyxl`).
- Optional connectors that enhance sourcing/outreach if available in the host: a job search connector
  (e.g. Indeed/Dice), a company/contact enrichment connector (e.g. Clay), a competitor-discovery
  source (e.g. Ahrefs), email drafting (e.g. Gmail), and browser automation for deep crawls.

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

## Status

Built and validated across the target job families. The knowledge base, scripts, and command set are
complete; plugging in a production profile is a straightforward, non-code step (change one path).

*Built with Claude. UK-first by design; the conventions layer can be swapped for another market.*
