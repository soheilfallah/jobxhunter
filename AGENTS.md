# AGENTS.md

jobxhunter is an agent-run job-hunting toolkit. Its core works in **any coding-agent CLI** that can read files and run Python: Claude Code, Codex, Gemini CLI / Antigravity, GitHub Copilot CLI, OpenCode, Qwen, Kimi, and others. This file tells your agent how to drive it. (Claude Code users get the full plugin experience; see `README.md`.)

## The one rule (non-negotiable)

The user's **master profile is the only source of truth** for anything submittable. Select, reframe, reorder, and emphasise the real experience in it. **Never invent** a title, number, skill, or date. If evidence for a job requirement isn't in the profile, surface it to the user as a gap; do not fill it. Only the `L2` "alternative-world" mode may go beyond the profile, and its output is never submitted.

## Start here

**Setting a user up for the first time?** Follow [`SETUP.md`](SETUP.md) — five steps, in order, one question at a time, keys last and optional. That file has the agent procedure and the per-step check.

Otherwise read [`SKILL.md`](SKILL.md). It is the engine: a workflow map that pulls deeper knowledge from `references/` only when a step needs it. Everything below is a pointer into it.

## The pipeline

| Step | What to do | Read |
|---|---|---|
| **Intake** | Build a master profile from the user's raw files (old CVs, LinkedIn export, notes, certificates). | `references/profile-intake.md`, `references/master-profile-schema.md` |
| **Source** | Find live roles that match. | `references/daily-hunt.md`, `references/job-search-guide.md` |
| **Tailor** | Produce an ATS-safe CV for one JD, then run the recruiter-critic scoring loop until it passes. | `references/tailoring-levels.md`, `references/recruiter-rubric.md`, `references/ats-mechanics.md`, `references/cv-craft.md` |
| **Cover / outreach** | Draft a cover letter or cold email in the user's own voice. | `references/cover-letter.md`, `references/company-discovery-cold-outreach.md`, `references/writing-voice.md` |
| **Track & prep** | File a per-job folder + a locked tracker row; build interview prep from the filed role. | `references/interview-prep.md` |

Each `commands/*.md` file reads as a plain-language task description, so use it directly even without slash-command support.

## Running the deterministic scripts

Rendering, tracking, and keyword coverage are deterministic Python under `scripts/`. Run them from the repo root:

```
python scripts/tracker.py …            # the application tracker (xlsx + csv, applied rows locked)
python scripts/render_docx.py …        # render the tailored CV to .docx
python scripts/keyword_coverage.py …   # deterministic must-have / nice-to-have coverage check
```

Needs **Python 3** with `python-docx` + `openpyxl`. The scripts preflight and print the exact fix if a dependency is missing.

## Portability notes (read once)

- **`${CLAUDE_PLUGIN_ROOT}`** in `SKILL.md` means **the repo root** on non-Claude hosts. Substitute it wherever it appears.
- **Slash commands** (`/jobxhunter:tailor`, …) are a Claude Code convenience. On other CLIs there are no slash commands, so perform the task in the matching `commands/*.md` file.
- **Job connectors** (Reed / Adzuna / Firecrawl) are Claude Code **MCP** servers. Without them, do the sourcing step with whatever web-search / fetch tools your agent has. **The tailoring, tracking, and interview core is identical on every host.** Only live-board sourcing changes.
- **No secrets in this repo.** The user brings their own API keys, and their real profile and applications live in a private, gitignored workspace.
