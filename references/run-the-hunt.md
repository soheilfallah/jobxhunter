# Run the hunt — the session procedure

What a Claude session does when the user says **"run the job hunt"**. Built so the session does not
lose context over a 40-minute run: read little, run one command, work the output, hand over in
`STATE.md`. Mechanics only — the hard rules for the run live in `daily-hunt.md`.

`<workspace>` is the resolved workspace root (see `daily-hunt.md`, "Resolve the workspace root").
`${CLAUDE_PLUGIN_ROOT}` is the plugin install. Every command below is `python "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"`.

---

## 0. Where everything is

| What | Where (relative to `<workspace>`) |
|---|---|
| Handover between runs | `STATE.md` — read first, overwrite last |
| Profile (the authority, with its `profile-rules` block) | `profiles/<name>.md` |
| Search list | `SEARCH-KEYWORDS.md` (queries per lane; `JOB-LANES.md` is filing tags only) |
| Employers' own boards | `TARGET-COMPANIES.md` |
| Dedupe ledger | `applications/daily-hunt/seen-jobs.csv` |
| Tracker (system of record) | `applications/tracker.xlsx` + `.csv` mirror — written only by `tracker.py` |
| Day folder | `tasks/daily/<YYYY-MM-DD>/` — pipeline CSVs, then the bundle |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/scripts/` |

**The run date is not today.** It is the day after the last folder in `tasks/daily/`, derived by
`_lib.next_run_date()`. Do not pass `--date` unless deliberately re-running a past day. A folder
created speculatively (a test, a dry run that wrote something) advances the sequence and shadows
the real last day — delete it.

---

## 1. Context discipline

1. **Read `STATE.md` first and only.** It holds the last run, the next action and what is blocked.
   Nothing else is pre-read; each step opens the one file it needs:

   | Step | Open |
   |---|---|
   | Running the day | this file |
   | Paths, tracker rules, gotchas | `WORKSPACE-MAP.md` |
   | Filing a role | `JOB-LANES.md` |
   | A query or title question | `SEARCH-KEYWORDS.md` — grep, do not read whole |
   | Tailoring a CV | `references/jd-analysis.md`, `references/cv-craft.md`, `references/ats-mechanics.md` |
   | Cover letter | `references/cover-letter.md`, `references/writing-voice.md` |
   | L2 alternative-world CV | `references/tailoring-levels.md` |
   | Written application questions instead of a letter | `references/application-answers.md` |
   | Recruiter scoring | `references/recruiter-rubric.md` |

2. **Read the profile fresh before any writing** — every tailoring or letter step, never from memory
   of an earlier session or an earlier role in the same batch.
3. **`STATE.md` stays under 30 lines** or it stops being read. Overwrite it as the last act of the
   run: what ran (date, counts), the single next action, what is blocked and why.
4. **Which surface runs what.** Claude Code runs the scripts and owns every write. Cowork / Claude
   Desktop reviews documents and may edit the profile — the stdio connectors (Reed, Adzuna,
   Firecrawl) cannot be reached from its VM, so a hunt started there silently sources from one
   connector and looks like a full run. Two surfaces writing the same workspace at once corrupts the
   tracker's csv mirror. Before starting, make sure no other session is mid-hunt.

---

## 2. Run it

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/run_hunt.py" --workspace "<workspace>" --top 400
```

That is the whole command. Stages: `full → companies → consolidate → rank → verify → jds`, ending at
`tasks/daily/<date>/to-tailor.csv`. Defaults are already right: every configured source, every lane
in the keyword file, no call budget, no salary floor.

| Flag | When |
|---|---|
| `--top N` | how many adverts get **read** at L2, round-robin across lanes. Lower it only to save scraper credits. |
| `--since-last-run` | an incremental day after a full sweep — only adverts posted since the previous completed run |
| `--force` | run the JD-fetch stage even though the verify gate failed (the only gate it bypasses; stages always re-run) |
| `--dry-run` | print the plan, touch nothing |
| `--skip-companies` | leave out the employer-board stage — the only L0 step that spends Firecrawl credits; a re-run after a dead key does not need it again |
| `--stage <name>` | start at that stage; everything after it also runs |

**It takes roughly 35–40 minutes.** Run it in the background and work the backlog (unsent
applications from earlier day folders) while it goes. Every query is logged to
`tasks/daily/<date>/queries.csv` as it runs.

---

## 3. Company boards stage

