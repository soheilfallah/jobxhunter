---
description: Scaffold a jobxhunter workspace and help register the job connectors (bring-your-own-keys).
argument-hint: "[optional: workspace directory to scaffold]"
---

Use the **jobxhunter** skill's **SETUP** routine.

**Walk the user through `SETUP.md`, one step at a time, and verify each step before the next.**
Keys are step 5 and optional — never lead with them, never block on them. Stop after the profile
is built and the user has looked at it; tell them which command to run next.

1. Resolve or create the workspace (`python "${CLAUDE_PLUGIN_ROOT}/scripts/_lib.py" resolve`; if none, scaffold with
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/init_workspace.py" --workspace <dir> [--name <who>]`). This drops the profile template,
   the `dump/` folder, `WORKSPACE-MAP.md`, and the tracker, then stops.
2. Onboard the connectors (only after the profile exists and the user said "now"): run
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_connectors.py" doctor` for a report of what's set vs
   missing, then follow the **Agent script** in `references/tools-and-connectors.md` for each missing
   one, in its order: Indeed first (built into claude.ai — *Settings → Connectors → Indeed → Connect*,
   no key), then Adzuna, Firecrawl, Reed, Dice optional. One connector per message; never block on a
   key; say what still works without it. Keys are the plugin's user-config values (`/plugin configure`
   or `claude plugin install … --config KEY=VALUE`) — no manual JSON editing. Re-run the doctor after
   the user restarts Claude Code.

Follow `SKILL.md` ("Command: SETUP") and `references/tools-and-connectors.md`. Stop after setup so
nothing runs against an empty profile.
