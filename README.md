<p align="center">
  <img src="assets/brand/jobsmith-icon.svg" width="96" alt="">
</p>

<h1 align="center">jobsmith</h1>

<p align="center"><strong>Your real experience in → tailored, ATS-safe applications out, without a single invented fact.</strong></p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude%20Code-plugin%20%2B%20skill-6E56CF" alt="Claude Code">
  <img src="https://img.shields.io/badge/markets-UK%20%2B%20Canada-1f6feb" alt="Markets">
  <img src="https://img.shields.io/badge/truth%20rule-never%20invents%20facts-2ea043" alt="Truth rule">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
</p>

A Claude Code **plugin** (and skill) for the **UK and Canada**, with more markets coming. It builds a master profile from your own files, tailors a CV and cover letter to each job, sources live roles across job boards, and tracks every application. The profile is a decoupled data feed, so you can point it at anyone.

<!-- Add a short demo GIF here (a /jobsmith:tailor run). It's the single biggest README upgrade. -->

---

## Quick start

```
/plugin marketplace add soheilfallah/jobsmith
/plugin install jobsmith@soheil-jobsmith
/jobsmith:setup
```

Then drop your old CVs and notes into the `dump/` folder it creates and run `/jobsmith:intake` to build your master profile.

---

## Install

### Plugin (recommended)

In Claude Code:

```
/plugin marketplace add soheilfallah/jobsmith
/plugin install jobsmith@soheil-jobsmith
/reload-plugins
```

Or from a terminal, for scripted or non-interactive setups:

```bash
claude plugin marketplace add soheilfallah/jobsmith
claude plugin install jobsmith@soheil-jobsmith
```

