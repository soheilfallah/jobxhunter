# Raw research notes — ATS parsing mechanics (2026-07-06)

Working notes for references/ats-mechanics.md. Mix of vendor docs, independent testing write-ups,
and SEO-adjacent career sites — reliability flagged per item. Distil, don't copy.

## Source reliability tiers
- TIER A (vendor/official): Oracle Taleo docs, GOV.UK, NHS Employers, Indeed career guide.
- TIER B (independent testing / recruiter accounts): atsverification.com research (8-engine benchmark,
  states methodology: no proprietary access, empirical testing), Jobscan (runs own parser tests),
  LinkedIn recruiter posts.
- TIER C (SEO career-content sites, plausible but unverifiable specifics): resumeoptimizerpro,
  resumemate, scale.jobs, fastapply, resumeadapter, teal, resumegeni, quickcv. Use directionally;
  do NOT present their exact numbers as fact.

## General parsing pipeline (multiple sources agree)
- 5-stage pipeline: text extraction -> tokenization -> section segmentation -> named-entity
  recognition -> structured output. Errors compound across stages.
- Parsers read the document as a LINEAR TEXT STREAM in code order, not visual order. Layout is
  invisible to them. This single fact explains almost every format trap.
- Claimed accuracy figures (Tier C, treat as indicative): ~87% field-level accuracy for modern
  parsers vs ~96% human; contact fields ~99% (regex), skills extraction 70–90%; "~23% of
  early-stage rejections trace to parsing errors" (ResumeAdapter claim — unverified).
- Commercial parsing engines are often licensed, not in-house: Sovren (now Textkernel), Daxtra,
  HireAbility, Textkernel. Greenhouse reportedly used Sovren historically (Tier C claim).

## Myth-busting (well supported)
- Most major ATS do NOT auto-reject on keyword score. Greenhouse explicitly: humans score via
  scorecards; no algorithmic auto-rejection; default candidate list ordered by date, not score
  (Jobscan Greenhouse guide; Greenhouse CEO Daniel Chait public statements).
- What DOES auto-reject: knockout/screening questions (see below), and Taleo-style weighted
  prescreening filters configured by the employer.
- Keywords matter mainly because RECRUITERS SEARCH the candidate database (boolean/exact-string)
  and because some systems compute match scores recruiters can sort by.
- Harvard Business School "Hidden Workers" (Fuller et al., 2021): 88% of employers say their
  systems screen out qualified candidates who don't match job-description wording.

## Per-system notes

### Workday
- Notorious for parse-then-re-key flow: resume parsed into "My Information" / "My Experience"
  fields; candidate must review and manually fix fields. Autofill error rates widely complained
  about (one Tier C source claims ~34% error rate — unverified, but the complaint is universal).
- Parsed structured fields become the candidate's persistent profile with that employer — bad
  parse hurts across all future applications at that company.
- Strict on dates: wants "Month YYYY" or MM/YYYY; inconsistent date formats can break the whole
  employment timeline (Tier B/C consistent).
- Fails hard on multi-column layouts and content in Word headers/footers (Tier B benchmark).
- Handles standard single-column .docx best.

### Greenhouse
- Structured hiring model: humans score on scorecards; recruiter typically views the ORIGINAL
  uploaded PDF with parsed fields as sidebar metadata. Readability of the actual document
  matters more than parse-field perfection here.
- No auto-rejection by keyword score; list default-sorted by application date.
- Parser (reportedly Sovren/Textkernel lineage) is among the better ones: keeps bullet structure,
  flexible on dates, good skill extraction — but sensitive to non-standard section headings
  ("Professional Journey" emptied the employment array in one test — Tier C).
- Recognises hyperlinks (LinkedIn/portfolio) well (Tier B).

### Lever
- Silently drops content it can't place — especially SIDEBAR content in two-column layouts
  (skills sidebar → empty skills array in tests). Candidate never sees what went missing.
- Forgiving contact parser; compresses bullets to a newline-joined string.
- Now part of Employ Inc. (with Jobvite/JazzHR).

### Taleo (Oracle)
- Oldest major enterprise ATS; legacy reputation for crude exact keyword matching is partially
  earned: plain-text-oriented parser, strict section labels, struggles with special characters
  (curly quotes, em dashes) and any non "Mon YYYY" date (Tier B benchmark).
- REAL ranking mechanism is documented by Oracle (Tier A): prescreening questions with
  Required / Asset / weighted answers. "Required" missed = candidate not considered. Weighted
  score as % of max points; ACE-candidate threshold (e.g. >=75% + all Required met) flags top
  candidates to recruiter. So Taleo gating = employer-configured questions more than resume NLP.
