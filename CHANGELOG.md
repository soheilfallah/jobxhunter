# Changelog

All notable changes to this plugin are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.1] - 2026-08-26

### Added

- **`SETUP.md`** — a five-step setup walkthrough with an agent procedure for the "I pasted the repo,
  set me up" case; README, AGENTS.md and the `setup` command point to it; API keys are explicitly
  optional and last.

### Fixed

- **Rendering a cover letter silently destroyed the CV next to it.** `render_docx.py --basename`
  defaulted to the literal string `"CV"`, so any input rendered into a job folder with `--outdir`
  and no explicit `--basename` landed on `CV.docx` / `CV.txt`. The documented two-step in SKILL.md
  — render the CV, then render the cover letter into the same folder — therefore overwrote the CV
  with the letter, and the script reported success both times. The default is now the input file's
  own stem, so `CV.md → CV.docx` and `CoverLetter.md → CoverLetter.docx`; an explicit `--basename`
  still wins.
- **A locked CSV mirror left the tracker's two files permanently out of step.** `_save()` committed
  `tracker.xlsx` first and only guarded against *the workbook* being locked, on the assumption that
  "open in Excel" was the only failure mode. It is not: on Windows a sync agent, an indexer or a
  second Claude session can deny `os.replace` on `tracker.csv` while `open(path, 'a')` still
  succeeds. The xlsx committed, the mirror write died, and every later read of the csv returned
  stale rows with nothing to signal it. The mirror's writability is now preflighted *before* the
  workbook is saved, the csv payload is rendered before anything is written, and a blocked atomic
  replace falls back to a truncating in-place write with a note on stdout. Added
  **`tracker.py repair-mirror --root <apps>`** to regenerate the csv from the xlsx after any
  interrupted write.
- **`tracker.py add` / `update` silently discarded unknown column names.** `--data
  '{"ats":"Agency","level":"L1"}'` exited 0, printed a success line, and wrote nothing — the real
  columns are `ats_platform` and `level_used`. Both commands now hard-fail before touching the
  workbook and print a did-you-mean (prefix and substring matched before falling back to difflib,
  so `ats` suggests `ats_platform` rather than `status`).
- **Reed and Adzuna were documented with the wrong calling convention.** SKILL.md and
  `references/job-search-guide.md` showed `reed_search_jobs(keywords, locationName,
  distanceFromLocation)` and `reed_get_job_details(jobId)`. Both servers wrap every argument in a
  single `params` object and use snake_case, so the documented form fails validation outright —
  `Field required [params]`, then `Extra inputs are not permitted` on the camelCase retry. Two
  wasted round trips per lane, mid-hunt. Both docs now show the `params` form, name the snake_case
  keys, and note that Indeed and Dice are the opposite (flat, no wrapper).
- **`build_seen_ledger.py` was the only script that rejected `--root`.** Every sibling takes
  `--root <applications dir>`; this one took only `--applications`, so the muscle-memory call
  failed mid-run. `--root` is now an accepted alias.

- **`Archived` status.** Retires a row from the active pipeline without deleting it — renders pale
  grey and sorts below every other status in `priority-view`. Previously an unknown status fell
  through `PRIORITY_BUCKET.get(..., 2)` and sorted *above* `Skipped`, so a bulk archive pushed
  retired rows above live ones on the worklist.
- **`tracker.py show --key <folder_path>`** prints one row with every populated column. Reading a
  row back after an update previously meant parsing the csv by hand.
- **`scripts/daily_bundle.py`** — assembles one day's hunt into a dated, self-contained
  apply-from-here folder. A day's output was previously scattered across per-job folders, the
  tracker, and a hand-assembled briefing, so actually applying meant opening four things at once.
  The bundle gathers a `CV_<Company>_<Role>.docx` and matching cover letter per role, a
  `<date>-roles.xlsx` sheet (status, pay, closing date, fit score, apply link, with closing ≤7 days
  in red and ≤14 in amber), and a `FINDINGS.md` scaffold. Rows are selected on tracker
  `logged_date`, so it never depends on folder naming; re-running refreshes in place; and an
  existing `FINDINGS.md` is **never** overwritten, since the written briefing is the one artefact
  the script must not touch.
