# Connector setup — bring your own keys (onboarding)

A new user has the skill but not the connectors. This is the guided setup: check what's configured,
help them get their **own** free keys, and register the ones they want. **No keys ship with the
skill** and every connector is **optional** — if one isn't configured the skill falls back to
WebSearch/browser crawling for that lane, so nothing breaks.

> [!IMPORTANT]
> **Sign-up links — give these to the user directly, don't make them search.**
>
> | Connector | Sign up | Priority |
> |---|---|---|
> | **Adzuna** | <https://developer.adzuna.com/signup> — returns `app_id` + `app_key` | ⭐ high — the only connector covering **both** UK and Canada, plus salary data |
> | **Firecrawl** | <https://www.firecrawl.dev> — key starts `fc-` | ⭐ high — without it, JDs on Workday/Greenhouse/Lever and PDFs can't be deep-crawled |
> | **Reed** | <https://www.reed.co.uk/developers/jobseeker> — Jobseeker API key | medium — **UK only**; skip it for a `ca` market user |
>
> All free. Lead with Adzuna and Firecrawl; they buy the most capability per signup.

## How setup works (the agent does the plumbing — you bring the key)

Each connector (Reed, Adzuna, **Firecrawl**) needs **your own account and API key** — sign-ups are
free. The flow is always the same three steps:

1. **You sign up** at the provider and copy your key (Firecrawl also requires a free account).
2. **You paste the key to the agent** in chat — e.g. "here's my Firecrawl key: fc-…".
3. **The agent sets up the MCP for you** — it reads your Claude config, backs it up, merges the
   connector under `mcpServers` with your key, and tells you to restart. You never hand-edit JSON.

Tell the user this explicitly at setup: *"To use Reed/Adzuna/Firecrawl you'll each need your own free
API key. Sign up, paste the key here, and I'll register the connector for you."* Never proceed with a
placeholder — wait for the user's real key, then register.

## Step 1 — check what's already there
```
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_connectors.py"          # human report (configured vs missing + how to add)
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_connectors.py" --json    # machine-readable (for the agent to branch on)
```
It reads the user's Claude config(s) (`~/.claude.json` for Claude Code; the Desktop config too) and
lists which of `firecrawl` / `reed` / `adzuna` are registered, plus the claude.ai OAuth connectors
(Indeed, Dice).

## Step 2 — get your own key (only for the connectors you want)
| Connector | Where to get a free key | You'll receive |
|---|---|---|
| **Firecrawl** | https://www.firecrawl.dev | `FIRECRAWL_API_KEY` (`fc-…`) |
| **Reed** | https://www.reed.co.uk/developers | `REED_API_KEY` |
| **Adzuna** | https://developer.adzuna.com | `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` |
| **Indeed / Dice** | claude.ai → Settings → Connectors (OAuth) | nothing to copy — just authorise |

## Step 3 — register it (the agent does this for the user)
When the user provides a key, the **agent** merges the snippet into their Claude config — never paste
a key into a skill file or a commit. Get the exact snippet:
```
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_connectors.py" --emit firecrawl   # or reed / adzuna
```
The agent then:
1. Reads the config (`~/.claude.json`, or the Desktop config), **backs it up**,
2. Merges the connector under `mcpServers` with the user's real key,
3. Tells the user to **restart** Claude Code / relaunch Desktop so the server loads.

**Windows note:** current Claude Code spawns bare `npx` fine on Windows — it resolves `npx.cmd`
itself, so the bundled `"command":"npx"` works as-is (verified with `claude mcp list`). Older hosts,
and some other MCP clients, can't launch a `.cmd` directly and fail with ENOENT. If a connector dies
at startup on Windows with nothing in the log, wrap it:
`"command":"cmd","args":["/c","npx","-y","--registry=https://registry.npmjs.org/","firecrawl-mcp"]`.
Both forms work; the wrapper is a fallback, not the default.

**Keep the pinning flags.** The emitted snippets carry `--registry=` (firecrawl) and
`--no-config --locked` (reed/adzuna) on purpose. Package managers read config from the *working
directory* — an `.npmrc` or `uv.toml` sitting in whatever folder the session was opened in can
otherwise redirect the install to an attacker's index, and the fetched package executes on import.
These flags pin resolution to the real registry and to the committed `server.py.lock`. Don't drop
them when merging a snippet into a user's config.

## Step 4 — verify
After restart, re-run `python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_connectors.py"` (should show `[OK]`) or ask the skill to run
a quick `reed_search_jobs` / `firecrawl_scrape`. If a tool name doesn't resolve, the server didn't
load — check the config path and the key.

## Connector availability by surface
- **Firecrawl** — public: `npx firecrawl-mcp` works for anyone with a key.
- **Reed / Adzuna** — small Python MCP servers **bundled in this repo** under `connectors/`:
  - Reed: `connectors/reed-mcp/`
  - Adzuna: `connectors/adzuna-mcp/`
  `pip install -e connectors/reed-mcp` (and/or adzuna-mcp), then point the config `args` at that
  `server.py` and set your key in `env`. A one-command install (PyPI) + a plugin-marketplace bundle
  is on the roadmap.
- **Indeed / Dice** — claude.ai OAuth connectors; no local config.

## Voice pass — built in, no companion needed
The CV/cover-letter voice and de-slop pass is the skill's own **writing model**
(`references/writing-voice.md`) plus the `cv-mistakes.md` catalogue. It's applied inline and needs no
companion skill, plugin, or key.
