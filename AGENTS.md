# AGENTS.md

jobxhunter is an agent-run job-hunting toolkit. It works in **any coding-agent CLI** that can read
and write files: Claude Code, Codex, Gemini CLI, GitHub Copilot CLI, OpenCode, Qwen, Kimi and
others. This file tells your agent how to drive it. (Claude Code users get the full plugin
experience; see `README.md`.)

## Start here

**Setting a user up for the first time?** Follow [`SETUP.md`](SETUP.md): five steps, in order, one
question at a time, keys last and optional.

Otherwise read [`SKILL.md`](SKILL.md). It is the engine: a short workflow map that pulls deeper
knowledge from `references/` only when a step needs it.

## The pipeline

| Step | What to do | Read |
|---|---|---|
| **Setup** | Copy `assets/workspace/` to a private folder the user chooses; test what is connected. | `SKILL.md` "SETUP" |
| **Intake** | Build one plain profile from the user's raw files and agree their target roles. | `references/profile-intake.md` |
| **Masters** | Write one master CV per target role, from the profile alone. | `agents/master-builder.md`, `references/cv-craft.md` |
| **Search** | Find adverts widely, then read each in full and judge it against the role's master CV. Never tailor here. | `references/search.md`, `agents/job-scout.md`, `agents/job-evaluator.md` |
| **Tailor** | Reword one master CV to one advert the user picked. | `agents/cv-tailor.md`, `references/cv-craft.md` |
| **Letter, interview, outreach** | On request. | `references/cover-letter.md`, `references/interview-prep.md`, `references/company-discovery-cold-outreach.md` |

Each `commands/*.md` file is a plain-language task description, usable without slash commands. Each
`agents/*.md` file is the brief for one kind of worker: if your CLI has subagents, give each worker
its own context; if not, do the same work one role or one advert at a time.

## Rules that hold everywhere

- The profile is the only source of truth. Never invent a fact, and never question the profile.
- A master CV is built from the profile alone; a tailored CV from its master and the advert alone.
- Whether a job fits is an agent's judgement on the full advert. Do not score, rank or filter jobs
  or CVs with code.
- Search and tailoring are separate runs.
- Never write a machine path or a key into this repo.

## Portability notes

- **`${CLAUDE_PLUGIN_ROOT}`** means **the repo root** on non-Claude hosts.
- **Slash commands** are a Claude Code convenience. Elsewhere, perform the task in the matching
  `commands/*.md` file.
- **Agent frontmatter** (`model`, `effort`) is read by Claude Code. Other hosts can ignore it; the
  body of each file is the brief.
- **Job connectors** (Reed, Adzuna, Firecrawl) are MCP servers. Without them, search with whatever
  web-search and fetch tools your agent has.
- **The one script** is `scripts/render_docx.py`, which turns a markdown CV into a Word file. Run it
  with `uv run --script scripts/render_docx.py ...`, or with Python after `pip install python-docx`.
