# Daily hunt — the autonomous run (workspace contract + Setup + Daily run)

`/jobxhunter` runs a repeatable daily job hunt for any user. The unit of state is a **workspace
directory** discovered or created at runtime — no hard-coded machine paths, ever.

## Workspace contract
```
<jobxhunter>/
  WORKSPACE-MAP.md                # plain-language map of this whole tree (generated at SETUP)
  dump/                           # user drops raw files here; INTAKE reads them -> profile
    _manifest.csv                 # dump_manifest.py: per-file status (new/ingested/unreadable/…)
  profiles/<name>.md              # master profile = the authority (a WAREHOUSE, not a CV)
    _intake/                      # intake book-keeping (private)
      placeholders/               # stub per un-extractable dump file (nothing lost)
      CHANGELOG.md                # what each intake run added to the profile
  JOB-LANES.md                    # filing lanes (### `lane` headings) — verify_run checks every lane was queried
  SEARCH-KEYWORDS.md              # the hunt's search list — sweep.py + rank.py read it as machine input
  TARGET-COMPANIES.md             # employers' own boards (`- Name` / `- Name | careers:<url>`) — harvest_companies.py
  STATE.md                        # the handover between runs: read first, overwrite last, keep short
  applications/
    tracker.xlsx | tracker.csv    # owned ONLY by tracker.py
    tracker-priority.xlsx         # generated day-to-day worklist (tracker.py priority-view)
    <category>/<YYYY-MM-DD>_<company>_<role>/
        job-description.md
        notes.md                  # coverage matrix + scorecard + L2 delta + pending-confirmation + parked questions
        CV.md  CV.docx  CV.txt  CoverLetter.md/.docx  CV-L2-alternative-world.md/.docx
    daily-hunt/
      _RUN-PLAYBOOK.md            # hard rules + lessons — read FIRST every run
      seen-jobs.csv               # dedupe ledger (canonical job key -> status)
  tasks/daily/<YYYY-MM-DD>/       # run_hunt.py's working files (queries.csv, to-tailor.csv, …) + daily_bundle.py's apply-from-here folder
  scripts/                        # _lib, tracker, new_application, render_docx,
                                  #   build_seen_ledger, dump_manifest, keyword_coverage
```
The profile is a **warehouse**: full experience, skills, education, a **not-on-CV** list,
career-target priority order, salary expectations, geography, confidential holds, conflicts to
resolve, and a `profile-rules` block that `validate_profile.py` enforces. The tailorer *selects from*
it. Every other document points at the profile rather than restating it —
titles, dates, estate and team sizes come from the profile only.

## Resolve the workspace root (once, path-agnostic)
Order: **explicit path the user gives → `JOBXHUNTER_DIR` env → discovery** (a dir with `profiles/` +
`applications/`, from cwd upward) **→ none → Setup mode**. Use `scripts/_lib.py`:
```
python "${CLAUDE_PLUGIN_ROOT}/scripts/_lib.py" resolve [--workspace <dir>]     # prints root, or NONE (exit 1)
python "${CLAUDE_PLUGIN_ROOT}/scripts/_lib.py" preflight                        # openpyxl + python-docx or exact fix
```
All sub-paths derive from the root; never write an absolute machine path into the skill.

## Command: SETUP (first run / new user — no workspace resolves)
```
python "${CLAUDE_PLUGIN_ROOT}/scripts/init_workspace.py" --workspace <dir> [--name <who>]
```
Scaffolds the contract tree, drops the **profile template** (sections the tailorer expects) + a starter
`_RUN-PLAYBOOK.md` + empty ledger, copies `scripts/`, runs `tracker.py init`, then **STOPS** for the
user to fill the profile. Idempotent; refuses to clobber a populated workspace. Runs a dependency
**preflight** first so the tracker can never half-commit.

## Command: DAILY RUN (populated workspace)
0. **Read the playbook, then read the profile fresh.** Profile missing/empty → STOP and report.
1. **Concurrency guard.** Write `applications/daily-hunt/.run.lock` (timestamp). If a fresh (<30 min)
   lock exists, a parallel run is active → dedupe extra-hard. **Rebuild the ledger at the start**
   (`build_seen_ledger.py`). Re-read tracker/ledger immediately before **every** write — never trust a
   start-of-run snapshot. Delete the lock at the end.
2. **Source — one command.**
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/run_hunt.py" --workspace <root>      # --dry-run lists the stages
   ```
   It sweeps every configured source across the WHOLE `SEARCH-KEYWORDS.md` (`sweep.py`, broad-to-narrow,
   novelty-stopped pagination), reads the employers' own boards from `TARGET-COMPANIES.md`
   (`harvest_companies.py` — the only step that can spend crawl credits; `--skip-companies` skips
   it), consolidates, ranks on title (`rank.py`), verifies breadth (`verify_run.py`), fetches the
   full JDs, and ends at `tasks/daily/<DATE>/to-tailor.csv`. Relevance is a **ranking, not a
   gate**: only security clearance and the Global knockouts list reject; an unmatched title scores
   0 and sorts last. There is no salary floor in the query — pull wide, gate locally where the
   rejects are countable. Every query is logged to `tasks/daily/<DATE>/queries.csv` as it runs.

   **Breadth is enforced, not assumed.** A thin run and a thorough run produce write-ups that read
   identically, and the tracker only records survivors. So: at least 4 distinct sources per run
   (official boards first, aggregators last), every lane in `JOB-LANES.md` queried, and a source that
   is genuinely unavailable (dead key, 403, quota) **logged with the reason**, never silently dropped.
   A rejected credential (401) stops that source and fails the run by name — re-key the connector,
   do not write the day up around it.

   **Sources the scripts cannot reach** (an OAuth MCP connector, a board serving a bot interstitial
   to a plain GET): query them yourself and hand the rows to `import_rows.py` before
   `--stage consolidate`, so they go through the same gate, ledger and query log. Verify each hit is
   **LIVE** (expired listings redirect / say "no longer advertised" — never tailor those). Keep only
   roles **new since last run** (canonical key not in the ledger).

   Then, before writing anything up:
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/verify_run.py" --workspace <root> --date <DATE>
   ```
   **A FAIL means the run is thin. Go back and search more** — do not write it up as thorough, and
   do not report a role count as though it were the result of a broad sweep.
