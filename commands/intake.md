---
description: Build or update your profile from the files in dump/, then agree the roles you are going for.
argument-hint: "[optional: workspace path]"
---

Plugin folder: `${CLAUDE_PLUGIN_ROOT}`

Before anything else, read `SKILL.md` in the plugin folder and `references/profile-intake.md`. Every `references/`, `assets/`, `agents/`
and `scripts/` path below is inside the plugin folder; give that real path to every agent you dispatch.

Use the **jobxhunter** skill's **INTAKE** routine (`SKILL.md`, "INTAKE") and follow
`references/profile-intake.md`.

- Read everything in `<workspace>/dump/`. Extract facts only; never infer one the files do not support.
- Write `<workspace>/profile.md` in plain prose and lists. No schema. On a later run, merge new facts
  in and leave what the user already confirmed alone.
- Ask about thin spots in small batches and write the answers into the profile.
- Ask what jobs the user is going for. Propose target roles grouped by family, each with its search
  titles, and fill in `master-cvs/TARGETS.md` once they agree.
- Show the user where the profile is and ask them to correct anything wrong.

Stop there. The next step is `/jobxhunter:masters`.