- **New keyword taxonomy family: `pa-ea-private-office`.** Covers private PA to a HNWI/UHNWI,
  executive assistant, private- and family-office support, lifestyle and household administration,
  property-portfolio administration, and AI-enabled VA work. This family had no palette at all
  despite being one of the most common bridge lanes, so every PA/EA job description was being
  decomposed from scratch. Includes the knockouts that actually decide these roles — managing
  domestic staff, events at the highest level, an established local supplier network, sector-specific
  EA backgrounds — a sector-flavour cheat-sheet (private household vs family office vs corporate EA
  vs property private office vs agency brief), and an explicit rule that a confidential principal is
  never identified by **profession**, not just by name.

- **The marketplace could not be added in Claude Desktop or Cowork.** Adding
  `soheilfallah/jobxhunter` there failed with "Marketplace sync failed. Check the repository URL
  and try again", which points at the wrong thing: the repository was fine. Desktop and Cowork
  register a marketplace with the claude.ai backend, which fetches it server-side and validates it
  more strictly than Claude Code does. It rejected the plugin entry's `"source": "."` with
  `marketplace_sync_external_source_unsupported`: an external marketplace must give each plugin an
  explicit source object, not a path relative to the marketplace repo. That shorthand is reserved
  for Anthropic's own first-party marketplace. The entry now names its own repository over HTTPS,
  so the same manifest works on Claude Code, Desktop, and Cowork.

  Deliberately the `url` form and not `github`: Claude Code resolves a `github` source by cloning
  over SSH, which fails with "Host key verification failed" for anyone without a github.com entry
  in `known_hosts` — most people installing a plugin. The HTTPS `.git` URL clones for everyone,
  and is what the majority of the official marketplace's entries use. Verified end to end by
  installing from a throwaway marketplace built on this manifest: `github` failed on SSH, `url`
  installed cleanly.
- **The connector doctor told you it could not see your keys, on the platforms where it can.**
  `setup_connectors.py` claimed the API keys were unreachable in the OS keychain and sent you to
  read a dialog instead. That is true only on macOS. On Windows and Linux, Claude Code stores plugin
  userConfig in `~/.claude/.credentials.json` under `pluginSecrets`, so the doctor can say exactly
  which of the four keys hold a value. It now does, reporting each as set or not set and offering a
  ready-to-run command that fills only the missing ones. Where the store genuinely cannot be read it
  reports *unknown* rather than *not set*, because guessing "not set" would send you to re-enter keys
  that were already fine. Lengths are reported, never values, so `--json` output stays safe to paste
  into an issue.
- **A connector that appears in your tool list proved nothing about its key.** The bundled Reed,
  Adzuna and Firecrawl servers start cleanly with empty credentials and only fail at the first real
  search, which makes a missing key look like a broken connector. The doctor now says this outright,
  alongside the other half of the trap: a key set while Claude Code is running does not reach the
  server until you restart.
- **The non-interactive way to set a key looked like a no-op and so went unused.**
  `claude plugin install <id> --config KEY=VALUE` answers `"is already installed"` on a plugin you
  already have, but it applies the values regardless. Since `claude plugin` has no `config`
  subcommand and `update` takes no `--config`, this is the only route that avoids the interactive
  dialog. The doctor now spells that out rather than printing the bare command.

- **The local-path guard missed the very form that caused the leak.** The pattern first shipped
  used a bare backslash escape with a quantifier, which `git grep -E` reduces to *one optional*
  backslash. It matched the prose form (`C:\Users\me`) but sailed straight past the
  backslash-escaped form used inside a JSON snippet (`C:\\Users\\me`) — which is exactly where
  the original leak lived. Rewritten as a bracket expression, unambiguous under git grep's ERE.
  Re-scanning with the corrected pattern found instances the first pass had reported as clean.
- **The guard now proves itself before it is trusted.** `_selftest_local_paths()` runs both
  patterns over known-bad and known-good fixtures through the same `git grep -E` engine on every
  invocation. Verified it fails on the old pattern, naming the two JSON-form examples it could
  not catch. A check that silently stops matching is worse than no check, because the passing
  build reads as proof.
- **The guard was still blind to forward-slash Windows paths, and too narrow besides.** A re-sweep
  from fresh clones found `D:/soh-workspace/...` in `evals/2026-07-06-run/tracker.csv` — four
  `folder_path` values in the public repo — which the backslash-only pattern could not see. The
  patterns now cover both separators, and a third general drive-letter rule catches any absolute
  Windows path rather than only the two workspace names that happened to be hardcoded. URLs are
  excluded via a leading boundary (`https://x` ends in a letter, colon, slash-slash). Placeholders
  are excused explicitly, so anything genuinely absolute has to be a deliberate entry.