> [!IMPORTANT]
> **You'll want free API keys for the job connectors.** Claude Code prompts for them during install, and nothing is committed. jobsmith *runs* without them, because sourcing falls back to web search, but you get noticeably fewer roles and job descriptions aren't deep-crawled.
>
> | Connector | Get a free key | What you lose without it |
> |---|---|---|
> | **[Adzuna](https://developer.adzuna.com/signup)** ⭐ | `developer.adzuna.com/signup` | UK **and Canada** job search, plus salary data |
> | **[Firecrawl](https://www.firecrawl.dev)** ⭐ | `firecrawl.dev` | Full job-description crawling on Workday / Greenhouse / Lever and PDFs |
> | **[Reed](https://www.reed.co.uk/developers/jobseeker)** | `reed.co.uk/developers/jobseeker` | UK-only listings (skip it if you're hunting in Canada) |
>
> ⭐ = the two that matter most. All are free to start; leave any blank to skip it.

### Try it without installing

```bash
git clone https://github.com/soheilfallah/jobsmith
claude --plugin-dir ./jobsmith
```

Loads for that session only.

### As a plain skill

Also works in Claude Desktop / cowork, which have no plugin system:

```bash
git clone https://github.com/soheilfallah/jobsmith ~/.claude/skills/jobsmith
pip install python-docx openpyxl
```

In this mode `${CLAUDE_PLUGIN_ROOT}` isn't set. Read it as the clone directory wherever a command mentions it.

### Requirements

| Requirement | Needed for |
|---|---|
| **Claude Code** | everything, or any `SKILL.md`-compatible host |
| **[`uv`](https://docs.astral.sh/uv/getting-started/installation/)** | the Reed / Adzuna connectors only. They self-resolve on first launch, so there's nothing to `pip install` |
| **Python 3** | CV rendering and the tracker, via `python-docx` + `openpyxl`. The scripts preflight and print the exact fix if missing |

---

## Commands

| Command | What it does |
|---|---|
| `/jobsmith:setup` | Scaffold your private workspace and connect job boards (bring your own keys) |
| `/jobsmith:intake` | Build your master profile from a folder of raw files: old CVs, LinkedIn export, notes, certificates |
| `/jobsmith:hunt` | Autonomous daily hunt. Sources, triages, and tailors every new live role, then files it |
| `/jobsmith:tailor` | Tailor an ATS-safe CV to one job description, with a recruiter-persona scoring loop |
| `/jobsmith:cover-letter` | Draft a cover letter in your own voice, to your market's conventions |
| `/jobsmith:discover` | Find target companies in the hidden job market and draft a cold email to the named contact |

You can also just talk to it in plain language. The commands are shortcuts.

---

## First run

1. **`/jobsmith:setup`** scaffolds a private workspace (`profiles/`, `dump/`, `applications/`, a tracker, and a `WORKSPACE-MAP.md`), then stops.
2. **Drop your files** into `dump/`: old CVs, LinkedIn PDF, certificates, notes.
3. **`/jobsmith:intake`** reads them, builds your master profile, and interviews you to fill the thin spots.
4. **`/jobsmith:tailor`** (one role) or **`/jobsmith:hunt`** (find + tailor many). Say *"I applied to this one"* to lock the tracker row.

---

## What it does differently

- **It never invents facts.** The master profile is the only source of truth. The skill selects, reframes, and reorders; gaps are surfaced, not faked. No fabricated titles, numbers, or skills.
- **Survives both readers.** Every CV is built for the **ATS parser** *and* the **six-second recruiter scan**, not one at the cost of the other.
- **A recruiter loop.** A JD-specific recruiter persona scores each draft and demands fixes until it passes. In testing it caught the tailorer drifting into unsupported buzzwords, and removed them.
- **Intake before tailoring.** Intake reads every file in your dump folder (with placeholders for formats it can't parse), runs incrementally, and asks targeted questions to fill thin spots.
- **No slop.** A researched ban-list blocks phrasing like "results-driven team player, passionate about synergy".
- **Everything filed.** Per-job folders and a locked tracker. Submit the `.docx` to the ATS, keep a PDF for humans.
- **Two markets, more coming.** The UK and Canada both work out of the box: A4 CV vs US-Letter résumé, British vs Canadian spelling, Reed/Adzuna vs Job Bank / Indeed.ca / University Affairs. Market is read from your profile, not hard-coded, so a new one is a conventions doc plus a board list. The engine doesn't change.

---

## How it works

```
intake → source → tailor (ATS + recruiter loop) → cover letter → track & file
```

The engine is `SKILL.md` (a lean workflow map); the deep knowledge lives in `references/` and loads only when a step needs it. Deterministic Python (`scripts/`) owns rendering and tracking so results are reproducible, not improvised. Full detail: [`SKILL.md`](SKILL.md).

The **tailoring dial:** `L0` true-and-reframed · `L1` aggressive-but-true (default) · `L2` an "alternative-world" ideal candidate + the gap-to-close (a roadmap, never submitted).

---

## Connectors: bring your own keys

No keys ship in this repo. Each job board is an optional MCP connector you register with your own free key; missing ones fall back to web search.

| Connector | Key | Cost |
|---|---|---|
| **Reed** (UK jobs) | [reed.co.uk/developers](https://www.reed.co.uk/developers) | free |
| **Adzuna** (UK + Canada jobs, salary data) | [developer.adzuna.com](https://developer.adzuna.com) | free tier |
| **Firecrawl** (job-description crawling) | [firecrawl.dev](https://www.firecrawl.dev) | free tier + paid |
| **Indeed / Dice** | claude.ai connectors (OAuth) | per host |

As a plugin, these keys are the plugin's user-config, so there's no manual JSON editing. Full map: [`references/tools-and-connectors.md`](references/tools-and-connectors.md).

---

## Validated

The pipeline was run end-to-end on live UK job descriptions, with an **independent recruiter agent** scoring each CV (the tailorer never grades its own work):

| Case | Level | Recruiter score |
|---|---|---|
| Strong-match research placement | L1 | **4.0 / 5** |
| Research assistant (partial fit) | L1 | 2.9 / 5, real gap surfaced not faked |
| Junior ML engineer (genuine stretch) | L1 + letter | 2.9 / 5, missing stack disclosed |

A true match scored 4.0; genuine stretches scored lower, with the reasons stated. ATS-safety was verified in the document XML.

---

## Privacy & supply chain

- **Your data stays yours.** Your real profiles and filed applications live in a private workspace and are gitignored, never committed. No keys ship in this repo.
- **Connector installs can't be hijacked.** `uv` and `npx` read config from the *working directory*, so a stray `uv.toml` or `.npmrc` in whatever folder you opened could otherwise redirect a connector's install to someone else's package index. All three connectors pin resolution to the real registries and to committed hash-verified lockfiles. If you add a dependency, re-run `uv lock --script connectors/<name>-mcp/server.py`. A stale lock fails the connector closed rather than silently resolving something else.

---

## Contributing

Issues and PRs welcome. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md), which covers the truth rule every change has to hold, how to test a real install, and the three things that silently break the plugin. Every change lands through a reviewed pull request.

See [`CHANGELOG.md`](CHANGELOG.md) for what's landed.

## Licence

MIT © Soheil Fallah. See [`LICENSE`](LICENSE).
