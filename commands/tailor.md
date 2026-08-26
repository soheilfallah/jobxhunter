---
description: Tailor an ATS-safe CV to one job description from the master profile.
argument-hint: "[JD: paste text, a file path, or a URL] [L0|L1|L2, default L1]"
---

Use the **jobxhunter** skill's **TAILOR** routine (its core) for a single job description.

Parse the JD → build the coverage matrix (strong / partial / adjacent-provisional / hard-gap) → select and
order real evidence → draft bullets (`strong verb + real task + method + quantified outcome`, anti-mirroring
guard) → voice pass + integrity checks (date / gap / profile check) → render an ATS-safe `CV.docx` + `CV.txt`
via `scripts/render_docx.py` → run the recruiter loop → file it. Respect the level (L0 / L1 default / L2).

Every build runs `python scripts/validate_profile.py --profile <profile.md> --folder <dir>` (exit 0
before rendering; exit 2 = the profile's rules block is broken — stop and report) and the mandatory
humanizer pass before anything is called ready.

Follow `SKILL.md` ("Command: TAILOR"). Never invent a fact — surface gaps.

**Which reference each step reads.** Load only what the step needs; a step whose file is listed here is
not finished until that file has been applied.

| Step | Read |
|---|---|
| 1. Parse the JD | `references/jd-analysis.md` |
| 2. Coverage matrix | `references/tailoring-levels.md` ("Gap classes"); for a career-change or non-linear story also `references/career-narrative.md` |
| 3. Select + order | `references/keyword-taxonomy/<family>.md` — as a *palette* to match real evidence, never a source of new skills |
| 4. Draft | `references/cv-craft.md` |
| 5. Voice pass | **`references/writing-voice.md`** (the de-slop + register model — never ship prose that has not been through it) and `references/cv-mistakes.md` §1 (banned buzzwords); then the installed `humanizer` skill, if present, on the summary and every bullet (mandatory when installed; `validate_profile.py` WARNs on AI-tell vocabulary as the mechanical backstop) |
| 5. Market conventions | pick by the profile's market: `references/uk-conventions.md` (`uk`) · `references/ca-conventions.md` (`ca`); academic/research targets also `references/academic-register.md` |
| 6. Render | `references/ats-mechanics.md` §9 — the ATS-safe checklist the render must satisfy |
| Recruiter loop | `references/recruiter-rubric.md`; the critic scores authenticity against `references/writing-voice.md`, the same standard the writer was held to |
| L2 only | `references/tailoring-levels.md` ("L2 — The alternative world"); the delta is mandatory |