- **The eval tracker's `folder_path` values are now repo-relative.** They pointed at an absolute
  path under a superseded project name, so they leaked the workspace layout and pointed nowhere a
  contributor could follow.
- **Stripped absolute local paths from the connector READMEs.** The `reed-mcp` and `adzuna-mcp`
  setup sections hardcoded a maintainer machine's home and workspace directories inside
  otherwise copy-pasteable `.mcp.json` snippets. Two problems in one: this repo is public, so
  the snippets published a username and folder layout; and they could not work for anyone who
  copied them, since nobody else has those paths. They now use `C:\path\to\...` placeholders,
  and the Cowork user-files note points at `%USERPROFILE%\Claude` / `~/Claude` instead.

### Added

- **`scripts/check_release.py` now fails on committed absolute paths** (check 7). It catches
  Windows and POSIX home directories in both prose and the backslash-escaped form used inside
  JSON snippets, while allowing obvious placeholders (`/Users/you/`, `/home/user/`) and the
  GitHub Actions runner home. CI already runs this check on every PR, so the leak fixed above
  cannot come back silently.

## [1.5.0] - 2026-07-31

### Changed

- **Relicensed from MIT to the PolyForm Noncommercial License 1.0.0.** jobxhunter is now
  source-available: free to use, study, and adapt for any noncommercial purpose (running your
  own job hunt included), but it may not be sold or put to commercial use. The `LICENSE` file,
  both manifests (`license` field), the README badge and licence note, `CONTRIBUTING.md`, and
  the landing page now carry the noncommercial terms. Copyright stays with Soheil Fallah, who
  retains all commercial rights. Anything already released under MIT stays MIT for whoever has
  it; the new terms apply going forward.

## [1.4.1] - 2026-07-31

### Changed

- **Cowork (Claude Desktop) support made explicit and correct.** Cowork runs in an isolated VM that
  cannot reach local stdio MCP servers, so the bundled Reed / Adzuna / Firecrawl connectors do not
  connect there. SOURCE now routes Cowork sourcing to the remote Indeed / Dice connectors plus
  WebSearch / WebFetch (and `/scrape` for JD capture), and a new "Running in Cowork" section in
  `SKILL.md` spells out exactly what works. Tailoring, the recruiter loop, tracking, interview prep,
  and native docx/xlsx rendering are unchanged. Also fixes a stale note that implied the bundled
  stdio connectors worked in Cowork under a different naming convention, and corrects the README's
  claim that Cowork has no plugin system.

## [1.4.0] - 2026-07-30

### Added

- **Hunt dashboard** (`/jobxhunter:dashboard`, `scripts/dashboard.py`). Renders the tracker CSV into
  one self-contained, offline HTML page: headline tiles, the apply/interview/offer funnel with
  conversion, status and category breakdowns, and the recruiter-score spread. Stdlib only, no network
  requests, read-only over the tracker.
- **`AGENTS.md`** so the tailoring core runs in any AGENTS.md-compatible CLI (Codex, Gemini and
  Antigravity, Copilot, OpenCode, Qwen, Kimi), not only Claude Code. Live-board sourcing uses the MCP
  connectors on Claude Code and falls back to the agent's own web search elsewhere.
- **Landing page** under `docs/` (GitHub Pages), with an in-page light/dark toggle.

### Changed

- **Repositioned** around fit and gap-recommendation: it searches live jobs, fits an ATS-safe CV to
  each role from your real experience, and recommends the gaps to close. The README now leads with the
  search.
- **Rewrote the README** story-first, with an animated demo and the validated recruiter score up front.
- **Rebranded** the demo and dashboard to a devil-red palette, in both light and dark themes.
- Removed em dashes across the README, `AGENTS.md`, and the shipped brand assets.

## [1.3.0] - 2026-07-28

### Added

- **Interview-prep stage** (`/jobxhunter:interview`, `references/interview-prep.md`). Turns the
  filed application into an honest prep pack in the job folder: predicted questions grouped by the
  JD's must-have competencies with STAR answers built only from real profile evidence, plus
  **gap-defence** for every hard-gap/partial the coverage matrix surfaced. Carries the candidate past
  "filed", where the pipeline used to stop.
