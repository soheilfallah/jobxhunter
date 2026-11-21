---
description: Write one master CV per target role from your profile. Every tailored CV later starts from the master for its role.
argument-hint: "[optional: one role to build or rebuild; default is every role without a master]"
---

Plugin folder: `${CLAUDE_PLUGIN_ROOT}`

Before anything else, read `SKILL.md` in the plugin folder. Every `references/`, `assets/`, `agents/`
and `scripts/` path below is inside the plugin folder; give that real path to every agent you dispatch.

Use the **jobxhunter** skill's **MASTERS** routine (`SKILL.md`, "MASTERS").

1. Read `master-cvs/TARGETS.md`. For each role with no master yet (or only the role named in the
   argument), create `master-cvs/<family>/<role>/`.
2. Dispatch one **`master-builder`** agent per role, all in a single message so they run in
   parallel. Give each: the plugin folder path, the profile path, that role's block from
   `TARGETS.md`, the market and its output folder. Give it **no adverts** and no other master.
3. Report the files written in a short list, and say they are the user's to edit: the edited master
   is the base for every tailored CV in that role.

Never rebuild a master that already exists unless the user names it. Their hand edits live there.
