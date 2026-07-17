# Connector setup — bring your own keys (onboarding)

A new user has the skill but not the connectors. This is the guided setup: check what's configured,
help them get their **own** free keys, and register the ones they want. **No keys ship with the
skill** and every connector is **optional** — if one isn't configured the skill falls back to
WebSearch/browser crawling for that lane, so nothing breaks.

## Step 1 — check what's already there
```
python scripts/setup_connectors.py          # human report (configured vs missing + how to add)
python scripts/setup_connectors.py --json    # machine-readable (for the agent to branch on)
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
python scripts/setup_connectors.py --emit firecrawl   # or reed / adzuna
```
The agent then:
1. Reads the config (`~/.claude.json`, or the Desktop config), **backs it up**,
2. Merges the connector under `mcpServers` with the user's real key,
3. Tells the user to **restart** Claude Code / relaunch Desktop so the server loads.

**Windows note:** `npx` can't be spawned directly — wrap it: `"command":"cmd","args":["/c","npx","-y","firecrawl-mcp"]`.

## Step 4 — verify
After restart, re-run `python scripts/setup_connectors.py` (should show `[OK]`) or ask the skill to run
a quick `reed_search_jobs` / `firecrawl_scrape`. If a tool name doesn't resolve, the server didn't
load — check the config path and the key.

## Connector availability by surface
- **Firecrawl** — public: `npx firecrawl-mcp` works for anyone with a key.
- **Reed / Adzuna** — need their small Python MCP servers. Until those are published, point the config
  at a local clone of each server (`command: python`, `args: [<path>/server.py]`). Packaging them for
  one-command install (npm/pip) + a plugin-marketplace bundle is on the roadmap (see README backlog).
- **Indeed / Dice** — claude.ai OAuth connectors; no local config.

## Voice-pass companion skills (optional, keyless)
- **`/humanizer`** — recommended: [blader/humanizer](https://github.com/blader/humanizer) (MIT):
  `npx skills add blader/humanizer`.
- **`/academic-prose`** — optional; only if you have an academic-prose skill (there's no public default
  the skill assumes). Absent → the inline `cv-mistakes.md` de-slop covers the pass.
