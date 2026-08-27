# Application-form answer pack — the tedious supplemental questions

The most time-consuming part of a modern application isn't the CV — it's the Workday /
Greenhouse / Lever supplemental questionnaire: right-to-work, years of experience, salary
expectation, notice period, and two or three free-text "why us / describe a time…" boxes.
jobxhunter already parses these as knockouts during JD analysis and already holds everything
needed to answer them: the master profile, the cover-letter brain-dump, and the Adzuna
salary band fetched during sourcing. This routine assembles a **draft answer pack** the user
reviews and pastes — it never auto-submits.

Every answer maps to profile evidence. A knockout the candidate can't clear is surfaced (and
the role is likely a `Skipped`).

## When
During TAILOR (or TRACK) for any role whose JD/application has screening or knockout
questions. Pull the parsed questions from the JD analysis (`references/jd-analysis.md` §0).

## Inputs
- Parsed screening/knockout questions.
- Master profile (work authorisation, timeline, skills, location, salary floor).
- The cover-letter brain-dump if one exists (for the free-text motivation boxes).
- The Adzuna salary band fetched during sourcing (for the expectation question).

## Build the pack (into the job folder's `notes.md`, under "## Application answer pack")
For each question, draft a ready-to-paste answer:
- **Right-to-work / visa** — straight from the profile's work-authorisation field. Never
  overstate status.
- **Years of experience with X** — *computed from the timeline*, not guessed. If it's
  below the ask, that's a surfaced gap.
- **Salary expectation** — anchor to the fetched Adzuna band and the profile's floor; give a
  range, not a single number, and note it's negotiable. Never below the floor.
- **Notice period / availability / relocation** — from the profile.
- **Free-text "why this company / describe a time…"** — draft from the brain-dump in the
  user's own voice (de-slopped via `references/writing-voice.md`); if there's no brain-dump,
  draft from profile + research only and **flag it as profile-only** so the user adds the
  personal angle. Keep to the box's word limit.
- **Yes/no eligibility gates** — answer only from fact; if a "no" is a hard knockout, say so
  and recommend logging the role `Skipped` with the reason.

## Rules
- **Human-in-the-loop.** This is a prep pack to review and paste — jobxhunter does not submit
  forms.
- Keep each answer labelled with its source question so the user can match them on the form.
- Flag every answer that is profile-only (no brain-dump behind it) so the user can add colour
  before pasting.
