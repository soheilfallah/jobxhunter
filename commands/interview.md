---
description: Prepare for an interview from a filed job - predicted questions, STAR answers from real evidence, and answers for the gaps.
argument-hint: "[job folder, or company and role to find it]"
---

Plugin folder: `${CLAUDE_PLUGIN_ROOT}`

Before anything else, read `SKILL.md` in the plugin folder and `references/interview-prep.md`. Every `references/`, `assets/`, `agents/`
and `scripts/` path below is inside the plugin folder; give that real path to every agent you dispatch.

Use the **jobxhunter** skill's **INTERVIEW** routine (`SKILL.md`, "INTERVIEW") and follow
`references/interview-prep.md`.

Read the job folder (`job-description.md`, `evaluation.md`, the tailored CV if there is one) and the
profile, then write `interview-prep.md` into that folder: a 30-second opener, predicted questions
grouped by what the advert requires with STAR answers built from profile evidence, an honest
answer for every gap `evaluation.md` lists (those are the questions they will probe), questions to
ask them, and the likely curveballs.

Set the job's row in `jobs/tracker.md` to `Interview`, whatever its status was before.

Where the profile has no example for a question, write a prompt for the user to fill in. Never
invent the example.
