# Contributing to jobxhunter

Contributions are welcome. This is a maintained project. Every change lands through a pull request that the maintainer reviews and merges. Nothing is pushed straight to `main`.

## Before you write anything

**Know how the work is split.** Agents do everything that needs judgement: searching, deciding whether a job fits, writing master CVs, tailoring. The repo ships one script, a renderer that turns a markdown CV into a Word file, because that step is mechanical. A change that adds code to score, rank or filter jobs or CVs will not be merged; put the judgement in an agent's brief instead.

**Know where the content comes from.** Every CV, letter and interview pack is built from the user's profile. A master CV is built from the profile alone, and a tailored CV from its master plus one advert. Nothing invents a fact, and a requirement the candidate cannot evidence is left out and noted.

## Setting up

```bash
git clone https://github.com/soheilfallah/jobxhunter
cd jobxhunter
```

You'll want [`uv`](https://docs.astral.sh/uv/getting-started/installation/) for the connectors and the renderer.

> [!NOTE]
> Opening this repo as your working directory shows `reed` and `adzuna` as **failed** connectors, warning `Missing environment variables: CLAUDE_PLUGIN_ROOT`. That's expected, not a bug. Your cwd makes `.mcp.json` load as a *project* config, and `${CLAUDE_PLUGIN_ROOT}` only exists when it loads as a *plugin*.

**Test the real thing from outside the repo:**

```bash
cd ..
claude --plugin-dir ./jobxhunter
```

Run `/jobxhunter:setup` into a throwaway folder and walk the five steps with an invented person's CV.

## Before you open a PR

```bash
python scripts/check_release.py                          # manifests, changelog, agent frontmatter, stale names, local paths
uv run --script scripts/render_docx.py --self-check      # the renderer, including the Word-to-markdown round trip
claude plugin validate . --strict                        # the same check the marketplace review pipeline runs
```

All must pass. CI runs the first two plus a lockfile check on every PR.

## Things that will break the plugin

These aren't style preferences. Each one has been verified to cause real breakage.

**Don't add a `skills/` directory.** `SKILL.md` lives at the plugin root, which Claude Code supports for a plugin shipping *exactly one* skill. Creating `skills/` makes the root file stop loading, **silently**, while every command still references it. If you genuinely need multiple skill directories, `SKILL.md`, `references/` and `assets/` all have to move together.

**Never write a bare relative path to a plugin file.** It resolves against the *user's* working directory, not the plugin, so it fails on a real install. In `.mcp.json`, use `${CLAUDE_PLUGIN_ROOT}`. In the instructions (`SKILL.md`, commands, agents), write `<plugin folder>`: the variable is not expanded in the shell an agent runs commands in, so the skill tells the agent to substitute the real path and to hand it to every agent it dispatches.

**Name agent models by alias.** `model: sonnet`, `opus`, `haiku` or `inherit`, never a dated id like `claude-...`. The alias moves to the newest model of that family with each Claude release; a pinned id goes stale without anyone noticing. Every agent also states an `effort`. `check_release.py` enforces both.

**Don't drop the connector pinning flags.** `uv` and `npx` read config from the working directory, so a stray `uv.toml` or `.npmrc` can redirect a connector's install to someone else's package index, and the fetched package executes on import. `--no-config --locked` (Reed, Adzuna) and `--registry=` (Firecrawl) exist to stop that. If you add a dependency, re-run:

```bash
uv lock --script connectors/<name>-mcp/server.py
```

**Keep the connector guides in one place.** The user-facing setup guides live in `assets/workspace/setup/` and are copied into each workspace. `references/tools-and-connectors.md` is the agent-facing manifest. Don't fork the instructions into a third file.

## Never commit

- **API keys.** No keys ship in this repo, and none ever should.
- **Real profiles, CVs or applications.** A workspace lives outside the repo. There is no sample profile here on purpose: examples built from a real history leak it.
- **Real personal details in examples.** Use invented people, `example.com` addresses and the Ofcom reserved `+44 7700 900xxx` range for phone numbers. Do not model an example on your own career.
- **Machine paths.** No absolute path from a real computer. `check_release.py` scans for them.

## Releasing (maintainer)

The plugin pins an explicit `version`, so **users receive changes only when it's bumped**. Pushing commits alone does nothing, and `/plugin update` reports "already at the latest version". To ship:

1. Bump `version` in **both** `.claude-plugin/plugin.json` and the marketplace entry.
2. Add a matching `## [x.y.z]` section to [`CHANGELOG.md`](CHANGELOG.md).
3. `python scripts/check_release.py` verifies steps 1 and 2, that the manifests agree on name and version, that every agent uses a model alias and an effort, that no dead URLs or command namespaces crept back in, and that every `owner/repo` reference matches the git remote.
4. `claude plugin validate . --strict` runs the same check the marketplace review pipeline does.

## Pull requests

1. Fork, then branch from `main`.
2. Keep the change focused: one concern per PR.
3. Explain *why*, not just what. If you verified something, say how.
4. Update [`CHANGELOG.md`](CHANGELOG.md) if the change affects users.
5. Open the PR. A maintainer reviews and merges; please don't expect self-merge.

Questions or a change you're unsure about? Open an issue first. It's cheaper than writing the wrong patch.

## Licence

By contributing you agree your work is licensed under the [MIT License](LICENSE).
