---
description: Create your private jobxhunter workspace, copy the connector tutorials into it, and test which job boards are connected.
argument-hint: "[optional: folder to create the workspace in]"
---

Plugin folder: `${CLAUDE_PLUGIN_ROOT}`

Before anything else, read `SKILL.md` in the plugin folder. Every `references/`, `assets/`, `agents/`
and `scripts/` path below is inside the plugin folder; give that real path to every agent you dispatch.

Use the **jobxhunter** skill's **SETUP** routine (`SKILL.md`, "SETUP").

1. Ask where the workspace should live if no path was given. One question; suggest `~/jobxhunter`.
2. Copy `<plugin folder>/assets/workspace/` into it. Never overwrite a file that already exists.
3. Test every connector with the one small live call listed in the workspace's `setup/README.md`,
   and write what you found to `setup/STATUS.md`. A connector that answers with an auth error is not
   connected, whatever the tool list says.
4. Say which optional skills are present (`humanizer`, `docx`).
5. Tell the user what works now and the next step: drop files in `dump/`, then `/jobxhunter:intake`.

**Keys are optional and come last.** Everything works on web search without them. If the user wants
a connector, open its tutorial in `setup/` and go one step per message. Never ask for three sign-ups
before anything has worked.

Stop after setup. Do not start an intake or a search on the user's behalf.
