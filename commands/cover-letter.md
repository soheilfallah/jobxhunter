---
description: Write a finished cover letter for a role, in the user's own voice.
argument-hint: "[a job folder, or an advert: paste, file or link]"
---

Plugin folder: `${CLAUDE_PLUGIN_ROOT}`

Before anything else, read `SKILL.md` in the plugin folder and `references/cover-letter.md`. Every `references/`, `assets/`, `agents/`
and `scripts/` path below is inside the plugin folder; give that real path to every agent you dispatch.

Use the **jobxhunter** skill's **COVER LETTER** routine (`SKILL.md`, "COVER LETTER").

**Write it complete. Never ask for a brain-dump.** Build the letter from the advert and the
profile, name the employer in the body, and build the "why this employer" paragraph from the advert
and verifiable public knowledge. If the user volunteers their own words, treat them as source text
and keep their voice. Every factual claim maps to the profile. No placeholders, no "draft" label.

The advert is enough for the "why this employer" paragraph. Look at the employer's own site only
when the advert says little. With no named recipient in the advert, write to the hiring team.

Save it as `CV/<First Last> - Cover Letter.md` in the job folder and render it (`SKILL.md`,
"Rendering"). The file starts with a `# <First Last>` line and the contact line, like a CV, then one
paragraph per block with a blank line between them. Anything worth telling the user goes in the
job's `notes.md` under a `## Cover letter` heading. Where the employer asks written questions instead of a letter, answer those per
`references/application-answers.md`.

| Step | Read |
|---|---|
| Understand the role | `references/jd-analysis.md` |
| Openers, structure, evidence, etiquette | `references/cover-letter.md` |
| Voice pass, before returning | `references/writing-voice.md` |
| Final wording pass | the installed `humanizer` skill, if present, on the whole letter |
| Academic and research targets | `references/academic-register.md` |
| Market norms | `references/uk-conventions.md` (`uk`) · `references/ca-conventions.md` (`ca`) |
