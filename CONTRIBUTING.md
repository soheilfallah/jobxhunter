# Contributing to jobsmith

Contributions are welcome. This is a maintained project. Every change lands through a pull request that the maintainer reviews and merges. Nothing is pushed straight to `main`.

## Before you write anything

**Read the one rule.** jobsmith's entire value is that it never invents a fact about a candidate. The master profile is the only source of truth; the skill selects, reframes, reorders, and emphasises, but it never fabricates. If evidence for a job requirement isn't in the profile, that's a **gap to surface, not a blank to fill**.

A change that makes the tool more persuasive by loosening that rule will be declined, however well it's written. If you think a change might touch it, say so in the PR and explain why it holds.

The only exception is the `L2` "alternative-world" mode, which generates beyond the profile on purpose. Its output is never submittable.

## Setting up

```bash
git clone https://github.com/soheilfallah/jobsmith
cd jobsmith
```

You'll want [`uv`](https://docs.astral.sh/uv/getting-started/installation/) for the connectors, and Python 3 with `python-docx` and `openpyxl` for the scripts.

> [!NOTE]
> Opening this repo as your working directory shows `reed` and `adzuna` as **failed** connectors, warning `Missing environment variables: CLAUDE_PLUGIN_ROOT`. That's expected, not a bug. Your cwd makes `.mcp.json` load as a *project* config, and `${CLAUDE_PLUGIN_ROOT}` only exists when it loads as a *plugin*.

**Test the real thing from outside the repo:**

```bash
cd ..
claude --plugin-dir ./jobsmith
```

## Before you open a PR

```bash
python scripts/check_release.py          # manifests, changelog, stale-name consistency
claude plugin validate . --strict        # the same check the marketplace review pipeline runs
```

Both must pass. CI runs the first one plus lockfile and connector-drift checks on every PR.

## Things that will break the plugin

These aren't style preferences. Each one has been verified to cause real breakage.

**Don't add a `skills/` directory.** `SKILL.md` lives at the plugin root, which Claude Code supports for a plugin shipping *exactly one* skill. Creating `skills/` makes the root file stop loading, **silently**. Measured: the current layout loads 7 skills; adding `skills/` drops it to 6 and the `jobsmith` engine disappears while all six commands still reference it. If you genuinely need multiple skill directories, `SKILL.md`, `references/`, and `assets/` all have to move together.

**Use `${CLAUDE_PLUGIN_ROOT}` for every script path.** A bare relative path like `python scripts/_lib.py` resolves against the *user's* working directory, not the plugin, so it fails on a real install.

**Don't drop the connector pinning flags.** `uv` and `npx` read config from the working directory, so a stray `uv.toml` or `.npmrc` can redirect a connector's install to someone else's package index, and the fetched package executes on import. `--no-config --locked` (Reed/Adzuna) and `--registry=` (Firecrawl) exist to stop that. If you add a dependency, re-run:

```bash
uv lock --script connectors/<name>-mcp/server.py
```

**Keep `.mcp.json` and `scripts/setup_connectors.py` in sync.** The doctor emits config for people registering connectors by hand. It has drifted before and shipped a stale launcher. CI now checks this.

## Never commit

- **API keys.** No keys ship in this repo, and none ever should. They belong in the plugin's user config or your own Claude config.
- **Real profiles or applications.** Your actual CV data lives in a private workspace outside the repo and is gitignored. The only profile here is `assets/sample-profile.md`, a fictional persona.
- **Real personal details in examples.** Use `example.com` addresses and the Ofcom reserved `+44 7700 900xxx` range for phone numbers.

## Releasing (maintainer)

The plugin pins an explicit `version`, so **users receive changes only when it's bumped**. Pushing commits alone does nothing. See the Releasing section in the [README](README.md#releasing).

## Pull requests

1. Fork, then branch from `main`.
2. Keep the change focused: one concern per PR.
3. Explain *why*, not just what. If you verified something, say how.
4. Update [`CHANGELOG.md`](CHANGELOG.md) if the change affects users.
5. Open the PR. A maintainer reviews and merges; please don't expect self-merge.

Questions or a change you're unsure about? Open an issue first. It's cheaper than writing the wrong patch.

## Licence

By contributing you agree your work is licensed under the [MIT Licence](LICENSE).