- **Real, independent recruiter critic** (`agents/recruiter-critic.md`). The recruiter loop can now
  run its scoring in a subagent that sees only the JD + rendered CV — never the tailorer's notes — so
  the "independent recruiter" is actually independent instead of self-scoring.
- **Per-role tailoring fan-out** (`agents/role-tailorer.md`). The daily hunt can spawn one subagent
  per surviving role so every CV is built in a clean context and quality doesn't decay across a long
  no-cap batch.
- **Deterministic keyword-coverage diagnostic** (`scripts/keyword_coverage.py`). Checks which of the
  JD's must-have/nice-to-have terms actually made it onto `CV.txt` ("N/M present, X%", plus acronyms
  missing an expansion). Explicitly a parse diagnostic, not a Jobscan-style auto-reject score; `--min`
  turns it into a pass/fail gate. Copied into new workspaces by SETUP.
- **Application-form answer pack** (`references/application-answers.md`). Drafts truthful,
  profile-grounded answers to Workday/Greenhouse screening questions into `notes.md` — salary anchored
  to the fetched Adzuna band, profile-only answers flagged, review-and-paste (never auto-submitted).

### Changed

- **Renamed from `jobsmith` to `jobxhunter`.** Clearer intent — this is a hunter's
  toolkit — and a distinct name in the marketplace.
  - Commands are now `/jobxhunter:tailor`, `/jobxhunter:hunt`, and so on.
  - Marketplace id is `jobxhunter@soheil-jobxhunter`; the repository is
    `soheilfallah/jobxhunter`.
  - **Breaking (re-install):** the live MCP tool namespace changes from
    `mcp__plugin_jobsmith_*` to `mcp__plugin_jobxhunter_*`. Re-install as
    `jobxhunter@soheil-jobxhunter`, re-enter your connector keys, and re-allow the
    new tool names.
  - **`JOBSMITH_DIR` still works.** The workspace env var is now `JOBXHUNTER_DIR`,
    but `JOBSMITH_DIR` (and the older `JOBHUNT_DIR`) are still read as fallbacks, so
    a pinned workspace keeps resolving. New name wins if more than one is set.
  - Paths under `career/job-hunt/` are deliberately untouched — a private data
    workspace, not the plugin.

### Fixed

- **tracker.py never truncates or dies on a locked file.** Saves are now atomic
  (temp file + `os.replace`) and a workbook open in Excel (or a read-only file)
  produces a clear "close it and re-run" message instead of a raw `PermissionError`
  traceback — and never a half-written/zeroed tracker. Both the `.xlsx` and its
  `.csv` mirror are written under one guard so they can't diverge.
- **Applied records can no longer be silently altered.** The "committed" set
  (Applied/Interview/Interviewed/Offer/Rejected) is now truly final: status may only
  move within it and identity/applied-date fields are immutable, unless `--data`
  carries `"_force": true`. Previously a non-status edit (e.g. rewriting `pay`)
  slipped past the guard.
- **Non-Latin-1 job data no longer crashes the scripts on Windows.** Every CLI now
  forces UTF-8 stdout/stderr, so an accented employer/role name (Łódź, Señor, £,
  em-dashes) prints fine on a default cp1252 console; `new_application`'s subprocess
  pipes decode as UTF-8 to match.
- **Adzuna salary histogram is ordered correctly.** Bands were sorted as strings, so
  `100000` sorted before `20000` and scrambled the distribution; numeric keys now
  sort numerically (ISO-month keys stay chronological). Covered by a unit test.
- **Adzuna renders a withheld salary as "Not disclosed"** (parity with Reed), not the
  ambiguous `? - ?`.
- **`dump_manifest.py --workspace` works before *or* after the subcommand** (an
  argparse shared-parent default was silently discarding a value given before it), and
  Windows `Thumbs.db` / `desktop.ini` droppings are skipped instead of becoming junk
  intake placeholders.
- **Connector `.env` files load when launched as a plugin** (anchored to the connector
  directory, not the current working directory).
- **Eval fixtures ship again.** An unanchored `tracker.csv` / `tracker.xlsx` ignore was
  sweeping up the committed `evals/**` fixtures that `CONTRIBUTING.md` references.

## [1.2.0] - 2026-07-26

### Changed

