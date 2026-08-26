---
description: Write a UK cover letter for a role, in the user's own voice.
argument-hint: "[role/JD: paste, file, or URL]"
---

Use the **jobxhunter** skill's **COVER LETTER** routine.

**Draft first — never ask for a brain-dump.** Write the letter complete from the JD + profile, name
the employer in the body, and build the "why this employer" paragraph from the advert and verifiable
public knowledge. If the user volunteers their own words (typed, or a voice-note transcript), treat
them as source text and preserve their voice. Every factual claim maps to profile evidence
(profile rule). Deliver it finished — no placeholders, no "draft" label.

Follow `SKILL.md` ("Command: COVER LETTER").

**Which reference each step reads.** A step whose file is listed here is not finished until that
file has been applied.

| Step | Read |
|---|---|
| Understand the role | `references/jd-analysis.md` |
| Openers, structure, evidence, etiquette | `references/cover-letter.md` |
| Voice pass, before returning | `references/writing-voice.md` — §"AI tells to strip" and §"Voice preservation"; the em-dash ban and the AI-vocabulary list are enforced here, not by taste |
| Humanizer pass (mandatory) | the installed `humanizer` skill, if present — apply its checklist to the whole letter. It supplements `writing-voice.md`, never replaces it. If it is not installed, `writing-voice.md` §"AI tells" is the whole pass; `scripts/validate_profile.py` WARNs on AI-tell vocabulary as the mechanical backstop |
| Academic / research targets | `references/academic-register.md`, on top of the above |
| Final scan | `references/cv-mistakes.md` §1 for buzzwords that leak from the CV into the letter |
| Market norms | `references/uk-conventions.md` (`uk`) · `references/ca-conventions.md` (`ca`) |