Job boards hold only what an employer chose to post there. The `companies` stage reads the
employers' own boards from `TARGET-COMPANIES.md` instead, and runs **before** `consolidate` because
it appends to the candidate pool that `consolidate` reads exactly once.

- **The list is the only limit on this source's reach — grow it.** Direct employers only; agencies
  are already on the boards.
- It resolves the six ATSes that publish a public JSON board (Greenhouse, Workable, Lever, Ashby,
  Recruitee, SmartRecruiters). **Workday, Taleo, iCIMS and Personio publish none**, so a company on
  one of those comes back `unresolved` — that means "cannot read", never "no vacancies". Do not
  report unresolved as covered.
- **Sanity-check the `ats/slug` it prints.** Recruitee and Workable are self-serve, so a short
  one-word name can resolve to a stranger's board. If the slug does not look like the company,
  pin it (`- Name | greenhouse:slug` or `| careers:<url>`) or delete the line.
- An empty board is not a resolution; SmartRecruiters answers `200 []` for any slug at all.
- Only titles that match a lane in `SEARCH-KEYWORDS.md` come through — a board has no query behind
  it, so relevance is a gate here and a ranking everywhere else. `--keep-unmatched` on
  `harvest_companies.py` disables that.
- Non-market roles are dropped by default (`--all-locations` keeps them); the count dropped is in
  the note, so a company that resolved but contributed nothing is visible.
- `.company-boards.json` caches what resolved; only the first run pays the probe cost.

Re-run by hand only if needed:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/harvest_companies.py" --workspace "<workspace>" --out company_rows.json
python "${CLAUDE_PLUGIN_ROOT}/scripts/import_rows.py" --workspace "<workspace>" --source companies --platform "Company boards" --rows company_rows.json --date <run-date> --max-days-old 30
```

`--max-days-old 30`, not 3: these adverts were never on a board, so recency is not the filter.

---

## 4. The verify gate

After ranking, `verify_run.py` checks the funnel. If it FAILs, the pipeline **skips the JD-fetch
stage on purpose**, so scraper credits are not spent on a run that cannot be written up as
thorough. That is correct behaviour, not a bug to route around.

```
FAIL  only 2 platform(s) queried (Adzuna, Reed); floor is 4
!! SKIPPING L2 — verify_run did not pass.
```

How to read the FAIL lines:

| Line | Meaning | Fix |
|---|---|---|
| `platform 'X' rejected the credentials (HTTP 401) on N ...` | dead key; the sweep stopped that source and it no longer counts toward the floor | re-key that connector (`references/connector-setup.md`), re-run that source: `--sources X --stage full --skip-companies` |
| `only N platform(s) queried ...; floor is 4` | too few sources answered | find which are missing in `queries.csv`; a source that is unavailable (403, quota) must be logged with a reason, not silently absent |
| `lane(s) never queried: a, b` | a lane declared in `JOB-LANES.md` has no queries | give it a `SEARCH-KEYWORDS.md` section, or `--skip-lanes a,b` if it is a filing-only lane |
| `... and no note says why` | a platform returned nothing with no explanation | check the connector; annotate or re-run |

Run it on its own any time: `verify_run.py --workspace "<workspace>" --date <run-date>`.

---

## 5. Triage every read advert

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/triage.py" --workspace "<workspace>" --date <run-date> --init        # one row per fetched advert
python "${CLAUDE_PLUGIN_ROOT}/scripts/triage.py" --workspace "<workspace>" --date <run-date> --next --n 5  # round-robin BY LANE
python "${CLAUDE_PLUGIN_ROOT}/scripts/triage.py" --workspace "<workspace>" --date <run-date> --mark <url> --verdict applied|skipped --reason "..."
python "${CLAUDE_PLUGIN_ROOT}/scripts/triage.py" --workspace "<workspace>" --date <run-date> --status      # exits non-zero while anything is pending
```

- `--next` hands out work round-robin across lanes on purpose: rank order lets the loudest lane fill
  the top and the quiet ones never get reached.
- **Every skip carries a named reason** — a credential the profile does not hold, a clearance,
  a duplicate (same employer under two company strings; one client role posted by two agencies),
  an expired listing ("watch for re-post"). Skipping most adverts is fine; leaving no record is not.
- **Requirements hide in the advert body** — clearance, a language, a licence, a residency
  condition. Title-level filters miss all of them. Read for them.
- The day is not finished until `--status` exits 0.

---

## 6. Write the documents

