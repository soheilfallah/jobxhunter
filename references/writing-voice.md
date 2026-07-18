# Writing & voice model — the de-slop + register pass

The skill's own, self-contained standard for how every **submittable line** reads: a CV bullet, a
cover-letter sentence, a cold email. The agent applies it **inline** on every draft — no external tools,
no plugins, no keys — so the voice pass reads identically on any surface.

It has two companions and doesn't duplicate them:
- `references/cv-mistakes.md` — the exhaustive CV-specific mistake + **banned-buzzword** catalogue.
- `references/cover-letter.md` — the letter's voice-preservation craft.
This doc is the cross-cutting register + anti-AI-tell standard the other two point to.

## Register first — three documents, three voices

Pick the register **before** editing; the rules below are calibrated to it.

- **CV** → concrete, quantified, professional-neutral. Achievements, not duties. **No first-person
  opinion, no "personality", no soul** — for a CV, neutral *is* the human voice. (This is where
  the voice-preservation rules further down do **not** apply.)
- **Cover letter** → the **user's own voice**, preserved (`cover-letter.md`). Warm-professional, their
  cadence and idiosyncrasy. This is where voice/soul belongs.
- **Cold email** → shorter still, spoken cadence, one human ask.

## The academic register (default for CVs and research/academic letters)

The default register for CVs and research/academic letters:
- **Precision over vagueness.** Name the method, tool, metric, scale. "Analysed data" → "cleaned and
  modelled 40k rows of trial data in R".
- **Active voice for the candidate's own actions** — "built", "led", "designed". Reserve passive only when
  the actor is genuinely irrelevant.
- **Evidence-led.** Every claim anchors to a real number or output; scale the verb to the evidence
  ("contributed to" ≠ "led"). Honest adjacency beats quiet inflation.
- **Controlled formality.** Professional, not inflated. Prefer the plain word: *use* not *utilise*,
  *start* not *commence*, *help* not *facilitate* — but keep genuinely precise technical terms.
- **Concision.** One idea per bullet; cut throat-clearing and stacked hedges.

## AI tells to strip (the Signs-of-AI-writing subset that matters for applications)

Hard rule and high-frequency offenders, each shown in application context:

- **Em & en dashes → cut (hard constraint).** Zero `—`/`–` in any submitted document. Replace with a
  period, comma, colon, or parentheses. Scan the final draft; any hit means it isn't done.
- **AI-vocabulary words.** spearheaded, leverage, utilise, delve, showcase, testament, underscore,
  pivotal, robust, seamless, vibrant, tapestry, honed, fostering, garner, intricate — drop or replace
  with the plain verb. (Full ban-list: `cv-mistakes.md` §1.)
- **Significance / promotional inflation.** "a testament to", "played a pivotal role", "passionate about",
  "results-driven" → state the fact and the number instead.
- **Superficial `-ing` tails.** "...cut costs, *driving efficiency and ensuring scalability*." Delete the
  fake-depth tail; keep the real outcome.
- **Copula avoidance.** "serves as / boasts / stands as" → *is / has*.
- **Rule of three.** Forced tricolons ("innovation, inspiration, and insight") — break the pattern; say the
  one true thing.
- **Negative parallelism.** "not just a role, but a mission" → cut.
- **Elegant variation.** Cycling synonyms for the same thing across bullets (analyst → practitioner →
  specialist) reads as padding — name it once, consistently.
- **False ranges.** "from stakeholder management to data pipelines" when they aren't on a scale — just list.
- **Filler & over-hedging.** "in order to" → "to"; "has the ability to" → "can"; "it could potentially be
  argued" → say it or cut it.
- **Formatting tells (in letters/emails and any prose you hand over).** Mechanical boldface, inline-header
  bullet lists (`**Skill:** ...`), emoji, curly quotes, and Title Case Headings — remove.
- **Letter/email-only tells.** Aphorism formulas ("X is the language of Y"), persuasive-authority tropes
  ("the real question is", "at its core"), signposting ("let's dive in"), sycophancy ("great
  opportunity!"), fake-candid openers ("Honestly?") — all out.

## Voice preservation (cover letters & cold emails only)

Here the voice-preservation rules **do** apply — but as *the user's* personality, not invented
warmth:
- Reuse the user's actual phrases, cadence, and one odd-but-true detail. Match their sentence length and
  register (dry stays dry; warm stays warm).
- **Upgrade, don't replace.** The ceiling of intervention is "the user on their best writing day", never "a
  different, more corporate person". A de-slopped letter that no longer sounds like them is a failure.
- Motivation/opinion comes from the brain-dump; facts come from the profile. Never let one impersonate the
  other.

## The pass: draft → audit → final

1. **Draft** in the correct register.
2. **Audit** — read it and ask: *"What here sounds generated or generic?"* List the specific tells.
3. **Final** — fix them, then scan explicitly for: em/en dashes (must be zero), any `cv-mistakes.md`
   buzzword, forced tricolons, and even mid-length cadence. Read it aloud; real writing varies rhythm.
4. This pass is part of finishing a draft, not an optional extra — never hand over a CV, letter, or email
   that hasn't been through it.

## Don't over-correct (false positives)

Polish is not AI. Before cutting, protect genuine signal:
- **Real, specific, hard-to-fabricate detail** — a metric, a named tool, a real project. Generated prose rounds
  specifics off; keep yours.
- **Precise technical vocabulary** — don't flatten "quasi-experimental", "ANOVA", "Kubernetes" just because
  they sound formal. AI overuses *specific* fancy words (§ above), not all of them.
- **One transition word, one short emphatic sentence** — a single "however" or a clipped line for emphasis
  is human. Flag only clusters and runs.
- **Real numbers and named employers/dates** — never touch; the truth rule owns these.

When in doubt, look for **clusters** of tells, not isolated ones — a lone comma-aside means nothing; buzzword
+ tricolon + significance inflation together is the confession.
