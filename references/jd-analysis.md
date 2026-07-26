# JD Analysis — decomposition reference (UK-first)

You are decomposing a single UK job description (JD) into a structured object the tailoring
pipeline consumes. Be literal first, inferential second. Extract what the posting SAYS, then
annotate what it WANTS. Never invent requirements the JD does not support. UK conventions
govern: right-to-work, SIA, university pay spines, £/year and £/hour, hybrid day-counts.

Your output is the `JDAnalysis` object defined at the bottom. Fill every field or mark it
`null`/`unknown` — the pipeline treats missing fields as "not stated", not "not required".

---

## 0. Prime directive: knockouts first

Before anything else, scan for HARD KNOCKOUTS. A knockout is a binary gate: fail it and the
application is dead regardless of skill fit. If the candidate fails a knockout, the tailorer
must surface it to the user, NOT paper over it. Recurring UK knockouts (from live JD capture —
see `kb-build/live-jds/_index.md`, "Recurring structural observations"):

- **Right-to-work / visa / sponsorship.** "UK-based candidates only", "must have right to work
  in the UK", "no sponsorship available", "work authorisation required". Appears explicitly in
  university and public-sector posts and as an application screening question.
- **Security clearance.** BPSS, SC (Security Check), DV (Developed Vetting), NPPV, CTC
  (Counter-Terrorist Check). Often "must be eligible for SC" = residency-history gate.
- **Professional licence.** SIA licence (frontline security — the single hardest knockout in
  that family; specify sub-type SG/DS/CP/CCTV), NMC/HCPC registration, GPhC, QTS, pesticide
  application PA1/PA6, forklift/PASMA/IPAF.
- **Driving licence.** "Full UK driving licence", "own transport" — a genuine gate for field
  science (travel to trial sites) and mobile security, not boilerplate.
- **Years-of-experience minimum.** "Minimum 2 years", "at least 5 years in X". Treat as a soft
  knockout unless phrased "essential"/"must".
- **"Immediate start" / notice period.** A gate if the candidate cannot start immediately.
- **Required degree / field.** "Master's degree a MUST", "first or masters degree in a
  biological science", "degree in a quantitative field". Field-specific degree gates are common
  in research and plant-science roles and are heavily weighted.
- **"Covering letter required" / application questions.** A process knockout: the application is
  rejected if the artefact is missing. Plant-science (Hypocotyl) and many public posts enforce
  this. Flag it so the tailorer produces the letter.
- **Location / on-site mandate.** "On-site 5 days", "must live within commuting distance of X".

Record each as a `Knockout{type, text (verbatim), severity: hard|soft, candidate_status:
pass|fail|unknown}`. Quote the JD verbatim in `text` — do not paraphrase a gate.

Application screening questions carry the same weight as body text. If the JD includes
"Application questions: …", parse each one as a potential knockout.

---

## 1. Must-haves vs nice-to-haves

Split every requirement into `must_haves` and `nice_to_haves`. Use the JD's own signalling:

- **Must-have signals:** "essential", "required", "must have", "you will have", "minimum
  criteria", "we need", requirement listed under "Essential" heading, or stated as a screening
  question. Also treat the degree/licence gates above as must-haves.
- **Nice-to-have signals:** "desirable", "preferred", "nice to have", "advantageous", "bonus",
  "ideally", "you may have", "an understanding of … would be beneficial", items under a "Key" or
  "Desirable" heading.

When a JD is unstructured (startup/agency posts are short and keyword-dense; NHS/university posts
are long and duty-enumerated), infer tier from verbs and repetition: a skill named in the title
or repeated across summary + requirements is a must-have; a skill named once in passing is a
nice-to-have. When genuinely ambiguous, default to must-have (safer for match scoring).

Each entry: `Requirement{term, expansion (if acronym), tier: must|nice, evidence (verbatim
JD phrase), category: hard_skill|tool|cert|soft|domain}`. Always pair acronyms with expansions
(SQL → Structured Query Language, GCP is ambiguous — Good Clinical Practice in research vs Google
Cloud Platform in data; disambiguate from context).

---

## 2. Seniority / level signals

Infer level; it drives which vocabulary tier the taxonomy reaches for (junior vs senior) and
whether the role is even eval-eligible for this junior-to-mid skill.