- Fails hard on multi-column; treats decorative Unicode as section boundaries (Tier C detail).

### iCIMS
- Modern parser, better error recovery; OCR fallback for image PDFs exists but degrades quality.
- Strict post-parse validation: uncertain fields get pushed back to the candidate to re-enter
  manually (Tier C).
- Enterprise; big in high-volume hiring.

### Ashby
- Newer, AI-forward. Automated parsing + AI candidate matching; recruiters can express filters
  in natural language → converted to structured filtering. Semantic-ish matching more likely
  here than in legacy systems. Little public detail on parser internals — be honest about that.

### SmartRecruiters
- AI engine scores/ranks applicants on skills/experience/role fit with configurable criteria
  weighting ("SmartAssistant"). Match-score sorting exists — keywords matter more here.

### BambooHR
- SMB-focused; basic built-in parsing/screening; heavier AI ranking typically via third-party
  integrations (e.g. Skima AI). Simplest parser expectations; plain formatting wins.
- Knockout questions supported in application forms.

## Format traps — WHY each breaks
- Tables: parser walks the XML/text stream; reads across a row through all cells (or in cell code
  order), interleaving unrelated content → "word salad". Some parsers skip table content wholly.
- Multi-column: text extractor reads line-by-line across the full page width, zipping two columns
  together; or reads sidebar first, destroying chronology. Single most damaging pattern in the
  8-engine benchmark.
- Headers/footers (Word/PDF layer): stored in a separate document layer from body text; many
  extractors pull body layer only → contact info in the header simply vanishes. Cited as
  problematic specifically for Workday, Taleo, iCIMS.
- Text boxes: floating objects outside main text flow; often skipped entirely or appended out
  of order.
- Images/icons/graphics/skill bars: no text layer → invisible. Icon-as-label (phone icon instead
  of "Phone:") removes the cue the NER stage needs. Skill-rating bars carry zero parseable data.
- PDFs-as-image (Canva/Photoshop/scan exports): no text layer at all; extract nothing unless the
  ATS OCRs (only some, e.g. iCIMS fallback, and OCR degrades to ~85% field level).
- Unusual/modern display fonts (Avenir, Proxima Nova, Montserrat...): font-substitution and
  glyph-mapping issues; ligatures can produce glued or garbled tokens. Stick to system-safe fonts.
- Glued tokens ("SAPOracle" from slash/pipe separators without spaces) break keyword matching in
  Greenhouse/Lever tests.
- Special characters: curly quotes, em dashes, decorative Unicode bullets → encoding issues
  (Taleo worst); use plain hyphens and standard round bullets.

## .docx vs PDF
- Modern consensus: LAYOUT matters more than container. Any clean single-column text file parses
  in any major modern system.
- .docx edge: XML with guaranteed text ordering → most consistent extraction across engines
  ("DOCX outperformed PDF in 6 of 8 systems" — Tier C test claim). Safer for Taleo and older/
  unknown systems, and when a staffing agency wants an editable file.
- Text-based PDF (exported from a word processor, NOT design tools): fine for virtually all
  modern systems; locks layout for the human reader; preferred where the recruiter reads the
  original doc (Greenhouse, Lever, Ashby).
- Absolute rule: explicit instructions in the job posting override everything.
- Never: PDF exported from Canva/Illustrator/Photoshop, scanned PDF, .pages, .odt, image files.

## Keywords
- Exact/near-exact string matching still dominates recruiter search (boolean). Semantic matching
  growing (Ashby, SmartRecruiters, AI add-ons) but cannot be relied on.
- Acronym rule: always pair acronym + expansion at least once — "NLP (Natural Language
  Processing)", "CIPD", "SQL". Recruiters may search either form; exact-match systems find only
  the literal string.
- Placement: keyword should appear in a dedicated Skills section (for field extraction/search)
  AND in context inside an experience bullet (for credibility with the human + phrase-level
  matching). Titles matter: mirror the target job title where truthful (e.g. in the headline).
- Mirror the job ad's exact phrasing for hard skills ("stakeholder management" vs "managing
  stakeholders" can matter to literal-match search).
- Anti-stuffing: white-text keywords are detected/normalised by modern parsers and visible to
  recruiters viewing the original doc; keyword walls fail the human reader who makes the actual
  decision. Density buys nothing in date-sorted systems (Greenhouse/Lever).

