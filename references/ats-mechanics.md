# ATS Mechanics — how applicant tracking systems parse, search, and gate CVs

Purpose: you are tailoring UK CVs that must survive machine parsing AND persuade a human.
This file tells you how ATS actually behave, what breaks them, and the rendering rules you
must never relax. HOLD THE LINE: every CV you produce is single-column, no tables, no
graphics, no header/footer content. No exception, however pretty the alternative.

## 1. Mental model — what an ATS actually does

- A parser reads the file as a LINEAR TEXT STREAM in code order, not visual order. Layout,
  columns, colour, and icons are invisible to it. This one fact explains every format trap.
- Typical pipeline: text extraction → tokenisation → section segmentation → named-entity
  recognition → structured fields (name, employer, title, dates, skills). Errors compound:
  a mis-segmented section can wipe an entire employment entry.
- Field-level accuracy of good parsers is roughly high-80s percent on CLEAN documents —
  contact details near-perfect, skills extraction weakest. A hostile layout drags this far lower.
- Kill the myth: most major ATS do NOT auto-reject on a keyword score. Humans reject. Keywords
  matter because (a) recruiters run exact-string/boolean searches over the candidate database,
  (b) some systems compute a match score recruiters can sort by, and (c) skim-reading humans
  look for the same terms. What DOES auto-reject is knockout questions (section 7).
- Two things persist beyond one application: parsed profile data (Workday keeps it per employer)
  and searchability (recruiters mine past applicants for new roles). Parse quality compounds.

## 2. Per-system behaviour (state confidence honestly)

Well-substantiated points are marked (solid); independent-test or recruiter-account claims
(reported); thin evidence (uncertain). Never present per-system trivia to users as certainty.

**Workday** — enterprise; the parse-then-re-key system.
- Parses the CV into "My Information"/"My Experience" fields, then forces the candidate to
  review and correct them; parse errors are common and candidates must fix fields by hand (solid).
- The corrected fields become a persistent profile with that employer — a clean parse pays off
  across every future application there (solid).
- Strict on dates: use "March 2022" or 03/2022 style consistently; mixed or abbreviated-with-dot
  formats ("Mar. 2022") can break the employment timeline (reported).
- Fails hard on multi-column layouts and header/footer content (reported). Cleanest with a
  plain single-column .docx (reported).