3. **Triage on disk, round-robin by lane.** `triage.py --init` writes one row per fetched advert;
   `--next --n 5` hands out work across lanes (rank order lets the loudest lane fill the top and the
   quiet ones never get reached); every skip carries a reason; `--status` exits non-zero while
   anything is pending, and the day is not finished until it exits 0. **Knockout sweep** (below).
4. **Tailor** every surviving new live match — **no cap**, best-fit-first, soonest-closing-first. For
   each: parse JD → coverage matrix (requirement→evidence: strong/partial/adjacent-provisional/
   hard-gap) → select+order from the profile → draft → voice pass + humanizer pass +
   **`scripts/validate_profile.py --folder <dir>` (must exit 0)** → render ATS-safe
   `CV.docx`+`CV.txt`. Surface hard gaps in `notes.md`, never on the page; put provisional inclusions
   in `notes.md` "pending confirmation" (don't block — there is nobody to ask). Run the recruiter
   loop; save the scorecard and set `fit_score`.
   **Every tailored role also gets the L2 alternative-world CV plus its delta** — write
   `CV-L2-alternative-world.md` and render it with `--basename CV-L2-alternative-world`. Rules in
   `references/tailoring-levels.md`; no disclaimer on the artifact; the delta is mandatory and goes
   in `notes.md`. A required output, not an optional extra.
5. **Cover letters — write them complete.** The unattended run has nobody to brainstorm with, and
   that is precisely why it must finish the letter rather than leave a scaffold: a role whose letter
   says "needs the user's words" is a role the user cannot send, so the run produced nothing for it.
   Draft the full, send-ready letter from JD + profile per `references/cover-letter.md`, then the
   voice pass (`references/writing-voice.md`) and the humanizer pass. No placeholders, no bracketed
   fill-ins, no "draft" label, no flag asking for words. Where the employer asks **written
   application questions instead of a letter**, produce `ApplicationAnswers.md` per
   `references/application-answers.md` and no letter.
6. **Track & file** every job via the scripts — `Drafted` (tailored) or `Skipped` (with a reason) —
   always with the source **link** so the ledger key resolves. Set `closing_date`/`fit_score` where
   known. **Never touch `Applied` rows.** Rebuild the ledger at the end; regenerate the priority view
   (`tracker.py priority-view`).
7. **Output: the day folder, built by `daily_bundle.py --root <apps>`.** One folder per job holding
   the CV, the cover letter, the L2 CV, the advert and the notes, plus the day's roles sheet. The
   tracker, `queries.csv` and this bundle are the record of the day — no separate summary file.
   Skipped roles keep their reason in the tracker and stay out of the day folder. Overwrite
   `STATE.md` last (what ran, what is pending, what the next run should know; keep it short).
   Same-day re-run → the ledger and `done_queries` prevent re-tailoring; treat the pool as
   near-exhausted and dedupe hard.

## Knockout sweep (profile-driven — record the reason on every Skip)
Read each JD's essentials and compare against the profile: languages, licences (SIA), right-to-work,
degree field, and anything on the profile's **not-on-CV** list (e.g. wet-lab techniques not
performed). A hard knockout the profile cannot evidence → `Skipped` with the reason. Log
expired-but-good-fit and bridge-lane stretch roles as `Skipped` with a "watch for re-post" reason so a
later run can notice a re-post.

## Hold-the-line invariants (do not weaken)
- **Profile first.** The profile is the authority. A line that does not trace to it does not go on
  the page, and `scripts/validate_profile.py` enforces the profile's declared rules mechanically —
  run it per role and treat a non-zero exit as a blocker, not a note. A CV that can't survive the
  interview question is worse than a shorter one. Respect **confidential holds** —
  capability, not protected specifics.
- **Ship complete, never ask.** Letters are finished; confirmations and gap questions go into
  `notes.md`; nothing is labelled a draft.
- **Dedupe on a stable key** (job ref or full URL), never a folder-name slug.
- **Tracker owned only by `tracker.py`.** `Applied` rows are final/locked; `dedupe` never drops them.
- **No cap** on how many roles to tailor — every strong, new, live match.
- **Same-day re-runs** are deduped by the ledger and `done_queries`; nothing is re-tailored.

## Known surface limitations to design around
- `WebFetch` needs a URL already in scope (WebSearch first) — prefer Firecrawl for cold crawls.
- jobs.ac.uk multi-facet queries silently drop a facet — search each discipline separately.
- The `.run.lock` is advisory — the real race guard is re-reading tracker/ledger before every write
  and rebuilding the ledger at start and end.
