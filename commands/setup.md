---
description: Scaffold a jobxhunter workspace and help register the job connectors (bring-your-own-keys).
argument-hint: "[optional: workspace directory to scaffold]"
---

Use the **jobxhunter** skill's **SETUP** routine.

1. Resolve or create the workspace (`python "${CLAUDE_PLUGIN_ROOT}/scripts/_lib.py" resolve`; if none, scaffold with
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/init_workspace.py" --workspace <dir> [--name <who>]`). This drops the profile template,
   the `dump/` folder, `WORKSPACE-MAP.md`, and the tracker, then stops.
2. Onboard the connectors: run `python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_connectors.py"` for a report of what's configured vs
   missing, and guide the user to free keys (Reed / Adzuna / Firecrawl). If this plugin's connectors are
   used, the keys are the plugin's user-config values — no manual JSON editing.

Follow `SKILL.md` ("Command: SETUP") and `references/connector-setup.md`. Stop after setup so nothing
runs against an empty profile.