Per kept role: a folder, a tailored CV, a complete send-ready cover letter, the advert, `notes.md`,
and the L2 alternative-world CV with its delta. In this order, opening the reference each step needs:

| Step | Command / skill | Opens |
|---|---|---|
| 1. Tailor the CV | `/jobxhunter:tailor` (or fan out `role-tailorer` per role) | `references/jd-analysis.md`, `cv-craft.md`, `ats-mechanics.md`; profile read fresh |
| 2. Cover letter | `/jobxhunter:cover-letter` | `references/cover-letter.md`, `writing-voice.md`; `application-answers.md` if the employer asks questions instead |
| 3. L2 alternative-world CV + delta in `notes.md` | render with `--basename CV-L2-alternative-world` | `references/tailoring-levels.md` |
| 4. Score | `recruiter-critic` agent — JD + rendered CV only, never the notes | `references/recruiter-rubric.md` |

Then render and check:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/render_docx.py" --in <folder>/CV.md
python "${CLAUDE_PLUGIN_ROOT}/scripts/render_docx.py" --in <folder>/CoverLetter.md --basename CoverLetter
python "${CLAUDE_PLUGIN_ROOT}/scripts/validate_profile.py" --profile "<workspace>/profiles/<name>.md" --folder <folder>
```

`validate_profile.py` is the consistency check: it reads the profile's own `profile-rules` block and
infers lane and advert from the folder. Exit 0 before anything is called ready; exit 1 = a document
breaks a rule; exit 2 = the rules block itself is broken (unknown verb, undeclared lane) and
nothing is certified until it parses. In a large batch, assemble CVs from shared blocks rather than
one at a time — a batch written individually drifts into slightly different versions of the same
fact. Gaps and provisional claims go in `notes.md`, never on the page.

File every role through `tracker.py` (`Drafted` or `Skipped` with reason and link). Never touch
`Applied` rows.

---

## 7. Bundle

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/daily_bundle.py" --root "<workspace>/applications" --date <run-date>
```

Pass `--date` — the script defaults to today, and the run date is not today. Output:
`tasks/daily/<date>/APPLY-TODAY.md`, one folder per role (CV, letter, L2 CV, advert, notes), the
day's roles sheet, `FINDINGS.md` (scaffolded once, never overwritten), and the pipeline CSVs tidied
into `_work/`.

It runs profile validation over every role. Any failure lands in a **"Fix before sending"** block
at the top of `APPLY-TODAY.md` instead of being listed as ready. **Line 3 of `APPLY-TODAY.md` is
always the profile-check provenance** — `Profile check: N docs, F failures, <profile> @ <mtime>`.
No line 3 means the gate never ran; the bundle cannot look the same whether it passed or was
skipped.

---

## 8. Report

Counts only: adverts enumerated, read, tailored, skipped (by reason), sources queried, verify
result. If a stage failed, say which. If part of the scope was dropped — a source that did not
answer, a lane not queried, unresolved companies — name it. Then overwrite `STATE.md` (§1.3).

---

## 9. Gotchas that cost time

- **Plugin install path vs plugin source.** If the install is a junction or a cache copy of the
  repo, a `/plugin update` can overwrite local edits. Know which path you are editing; edit the
  source, never the cache.
- **Run from the workspace or pass `--workspace` everywhere.** Discovery walks up from cwd; a
  command run from another directory resolves a different (or no) workspace.
- **`render_docx.py` writes `CV.docx` unless you pass `--basename`.** Rendering a letter without it
  silently overwrites the CV you just made.
- **`tracker.py` writes the xlsx, then the csv mirror; its lock covers only the xlsx.** A csv-only
  lock (usually a second session holding the file) leaves the two diverged. Repair by regenerating
  the csv from the xlsx; check `csv rows == xlsx rows`.
- **`tracker.py update --data` ignores unknown keys silently.** Read the row back after an update.
- **A dry run must leave no trace** — a speculative day folder shifts the run-date sequence.
- **`sweep.py` only reads the ledger**, so a test sweep does not poison tomorrow's run; still delete
  any throwaway folder.
- **Adzuna `what_or` ORs words, not phrases** — use `what_phrase`. Reed distance is miles, Adzuna km.
- **Adding a lane to `JOB-LANES.md` adds it to the verify floor.** Give it queries or `--skip-lanes` it.
- **Short-link adverts** (`to.indeed.com/...`) redirect cross-host; `WebFetch` returns the redirect.
  Use the connector's job-details call, which also confirms the posting is live.
