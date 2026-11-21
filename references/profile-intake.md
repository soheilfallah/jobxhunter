# Profile intake: build the profile from a dump folder

The user drops everything they have about their working life into `<workspace>/dump/`. Intake reads
it and writes `profile.md`, then agrees the target roles. No blank template to fill by hand.

The profile is the foundation. Every master CV is built from it alone, so a thin profile is where
vague CVs come from. Intake therefore does two jobs: capture every fact in the dump, and ask the
user about the thin spots before any CV is written.

## What goes in `dump/`

Anything, in any format and any language:

- old CVs and résumés, cover letters
- a LinkedIn export (Profile, then Save to PDF)
- certificates, licences, transcripts
- notes, brag documents, performance reviews, reference letters, project write-ups
- adverts for jobs they liked
- a short note on location, right to work and where they want to work

## The profile is plain

`profile.md` is ordinary prose and lists under ordinary headings. There is no schema to satisfy and
no rules block. A sensible shape:

- name and contact details, location, right to work
- each job: title, employer, city, dates, what they did, numbers, tools
- education and qualifications
- skills, with where each was used
- publications, projects, anything public
- anything the user said they do not want on a CV

It holds far more than any one CV shows. Each master CV takes only the facts its role needs.

## Steps

1. **Read every file in `dump/`.** PDFs, Word files and images included, where the surface can read
   them. For a file that cannot be read, say so by name and ask the user for a text copy. Never skip
   one silently.
2. **Extract facts only.** Roles, dates, what was done, numbers, tools, education, licences,
   outputs, contact details. Keep the mundane. Never infer a fact the dump does not support.
3. **Write or merge `profile.md`.** The first run creates it. A later run adds what is new and
   leaves alone everything the user has already confirmed or corrected.
4. **Ask about the thin spots** (below), and write the answers into the profile.
5. **Ask what jobs they are going for,** then propose the target roles and write
   `master-cvs/TARGETS.md` (below).
6. **Show the user** the profile's path and its job headings, and ask them to correct anything
   wrong. An error here is an error on every CV.

Once the user has confirmed the profile it is the only source of truth. From then on nothing
questions it, fact-checks it or flags gaps in it.

## Asking about thin spots

Vague CVs are a profiling failure, not a writing failure: a detail that was never captured cannot
be chosen later. Ask only where evidence is missing, never about a section the dump already
answers:

- a job with no outcome, number, scale or method
- a skill with no project or role behind it
- a qualification missing its institution or grade
- an unclear date

Ask in small batches grouped by job, framed as memory-jogs ("you probably did this and did not
write it down"). Offer a voice note to anyone who would rather talk. Useful questions:

- *Per job:* what was the measurable result (a number, a percentage, money, time saved, or scale
  such as team size, users, sites)? What was the method or tool? What was your own part?
- *Per skill:* where did you use this, how recently, and to what depth?
- *Outputs:* anything published, shipped or public, with a link?

Stop when each job has concrete evidence. This is an interview during intake only; it is not
repeated at tailoring time. If a question goes unanswered, drop it or note it in `STATE.md`. Do not
write open questions into `profile.md`: the master builders read that file as fact.

## Agreeing the target roles

One master CV is not enough, so the roles need naming before any CV is written.

1. Ask what the user wants to apply for. Take their words first.
2. From their answer and the profile, propose roles grouped by family, for example `data/data-analyst`
   and `operations/operations-manager`. Include adjacent roles the profile clearly supports and say
   why each is there. The user removes or adds freely.
3. For each agreed role, draft its four title lists: core titles, aim up, same work under a
   different name, and title knockouts (`references/job-search-guide.md`).
4. Ask the market (`uk` or `ca`), the locations, and whether anything is a hard filter. Record a
   hard filter only when the user states it as a fact ("I cannot hold security clearance"). Pay,
   contract type and seniority are not filters unless they say so.
5. Fill in the workspace's `master-cvs/TARGETS.md`, keeping its layout. Leave `Queries:` empty
   unless the user has exact search strings they want run as well.

## Rules

- **Blanks are questions.** Where the dump is silent, ask. Never fill a gap with a guess.
- **Private.** `dump/` and `profile.md` are personal data and stay in the workspace.
- **Never clobber.** A later intake enriches the profile. Confirmed content is not rewritten.
