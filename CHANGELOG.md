# Changelog

All notable changes to this plugin are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
