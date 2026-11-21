<p align="center">
  <img src="assets/brand/jobxhunter-icon.svg" width="88" alt="">
</p>

<h1 align="center">jobxhunter</h1>

<p align="center"><strong>Finds the jobs worth your application. Then fits your CV to each one.</strong></p>

<p align="center">
  Agents search the UK and Canada job boards, read every advert in full, judge it against your own master CV, and file the ones worth applying to. Tailoring is a separate step you start when you have chosen.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude%20Code-plugin%20%2B%20skill-590000" alt="Claude Code">
  <img src="https://img.shields.io/badge/markets-UK%20%2B%20Canada-6b4a45" alt="Markets">
  <img src="https://img.shields.io/badge/agent--run-no%20scoring%20scripts-590000" alt="Agent-run">
  <img src="https://img.shields.io/badge/license-MIT-590000" alt="License">
</p>

---

## Why I built this

I was hunting for a job in the UK, and I built this to take the grunt work off my plate: re-cutting the CV for every role, mapping it to the job description, keeping it honest and ATS-readable, filing it, tracking it.

It worked. I found a job. Then a friend in Canada asked me to run their search too, so I made Canada work out of the box. Then a friend in Italy asked. So instead of hard-coding one country, I made the market a setting, and more are on the way.

It works from your real history and shows you the gaps to close.

It's the tool I used for my own hunt, and my friends used for theirs. It's yours now too.

