# Master profile schema — the data contract

The master profile is the **only source of truth** for L0/L1 CVs and for the evidence in cover letters. This doc describes the *shape* of the feed the tailorer expects to read. It is deliberately **loose**: it describes the shape of the data, not the person. Any conforming markdown file works as input — yours, a friend's, or an invented persona. `assets/sample-profile.md` is just the first sample.

## Design principle

The profile is a **decoupled data feed**. The skill logic and knowledge base never change based on whose profile they read. Point the skill at a path; it reads the profile as inert data. Keep the profile richer than any single CV needs — it is a *warehouse* the tailorer selects from, not a pre-built CV. The more raw evidence it holds (every role, every skill, every number, every output), the better the tailoring, because selection beats generation.

## Format

Plain markdown with `##` section headers matching the field names below. The tailorer parses by heading, so keep headings close to these names. Extra sections are fine and ignored if irrelevant. Missing sections are treated as "no evidence here" — never as a licence to invent.

## Fields

### `## Identity`
Name; location (city/area — full address optional); phone (UK format); professional email; LinkedIn; portfolio/GitHub/website; **right-to-work status** (e.g. "UK — Skilled Worker visa", "British citizen", "requires sponsorship"). Right-to-work is load-bearing because many UK JDs knock out on it.

### `## Headline / positioning` (optional but useful)
One or two lines the person uses to describe themselves per track (e.g. a "horticultural researcher" line AND a "data analyst" line). Gives the tailorer honest raw material for the summary without inventing a stance.

### `## Experience`
The core warehouse. For each role, in reverse-chronological order:
- Job title, organisation, location, dates (month/year – month/year or "Present").
- Employment type if relevant (permanent, contract, self-employed, voluntary, research).
- **Bullets of what was actually done** — richer than a CV needs. Each ideally: what was done + how (method/tools) + outcome/scale/number where it exists. Include the mundane and the impressive; the tailorer decides what to foreground.
- Real numbers wherever they exist (team size, sample size, %, duration, throughput, budget). Numbers are gold for tailoring; capture them here even if messy.

### `## Skills warehouse`
A broad, clustered inventory — bigger than any one CV uses. Group loosely (e.g. lab techniques, data/analysis, tools/software, languages, domain knowledge, operational/soft). List everything the person can genuinely do. The tailorer pulls the matching cluster per JD; it must never add a skill that isn't here.

### `## Education`
Degrees/qualifications: title, institution, location, dates, classification/grade if known. Include international qualifications as-stated; note UK equivalence if known (the tailorer can present equivalence per `uk-conventions.md`). Relevant modules/dissertation titles optional but useful for early-career tailoring.

### `## Certifications & licences`
Professional licences (e.g. SIA SG/DS/CP, driving licence), certificates (e.g. EFAW first aid, lab safety), memberships, training. Mark expiry where relevant. These are frequent JD knockouts — capture precisely.

### `## Outputs`
Publications (with DOI/links), conference talks, posters, patents, notable projects, portfolio pieces, open-source contributions. Anything externally verifiable that evidences capability.

### `## References` (optional)
Referees with relationship and contact, OR a note that references are available on request. Kept in the profile so the tailorer knows they exist; per UK convention they usually don't go on the CV itself.

### `## Confidential hold` (optional)
Anything the person does NOT want surfaced on any CV/letter (e.g. reasons for a gap, sensitive employers, immigration detail beyond right-to-work status, personal circumstances). The tailorer must treat this section as **read-for-context, never-output**. It exists so the person can be honest with the tool without that honesty leaking onto a document.

## What the tailorer may and may not do with the profile

- **May**: select, reframe, reorder, emphasise, cluster, quantify from stated numbers, translate a duty into an achievement, present international qualifications with UK equivalence, choose which headline to lead with.
- **May not**: invent a role, skill, number, date, employer, qualification, or output not present here; upgrade a stated fact into a stronger false claim; output anything from `Confidential hold`.
- **On a gap** (JD wants X, profile has no X): first classify it (`tailoring-levels.md`, "Gap classes"). A **hard gap** (no plausible basis) is surfaced, never filled (only L2 may fill it). An **adjacent/plausibly-held** item (X under a different name, or one a listed role obviously implies) is *provisionally* included and confirmed in one neutral yes/no batch at the end of the run — not dropped, not treated as a lie. The profile being incomplete is expected: people forget experiences and rename skills.

## Minimal viable profile

A profile is usable with just `Identity`, `Experience`, `Education`, and `Skills warehouse`. Everything else enriches tailoring. The portability test for the skill: swapping in a second minimal profile at a different path must produce a sensible CV with **zero changes to skill logic**.
