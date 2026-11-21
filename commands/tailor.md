---
description: Tailor the right master CV to one evaluated job, or to an advert you paste. Run it after a search, never during one.
argument-hint: "[a job folder | several | 'top N' from the latest shortlist | a pasted advert or link]"
---

Plugin folder: `${CLAUDE_PLUGIN_ROOT}`

Before anything else, read `SKILL.md` in the plugin folder and `references/cv-craft.md`. Every `references/`, `assets/`, `agents/`
and `scripts/` path below is inside the plugin folder; give that real path to every agent you dispatch.

Use the **jobxhunter** skill's **TAILOR** routine (`SKILL.md`, "TAILOR").

1. Resolve the jobs. `top N` means the first N entries under "Kept, best first" in the newest
   `SHORTLIST.md` (the closing-soon block above it is a reminder, not the ranking). For a pasted
   advert or a link, file it first: `jobs/<today>/<Company> - <Role>/job-description.md` with the full
   text, an empty `CV/` folder and a `notes.md`; ask which role's master to use only if it is not
   obvious.
2. For each job, find the role's master CV (the `Tailor from` line in `evaluation.md`). **No master,
   no tailoring:** say so in one line and stop. Do not build a master on the way.
3. Dispatch one **`cv-tailor`** agent per job, in a single message when there are several. Give each:
   the plugin folder path, the job folder, the master CV path and the market.
4. Set the job's row in `jobs/tracker.md` to `Tailored` yourself. The agent sets the `Status:` line
   in the job's `notes.md`.
5. Report each CV's path and how many requirements were left out, one or two lines per job. The
   list itself is in the job's `notes.md`.

Tailoring is a keyword pass over the master: reword and reorder what is already there. It does not
restructure the CV, add facts, score the result or ask for confirmation batches.

When the user says they applied, set that row to `Applied`.