[Soheil](https://github.com/soheilfallah)

---

## Quick start

```
/plugin marketplace add soheilfallah/jobxhunter
/plugin install jobxhunter@soheil-jobxhunter
/jobxhunter:setup
```

Leave the API-key prompts blank during install. They are optional and come last. Full walkthrough: [`SETUP.md`](SETUP.md), five steps. Pasting this repo into Claude Code? Say *"set me up"* and it follows that file one step at a time.

---

## How it works

```
setup  →  intake  →  masters  →  search  →  tailor
folder    profile    one CV      find and    fit one CV
          from your  per role    judge       to one job
          files
```

| Command | What it does |
|---|---|
| `/jobxhunter:setup` | Makes your private workspace, copies the connector guides into it, and tests which job boards are really connected |
| `/jobxhunter:intake` | Reads the old CVs and notes you drop in `dump/`, writes one plain profile, and agrees the roles you are going for |
| `/jobxhunter:masters` | Writes a master CV for each of those roles, from your profile alone. You edit them; they are yours |
| `/jobxhunter:search` | Searches every board for every role and evaluates each advert against the right master CV. **Never tailors** |
| `/jobxhunter:tailor` | Fits the role's master CV to one job you picked from the shortlist |
| `/jobxhunter:cover-letter` | Writes a finished cover letter in your voice |
| `/jobxhunter:interview` | Builds interview prep from a filed job, gaps included |
| `/jobxhunter:discover` | Finds employers to approach directly and drafts the cold email |

You can also just talk to it in plain language. The commands are shortcuts.

## What makes it different

- **Agents judge, not scripts.** Whether a job fits you is decided by an agent that has read the whole advert and your master CV. Nothing ranks a role by keyword overlap or a title match.
- **More than one master CV.** A data role and an operations role need different evidence up front. You get a master CV per role you are going for, and every tailored CV starts from the right one.
- **The first search is massive.** Every title, on every connected board, with no date limit, until the boards run dry. Later searches only fetch what is new.
- **Search and tailoring never mix.** A search ends at a ranked shortlist. You read it, choose, and then tailor. No CV is written for a job you would not apply to.
- **A folder for every job.** Each kept job gets the full advert, an evaluation (what it asks, what you can show, the gaps) and your notes, in a folder dated by the day it was found.
- **Honest about what it searched.** Each connector is tested with a live call before a search. A board that fails is named, and the search is never presented as complete when it was not.
- **Tailoring that keeps your CV yours.** It carries the advert's keywords into what your master already says. It does not restructure, pad or invent, and it never states a fact differently to two employers.
- **No slop.** Short and straight to the point. A researched ban-list blocks phrasing like *"results-driven team player, passionate about synergy."*
- **Two markets.** UK and Canada both work out of the box (A4 or US Letter, British or Canadian spelling, the right boards for each).

## Your workspace

Everything lives in one private folder that you choose. Nothing in it is uploaded or committed.

```
your-workspace/
  dump/            your old CVs, certificates and notes
  profile.md       your one plain profile
  setup/           step-by-step guides for each job-board connector
  master-cvs/      TARGETS.md and one master CV per role
  jobs/
    tracker.md     every advert seen, and where each application stands
    2026-01-15/
      SHORTLIST.md
      Acme - Data Analyst/
        job-description.md
        evaluation.md
        notes.md
        CV/
          Your Name - CV.docx
```

---

## Install

### Plugin (recommended)

In Claude Code:

```
/plugin marketplace add soheilfallah/jobxhunter
/plugin install jobxhunter@soheil-jobxhunter
/reload-plugins
```

Or from a terminal:

```bash
claude plugin marketplace add soheilfallah/jobxhunter
claude plugin install jobxhunter@soheil-jobxhunter
```

Then run `/jobxhunter:setup`. It creates the workspace and tells you exactly what is connected.

### Connectors: bring your own keys

No keys ship in this repo. Every connector is optional; with none, the search runs on web search and finds fewer roles. `setup` copies a step-by-step guide for each one into your workspace.

| Connector | Adds | Needs |
|---|---|---|
| **Indeed** | the biggest board for the UK and Canada, full adverts | a click in [claude.ai → Settings → Connectors](https://claude.ai/settings/connectors), no key |
| **[Adzuna](https://developer.adzuna.com/signup)** | UK and Canada search plus salary data | free app id and key |
| **[Firecrawl](https://www.firecrawl.dev)** | the full advert behind any link, including company career sites | free key |
| **[Reed](https://www.reed.co.uk/developers/jobseeker)** | UK only, full adverts | free key |

Set keys with `/plugin configure jobxhunter@soheil-jobxhunter`, then restart Claude Code. If a connector still reports a missing key, put the keys in `~/.jobxhunter/.env`: that file sits outside the plugin, so it survives every update.

### Requirements

| Requirement | Needed for |
|---|---|
| **Claude Code** | everything, or any `SKILL.md`-compatible host |
| **[`uv`](https://docs.astral.sh/uv/getting-started/installation/)** (≥ 0.4) | the Reed and Adzuna connectors and the Word renderer. It fetches their dependencies by itself, so there is nothing to `pip install` |
| **Node.js / `npx`** | the Firecrawl connector only |

<details>
<summary><strong>Other ways to install</strong></summary>

<br>

**Try it without installing.** Loads for that session only.

```bash
git clone https://github.com/soheilfallah/jobxhunter
claude --plugin-dir ./jobxhunter
```

**In Cowork (Claude Desktop).** jobxhunter installs as a plugin in Cowork too. One difference: the bundled Reed, Adzuna and Firecrawl connectors are local processes that do not run in Cowork's sandbox, so searching uses the Indeed and Dice connectors plus web search, and Word files are made with the native `docx` skill. Everything else is the same.

**As a plain skill** (for hosts with no plugin system):

```bash
git clone https://github.com/soheilfallah/jobxhunter ~/.claude/skills/jobxhunter
```

In this mode `${CLAUDE_PLUGIN_ROOT}` is not set. Read it as the clone directory wherever a file mentions it.

**Other agent CLIs.** Point Codex, Gemini CLI, Copilot, OpenCode and others at [`AGENTS.md`](AGENTS.md).

</details>

### Updating

```
/plugin marketplace update soheil-jobxhunter
/plugin update jobxhunter@soheil-jobxhunter
```

Your workspace is never touched by an update. Coming from 1.x? Read the 2.0.0 entry in [`CHANGELOG.md`](CHANGELOG.md): the workflow and the workspace layout both changed.

---

## Under the hood

The engine is [`SKILL.md`](SKILL.md), a short workflow map. The depth lives in `references/` and loads only when a step needs it. Four agents do the work:

| Agent | Job |
|---|---|
| `job-scout` | searches every board for one role |
| `job-evaluator` | reads each advert in full against the role's master CV and decides |
| `master-builder` | writes one master CV from your profile |
| `cv-tailor` | fits one master CV to one advert |

Each agent names its model by family alias (`sonnet`, `opus`), not by version, so the plugin moves to the newest model of each family without an edit. The one bundled script turns a markdown CV into an ATS-safe Word file.

## Privacy & supply chain

- **Your data stays yours.** Your profile, CVs and applications live in your private workspace. Nothing is sent anywhere except the search queries you ask for. No keys ship in this repo.
- **Connector installs stay pinned.** `uv` and `npx` read config from the working directory, so a stray `uv.toml` or `.npmrc` could otherwise redirect a connector's install to someone else's package index. The connectors pin resolution to the real registries and to committed hash-verified lockfiles.
- **Responsibility sits with you.** jobxhunter is provided as-is, with no warranty (see the [licence](#licence)). You review and send every application yourself.

## Contributing

Issues and PRs welcome. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md). See [`CHANGELOG.md`](CHANGELOG.md) for what's landed.

## Licence

Open source under the [MIT License](LICENSE). Copyright © 2026 Soheil Fallah.
