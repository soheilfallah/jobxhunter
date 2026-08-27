---
description: Build or update your master profile from the files in your workspace dump/ folder.
argument-hint: "[optional: workspace path; else resolved or scaffolded]"
---

Use the **jobxhunter** skill's **INTAKE** routine to build/enrich the master profile from the user's
`<workspace>/dump/` folder.

- Scan first: `python "${CLAUDE_PLUGIN_ROOT}/scripts/dump_manifest.py" scan --workspace <root>` — read the `new`/`updated` files,
  handle `unreadable` ones (placeholders already created), skip `ingested`.
- Extract only real facts; synthesise or merge into `profiles/<name>.md` per
  `references/master-profile-schema.md`; mark each file `ingested` and log to `profiles/_intake/CHANGELOG.md`.
- Run the **profile enrichment interview** (`references/profile-intake.md`) — ask targeted starter
  questions wherever a bullet is unquantified, a skill has no project behind it, or a target is unset, and
  write answers straight into the profile. This is what keeps later CVs and cover letters concrete.
- Detect the market, surface gaps in one neutral batch, then hand off.

Follow `SKILL.md` ("Command: INTAKE") and `references/profile-intake.md` exactly.
