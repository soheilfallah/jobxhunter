# Company discovery & cold outreach (UK-first)

The hidden job market: most roles are filled before — or without — a public advert. This doc covers
the proactive path — **find the right companies, find the right person, and cold-email them** — for
when there is no listing to apply to, or to get ahead of one. Profile-agnostic: target the family
and the candidate's constraints, not a fixed person.

Pipeline:
```
DISCOVER companies  →  ENRICH + find contact  →  COLD MAIL (from the user's own words)  →  TRACK
build a target list    hiring manager + email    voice-preserved, tailored                log + follow up
```

## 1. DISCOVER — build a target-company list ("deep/cold company search")

You are assembling a list of realistic employers for the target family + location, then ranking them.
Use several angles (no single source is complete):

- **`WebSearch`** — sector + geography + size: `data consultancies Leeds`, `fintech startups
  London hiring`, `contract research organisations UK`, `logistics firms West Midlands`. Also "top N" and directory pages, industry association member lists, and
  accelerator/portfolio pages (e.g. an accelerator's cohort = a ready-made target list).
- **`WebFetch` / `Claude-in-Chrome`** — open the directories/association member lists and extract the
  company names + sites; crawl each company's "careers" and "about/team" pages.
- **Clay** (`find-and-enrich-company`, `query-objects`) — enrich each company: size, HQ, industry,
  funding, domain. Use it to **filter** the list (right size/stage/location) and to dedupe.
- **Ahrefs** (`site-explorer-organic-competitors`, `serp-overview`) — a creative angle for "related
  companies": feed one known target's domain and pull its organic competitors — often a clean list
  of same-sector companies you'd otherwise miss. Also mine SERPs for "companies that rank for
  <domain keyword>".
- **Indeed** (`get_company_data`) — for any candidate company, pull reviews/ratings/salary to vet it
  before spending outreach effort.

Rank the list by: family fit, location/right-to-work feasibility, size/stage (startups answer cold
mail more than corporates), and any warm-ish signal (recent funding, a relevant project, a shared
connection). Keep the ranked list in the outreach folder (see TRACK).

## 2. ENRICH — find the right person and their email

Cold-mailing `info@` is near-useless. Find the individual who owns the hire or the work:

- **Clay** (`find-and-enrich-contacts-at-company`, `find-and-enrich-list-of-contacts`) — the primary
  tool: give it the company + the role/team, get named contacts with titles and (where available)
  work emails. Prefer the **hiring manager / team lead / head of <function>** over generic HR for
  research and technical roles; for security/frontline, the ops or resourcing manager.
- **jobs.ac.uk / institute pages** — academic and research posts list a named "informal enquiries"
  contact. That is your warm target — email them directly.
- **Claude-in-Chrome** — read the company "team/people" page or LinkedIn to identify the right name
  when Clay is thin.
- Verify the email format before sending (Clay's verification, or a pattern check). Don't blast
  unverified addresses — it wrecks deliverability.

**UK legal note (state briefly, don't over-lawyer):** cold B2B outreach to a *named individual* at a
company about a genuine, relevant professional matter is normally acceptable under UK GDPR/PECR
legitimate-interest grounds. Keep it individual, relevant, low-volume, and honour any "don't contact
me" reply. This is personal career outreach, not marketing — treat it that way.

## 3. COLD MAIL — write it FROM the user's own spoken/verbal narrative

**The voice rule (shared with cover letters):** a cold email must sound like the user, not like a
template. Before drafting, get the user's **own words** — and explicitly invite a **spoken/verbal
narrative**: a voice note or a stream-of-consciousness ramble ("just talk, messy is fine") about why
this company, what they'd bring, what they want. Then transcribe/work from that.

- **If the user hasn't given their narrative, STOP and ask for it, then wait.** Never cold-generate a
  cold email (or a cover letter) from the JD/company alone. Prompt: *"Before I write this, tell me in
  your own words — a voice note or a quick ramble is perfect — why this company, and what you'd bring.
  I'll keep your voice, just tidy it."* Then wait.
- **Preserve the spoken cadence.** Spoken narrative is looser, warmer, more digressive than writing.
  Keep that energy — short, human, direct. Strip only true filler and repetition; do NOT flatten it
  into corporate email-speak. A de-voiced cold email is a failure (same rule as `cover-letter.md`).
- Translate *energy*, not literal words, when something is too casual for an email ("their work is
  sick" → "I've genuinely followed their work") — still them, dressed for the occasion.

### Cold-email craft
- **Short.** 120–180 words, scannable on a phone. Nobody reads a long cold email.
- **Subject line:** specific and human — "Data analyst keen on your Leeds operations
  team", not "Job application". No clickbait.
- **Structure:** (1) one-line who-you-are + why-them hook (from their narrative, specific to the
  company — a real project/paper/product, not flattery); (2) 2–3 lines of the single most relevant
  evidence from the profile, mapped to what the company does; (3) a clear, low-friction ask
  ("Would you be open to a 15-minute chat?" or "Are you taking on anyone with this background?");
  (4) sign-off + one-line signature. Attach the master CV for the closest role.
- Claims map to profile evidence. Cold mail is first-person.
- **UK etiquette:** named recipient → warm but professional; "Best regards"/"Kind regards" is the
  norm for email (not the formal letter "Yours sincerely/faithfully"). UK spelling.
- **Deliverability:** plain text, no images/tracking pixels, one link at most, real signature.
- **Follow-up:** one polite follow-up after ~5–7 working days if no reply, then stop. Log both.

## 4. TRACK — log outreach like any other pipeline entry

Cold outreach is company-centric, but it uses the same tracker and folder layout:

- Create `jobs/<YYYY-MM-DD>/<Company> - Speculative/` with a `notes.md` holding the contact, the
  sent email and the user's own words, and a `CV/` folder for the CV that was attached.
- Add a row to `jobs/tracker.md` with source `cold outreach` and status `Cold-emailed`. Move it to
  `Replied` on a response, then into the normal flow (`Interview`, `Applied`) if it converts. A
  company researched and passed over is recorded as `Skipped`, so the whole search stays on record.
- Add the employer to `Target employers` in `master-cvs/TARGETS.md`, so the next search reads its
  own job board.

## Sources / tools referenced
- Clay (`find-and-enrich-company`, `find-and-enrich-contacts-at-company`,
  `find-and-enrich-list-of-contacts`, `query-objects`), Ahrefs (`site-explorer-organic-competitors`,
  `serp-overview`), Indeed (`get_company_data`), Gmail (`create_draft`), WebSearch/WebFetch,
  Claude-in-Chrome, where the surface has them.
- UK GDPR/PECR position on B2B cold outreach to named individuals (ICO guidance, high level).
