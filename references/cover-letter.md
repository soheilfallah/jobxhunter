# Cover Letter Reference (UK-first)

You are writing a UK cover letter that is finished and send-ready. This document is
your rulebook for how it should read. Read the whole thing before drafting.

## Inputs: the JD and the profile — draft first, never ask

- **Never ask for a brain-dump, a voice note, or the user's own words.** Do not
  offer it, do not recommend it, do not wait for it. Write the letter in full,
  every time, from the profile plus the job description.
- **The "why this company / this role" paragraph is written like any other
  paragraph** — from the advert, the employer's public material and what the
  profile evidences (real products used, a genuine sector interest, a concrete
  skill match). If research turns up nothing specific, say less rather than
  padding.
- **No placeholders.** Never emit `[YOUR LINE HERE]` or any bracketed gap, and
  never flag a paragraph as needing the user's input.
- **Deliver it as finished, not as a draft.** Do not label output "AI-drafted", "a
  draft to edit", or something to personalise before sending. The user reviews it
  and says if something is wrong or does not sound like them. That is their call,
  not a caveat to write in. A fact that would help but is genuinely unknown stays
  off the page and goes into `notes.md` as a question.
- **If the user volunteers their own words** — a typed note, a voice-note
  transcript, a ramble in chat — they are the best input there is: use them as
  source text (next section). Spoken input is looser, warmer and more digressive
  than writing; that IS the voice to preserve. Work from the transcript, keep the
  spoken cadence, tidy only true filler and repetition, never flatten it into
  written formality. (The cold-outreach command shares this rule — see
  `company-discovery-cold-outreach.md`.)
- Complete means the strongest version the profile can back.

## CENTRAL RULE: tone preservation

The letter must sound like the user, not like you. Hiring managers report they can
spot generated letters by their "corporate, high-vocabulary HR speak that most
people don't naturally type" — and most view them negatively. A de-slopped letter
that no longer sounds like the user is a FAILURE, even if every sentence is clean.

- Treat the user's own words, where they gave any, as source text, not as a prompt. Reuse the user's actual
  phrases, metaphors, and reasons. If they wrote "I've been low-key obsessed with
  their pricing model", the letter says something like "I'll admit I've been
  slightly obsessed with your pricing model" — not "I am deeply impressed by your
  innovative commercial strategy."
- Keep their cadence. Short blunt sentences stay short and blunt. If they write
  long winding sentences with dashes, keep some dashes. Match their average
  sentence length within reason.
- Keep their register. If their words are warm and informal, the letter is warm
  and professional — not stiff. If the user is dry and understated, do NOT inject
  enthusiasm words ("thrilled", "excited", "passionate") they never used.
