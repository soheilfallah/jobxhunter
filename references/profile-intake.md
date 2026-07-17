# Profile intake — build the master profile from a dump folder

The zero-friction first run, best in **cowork** (where the agent can read PDFs, DOCX, images and text
directly). The user drops everything they have about themselves into `<workspace>/dump/`; the skill
reads it and writes their master profile. No blank template to fill by hand.

## What goes in `dump/` (tell the user)
Anything and everything, in any format:
- Old **CVs / résumés** (any version), cover letters
- **LinkedIn export** (Profile → Save to PDF, or the data-export archive)
- **Certificates, licences, transcripts, degree certificates** (PDF/photo)
- **Brag docs / notes / brain-dumps** — freeform is fine, even messy
- Performance reviews, reference letters, portfolios, project write-ups
- **Job ads they liked** (helps infer target families + market)
- A short note on **location, work authorisation, salary floor, and where they want to work**

## The intake steps
1. **Enumerate + read every file in `dump/`.** In cowork, read PDFs/DOCX/images/text with the file
   tools. Note each file's type so nothing is skipped.
2. **Extract only real facts** — roles (title, org, location, dates, what they did, numbers), skills,
   education, certifications/licences, outputs (with links/DOIs), contact details, location, and work
   authorisation. Keep the mundane; the tailorer selects later. **Never infer a fact the dump doesn't
   support.**
3. **Synthesise `profiles/<name>.md`** per `references/master-profile-schema.md` — a WAREHOUSE (richer
   than any CV), section headings matching the schema, including `## Career targets & market`.
4. **Build the "never claim" list** by asking: which listed skills/techniques has the person NOT
   actually performed? This guards the truth rule downstream.
5. **Detect the market** from location + work authorisation + the target job ads (`uk` / `ca` / …).
   Confirm it with the user — it drives conventions, boards and connectors (see the "Market" section in
   `SKILL.md`).
6. **Surface gaps and conflicts** in one neutral batch: unexplained timeline gaps, ambiguous dates,
   overlapping roles, missing licences, anything to put under **Confidential hold**. Frame as
   memory-jogs, never accusations — the dump is rarely complete.
7. **Confirm, then proceed** to DAILY HUNT or TAILOR on the chosen market path.

## Rules
- **Truth first.** The profile may hold only what the dump + the user's confirmations support. A blank
  is a gap to ask about, never a licence to invent.
- **Privacy.** The `dump/` folder and the built profile are personal data — they live in the workspace,
  which is gitignored/kept out of any published repo. Never echo `Confidential hold` content onto a
  document.
- **Idempotent-ish.** Re-running intake after the user adds more files should enrich the profile, not
  clobber confirmed content — merge, surface new facts, keep prior confirmations.
