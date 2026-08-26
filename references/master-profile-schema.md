# Master profile schema — the data contract

The master profile is the **only source of truth** for L0/L1 CVs and for the evidence in cover letters. This doc describes the *shape* of the feed the tailorer expects to read. It is deliberately **loose**: it describes the shape of the data, not the person. Any conforming markdown file works as input — yours, a friend's, or an invented persona. `assets/sample-profile.md` is just the first sample.

## Design principle

The profile is a **decoupled data feed**. The skill logic and knowledge base never change based on whose profile they read. Point the skill at a path; it reads the profile as inert data. Keep the profile richer than any single CV needs — it is a *warehouse* the tailorer selects from, not a pre-built CV. The more raw evidence it holds (every role, every skill, every number, every output), the better the tailoring, because selection beats generation.

## Format

Plain markdown with `##` section headers matching the field names below. The tailorer parses by heading, so keep headings close to these names. Extra sections are fine and ignored if irrelevant. Missing sections are treated as "no evidence here" — never as a licence to invent.

## Fields

### `## Identity`
Name; location (city/area — full address optional); phone (local format for the market); professional email; LinkedIn; portfolio/GitHub/website; **work-authorisation status expressed for the market** (UK: "British citizen", "Skilled Worker visa", "requires sponsorship"; Canada: "Canadian citizen", "permanent resident", "open/closed work permit", "requires sponsorship/LMIA"). Work authorisation is load-bearing because many JDs knock out on it.

### `## Career targets & market`
Priority-ordered target job families (1 = most wanted); bridge/fallback lanes; last-resort lanes; salary floor; work pattern; and the **market** — the country/labour-market the hunt runs in, e.g. `uk`, `ca`, `us`. **The market is the switch** that selects the conventions layer (`uk-conventions.md` / `ca-conventions.md` / …), the job-board list, and the connectors the skill uses. If the market isn't stated, infer it from `location` + work authorisation and confirm with the user before tailoring. One profile can hold more than one target market (e.g. UK + Canada) — the run picks the active one.

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

### `## Rules` — the ` ```profile-rules ` block (optional, strongly recommended)

`scripts/validate_profile.py` checks every CV, cover letter and notes file against the profile, and
the **profile declares its own rules** in a fenced block so the checker stays portable: a second
user gets their own rules for nothing, and a rule written down is a rule that actually runs.
`python scripts/validate_profile.py --emit-template` prints the block; `assets/sample-profile.md`
uses every verb. **An unknown verb is a hard error** (exit 2, "nothing was checked") — a typo can
never silently disable a rule. Phrases match whole words, case-insensitively, with `–`/`—` equal
to `-`.

| Verb | Meaning |
|---|---|
| `forbid: P` | `P` may never appear in a submitted document. |
| `require-cv: L` | Exact line every CV must contain, in its **last** `## ` section (e.g. the right-to-work line). |
| `allow: P` | The candidate's vocabulary: never an unknown-noun warning, and blanked out before the lane/JD gates run (never before `forbid`, so `forbid: Manager - Acme` still works when `allow: Acme` exists). |
| `role: K` | Declares one employer. `K` must match **exactly one** `### ` heading under `## Experience` — and every Experience heading needs one. The same substring must appear in the CV heading that prints it: that is the identity contract the overlap and evidence-crossing checks key on. |
| `forbid-unless-lane: P1, P2 -> lane1, lane2` | Any of the phrases may print only on those lanes (fails closed with no lane). |
| `forbid-unless-jd-mentions: P1, P2` | One group: any phrase on the page needs any phrase in the advert (fails closed with no advert). |
| `education-for-lane: lane1, lane2 -> K1, K2` | Only these degrees print, in this order; `*` is the default. Each `K` must match exactly one `## Education` heading. |
| `overlap-print: lane1, lane2 -> K1, K2` | **Menu** semantics for concurrent roles: a CV prints **at most one** role from the whole group, and it must be on the lane's menu. Keys are `role:` keys. |

Arrow verbs split on ` -> ` before `,`. Lane tokens must be lanes declared in the workspace's
`JOB-LANES.md` (or `*`); the lane and advert normally come from the application folder
(`applications/<lane>/<folder>/job-description.md`), so `--folder` needs no extra flags. Beyond the
declared rules the checker also flags orphan bullets (a bullet under `## Experience` with no
employer heading), evidence lifted from one employer's entry printed under another, a cover letter
that never names the employer outside the salutation, and AI-tell vocabulary (a warning, never a
failure). Profiles written before the block existed fall back to a `never claim` prose section for
`forbid` only — blunt; declare the block instead.

### `profiles/<name>.blocks.md` — CV blocks (optional; needed by `cvgen.py`)

`scripts/cvgen.py` assembles a batch of CVs from shared, curated blocks so the same fact cannot drift
between documents. Blocks live in a file beside the profile; every `fact:` it declares must exist in
the profile or the build aborts. The format is documented in `cvgen.py`'s docstring, with a complete
example at `assets/sample-profile.blocks.md`.

## Minimal viable profile

A profile is usable with just `Identity`, `Experience`, `Education`, and `Skills warehouse`. Everything else enriches tailoring. The portability test for the skill: swapping in a second minimal profile at a different path must produce a sensible CV with **zero changes to skill logic**.