**Greenhouse** — structured hiring; humans decide.
- No algorithmic auto-rejection; scoring is done by humans on scorecards, and the default
  candidate list is date-sorted, not score-sorted (solid — Greenhouse's own positioning).
- Recruiters typically view the ORIGINAL uploaded document with parsed fields as sidebar
  metadata — so human readability of the actual file matters most here (reported).
- Good parser (commercial lineage, reportedly ex-Sovren/Textkernel) but sensitive to
  non-standard section headings — creative headings have emptied whole employment arrays in
  tests (reported). Handles hyperlinks (LinkedIn, portfolio) well (reported).

**Lever** — silent dropper.
- Drops content it cannot place — especially sidebar/second-column content — without any
  warning; skills sidebars have parsed to an empty skills list (reported).
- Otherwise forgiving on contact details; flattens bullets into one text block (reported).

**Taleo (Oracle)** — oldest enterprise ATS; the "keyword-bot" reputation is half right.
- Parser is genuinely primitive: plain-text oriented, strict section labels, chokes on curly
  quotes, em dashes, decorative Unicode bullets, and any date not like "Mon YYYY" (reported).
- Its REAL gate is documented by Oracle (solid): employer-configured prescreening questions
  marked Required or Asset, optionally weighted. Miss a Required answer → not considered.
  Score above a threshold with all Requireds met → flagged an "ACE candidate" to the recruiter.
  So Taleo filters mostly on questions, not CV NLP. Get the CV parse clean AND the questions right.

**iCIMS** — enterprise, high-volume.
- Modern parser with better error recovery; has an OCR fallback for image PDFs, but OCR output
  is degraded — never rely on it (reported).
- Strict post-parse validation: uncertain fields are pushed back to the candidate to re-type
  (reported). Multi-column layouts and header contact info still problematic (reported).

**Ashby** — newer, AI-forward startups/scale-ups.
- AI matching and natural-language recruiter filters; more semantic tolerance than legacy
  systems is likely, but parser internals are not public (uncertain). Do not assume semantic
  matching will rescue a missing keyword.

**SmartRecruiters** — enterprise, EU-popular.
- Ships AI scoring/ranking on skills and role fit with configurable weighting; match-score
  sorting is real here, so exact keyword coverage matters more than in date-sorted systems
  (reported).

**BambooHR** — SMB.
- Basic built-in parsing and screening; heavier AI ranking usually via third-party add-ons.
  Assume the simplest possible parser: plain formatting wins (reported).

## 3. Format traps — what breaks parsing and WHY

- **Tables**: the extractor walks cells in code order or slices rows across all columns,
  interleaving unrelated content into word salad; some parsers skip table content entirely.
- **Multi-column / sidebar layouts**: the extractor reads line-by-line across the full page
  width (zipping the columns together) or reads the sidebar first, destroying chronology.
  The single most damaging pattern in independent multi-engine tests.
- **Headers/footers**: Word and PDF store these in a separate document layer; many extractors
  read the body layer only, so contact details in a header simply vanish.
- **Text boxes / shapes**: floating objects outside the main text flow; skipped or appended
  out of order.
- **Images, icons, logos, skill bars, charts**: no text layer → invisible. A phone icon instead
  of a labelled number removes the cue the entity-recogniser needs. Skill-rating bars carry
  zero machine-readable data and waste space for the human too.
- **PDF-as-image** (Canva/Illustrator/Photoshop exports, scans): no text layer at all; most
  systems extract nothing; the few with OCR produce degraded fields.
- **Unusual/display fonts**: glyph-substitution and ligature issues garble tokens. Use Arial,
  Calibri, Helvetica, Georgia, Garamond, Times New Roman, or similar system-safe faces.
- **Special characters**: curly quotes, em dashes, arrows, decorative bullets cause encoding
  faults (Taleo worst). Use straight quotes, hyphens, and standard round bullets (•) or hyphens.
- **Glued tokens**: "SAP/Oracle" or "SQL|Python" without spaces can parse as one unknown token
  and defeat keyword search. Write "SAP / Oracle" or comma-separate.

## 4. .docx vs PDF

- Layout matters far more than container: a clean single-column file parses in any major
  modern system in either format.
- DO default to **.docx** when: system is Taleo or unknown/legacy, the posting asks for Word,
  or a recruitment agency needs an editable file (UK agencies routinely re-template CVs).
  .docx is XML with guaranteed text ordering — the most consistent extraction across engines.
- DO use a **text-based PDF** (exported from a word processor, never a design tool) when: the
  posting allows it and the system is Greenhouse/Lever/Ashby-class where recruiters read the
  original file — PDF locks the layout the human sees.
- DO obey explicit instructions in the job advert — they override every rule here.
- DON'T ever submit: design-tool PDF exports, scanned PDFs, .pages, .odt, .txt, images.

## 5. Keyword mechanics

- Assume EXACT-STRING matching. Recruiter search is boolean/literal in most systems; semantic
  matching (Ashby, SmartRecruiters AI, add-ons) is a bonus, never a safety net. The HBS "Hidden
  Workers" study: 88% of employers admit their systems filter out qualified candidates who
  don't match the job-description wording.
- ALWAYS pair acronym and expansion at least once each: "NLP (Natural Language Processing)",
  "CIPD (Chartered Institute of Personnel and Development)", "AML (anti-money laundering)".
  Recruiters search either form; a literal matcher finds only the string that is present.
- Mirror the advert's exact phrasing for hard skills and qualifications ("stakeholder
  management", not "managing stakeholders") — and the target job title, where truthful, in the
  headline/profile line.
- Place each priority keyword TWICE: once in the Skills section (clean field extraction and
  database search) and once in context inside an achievement bullet (phrase-level match plus
  credibility for the human). A skills-list-only keyword looks hollow; a buried-only keyword
  may miss field extraction.
- DON'T stuff: no white text (parsers normalise it and recruiters see the original file), no
  keyword walls, no skills you can't defend at interview. In date-sorted systems density buys
  nothing; in every system the human reader is the actual decision-maker and stuffing reads
  as spam.

## 6. Section headings — use the boring ones

- USE exactly these conventional headings: "Professional Summary" (or "Profile"),
  "Work Experience" (or "Professional Experience" / "Employment History"), "Education",
  "Skills" (or "Key Skills" / "Technical Skills"), "Certifications" (UK: "Licences &
  Certifications"), "Projects", "Publications", "Volunteering".
- Segmentation keys off these labels. Creative headings ("My Journey", "Where I've Made
  Impact", "Career Story", "Professional Journey") have caused whole sections to be
  misclassified or dropped in multi-engine tests.
- Headings must be plain flowed text (bold and/or larger size is fine) — never inside a text
  box, table cell, or graphic.
- Date format: pick one style — "Mar 2022 – Present" or "March 2022 – Present" — and use it
  for every entry. No "Mar. 2022", no bare years mixed with month-years.

## 7. Knockout / screening questions — the real auto-reject

- Knockouts are application-form questions with a disqualifying answer; the wrong answer
  auto-archives the application with a templated rejection and the CV is never opened. They
  fire BEFORE parsing or ranking matters.
- Common UK knockouts: right to work in the UK; "will you now or in the future require visa
  sponsorship"; driving licence; professional registration (NMC PIN, GMC, SIA, Gas Safe,
  CORGI, ECS/CSCS); minimum years of experience; degree/qualification yes-no; shift and
  location availability; salary expectation vs banding; notice period / "can you start
  immediately"; willingness to undergo DBS checks.
- Taleo formalises this (Oracle-documented): Required vs Asset answers with weights and an
  "ACE candidate" threshold. Other systems implement the same idea as auto-disqualify rules.
- DO tell the user these questions exist and gate everything; DO ensure the CV's stated
  experience, licences, and locations are consistent with the answers they will give.
- DON'T ever advise lying — UK right-to-work is verified by statute before hire, and licence
  claims are checked. DO advise answering the literal question: settled/pre-settled status or
  ILR means "yes" to right-to-work and usually "no" to needing sponsorship — candidates
  routinely knock themselves out by answering ambiguously.
- Where a question allows free text, reuse the advert's language, exactly as in section 5.

## 8. File naming and contact block

- File name: `Firstname-Lastname-CV.pdf` (or `Firstname-Lastname-CV-Company.docx` when
  tailoring). Recruiters see it and some systems label the record with it. No "final_v3",
  no bare "CV.pdf", no spaces-and-underscores mix, no special characters.
- Name: the first line of BODY text, plain text, the largest text on the page. Never in the
  Word header layer, never a logo or image.
- Contact block, lines 2–4 of the body: phone in clean format (+44 7700 900123 or
  07700 900123); plain-text professional email; town/city + country (full street address is
  unnecessary on UK CVs); LinkedIn URL as visible text. One item per separator, spaced —
  "London, UK | 07700 900123 | name@mail.com | linkedin.com/in/name".
- No photo. Standard for UK CVs and photos are unparseable and bias-risky.

## 9. ATS-safe rendering checklist — apply to EVERY CV produced

Fail any item → fix before delivery. This enforces the skill's invariant.

1. Single column, top-to-bottom flow. Zero tables, zero text boxes, zero sidebars, zero
   multi-column sections (including two-column skills lists — use comma-separated lines).
2. Zero images, icons, logos, photos, charts, skill bars, or graphical dividers.
3. Nothing in the document header or footer — page numbers included; name and contact
   details are body text at the top.
4. Candidate's full name is the first body line; contact block directly beneath in plain text.
5. Conventional section headings only (section 6 list), as plain flowed text.
6. One consistent date format throughout ("Mon YYYY – Mon YYYY" or "Month YYYY – Present").
7. System-safe font (Arial/Calibri/Helvetica/Georgia/Times), 10–12 pt body, standard round
   bullets or hyphens only; straight quotes; hyphens not em dashes; no decorative Unicode.
8. Every priority keyword from the advert appears in the Skills section AND in one
   experience bullet; every acronym paired once with its expansion.
9. No glued tokens: spaces around slashes and pipes in skill lists.
10. Output format: .docx by default for Taleo/unknown/agency; text-based PDF acceptable for
    modern systems; always follow the advert's explicit instruction. Never a design-tool or
    scanned PDF.
11. File named `Firstname-Lastname-CV[-Company].ext`.
12. Sanity test: copy-paste the rendered file into plain text — reading order must be perfect
    and nothing may go missing. If the paste is scrambled or lossy, so is the parse.

## Sources

- https://atsverification.com/research/ (8-engine parsing benchmark and failure patterns)
- https://resumeoptimizerpro.com/blog/how-resume-parsers-actually-work (per-system parse tests)
- https://www.jobscan.co/blog/resume-tables-columns-ats/
- https://www.jobscan.co/blog/greenhouse-ats-what-job-seekers-need-to-know/
- https://www.jobscan.co/blog/resume-pdf-vs-word/
- https://www.jobscan.co/blog/knockout-questions-answer-application/
- https://docs.oracle.com/en/cloud/saas/taleo-enterprise/20b/otrec/candidate-prescreening.html (Oracle: Required/Asset/weighting, ACE candidates)
- https://docs.oracle.com/cloud/latest/taleo/OTREC/_prescreening_ug.htm
- https://www.nhsemployers.org/articles/employer-responsibilities-and-avoiding-discrimination-qa (UK sponsorship-screening legality)
- https://www.gov.uk/uk-visa-sponsorship-employers
- https://www.indeed.com/career-advice/resumes-cover-letters/ats-resume-template
- https://www.tealhq.com/post/workday-resume
- https://scale.jobs/blog/get-through-workday-application-system-successfully
- https://www.resumemate.io/blog/pdf-vs-docx-for-resumes-in-2025-what-recruiters-ats-really-prefer/
- https://www.resumemate.io/blog/tables-columns-text-boxes-do-they-break-ats-safer-layouts/
- https://www.hiretruffle.com/blog/knockout-questions
- https://www.talentprise.com/semantic-search-vs-keyword-search-recruitment/
- https://arc.dev/employer-blog/13-best-ats-for-startups-ashby-greenhouse-lever/
- https://skima.ai/integrations/bamboohr-ai-screening
- https://www.hbs.edu/managing-the-future-of-work/Documents/research/hiddenworkers09032021.pdf (HBS "Hidden Workers", Fuller & Raman 2021)
