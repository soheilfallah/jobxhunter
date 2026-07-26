---
description: Tailor an ATS-safe CV to one job description from the master profile.
---

Use the **jobsmith** skill's **TAILOR** routine (its core) for a single job description.

Parse the JD → build the coverage matrix (strong / partial / adjacent-provisional / hard-gap) → select and
order real evidence → draft bullets (`strong verb + real task + method + quantified outcome`, anti-mirroring
guard) → voice pass + integrity checks (date/gap/truth sweeps) → render an ATS-safe `CV.docx` + `CV.txt`
via `scripts/render_docx.py` → run the recruiter loop → file it. Respect the level (L0 / L1 default / L2).

Follow `SKILL.md` ("Command: TAILOR"), `references/jd-analysis.md`, `references/cv-craft.md`,
`references/cv-mistakes.md`, and `references/tailoring-levels.md`. Never invent a fact — surface gaps.
