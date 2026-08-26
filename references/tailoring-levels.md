# Tailoring levels — the dial from true to aspirational

This doc defines the control dial the tailorer operates on. Read it before producing any CV. The level is chosen by the user (or defaults to L1). The `%` is a knob *within* a level, not a fourth level.

## The three levels

### L0 — True, reframed
Same facts as the master profile, optimally worded and ordered for this specific JD. Nothing is dropped for being unflattering unless it's simply irrelevant to the target. This is the honest baseline and is **always submittable**.
- Use when: the user wants a faithful CV, or as the floor of any run.
- Rule: every line traces to profile evidence. Reframing and reordering only.

### L1 — Aggressive but true (DEFAULT)
Maximal *honest* emphasis. Foreground the best-matching evidence, drop weak or irrelevant items entirely, use the most favourable accurate framing of real facts. Still **fully submittable** — nothing here is fiction.
- The `%` knob (0–100) sets how aggressive the emphasis is:
  - **~25%**: light touch — mild reordering, keep most content, gentle keyword weaving.
  - **~50%**: balanced — clear foregrounding of matches, cut the weakest 1–2 items.
  - **~75–100%**: maximal honest slant — lead hard with matching evidence, cut everything that doesn't serve the target, most favourable (but still accurate) framing of every remaining line.
- The knob NEVER crosses into invention. 100% aggressive is still 100% true.
- Use when: real applications. This is the workhorse.

### L2 — The alternative world
A *different realistic person* — a "John/Jane Doe" — who already holds the experience the JD wants and would win the interview. **Realistic, not heavenly-perfect**: a genuinely strong CV that earns a callback, not a fantasy stack of every buzzword. A clean, normal CV.
- **No watermark, no disclaimer on the artifact itself.** (Agreed design: it's for learning/targeting, never submission.)
- Delivered ALONGSIDE a plain statement of the **delta** — the specific experience, skills, and certifications that separate the real candidate from this persona. That delta is the entire point: it's the user's roadmap to the role.
- Use when: the user wants to see the ceiling and the exact route to it.
- Construct the persona by: taking the JD's must-haves and nice-to-haves, and imagining a *plausible* individual whose history naturally covers them — realistic career progression, realistic (not maximal) achievements, believable institutions and timelines. Anchor it near the real candidate's field so the delta is instructive, not absurd.

## Non-negotiables (hold the line)

1. **L0 and L1 never cross into fiction.** They select, reframe, reorder, emphasise — they never invent a fact, a role, a skill, a date, or a metric not grounded in the profile. If evidence for a requirement isn't in the profile, that's a **gap to surface**, not a blank to fill.
2. **Only L2 generates beyond the profile**, and only as the alternative-world persona, and only ever labelled as such **in the conversation/notes — never on the document**.
3. **L2 is never presented as submittable.** When delivering L2, always pair it with the delta statement and a clear in-conversation note that this is a target persona, not the user.
4. **The delta is mandatory output for L2.** An L2 CV with no delta statement is an incomplete, and dangerous, deliverable.

## How the level interacts with the pipeline

- **Coverage matrix** (built for every run) marks each JD requirement as *strong / partial / gap* against profile evidence.
  - L0/L1 work only from *strong* and *partial* rows; *gap* rows are surfaced to the user, never fabricated.
  - L2 is allowed to fill *gap* rows — that's what makes it the alternative world, and filling them is exactly what defines the delta.
- The recruiter loop scores whatever level was produced. An L1 CV that scores poorly because of genuine gaps should NOT be "fixed" by inventing evidence — surface the gap and, if useful, offer to show the L2 delta instead.

## Gap classes, provisional inclusions & the end-of-run confirmation

The master profile is rarely a complete record of a person. People forget experiences, and the same
skill often lives under a *different name* than the JD uses (JD says "PostgreSQL"; profile says "SQL
(working)"; JD says "stakeholder reporting"; profile has roles where that was obviously done but
never spelled out). The rule "surface gaps, never fill them" must not become a blunt instrument that
**undersells a real candidate** or **interrupts the flow** with a challenge for every term.

So classify each unmatched JD requirement into one of three, at coverage-matrix time:

1. **Strong / partial** — real evidence in the profile. Use it (that's normal tailoring).
2. **Adjacent / plausibly-held (PROVISIONAL)** — the profile gives a *plausible basis* to think the
   candidate has it: an equivalent skill under another name, or a skill a listed role obviously
   implies but doesn't state. **Provisionally include it, keep going, and confirm it at the end** (below).
3. **Hard gap** — no plausible basis at all (SIA licence, a PhD, a specific tool with zero adjacency).
   Do NOT add it, even provisionally. Surface it honestly; this is L2/roadmap territory.

### How provisional inclusions work (no interruption, no accusation)

- **Do not stop mid-draft.** When you hit a class-2 item, add it to the draft *and* to a running
  **"pending confirmation" list** (record it in the job's `notes.md`). Continue to the end.
- **One batch at the very end.** Before the CV is treated as final/submittable, present the whole
  pending list as a single neutral yes/no check — a **memory-jog, not an interrogation**. Frame it as
  making sure the CV neither *oversells* nor *undersells* the person:

  > "Quick confirm before this is final — I've included a few things the role asked for on a
  > reasonable read of your background, but I'd rather check than assume. Just yes/no for each:
  > 1. Have you used **PostgreSQL** specifically (your profile lists SQL — was it Postgres, or another dialect)?
  > 2. Have you done **stakeholder reporting / presentations** in any of your roles?
  > 3. …"

- **Tone rule — this is NOT misconduct.** Never frame a provisional item as the AI catching the user
  in a lie, and never imply the candidate was dishonest. The premise is the opposite: the person
  probably *did* this and simply forgot to write it down, or calls it something else. The check
  exists to *rescue real experience*, not to police it.
- **On the answer:** *yes* → keep it (and suggest adding it to the master profile so it's captured
  next time). *no* → remove it and re-render; it may then become a genuine gap to surface. Nothing
  provisional is ever presented as confirmed, or shipped in a "final" CV, until the user says yes.
- **Reconciles with the anti-mirroring guard** (`SKILL.md` step 4 / `cv-mistakes.md`): pasting a JD
  term with **no** basis in the profile is still fabrication and stays banned. The difference is
  *plausible basis*: class-2 has one (adjacency or an implying role) and is gated by the end-of-run
  yes/no; pure JD-echo with nothing behind it is class-3-or-worse and never goes in.

This keeps the profile invariant intact — nothing false reaches a submittable document, because the
user confirms before it's final — while never interrupting the draft and never treating a forgotten
experience as a lie.

## Cover letters

The L0–L2 dial does **not** apply to cover letters. A cover letter is inherently first-person and
profile-grounded, and is written **in full from the profile plus the JD** — finished and send-ready,
never waiting on a brain-dump. The user's own words, where they volunteer them, are source text for
the voice. See `cover-letter.md`.