- **Renamed from `job-hunt` to `jobsmith`.** The old name sat in a crowded
  corner of the community marketplace — of 2269 plugins, 19 are job/career
  adjacent, and `job-hunt-skills` (a direct competitor, same audience) scored
  0.64 name similarity. `jobsmith` keeps the searchable "job" token, has no
  close neighbour in the catalog, and the `-smith` suffix says what the tool
  actually does: raw material in, something made well out.
  - Commands are now `/jobsmith:tailor`, `/jobsmith:hunt`, and so on.
  - Marketplace id is `jobsmith@soheil-jobsmith`.
  - The repository moved to `soheilfallah/jobsmith`. Existing git remotes and
    API references still resolve through GitHub's rename redirect (verified by
    cloning via the old URL).
  - *Correction to an earlier note here:* the old web URL was described as
    404ing because rename redirects don't cover web URLs. That was wrong — at
    the time, **both** the old and new URLs 404ed to anyone unauthenticated
    because the repository was still private. Visibility, not the redirect.
  - **`JOBHUNT_DIR` still works.** The workspace env var is now
    `JOBSMITH_DIR`, but the old name is still read as a fallback, so an
    existing workspace needs no change. New name wins if both are set.
  - Paths under `career/job-hunt/` are deliberately untouched — that is a
    private data workspace, not the plugin.

## [1.1.0] - 2026-07-26

Marketplace-readiness pass. No change to skill behaviour or output quality.

### Fixed

- **Script paths now resolve when installed as a plugin.** Every executable
  invocation in `SKILL.md`, `commands/`, and `references/` was bare-relative
  (`python scripts/_lib.py`), which resolved against the user's working
  directory rather than the plugin. The bootstrap path — workspace resolution
  and `init_workspace.py` — could not run at all on a clean install. All 22
  call sites are now anchored to `${CLAUDE_PLUGIN_ROOT}`.
- **Reed and Adzuna connectors start without manual setup.** Both were launched
  via a bare `python`, which is absent on most macOS/Linux systems and a stub on
  many Windows ones, against dependencies the user had to `pip install` by hand
  into an unknown environment. Both servers now carry PEP 723 inline metadata
  and launch under `uv run --script`, which resolves an isolated environment on
  first run.
- **`pydantic` is now declared** in both connector `pyproject.toml` files. It is
  imported directly by both servers and was previously satisfied only
  transitively via `mcp`.
- **`setup_connectors.py` emitted stale config snippets.** The doctor still
  handed manual registrants the old `python <path>/server.py` form, so anyone
  registering a connector by hand got the launcher this release replaced. It
  now emits the same hardened `uv` and `npx` invocations as `.mcp.json`.

### Security

- **Connector dependency resolution is pinned against working-directory
  hijacking.** `uv` and `npx` both read configuration from the current working
  directory and its parents, not from the script's own location. A `uv.toml` or
  `.npmrc` planted in whatever folder a session happens to open in could
  redirect a connector's install to an attacker-controlled index, and the
  fetched package executes on import. Verified reproducible: with no lockfile,
  a hostile `uv.toml` sent resolution to `http://127.0.0.1:9/simple/pydantic/`,
  and `npx -y firecrawl-mcp` followed a hostile `.npmrc` the same way.
  Mitigated on all three servers — `--no-config --locked` for Reed and Adzuna,
  an explicit `--registry=https://registry.npmjs.org/` for Firecrawl. Verified
  against a hostile config with a cold cache: all three now resolve from the
  real registries and start cleanly.
- **Added hash-verified lockfiles** (`connectors/*/server.py.lock`, 555 hashes
  each) via `uv lock --script`. Resolution is deterministic rather than "newest
  release satisfying a lower bound." Adding a dependency requires re-running
  `uv lock --script`; a stale lock fails the connector closed.

### Added

- `LICENSE` (MIT) and a `license` field in both manifests.
- This changelog.
- `version` on the marketplace plugin entry, so updates are pinned to an
  explicit release rather than every commit SHA.

### Changed

- Trimmed the plugin description to 170 characters for marketplace display.
- `.gitignore` now covers `.claude/` and `.claude-flow/` local agent state.

### Removed

- Stale `dist/` build output — a full duplicate of `SKILL.md`, `references/`,
  and `scripts/` that had drifted from source. Packaging is marketplace-driven.

## [1.0.0] - 2026-07-18

Initial release: profile intake, ATS-safe CV tailoring, sourcing across
connectors, cover letters, cold outreach, and application tracking.
