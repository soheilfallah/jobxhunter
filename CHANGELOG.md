# Changelog

All notable changes to this plugin are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  - The repository moved to `soheilfallah/jobsmith`; GitHub redirects the old
    URL, so existing clones and links keep resolving.
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
