# job-hunt

**Your real experience in → tailored, ATS-safe applications out — without a single invented fact.**

A UK-first Claude Code **plugin** (and skill) — **with Canada built in** — that builds a master profile from your own files, tailors a CV and cover letter to each job, sources live roles across job boards, and tracks every application. The profile is a decoupled data feed — point it at anyone.

![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin%20%2B%20skill-6E56CF) ![Market](https://img.shields.io/badge/market-UK%20%2B%20Canada%20built--in-1f6feb) ![Truth rule](https://img.shields.io/badge/truth%20rule-never%20invents%20facts-2ea043)

<!-- Add a short demo GIF here (a /job-hunt:tailor run) — it's the single biggest README upgrade. -->

---

## Commands

| Command | What it does |
|---|---|
| `/job-hunt:setup` | Scaffold your private workspace and connect job boards (bring your own keys) |
| `/job-hunt:intake` | Build your master profile from a folder of raw files — old CVs, LinkedIn export, notes, certificates |
| `/job-hunt:hunt` | Autonomous daily hunt — source, triage, and tailor every new live role, then file it |
| `/job-hunt:tailor` | Tailor an ATS-safe CV to one job description, with a recruiter-persona scoring loop |
| `/job-hunt:cover-letter` | Draft a UK cover letter in your own voice |
| `/job-hunt:discover` | Find target companies in the hidden job market and draft a cold email to the named contact |

You can also just talk to it in plain language — the commands are shortcuts.

---

## Install

**As a plugin (recommended):**

```
/plugin marketplace add soheilfallah/job-hunt
/plugin install job-hunt@soheil-job-hunt
/reload-plugins
```

Keys (Reed / Adzuna / Firecrawl) are prompted on install and optional — leave blank to fall back to web search. Nothing is committed.

**Prerequisites:**

- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) — the Reed and Adzuna connectors run as `uv run --script`, which resolves their dependencies into an isolated environment on first launch. Nothing to `pip install`. Firecrawl needs nothing.
- Python with `python-docx` and `openpyxl` for the bundled scripts (CV rendering and the tracker). They preflight and tell you the exact `pip install` if missing.

**As a plain skill (also works in Claude Desktop / cowork):**

```
git clone https://github.com/soheilfallah/job-hunt ~/.claude/skills/job-hunt
pip install python-docx openpyxl
```

Note: in this mode `${CLAUDE_PLUGIN_ROOT}` is not set, so read it as the clone directory when you see it in a command.

---

## First run

1. **`/job-hunt:setup`** — scaffolds a private workspace (`profiles/`, `dump/`, `applications/`, a tracker, and a `WORKSPACE-MAP.md`), then stops.
2. **Drop your files** — old CVs, LinkedIn PDF, certificates, notes — into `dump/`.
3. **`/job-hunt:intake`** — reads them, builds your master profile, and interviews you to fill the thin spots.
4. **`/job-hunt:tailor`** (one role) or **`/job-hunt:hunt`** (find + tailor many). Say *"I applied to this one"* to lock the tracker row.

---

## Why it's different

- **It never invents facts.** The master profile is the only source of truth — the skill selects, reframes, and reorders; gaps are surfaced, not faked. No fabricated titles, numbers, or skills.
- **Beats both readers.** Every CV is built to survive the **ATS parser** *and* the **six-second recruiter scan** — not one at the cost of the other.
- **A recruiter loop that fights back.** A JD-specific recruiter persona scores each draft and demands fixes until it passes — it caught the tailorer drifting into buzzwords with no basis, and removed them.
- **Profiling-first, so nothing reads vague.** Intake ingests every file (placeholders for formats it can't read), stays incremental, and asks targeted questions — concrete evidence beats generic filler.
- **No slop.** A researched ban-list kills "results-driven team player, passionate about synergy."
- **Everything filed.** Per-job folders + a locked tracker; submit the `.docx` to ATS, keep a PDF for humans.
- **UK-first, Canada built in, swappable.** UK conventions by default; Canada works out of the box (US-Letter résumé, Canadian spelling, Job Bank / Indeed.ca / University Affairs). Add another market by dropping in a conventions doc.

---

## How it works

```
intake → source → tailor (ATS + recruiter loop) → cover letter → track & file
```

The engine is `SKILL.md` (a lean workflow map); the deep knowledge lives in `references/` and loads only when a step needs it. Deterministic Python (`scripts/`) owns rendering and tracking so results are reproducible, not improvised. Full detail: [`SKILL.md`](SKILL.md).

The **tailoring dial:** `L0` true-and-reframed · `L1` aggressive-but-true (default) · `L2` an "alternative-world" ideal candidate + the gap-to-close (a roadmap, never submitted).

---

## Connectors — bring your own keys

No keys ship in this repo. Each job board is an optional MCP connector you register with your own free key; missing ones fall back to web search.

| Connector | Key | Cost |
|---|---|---|
| **Reed** (UK jobs) | [reed.co.uk/developers](https://www.reed.co.uk/developers) | free |
| **Adzuna** (UK jobs + salary data) | [developer.adzuna.com](https://developer.adzuna.com) | free tier |
| **Firecrawl** (job-description crawling) | [firecrawl.dev](https://www.firecrawl.dev) | free tier + paid |
| **Indeed / Dice** | claude.ai connectors (OAuth) | per host |

As a plugin, these keys are the plugin's user-config — no manual JSON editing. Full map: `references/tools-and-connectors.md`.

---

## Validated

The pipeline was run end-to-end on live UK job descriptions, with an **independent recruiter agent** scoring each CV (the tailorer never grades its own work):

| Case | Level | Recruiter score |
|---|---|---|
| Strong-match research placement | L1 | **4.0 / 5** |
| Research assistant (partial fit) | L1 | 2.9 / 5 — real gap surfaced, not faked |
| Junior ML engineer (genuine stretch) | L1 + letter | 2.9 / 5 — missing stack disclosed |

Scores discriminate honestly: a true match scored 4.0; genuine stretches scored lower with clear reasons. ATS-safety was verified in the document XML.

---

## Notes

- **Privacy:** the skill is the publishable artifact; your real profiles and filed applications live in a private workspace and are gitignored — never committed.
- **Requirements:** Claude Code (or a `SKILL.md`-compatible host) + Python 3 with `python-docx` and `openpyxl` (the scripts preflight these and fail with the exact fix).
- **Status:** built and validated across several job families; plugging in a real profile is a one-path, non-code step.

*Built with Claude. UK-first by design; the conventions layer swaps for other markets.*
