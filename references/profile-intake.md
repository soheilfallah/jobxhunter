# Profile intake — build the master profile from a dump folder

The zero-friction first run, best in **cowork** (where the agent can read PDFs, DOCX, images and text
directly). The user drops everything they have about themselves into `<workspace>/dump/`; the skill
reads it and writes their master profile. No blank template to fill by hand.

Intake is **profiling** — the foundation everything else stands on. A rich, specific profile is what
lets the tailorer and cover-letter writer stay concrete; a thin one is where vague, generic statements
come from. So intake does two jobs: **capture every fact in the dump**, and **actively interview the
user to fill the thin spots** before any CV is written.

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

1. **Scan the dump — manifest first, so nothing is lost and re-runs are incremental.**
   Run the book-keeper before reading anything:
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/dump_manifest.py" scan --workspace <root>
   ```
   It writes/updates `dump/_manifest.csv` (one row per file: `status ∈ new / updated / unreadable /
   ingested / missing`) and prints exactly what to act on:
   - **new / updated** text files → read them now.
   - **unreadable** files (Word/PDF/image/binary it can't auto-extract as text on this surface) → it has
     already created an **empty placeholder stub** under `profiles/_intake/placeholders/` naming each
     source file and how to ingest it. In cowork/Desktop (and for PDFs/images in Claude Code) read them
     directly with the file tools; otherwise leave the stub and tell the user to convert-to-text or
     re-run intake in cowork. **Never silently skip an unreadable file — the stub is its receipt.**
   - **ingested** files are already in the profile — skip them. This is what makes a second intake only
     process what's genuinely new ("update the profile every time new information comes").

2. **Read every actionable file and extract only real facts** — roles (title, org, location, dates,
   what they did, numbers), skills, education, certifications/licences, outputs (with links/DOIs),
   contact details, location, and work authorisation. Keep the mundane; the tailorer selects later.
   **Never infer a fact the dump doesn't support.**

3. **Synthesise / enrich `profiles/<name>.md`** per `references/master-profile-schema.md` — a WAREHOUSE
   (richer than any CV), section headings matching the schema, including `## Career targets & market`.
   On a first run this creates the file; on later runs it **merges** (see the incremental contract below).

4. **Mark each file done as you go** so the manifest stays current:
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/dump_manifest.py" mark --workspace <root> --path "<rel_path>" --status ingested
   ```
   Then delete that file's placeholder stub if one was created. Append a one-line entry to
   `profiles/_intake/CHANGELOG.md` describing what this run added (the audit trail).

5. **Build the not-on-CV list** by asking: which listed skills/techniques has the person NOT
   actually performed, and what else do they not want printed?

6. **Run the profile enrichment interview** (below) — turn thin, vague, or unquantified spots into
   concrete evidence *now*, at the source, before any CV is tailored.

7. **Detect the market** from location + work authorisation + the target job ads (`uk` / `ca` / …).
   Confirm it with the user — it drives conventions, boards and connectors (see the "Market" section in
   `SKILL.md`).

8. **Surface gaps and conflicts** in one neutral batch: unexplained timeline gaps, ambiguous dates,
   overlapping roles, missing licences, still-unreadable dump files, anything to put under
   **Confidential hold**. Frame as memory-jogs, never accusations — the dump is rarely complete.

9. **Confirm, then proceed** to DAILY HUNT or TAILOR on the chosen market path.

## The profile enrichment interview (the anti-vague engine)

Vague CVs are almost always a *profiling* failure, not a writing failure — you can't select a concrete
detail that was never captured. So when a section is thin or a claim is unquantified, **ask the user
now** and write the answer straight into the profile. Fixing it here fixes it for every future CV and
cover letter; patching it per-document does not.

**When to ask** — trigger a question only where evidence is genuinely missing (never interrogate a
section the dump already answers):
- an **experience** bullet with no outcome, number, scale, or method;
- a **skill** listed with no project or role behind it;
- **education/cert** missing grade, institution, or real years;
- a **timeline gap**, ambiguous date, or overlapping roles;
- **targets** unset (priority order, salary floor, geography, work pattern);
- a claim you can't tell is real vs aspirational (→ candidate for the not-on-CV list).

**How to ask** — small neutral batches (5–8 at a time), grouped by profile section, framed as
memory-jogs ("you probably did this and just didn't write it down"). Offer a voice note for anyone who'd
rather talk it out. Record answers directly into `profiles/<name>.md`; **never** hold them only for the
current CV.

**Starter-question bank** (adapt to the person; don't ask what's already answered):
- *Per role:* "What was the measurable outcome — a number, %, £, time saved, or scale (team size, users,
  rows, sites)?" · "What was the method or tool, specifically?" · "What changed because you were there?"
  · "Was this solo or a team — and what was *your* part?"
- *Per skill:* "Where did you actually use this — which project or role?" · "How recently, and to what
  depth (tried once / used in production / taught others)?"
- *Education/certs:* "Institution, country, real years, and grade/classification?" · "Any licence number
  or expiry that matters (e.g. SIA, driving)?"
- *Outputs:* "Anything published, shipped, or public — a DOI, repo, portfolio link, product name?"
- *Gaps/timeline:* "The stretch between X and Y — study, caring, travel, freelance? One line is all
  we need."
- *Targets/market:* "Rank your target roles 1–3." · "Salary floor you won't go below?" · "Locations,
  remote/hybrid, willing to relocate?" · "Full-time / part-time / contract?"
- *Not-on-CV:* "Anything here you've read about but not actually done, or don't want printed? That
  goes on the not-on-CV list."

Stop when the schema's minimal-viable sections (Identity, Experience, Education, Skills warehouse) are
concrete and the top-priority target lane has enough specific evidence to tailor without hand-waving.

## Rules
- **Blanks are questions.** The profile holds what the dump and the user's answers give it; where
  the dump is silent, ask.
- **Privacy.** The `dump/` folder, the built profile, and `profiles/_intake/` are personal data — they
  live in the workspace, which is gitignored/kept out of any published repo. Never echo
  `Confidential hold` content onto a document.
- **Incremental, never clobbering.** Re-running intake after the user adds files must **enrich**, not
  overwrite: the manifest tells you what's new; merge new facts in, keep prior confirmations and the
  not-on-CV list intact, and log the delta to `profiles/_intake/CHANGELOG.md`. Confirmed content is
  never silently rewritten.
