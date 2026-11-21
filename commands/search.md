---
description: Search the job boards for every target role and evaluate each advert against the right master CV. Finds and judges only; it never tailors.
argument-hint: "[optional: full | one role name | workspace path]"
---

Plugin folder: `${CLAUDE_PLUGIN_ROOT}`

Before anything else, read `SKILL.md` in the plugin folder and `references/search.md`. Every `references/`, `assets/`, `agents/`
and `scripts/` path below is inside the plugin folder; give that real path to every agent you dispatch.

Use the **jobxhunter** skill's **SEARCH** routine (`SKILL.md`, "SEARCH") and follow
`references/search.md` step by step.

**This run never writes a CV.** It ends at `SHORTLIST.md`. Tailoring is `/jobxhunter:tailor`, a
separate run the user starts after reading the shortlist.

- **First search** (empty `jobs/tracker.md`) or the argument `full`: massive. Every title of every
  role, on every working source, no date limit, paging until nothing new comes back.
- **Later searches:** the same queries, limited to adverts posted since the last search date in
  `STATE.md`.

Steps: preflight every connector with a live call and name any that fail → one **`job-scout`** per
role, all in one message → merge and drop anything already in `tracker.md` → **`job-evaluator`**
agents in parallel, up to 10 adverts of one role each, with that role's master CV → write
`tracker.md`, `SHORTLIST.md` and `STATE.md` → report and stop.

Relevance is decided by the evaluator agents from the full advert text. Never rank or drop an advert
by keyword overlap, title match or any script.

The report is a few lines: sources that worked, sources that failed and why, adverts found, new,
kept, skipped, unread, and where the shortlist is. If a source failed, say the search was thinner
for it; never present a partial search as complete.
