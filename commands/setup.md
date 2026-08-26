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
2. Onboard the connectors: run `python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_connectors.py"` for a report of what's configured vs
   missing, and guide the user to free keys (Reed / Adzuna / Firecrawl). If this plugin's connectors are
   used, the keys are the plugin's user-config values — no manual JSON editing.

Follow `SKILL.md` ("Command: SETUP") and `references/connector-setup.md`. Stop after setup so nothing
runs against an empty profile.
