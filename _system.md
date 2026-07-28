---
title: jobxhunter — job-hunting skill for the UK and Canada
type: project
updated: 2026-07-06
tags: [project, skill, career, cv, job-search, ats, claude-code]
status: built
---

# jobxhunter — the job-hunting skill for the UK and Canada

**What it is:** A general-purpose **job-hunting skill** covering the UK and Canada (a Claude Code / chat `SKILL.md` skill).
CV tailoring at its core — read a master profile plus a job description and produce an ATS-friendly,
slop-free CV that survives both the parser and the six-second human scan — extended with job
**sourcing** (Indeed/Reed/Adzuna/Dice connectors, a Firecrawl→WebSearch→browser deep-crawl fallback,
and UK boards), **company discovery + cold outreach** (find target companies via Clay/Ahrefs/web, find the
named contact, cold-email them from the user's own spoken words), cover letters, a recruiter-persona
scoring loop, an "alternative world" L2 mode (a realistic stronger persona plus the delta to reach
it), and application tracking.

**The key design idea — decoupled profile:** the skill logic and knowledge base are generic and never
change based on whose profile they read. The **master profile is inert data at a path you point the
skill at**; it can be anyone (yours, a friend's, an invented persona). To use the skill for a
different person, change one input path — nothing in the skill changes. The profile lives OUTSIDE
this project, under `career/job-hunt/`, precisely to keep the tool and the personal data separate.

## Layout
```
projects/jobxhunter/
├── SKILL.md              # the skill: workflow map + commands (tailor, recruiter loop, L2, cover letter, track)
├── references/           # the distilled knowledge base (progressive disclosure)
│   ├── cv-craft.md, career-narrative.md, cover-letter.md
│   ├── ats-mechanics.md, cv-mistakes.md, uk-conventions.md
│   ├── jd-analysis.md, recruiter-rubric.md
│   ├── job-search-guide.md, company-discovery-cold-outreach.md
│   ├── tailoring-levels.md, master-profile-schema.md
│   └── keyword-taxonomy/  # 5 families: plant-science, research-assistant, ai-technician, data-analysis, security
├── assets/               # CV markdown-input template + render contract + sample-profile.md (demo fixture)
├── scripts/              # render_docx.py, tracker.py, new_application.py (Python; python-docx + openpyxl)
├── kb-build/             # Phase-0 working area: live JD captures + raw research notes (provenance)
└── evals/                # eval notes + self-contained 2026-07-06-run/ (kept OUT of the real applications home)
```

## The data feed
The skill ships a **demo fixture** — `assets/sample-profile.md` (a sample persona) — so it runs out of
the box. The **real production profile** is a separate, private, LATER track and lives OUTSIDE the
skill so tool and personal data stay decoupled:
```
career/job-hunt/
└── applications/   # real applications home — empty/clean until a production profile exists
                    #   (every real run files a job by category + updates tracker.xlsx/.csv)
```
Point the skill at any conforming profile path. Note: the build eval ran on the sample fixture and its
outputs live in `evals/2026-07-06-run/`, deliberately NOT in `career/job-hunt/applications/`, which
stays clean for real use.

## How to run it
Invoke the skill and give it: a profile path (default `assets/sample-profile.md`),
a job description, and a level (L0 / L1-default / L2). It parses the JD, builds a coverage matrix
against real profile evidence, drafts and de-slops an ATS-safe CV, runs the recruiter loop, renders
`CV.docx` + `CV.txt`, files everything into `applications/<category>/<date>_<company>_<role>/`, and
logs a tracker row. Say "I applied to this one" to turn the row green and lock it.

## Non-negotiables it enforces
Master profile is truth for L0/L1 (gaps surfaced, never filled) · ATS-safe rendering (no
tables/columns/graphics) · no slop (`cv-mistakes.md`) · UK conventions on by default · L2 realistic,
unwatermarked, delta stated, never submittable · profile stays swappable data · every job filed and
logged, applied rows green and locked, skipped jobs recorded.

## Status
Built and validated 2026-07-06 across the target families (plant-science, research-assistant, AI/data)
via live UK JDs and an independent recruiter-scoring pass. Build plan and eval provenance in
`kb-build/` and `evals/`. Related: [[career/readme|career]] · [[projects/readme|projects]].