## Section headings
- Reliably recognised: Professional Summary / Summary, Work Experience / Professional Experience /
  Employment History, Education, Skills / Key Skills / Technical Skills, Certifications /
  Licences & Certifications, Projects, Publications, Volunteering. (UK: "Career History" is
  common but "Work Experience" is safest cross-parser.)
- Creative headings ("Where I've Made Impact", "My Journey", "Professional Journey", "Career
  Story") cause misclassification or whole-section loss — documented in Greenhouse/Lever tests.
- Heading should be plain body-flow text, bold/larger ok; not inside a text box or graphic.

## Knockout / screening questions
- Definition: mandatory application-form questions with disqualifying answers; wrong answer →
  auto-reject/auto-archive with templated email; recruiter never opens the CV.
- Common knockouts: right to work in the UK; "will you now or in future require sponsorship";
  driving licence / professional licence (SIA, NMC PIN, Gas Safe); years of experience threshold;
  qualifications (degree yes/no); shift/location availability; salary expectation vs range;
  notice period / "can you start immediately"; DBS willingness.
- These fire BEFORE any parsing/ranking matters. Answer accurately; never lie (right-to-work is
  verified by law in the UK — Employer's illegal-working checks). But answer the question actually
  asked: e.g. someone with a Graduate visa now but needing future sponsorship must answer the
  literal question; a British/ILR/settled-status candidate should never ambiguously self-describe.
- UK legal nuance (NHS Employers / discrimination guidance): blanket early-stage sponsorship
  exclusion carries discrimination risk for EMPLOYERS — but as a candidate-side skill, assume the
  knockout exists and is enforced.
- Taleo formalises this as Required/Asset weighted prescreening + ACE thresholds (Oracle docs).

## File naming & contact info
- File name: Firstname-Lastname-CV.pdf / .docx (or Firstname-Lastname-CV-Company.pdf). No
  spaces→use hyphens ok; no version cruft ("final_v3"), no "CV" alone, no special characters.
  File name is visible to recruiters and sometimes used as record label.
- Name: first line of body text, plain text, largest font on page. NOT in Word header layer,
  not in an image/logo, no nicknames mixed formats.
- Contact block (body text, lines 2–4): phone in international or clean national format
  (+44 7700 900123 or 07700 900123), plain-text email (no mailto graphics), town/city + country
  (full street address unnecessary in UK now), LinkedIn URL as visible text.
- Email: professional, personal domain fine; avoid dots-heavy or joke addresses.
- Don't put contact info side-by-side in table cells across the top.

## URLs collected
- https://resumeoptimizerpro.com/blog/how-resume-parsers-actually-work
- https://atsverification.com/research/
- https://www.jobscan.co/blog/resume-tables-columns-ats/
- https://www.jobscan.co/blog/greenhouse-ats-what-job-seekers-need-to-know/
- https://www.jobscan.co/blog/resume-pdf-vs-word/
- https://www.jobscan.co/blog/knockout-questions-answer-application/
- https://www.jobscan.co/blog/20-ats-friendly-resume-templates/
- https://docs.oracle.com/en/cloud/saas/taleo-enterprise/20b/otrec/candidate-prescreening.html
- https://docs.oracle.com/cloud/latest/taleo/OTREC/_prescreening_ug.htm
- https://www.nhsemployers.org/articles/employer-responsibilities-and-avoiding-discrimination-qa
- https://www.gov.uk/uk-visa-sponsorship-employers
- https://www.indeed.com/career-advice/resumes-cover-letters/ats-resume-template
- https://www.tealhq.com/post/workday-resume
- https://www.resumemate.io/blog/pdf-vs-docx-for-resumes-in-2025-what-recruiters-ats-really-prefer/
- https://www.resumemate.io/blog/tables-columns-text-boxes-do-they-break-ats-safer-layouts/
- https://www.hiretruffle.com/blog/knockout-questions
- https://scale.jobs/blog/get-through-workday-application-system-successfully
- https://blog.fastapply.co/ats-resume-format-guide-2026
- https://www.talentprise.com/semantic-search-vs-keyword-search-recruitment/
- https://www.brainner.ai/blog/article/the-benefits-of-semantic-search-over-keyword-matching-in-resume-screening
- https://arc.dev/employer-blog/13-best-ats-for-startups-ashby-greenhouse-lever/
- https://skima.ai/integrations/bamboohr-ai-screening
- HBS Hidden Workers report (Fuller/Raman 2021): https://www.hbs.edu/managing-the-future-of-work/Documents/research/hiddenworkers09032021.pdf
