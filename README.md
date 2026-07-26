<img src="assets/brand/jobsmith-icon.svg" width="84" align="left" alt="" hspace="18" vspace="4">

# jobsmith

**Your real experience in → tailored, ATS-safe applications out — without a single invented fact.**

<br clear="left">

![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin%20%2B%20skill-6E56CF) ![Market](https://img.shields.io/badge/markets-UK%20%2B%20Canada-1f6feb) ![Truth rule](https://img.shields.io/badge/truth%20rule-never%20invents%20facts-2ea043) ![License](https://img.shields.io/badge/license-MIT-blue)

A Claude Code **plugin** (and skill) for the **UK and Canada** — more markets coming — that builds a master profile from your own files, tailors a CV and cover letter to each job, sources live roles across job boards, and tracks every application. The profile is a decoupled data feed — point it at anyone.

<!-- Add a short demo GIF here (a /jobsmith:tailor run) — it's the single biggest README upgrade. -->

---

## Quick start

```
/plugin marketplace add soheilfallah/jobsmith
/plugin install jobsmith@soheil-jobsmith
/jobsmith:setup
```

Then drop your old CVs and notes into the `dump/` folder it creates, run `/jobsmith:intake`, and you have a master profile. Everything else tailors from there.

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

Keys (Reed / Adzuna / Firecrawl) are prompted on install and all optional — leave them blank and sourcing falls back to web search. Nothing is committed.

### Try it without installing

```bash
git clone https://github.com/soheilfallah/jobsmith
claude --plugin-dir ./jobsmith
```

Loads for that session only. The cleanest way to kick the tyres.

### As a plain skill

Also works in Claude Desktop / cowork, which have no plugin system:

```bash
git clone https://github.com/soheilfallah/jobsmith ~/.claude/skills/jobsmith
pip install python-docx openpyxl
```

In this mode `${CLAUDE_PLUGIN_ROOT}` isn't set — read it as the clone directory wherever a command mentions it.

### Requirements

| Requirement | Needed for |
|---|---|
| **Claude Code** | everything — or any `SKILL.md`-compatible host |
| **[`uv`](https://docs.astral.sh/uv/getting-started/installation/)** | the Reed / Adzuna connectors only. They self-resolve on first launch — nothing to `pip install` |
| **Python 3** | CV rendering and the tracker, via `python-docx` + `openpyxl`. The scripts preflight and print the exact fix if missing |

---

## Commands

| Command | What it does |
|---|---|
| `/jobsmith:setup` | Scaffold your private workspace and connect job boards (bring your own keys) |
| `/jobsmith:intake` | Build your master profile from a folder of raw files — old CVs, LinkedIn export, notes, certificates |
| `/jobsmith:hunt` | Autonomous daily hunt — source, triage, and tailor every new live role, then file it |
| `/jobsmith:tailor` | Tailor an ATS-safe CV to one job description, with a recruiter-persona scoring loop |
| `/jobsmith:cover-letter` | Draft a cover letter in your own voice, to your market's conventions |
| `/jobsmith:discover` | Find target companies in the hidden job market and draft a cold email to the named contact |

You can also just talk to it in plain language — the commands are shortcuts.

---

## First run

1. **`/jobsmith:setup`** — scaffolds a private workspace (`profiles/`, `dump/`, `applications/`, a tracker, and a `WORKSPACE-MAP.md`), then stops.
2. **Drop your files** — old CVs, LinkedIn PDF, certificates, notes — into `dump/`.
3. **`/jobsmith:intake`** — reads them, builds your master profile, and interviews you to fill the thin spots.
4. **`/jobsmith:tailor`** (one role) or **`/jobsmith:hunt`** (find + tailor many). Say *"I applied to this one"* to lock the tracker row.

---

## Why it's different

- **It never invents facts.** The master profile is the only source of truth — the skill selects, reframes, and reorders; gaps are surfaced, not faked. No fabricated titles, numbers, or skills.
- **Beats both readers.** Every CV is built to survive the **ATS parser** *and* the **six-second recruiter scan** — not one at the cost of the other.
- **A recruiter loop that fights back.** A JD-specific recruiter persona scores each draft and demands fixes until it passes — it caught the tailorer drifting into buzzwords with no basis, and removed them.
- **Profiling-first, so nothing reads vague.** Intake ingests every file (placeholders for formats it can't read), stays incremental, and asks targeted questions — concrete evidence beats generic filler.
- **No slop.** A researched ban-list kills "results-driven team player, passionate about synergy."
- **Everything filed.** Per-job folders + a locked tracker; submit the `.docx` to ATS, keep a PDF for humans.
- **Two markets today, more coming.** The UK and Canada both work out of the box — A4 CV vs US-Letter résumé, British vs Canadian spelling, Reed/Adzuna vs Job Bank / Indeed.ca / University Affairs. Market is read from your profile, not hard-coded, so a new one is a conventions doc plus a board list — the engine doesn't change.

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
| **Adzuna** (UK + Canada jobs, salary data) | [developer.adzuna.com](https://developer.adzuna.com) | free tier |
| **Firecrawl** (job-description crawling) | [firecrawl.dev](https://www.firecrawl.dev) | free tier + paid |
| **Indeed / Dice** | claude.ai connectors (OAuth) | per host |

As a plugin, these keys are the plugin's user-config — no manual JSON editing. Full map: [`references/tools-and-connectors.md`](references/tools-and-connectors.md).

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

## Privacy & supply chain

- **Your data stays yours.** The skill is the publishable artifact; your real profiles and filed applications live in a private workspace and are gitignored — never committed. No keys ship in this repo.
- **Connector installs can't be hijacked.** `uv` and `npx` read config from the *working directory*, so a stray `uv.toml` or `.npmrc` in whatever folder you opened could otherwise redirect a connector's install to someone else's package index. All three connectors pin resolution to the real registries and to committed hash-verified lockfiles. If you add a dependency, re-run `uv lock --script connectors/<name>-mcp/server.py` — a stale lock fails the connector closed rather than silently resolving something else.

---

## Contributing & license

Issues and PRs welcome — see [`CHANGELOG.md`](CHANGELOG.md) for what's landed. Run `claude plugin validate . --strict` before opening a PR; it's the same check the marketplace review pipeline runs.

**Working on the repo itself?** Opening this directory in Claude Code shows `reed` and `adzuna` as failed connectors, warning `Missing environment variables: CLAUDE_PLUGIN_ROOT`. That's expected and not a bug: your cwd makes `.mcp.json` load as a *project* config, and `${CLAUDE_PLUGIN_ROOT}` only exists when it loads as a *plugin*. Test the real thing with `claude --plugin-dir .` from a directory outside the repo.

### Releasing

This plugin pins an explicit `version`, so **users receive changes only when you bump it** — pushing commits alone does nothing, and `/plugin update` will report "already at the latest version". To ship:

1. Bump `version` in **both** `.claude-plugin/plugin.json` and the marketplace entry.
2. Add a matching `## [x.y.z]` section to [`CHANGELOG.md`](CHANGELOG.md).
3. `python scripts/check_release.py` — verifies steps 1 and 2, that the manifests agree on name and version, and that no dead `job-hunt` URLs or command namespaces crept back in.
4. `claude plugin validate . --strict` — the same check the marketplace review pipeline runs.

Steps 3 and 4's automatable parts run on every PR via [`.github/workflows/release-check.yml`](.github/workflows/release-check.yml), which also asserts the connector lockfiles exist and that `setup_connectors.py` hasn't drifted from `.mcp.json`.

> **A structural warning.** `SKILL.md` lives at the plugin root, which Claude Code supports for a plugin shipping *exactly one* skill. **Do not add a `skills/` directory without also moving `SKILL.md` into it** — creating `skills/` makes the root file stop loading, silently. Verified: the current layout loads 7 skills; adding `skills/` drops it to 6 and the `jobsmith` engine disappears while every command still references it.

MIT © Soheil Fallah — see [`LICENSE`](LICENSE).

*Built with Claude. UK and Canada ship today; the conventions layer is designed for the next market to drop in.*