- **Entry / junior:** "junior", "graduate", "trainee", "apprentice", "assistant", "entry-level",
  "0-2 years", "training provided", "no experience necessary", university Grade 5.
- **Mid:** "analyst", "associate", "officer", "2-5 years", "some experience", named tools
  expected but not architecture ownership, university Grade 6/7.
- **Senior / lead (usually out of scope):** "senior", "lead", "principal", "staff", "manager",
  "head of", "own the strategy", "mentor the team", "architecture", "5+ years", MLOps/CI-CD
  ownership. Flag `level: senior` and `eval_eligible: false` unless the caller overrides.

Record `level` and `eval_eligible`. Note title inflation: agency posts over-title; a "Data
Analyst" asking only for Excel + one BI tool is entry despite the bare title.

---

## 3. Tone / culture signals

Read register to set the CV's voice and the covering letter's warmth.

- **Corporate / formal** (banking, NHS, university): measured, competency-framework language,
  "stakeholder engagement", "governance". Mirror with precise, duty-anchored bullets.
- **Startup / fast** ("greenfield", "wear many hats", "thrive in ambiguity", "0-to-1"): mirror
  with initiative, breadth, shipping.
- **Mission-driven** (research institutes, safety/health charities, public health): mirror with
  purpose alignment and rigour.
- **Team / values cues:** "collaborative", "inclusive", "fast-paced", "detail-oriented". Capture
  as `culture_signals[]` for the letter, not the skills match.

---

## 4. Salary-band inference (UK)

Populate `salary` even when the JD omits a figure — infer a range from level + sector + region.

- **Stated ranges:** capture verbatim. UK posts give £/year ranges (agencies, corporates) or
  £/hour (frontline, part-time, seasonal science). Contract/day-rate appears as £/day (e.g.
  Data Analyst £250-400/day). Convert for comparison: annual ≈ hourly × 37.5 × 52; day-rate ×
  ~220 working days for a rough FTE-equivalent.
- **University pay spines:** exact bands stated (e.g. Imperial RA £43,863-47,223; RA/Associate to
  £57,472). These follow the New JNCHES single pay spine (2% uplift from 1 Aug 2026). RA ≈ Grade
  5/6, Research Associate ≈ Grade 7 (spine point 41+). London roles add London weighting — do not
  read a London figure as the national rate.
- **Frontline floor:** SIA security pay sits at/just above National Living Wage (£12.71/hr from
  1 Apr 2026), typically £12.71-16/hr; casino/CP/specialist environments pay the top of that.
- **Inference when unstated:** entry data/AI London ~£30-45k; mid ~£45-60k. Entry lab/plant-science
  £24-30k or £15-23/hr. Research assistant (uni) £30-38k; associate £40-49k. Mark `salary.source:
  stated|inferred`.

---

## 5. Reading between the lines — WANT beneath SAY

After the literal pass, infer the unstated. This is where tailoring earns its keep.

- A long "desirable" list on an entry role = they will hire on attitude + core must-haves;
  emphasise learning speed, don't fake the desirables.
- "Fast-paced" + short JD = they value shipping and low-ceremony; lead with outcomes.
- Repeated "stakeholder"/"non-technical audience" = communication is a real gate, not filler;
  surface presentation/reporting evidence.
- "Greenfield"/"build from scratch" = comfort with ambiguity and ownership > polished process.
- Named specific tool (Teradata, IAPTus, M365 Purview, Polars) = they have that stack in
  production and value exact-match evidence; a transferable equivalent is worth naming.
- Enumerated duties (NHS/uni) = the CV should map bullet-to-duty; coverage breadth is scored.
- Degree-field emphasis in research/plant roles = field match is a near-knockout; foreground the
  matching degree early.
- "Training provided" against a desirable = genuinely optional; do not let its absence block.

Record as `subtext[]{observation, tailoring_implication}`. Keep each grounded in a JD phrase —
no free-floating speculation.

---

## 6. Step-by-step decomposition procedure

Execute in order:

1. **Segment** the JD into blocks: title, summary, responsibilities/duties, essential,
   desirable, about-you/culture, benefits/salary, application questions.
