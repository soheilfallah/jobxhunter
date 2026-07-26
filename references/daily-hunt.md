# Daily hunt — the autonomous run (workspace contract + Setup + Daily run)

`/job-hunt` runs a repeatable daily job hunt for any user. The unit of state is a **workspace
directory** discovered or created at runtime — no hard-coded machine paths, ever.

## Workspace contract
```
<job-hunt>/
  WORKSPACE-MAP.md                # plain-language map of this whole tree (generated at SETUP)
  dump/                           # user drops raw files here; INTAKE reads them -> profile
    _manifest.csv                 # dump_manifest.py: per-file status (new/ingested/unreadable/…)
  profiles/<name>.md              # master profile = source of truth (a WAREHOUSE, not a CV)
    _intake/                      # intake book-keeping (private)
      placeholders/               # stub per un-extractable dump file (nothing lost)
      CHANGELOG.md                # what each intake run added to the profile
  applications/
    tracker.xlsx | tracker.csv    # owned ONLY by tracker.py
    tracker-priority.xlsx         # generated day-to-day worklist (tracker.py priority-view)
    <category>/<YYYY-MM-DD>_<company>_<role>/
        job-description.md
        notes.md                  # coverage matrix + scorecard + braindump flag + pending-confirmation
        CV.md  CV.docx  CV.txt
    daily-hunt/
      _RUN-PLAYBOOK.md            # hard rules + lessons — read FIRST every run
      seen-jobs.csv               # dedupe ledger (canonical job key -> status)
      <YYYY-MM-DD>-summary.md     # one per run (-run-b, -run-c on same-day re-runs)
  scripts/                        # _lib, init_workspace, tracker, new_application,
                                  #   build_seen_ledger, render_docx
```
The profile is a **warehouse**: full experience, skills, education, a "**never claim**" gap list,
career-target priority order, salary floor, geography, confidential holds, conflicts to resolve. The
tailorer *selects from* it and never invents facts.

## Resolve the workspace root (once, path-agnostic)
Order: **explicit path the user gives → `JOBHUNT_DIR` env → discovery** (a dir with `profiles/` +
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
2. **Source.** Derive families/keywords from the profile's **priority order**. One search per
   title-variant across every priority family + bridge/fallback lanes, using the live connectors
   (`references/tools-and-connectors.md`; board choice follows the lane — academic→jobs.ac.uk searched
   one discipline facet at a time, commercial→Adzuna/Reed, niche→Firecrawl). Honour the **source-effort
   dial** (`references/job-search-guide.md`): `full` (default, fan out across all connectors + the crawl
   net) or `budget` (tiered connectors→MCP→web with early-stop) if the user asked to save tokens. Verify
   each hit is
   **LIVE** (expired listings redirect / say "no longer advertised" — never tailor those). **Knockout
   sweep** (below). Keep only roles **new since last run** (canonical key not in the ledger).
3. **Tailor** every surviving new live match — **no cap**, best-fit-first, soonest-closing-first. For
   each: parse JD → coverage matrix (requirement→evidence: strong/partial/adjacent-provisional/
   hard-gap) → select+order from the profile → draft → voice + **truth/integrity check** → render
   ATS-safe `CV.docx`+`CV.txt`. Surface hard gaps; put provisional inclusions in `notes.md` "pending
   confirmation" (don't block). Run the recruiter loop; save the scorecard and set `fit_score`.
4. **Cover letters — default to scaffold, don't auto-send.** In the unattended daily run there's no
   user present to brainstorm with, so do the JD analysis, prep the scaffold, and flag
   "**needs the user's brain-dump**" in `notes.md`; list these in the summary. (The on-demand
   COVER LETTER command *can* draft a profile-only letter without a brain-dump — recommended, not
   required — but the autonomous run leaves that final voice pass to the user.)
5. **Track & file** every job via the scripts — `Drafted` (tailored) or `Skipped` (with a reason) —
   always with the source **link** so the ledger key resolves. Set `closing_date`/`fit_score` where
   known. **Never touch `Applied` rows.** Rebuild the ledger at the end; regenerate the priority view
   (`tracker.py priority-view`).
6. **Output** `daily-hunt/<DATE>-summary.md` (scannable): new vs skipped counts; each tailored role
   (company / role / location / link / one-line why-it-fits / recruiter score / hard gaps); roles
   awaiting a cover-letter brain-dump; pending-confirmation items; a **watch-list** of
   expired-but-good-fit roles to re-check. Same-day re-run → write `-run-b.md`, `-run-c.md` (never
   overwrite); treat the pool as near-exhausted and dedupe hard.

## Knockout sweep (profile-driven — record the reason on every Skip)
Read each JD's essentials and compare against the profile: languages, licences (SIA), right-to-work,
degree field, and anything under the profile's "**never claim**" list (e.g. wet-lab techniques not
performed). A hard knockout the candidate cannot **truthfully** meet → `Skipped` with the reason. Log
expired-but-good-fit and bridge-lane stretch roles as `Skipped` with a "watch for re-post" reason so a
later run can notice a re-post.

## Hold-the-line invariants (do not weaken)
- **Truth first.** Never claim a "never performed" technique. A CV that can't survive the interview
  question is worse than a shorter honest one. Respect **confidential holds** — capability, not
  protected specifics.
- **Dedupe on a stable key** (job ref or full URL), never a folder-name slug.
- **Tracker owned only by `tracker.py`.** `Applied` rows are final/locked; `dedupe` never drops them.
- **No cap** on how many roles to tailor — every strong, new, live match.
- **Same-day re-runs** append (`-run-b`), never overwrite; the ledger prevents re-tailoring.

## Known surface limitations to design around
- `WebFetch` needs a URL already in scope (WebSearch first) — prefer Firecrawl for cold crawls.
- jobs.ac.uk multi-facet queries silently drop a facet — search each discipline separately.
- The `.run.lock` is advisory — the real race guard is re-reading tracker/ledger before every write
  and rebuilding the ledger at start and end.