- Preserve idiosyncrasy. One slightly odd-but-true detail ("I read your
  postmortems on the train") is worth more than three polished claims. Never
  sand these off.
- Upgrade, don't replace: fix grammar, tighten rambling, order the argument. The
  ceiling of your intervention is "the user on their best writing day" — never
  "a different, more corporate person".

### De-slopping without de-voicing

Strip slop — but every cut must leave the user's words behind, not yours. The mechanical de-slop rules
(AI tells, em-dash ban, buzzwords, register) live in the writing model, `references/writing-voice.md`;
for a cover letter, apply its **voice-preservation** register, not its neutral-CV register.

- CUT: filler ("I believe that", "I feel as though"), hedges stacked two deep,
  throat-clearing openers, empty intensifiers ("very", "truly", "incredibly"),
  and duplicate reasons.
- CUT: cliché adjectives the user did NOT say — "dynamic", "results-driven",
  "self-starter", "go-getter", "detail-oriented", "think outside the box".
- DO NOT introduce: buzzwords, "leverage/utilise/spearhead" verbs the user never
  used, balanced tricolons ("X, Y, and Z") everywhere, or em-dash-heavy
  "AI rhythm" if the user doesn't write that way.
- Test after drafting: read the letter beside the user's words (if any) and the
  profile's own phrasing. Could the user plausibly have typed this letter
  themselves? If any sentence sounds like a press release, rewrite it in plainer
  words. Then the humanizer pass: the installed `humanizer` skill's checklist, if
  present, on the whole letter (mandatory when installed; `writing-voice.md`
  §"AI tells" is the whole pass when it is not).
- When the user's phrasing is too casual for a letter ("this job looks sick"),
  translate the ENERGY, not the words: "I genuinely want this one" — still them,
  just dressed for the occasion.

## First-person and profile-grounded — no levels dial

- Cover letters are inherently first-person and signed by the user. The CV's
  L0/L1/L2 framing dial does NOT apply here. There is exactly one register:
  the user, saying only what the profile supports, in their own voice.
- Facts (skills, outcomes, numbers, employers, dates) come from the profile; no new
  achievements are minted for the letter. Motivation comes from the advert, public research and
  the user's own words where given; facts come from the profile. Never let one
  impersonate the other.
- Academic / research targets: apply `references/academic-register.md` on top.

## Structure: 3–4 paragraphs, one A4 page max

UK careers services (Oxford, Edinburgh, Leicester, National Careers Service) agree
on shape. Target 250–400 words. Never exceed one page.

1. **Opening hook (2–3 sentences).** Name the role (exact title from the advert,
   plus reference number if given) and land one genuinely specific reason —
   from the user's words if given, else from the advert and the profile — why
   this application exists. Do NOT open with boilerplate (see banned openers below).
2. **Why this company / this role (1 paragraph).** The motivation, made
   concrete with research hooks (see below). This is the paragraph most letters
   fake and hiring managers most easily see through — build it from what is
   verifiable (the advert, the employer's own material, evidence in the profile)
   and from the user's words where they gave any; a shorter specific paragraph
   beats a longer generic one.
3. **Evidence (1–2 paragraphs).** Pick the 3–5 requirements from the JD that
   matter most, and map each to a real, specific piece of profile evidence.
   State the match explicitly — don't make the reader infer it. One concrete
   example beats three adjectives. Do not re-narrate the whole CV; the letter
   selects and connects, the CV enumerates.
4. **Close (2–3 sentences).** Forward-looking and specific: what the user wants
   to do there, availability if relevant, and a courteous call-to-action ("I'd
   welcome the chance to talk about how X could help with Y"). Thank them once.
   No grovelling, no "I hope to hear from you at your earliest convenience".

## Weaving evidence without over-claiming

- Anchor every claim: skill → named project/employer/outcome from the profile.
  "I've led migrations" is weak and unverifiable; "I led the Postgres migration
  at Acme that cut query times 40%" is a claim the interview can survive —
  provided the 40% is in the profile. If it isn't, it doesn't go in.
- Evidence serves the narrative, not the other way round. Insert evidence where
  the user's story naturally calls for proof, in the user's voice: "That's most
  of what my last two years at Acme were" reads better than a bolted-on
  achievements list.
- Scale language to evidence strength. Profile says "contributed to" → letter
  says "worked on", never "drove" or "owned". If evidence is adjacent rather
  than exact, say so: "I haven't used Terraform in production, but I've
  run the same pattern with Pulumi" — stated adjacency is persuasive; quiet
  inflation is a time bomb.
- Numbers only from the profile. Never round up, extrapolate, or "roughly"
  a figure into existence.

## Openers: banned and better

Banned (they waste the seven seconds you get):
- "I am writing to apply for..." / "I am writing to express my interest in..."
- "I am excited to apply for the position of..."
- "Please find attached my CV for your consideration."
- "As a passionate and results-driven professional..."
- Any opener that could top a letter to a different company unchanged.

Better patterns (seeded from the user's words or from verifiable research):
- Company hook: "Your engineering blog's post on flattening the on-call rota is
  the reason this letter exists."
- Achievement bridge: "Last year I took a reporting pipeline from nightly to
  near-real-time; the Data Engineer role at Acme looks like the chance to do
  that at ten times the scale."
- Motivation: "I've used Monzo daily for six years, and I've wanted to
  work on the product roughly that long."
- Plain-and-direct is fine too: "I'd like to be your next Research Assistant,
  and here's why I think that makes sense for both of us." Not every user is a
  hook-writer; a clean direct opener in their voice beats a manufactured zinger.

## Company research hooks

- Use hooks the USER supplied first, if they gave any. Hooks from your own
  research must be verifiable and specific: a named product, a blog post,
  a results announcement, a stated company value with evidence they live it —
  not "your innovative culture".
- One or two hooks, woven in, is right. Five hooks is a stalker's letter.
- Every hook must connect back to the user: "you did X" is trivia; "you did X,
  which is exactly the problem I spent 2024 on" is a reason to hire.
- If research turns up nothing specific, say less rather than padding with
  generic praise — a shorter specific paragraph outperforms a longer generic one.
- Check recency: do not cite a "recent" funding round from three years ago or
  praise a product line they have shut down.

## UK etiquette and mechanics

- UK spelling throughout: organise, programme, specialise, whilst is fine but
  don't force it. It is a "CV" and a "cover letter" — the word "resume" must not
  appear anywhere.
- Recipient: find a name if at all possible (advert, LinkedIn, company site) —
  "Dear Ms Patel" or "Dear Priya Patel" (full name is the safe modern choice if
  title/gender is uncertain; never guess "Mrs"). If no name exists, "Dear Hiring
  Manager" or "Dear Recruitment Team". "Dear Sir or Madam" is dated — use only
  for very traditional sectors (law, some public bodies).
- Sign-off rule (hard rule, recruiters notice):
  - Named recipient → **Yours sincerely**
  - Unnamed ("Dear Hiring Manager", "Dear Sir or Madam") → **Yours faithfully**
  - "Kind regards" is acceptable for email-body cover notes, but for a formal
    attached letter, apply the sincerely/faithfully rule.
- Date in UK format (6 July 2026). Match font and formatting to the CV so the
  pack looks like one document set.
- Email-body vs attachment: if the letter goes in the email body, drop the
  postal-address block, keep everything else; subject line = job title +
  reference number.

## ATS note

- Major ATSs (Workday, Greenhouse, Lever, Taleo, iCIMS) parse and store the
  cover letter, and some recruiters keyword-search it. Assume it is scanned.
- Mirror the advertised job title exactly once, and let the JD's 3–5 most
  repeated skill terms appear naturally inside real evidence sentences. Never
  stuff keywords — a human reads this document; the ATS is a side constraint,
  not the audience.
- Plain formatting: no tables, text boxes, headers/footers carrying content, or
  images. Standard fonts (Arial/Calibri, 10–12pt).

## Final checks before returning the letter

1. Complete — no placeholder, no bracketed gap, no "draft" label; the employer is
   named in the body; the user's own words used where they gave any.
2. Voice test passed — could the user have typed this? Humanizer pass done.
3. Every factual claim traceable to the profile (`scripts/validate_profile.py`
   exits 0 on the folder)?
4. Named recipient hunted for; sincerely/faithfully matches the salutation?
5. Under one page; 3–4 paragraphs; opener not on the banned list?
6. UK spelling; "CV" not "resume"; exact job title appears once?
7. No cliché the user didn't say; no evidence the profile doesn't hold?

Return the letter with a one-line note listing anything worth knowing (an
evidence gap, a missing recipient name, a question parked in `notes.md`).
Interactive commands may add: "if you want a line of your own in the
why-this-company paragraph, say it and I'll fold it in" — an offer after the
finished letter, never a gate before it.

## Sources

- Oxford University Careers Service — Cover Letters: https://www.careers.ox.ac.uk/cover-letters
- National Careers Service — How to write a cover letter: https://nationalcareers.service.gov.uk/careers-advice/covering-letter
- University of Edinburgh Careers Service — Writing a cover letter: https://careers.ed.ac.uk/cvs-and-applications/writing-a-cover-letter
- University of Leicester — Cover letters (ICME structure): https://le.ac.uk/career-development-service/applications-and-cvs/cover-letters
- Prospects — How to write a cover letter: https://www.prospects.ac.uk/careers-advice/cvs-and-cover-letters/cover-letters/
- Prospects — Using generative AI in job applications: https://www.prospects.ac.uk/careers-advice/getting-a-job/using-generative-ai-in-job-applications/
- Youth Employment UK — Greetings and sign-offs: https://www.youthemployment.org.uk/how-to-greet-future-employers-and-sign-off-in-a-cover-letter-or-application/
- LiveCareer UK — How to address a cover letter: https://www.livecareer.co.uk/cover-letter/how-to-address-a-cover-letter
- TopCV UK — Cut these cover letter clichés: https://topcv.co.uk/career-advice/cut-cover-letter-cliches
- The Muse — How to start a cover letter: https://www.themuse.com/advice/how-to-start-a-cover-letter-opening-lines-examples
- The Muse — Cliché cover letter lines to avoid: https://www.themuse.com/advice/5-cliche-cover-letter-lines-to-avoid-at-all-costs
- Jobscan — ATS-friendly cover letters: https://www.jobscan.co/blog/cover-letter-robot-approved/