2. **Knockout sweep** (Section 0) across ALL blocks incl. screening questions. Quote verbatim.
3. **Title parse** → extract title variants, seniority hint, family.
4. **Extract requirements** line by line; assign tier (Section 1) + category; pair acronyms with
   expansions.
5. **Classify level** (Section 2); set `eval_eligible`.
6. **Read tone** (Section 3) → `culture_signals`.
7. **Resolve salary** (Section 4) → stated or inferred range with source flag.
8. **Infer subtext** (Section 5) → `subtext[]`.
9. **Family-map** the extracted terms against the matching keyword-taxonomy file
   (`references/keyword-taxonomy/*`) to normalise synonyms and weight them.
10. **Emit** the `JDAnalysis` object. Leave unknowns explicit.

Downstream, the tailorer matches `must_haves`/`nice_to_haves` to REAL profile evidence only. If
the profile lacks a must-have, the tailorer flags a gap — it never fabricates the skill.

---

## 7. Output shape — `JDAnalysis`

```json
{
  "title_raw": "Junior Machine Learning Engineer",
  "title_variants": ["Junior ML Engineer", "Machine Learning Engineer", "ML Engineer"],
  "family": "ai-technician-junior-ai",
  "level": "entry",
  "eval_eligible": true,
  "employer": "Information Tech Consultants",
  "sector": "consultancy",
  "location": { "city": "Greater London", "region": "London", "remote": "on-site" },
  "knockouts": [
    { "type": "right_to_work", "text": "UK-based candidates only; visa status asked",
      "severity": "hard", "candidate_status": "unknown" },
    { "type": "degree", "text": "Master's degree a MUST", "severity": "hard",
      "candidate_status": "unknown" },
    { "type": "immediate_start", "text": "immediate start", "severity": "soft",
      "candidate_status": "unknown" }
  ],
  "must_haves": [
    { "term": "Python", "tier": "must", "category": "tool",
      "evidence": "strong Python with ML/AI libraries" },
    { "term": "SQL", "expansion": "Structured Query Language", "tier": "must",
      "category": "tool", "evidence": "write & optimise SQL queries" }
  ],
  "nice_to_haves": [
    { "term": "Docker", "tier": "nice", "category": "tool", "evidence": "Docker/Kubernetes" }
  ],
  "seniority_signals": ["\"junior\"", "\"assist developing\"", "entry-level"],
  "culture_signals": ["continuous learning", "partner with cross-functional teams"],
  "salary": { "min": 35000, "max": 45000, "unit": "gbp_year", "source": "stated" },
  "subtext": [
    { "observation": "long 'preferred' list on an entry role",
      "tailoring_implication": "hire on core must-haves + learning speed; do not fake preferred items" }
  ],
  "required_artifacts": ["cv"],
  "notes": "Master's stated as hard gate; confirm candidate holds one before proceeding."
}
```

Field rules:
- `title_variants` — seed from the taxonomy file's TITLE VARIANTS; include the raw title.
- `family` — one of: `plant-science-research`, `research-assistant-lead`,
  `ai-technician-junior-ai`, `data-research-analysis`, `security-frontline`.
- `required_artifacts` — add `cover_letter` whenever a covering letter / application questions
  are demanded; add `portfolio`/`references` if requested.
- `candidate_status` — set only when profile data is available; else `unknown`.
- Always keep `evidence`/`text` verbatim so the tailorer can cite the JD back to the user.

---

## Sources
- Live UK JD capture (primary), 2026-07-06: `kb-build/live-jds/_index.md`, `ai-ml.md`,
  `data-analysis.md`, `research-assistant.md`, `security-frontline.md`, `plant-science.md`.
- GOV.UK — SIA licensing (licence types, clearance gates): https://www.gov.uk/guidance/find-out-if-you-need-an-sia-licence
- UCEA / New JNCHES HE single pay spine 2026-27: https://www.ucea.ac.uk/our-work/collective-pay-negotiations-landing/2026-27-nj-pay-round/ ; UCU: https://www.ucu.org.uk/he_singlepayspine
- O*NET OnLine occupation structure (levels, task/skill vocabulary): https://www.onetonline.org
- ESCO occupation & skill taxonomy (EU/UK-facing): https://esco.ec.europa.eu
