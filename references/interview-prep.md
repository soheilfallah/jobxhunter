# Interview prep — carry the candidate past "filed"

Most tools stop at the application. The pipeline already holds everything needed to
prepare for the interview **honestly**: the JD (what they'll probe), the coverage matrix
in `notes.md` (exactly where the candidate is strong, partial, or has a hard gap), and the
master profile (the real evidence). This routine turns that into a prep pack the candidate
can actually walk in with — and, crucially, it prepares them for the questions their *gaps*
invite, which generic prep never does.

**Truth rule still holds.** Every STAR answer is built from real profile evidence. For a
hard gap, you do **not** invent experience — you prepare an honest, confident way to handle
the question (transferable evidence + a learning plan), which is what a good candidate
actually does.

## Inputs
- The job folder: `job-description.md` + `notes.md` (the coverage matrix, provisional items,
  recruiter scorecard).
- The master profile (source of truth for every claim).
- The market + role type (sets tone: NHS panel vs startup vs university vs security ops).

## Method
1. **Adopt the interviewer persona** for this JD (reuse `references/recruiter-rubric.md`'s
   persona logic). A PI, an NHS panel, a fintech EM, and a security lead ask different
   questions and reward different things. State which persona you assumed.
2. **Predict the questions, grouped by the JD's real must-have competencies.** For each
   must-have, write the 1–3 questions an interviewer would use to test it — a mix of
   behavioural ("tell me about a time…"), technical/role-specific, and situational.
3. **Draft a STAR answer for each, from real evidence only.** Situation · Task · Action ·
   Result, pulled from the profile (prefer quantified outcomes). Keep them spoken-length
   (60–90 seconds), first person, in the candidate's own register — not corporate.
4. **Gap-defence — the differentiator.** For every `hard-gap` and `partial` row in the
   coverage matrix, prepare the question they *will* ask and an honest, non-defensive answer:
   the closest transferable evidence, genuine enthusiasm, and a concrete "here's how I'd get
   up to speed" line. Never fake the experience; show the trajectory. Also prep any
   provisional ("pending confirmation") item — if it makes the CV, the candidate must be able
   to speak to it truthfully.
5. **Questions for them.** 4–6 sharp, specific questions the candidate can ask — drawn from
   the JD and company research, signalling genuine interest (team shape, success in 6 months,
   the real challenge behind the role). Avoid anything answerable from the JD.
6. **Logistics + first impression.** Format (panel/technical/take-home), the 30-second
   "walk me through your CV" opener built from the tailored CV's headline, and 2–3 likely
   curveballs (salary expectation — anchor to the Adzuna band already fetched; notice period;
   the timeline gap the CV surfaced).

## Output
Write `interview-prep.md` into the **same job folder**, with sections: Persona & format ·
Your 30-second opener · Questions by competency (with STAR answers) · Gap-defence · Questions
to ask them · Curveballs & logistics. Then remind the user this ties to the tracker: when they
land the interview, `tracker.py update … {"status":"Interview"}` stamps the date and this pack
is right there in the folder.

## Tone
Encouraging and specific, never generic filler. The value is that it is built from *their*
real evidence against *this* JD — so it rehearses the exact conversation, gaps included.
