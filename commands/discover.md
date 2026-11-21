---
description: Find employers worth approaching directly and draft a cold email to the right person.
argument-hint: "[target field and location, e.g. data science in Leeds]"
---

Plugin folder: `${CLAUDE_PLUGIN_ROOT}`

Before anything else, read `SKILL.md` in the plugin folder and `references/company-discovery-cold-outreach.md`. Every `references/`, `assets/`, `agents/`
and `scripts/` path below is inside the plugin folder; give that real path to every agent you dispatch.

Use the **jobxhunter** skill's **DISCOVER** routine (`SKILL.md`, "DISCOVER") and follow
`references/company-discovery-cold-outreach.md`.

Build a ranked list of target employers → find the named person who owns the hire and a verified
address (paid lookups one confirmed target at a time) → draft a short email from the user's own
words, with the role's master CV attached, for the user to review and send. Never write to `info@`.

Add the employers to the `Target employers` section of `master-cvs/TARGETS.md` so the next search
reads their own job boards, and record each approach in `jobs/tracker.md`.
