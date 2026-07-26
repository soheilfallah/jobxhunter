# Canadian conventions (market = `ca`)

Apply this layer instead of `uk-conventions.md` when the profile's **market** is `ca` (Canada). It is
written as a **delta against the UK layer** — everything the tailorer already does (ATS-safe render,
truth rule, quantified bullets, no slop) still holds; this only changes the market-specific norms.

## Terminology
- Call it a **résumé**, not a CV. In Canada "CV" means the long **academic** document (research,
  publications, teaching) used for academia/research/medicine only. For all other roles: résumé.
- Use an academic **CV** only for university/research/faculty applications.

## Length & page size
- **1 page** for early career (0–5 years); **2 pages** for experienced professionals. Not longer
  unless it's an academic CV.
- **US Letter (8.5 × 11 in)** — NOT A4. This matters: ATS parsers and printers expect Letter in
  Canada; A4 can misalign. Set the render to Letter for `ca`.

## Personal details to OMIT (human-rights law)
Never include **photo, date of birth, age, marital/family status, religion, nationality (beyond work
authorisation), SIN, or a headshot**. The Canadian Human Rights Act and every provincial human-rights
code prohibit hiring discrimination on these protected grounds; reputable employers don't want them at
application stage. (Same omissions as the UK, plus SIN.)

## Spelling & language
- **Canadian English** — a UK/US hybrid: British-style `colour, centre, honour, favour, labour,
  cheque`, but often US-style `-ize` (`organize, recognize, analyze`) and `program` (not
  "programme"). When in doubt, prefer the British `-our`/`-re` and the `-ize` verb ending.
- **Bilingualism:** French is a strong asset nationally and frequently **required** for federal and
  Quebec roles. For a Quebec-based or federal-government application, offer a **French version** and
  note French proficiency. (Quebec's language law, Bill 96, pushes French-first.) Flag this to the
  user rather than machine-translating.

## Dates
- ISO **`YYYY-MM-DD`** or **`Month YYYY`** (e.g. `2024-06` / `June 2024`). Avoid the ambiguous
  DD/MM/YYYY the UK uses — in Canada numeric dates read as YYYY-MM-DD.

## Structure & emphasis
- Open with a **Professional Summary** (2–4 lines) — Canada's equivalent of the UK "personal
  statement"; an "Objective" is acceptable for career-changers/newcomers.
- **Volunteer work and community involvement** carry more weight than in the UK — include a section if
  relevant, especially for newcomers building **Canadian experience**.
- **Canadian experience** is valued by employers; foreground any Canadian roles/education. For
  newcomers with none, lean on transferable skills, Canadian volunteering, and credential recognition.
- Present international qualifications as-stated; note **Canadian equivalency** where known (e.g. WES/
  ICAS credential-assessment equivalence) the way the UK layer notes UK equivalence.

## Work authorisation (load-bearing — many postings ask)
Express status in Canadian terms and, when a posting asks, include a one-line eligibility statement:
- `Canadian citizen` · `Permanent resident` · `Valid open work permit` · `Eligible to work in Canada`
  · `Requires employer sponsorship (LMIA)`.
Put it in the header or a short "Work eligibility" line when the JD raises it. Keep any deeper
immigration detail in the profile's **Confidential hold**, never on the résumé.

## ATS notes (Canada)
Same universal ATS rules as `ats-mechanics.md` (single column, no tables/text-boxes/graphics,
standard headings, .docx). The one Canada-specific parser point: render on **US Letter** —
`render_docx.py --page letter` (the bundled script defaults to A4 for `uk`; pass `letter` for `ca`).
Expect **NOC codes** (National Occupational Classification) to matter for government/Job-Bank and
immigration-linked applications — mirror the posting's NOC/title language where given.

## Deltas vs `uk-conventions.md` (quick table)
| Dimension | UK | Canada |
|---|---|---|
| Document name | CV | Résumé (CV = academic only) |
| Page size | A4 | **US Letter 8.5×11** |
| Length | ~2 pages | 1 (junior) / 2 (senior) |
| Spelling | British | Canadian (British `-our/-re` + US `-ize`) |
| Numeric dates | DD/MM/YYYY | **YYYY-MM-DD** |
| Opening | Personal statement | Professional summary |
| Second language | — | **French** an asset / required (federal, Quebec) |
| Work-auth terms | citizen / visa / sponsorship | citizen / PR / work permit / LMIA |
| Extra omission | — | SIN (never include) |

## Sources
- Canadian résumé format: [Monster](https://www.monster.com/career-advice/resume/canadian-resume-format),
  [Novoresume](https://novoresume.com/career-blog/canada-resume-format),
  [Canadavisa](https://www.canadavisa.com/resume.html),
  [Resumemate](https://www.resumemate.io/blog/canadian-resume-format-sections-length-and-tips-for-2025/)
- UK comparison: [VisualCV UK](https://www.visualcv.com/international/uk-cv/)
- Anti-discrimination basis: Canadian Human Rights Act + provincial human-rights codes (age/DOB a
  protected ground).
