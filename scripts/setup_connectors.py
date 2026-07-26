#!/usr/bin/env python3
"""Connector doctor — check which jobsmith MCP connectors are configured, and guide
the user to set up the missing ones with THEIR OWN api keys.

No keys ship with the skill. This reads the user's Claude config(s), reports which
connectors are registered, and for the missing ones prints where to get a free key
plus a ready-to-paste config snippet (placeholder key). It never writes a key and
never edits the config itself — the agent running the skill applies changes after
the user supplies a key (so JSON merge + backup happen with confirmation).

Usage:
  python setup_connectors.py                 # human report
  python setup_connectors.py --json          # machine-readable status
  python setup_connectors.py --emit <name>   # print just one connector's config snippet
"""
import argparse
import glob
import json
import os
import sys

# Connectors the skill can use. `public` = installable by any user today.
CONNECTORS = {
    "firecrawl": {
        "what": "JD crawling — external ATS (Workday/Greenhouse/Lever), PDFs, careers pages",
        "key_url": "https://www.firecrawl.dev  (free tier)",
        "public": True,
        "config": {"command": "npx",
                   "args": ["-y", "--registry=https://registry.npmjs.org/", "firecrawl-mcp"],
                   "env": {"FIRECRAWL_API_KEY": "<YOUR_FIRECRAWL_KEY>"}},
        "note": "Windows: wrap as \"command\":\"cmd\",\"args\":[\"/c\",\"npx\",\"-y\","
                "\"--registry=https://registry.npmjs.org/\",\"firecrawl-mcp\"]. The explicit "
                "--registry pins resolution to npmjs so an .npmrc in the working directory "
                "cannot redirect the install.",
    },
    "reed": {
        "what": "UK job search — Reed.co.uk (security/data/admin/agency roles)",
        "key_url": "https://www.reed.co.uk/developers  (free Jobseeker API key)",
        "public": True,
        "config": {"command": "uv",
                   "args": ["run", "--no-config", "--locked", "--script",
                            "<jobsmith>/connectors/reed-mcp/server.py"],
                   "env": {"REED_API_KEY": "<YOUR_REED_KEY>"}},
        "note": "Server is BUNDLED in this repo at connectors/reed-mcp/. Requires `uv` "
                "(https://docs.astral.sh/uv/) — no pip install needed: the script's PEP 723 header "
                "plus server.py.lock resolve a hash-verified environment on first launch. "
                "--no-config and --locked keep a uv.toml in the working directory from "
                "redirecting that resolution.",
    },
    "adzuna": {
        "what": "UK job search + salary/labour-market data — Adzuna",
        "key_url": "https://developer.adzuna.com  (free app_id + app_key)",
        "public": True,
        "config": {"command": "uv",
                   "args": ["run", "--no-config", "--locked", "--script",
                            "<jobsmith>/connectors/adzuna-mcp/server.py"],
                   "env": {"ADZUNA_APP_ID": "<YOUR_APP_ID>", "ADZUNA_APP_KEY": "<YOUR_APP_KEY>"}},
        "note": "Server is BUNDLED in this repo at connectors/adzuna-mcp/. Requires `uv` "
                "(https://docs.astral.sh/uv/) — no pip install needed: the script's PEP 723 header "
                "plus server.py.lock resolve a hash-verified environment on first launch. "
                "--no-config and --locked keep a uv.toml in the working directory from "
                "redirecting that resolution.",
    },
}
# Connectors you enable in claude.ai (OAuth) — no local config / key here.
OAUTH_CONNECTORS = {
    "Indeed": "Enable the Indeed connector in claude.ai → Settings → Connectors (OAuth, no key).",
    "Dice": "Enable the Dice connector in claude.ai (OAuth, US-leaning tech; optional).",
}


def _config_paths():
    """Best-effort Claude config locations across surfaces."""
    home = os.path.expanduser("~")
    paths = [(os.path.join(home, ".claude.json"), "Claude Code")]
    # Claude Desktop (per-OS; also the Windows Store packaged variant)
    candidates = [
        os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude_desktop_config.json"),
        os.path.join(home, "Library", "Application Support", "Claude", "claude_desktop_config.json"),
        os.path.join(home, ".config", "Claude", "claude_desktop_config.json"),
    ]
    candidates += glob.glob(os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local")),
        "Packages", "Claude_*", "LocalCache", "Roaming", "Claude", "claude_desktop_config.json"))
    for c in candidates:
        if c and os.path.exists(c):
            paths.append((c, "Claude Desktop"))
    return [(p, label) for p, label in paths if os.path.exists(p)]


def _registered_servers():
    """Set of mcpServers names found across all config files."""
    found = set()
    for path, _ in _config_paths():
        try:
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f)
            found.update((cfg.get("mcpServers") or {}).keys())
        except (OSError, json.JSONDecodeError):
            continue
    return found


def _snippet(name):
    return json.dumps({name: CONNECTORS[name]["config"]}, indent=2)


def main():
    ap = argparse.ArgumentParser(description="Jobsmith connector doctor.")
    ap.add_argument("--json", action="store_true", help="machine-readable status")
    ap.add_argument("--emit", help="print one connector's config snippet and exit")
    args = ap.parse_args()

    if args.emit:
        if args.emit not in CONNECTORS:
            sys.exit(f"Unknown connector '{args.emit}'. Known: {', '.join(CONNECTORS)}")
        print(_snippet(args.emit))
        return

    registered = _registered_servers()
    status = {n: (n in registered) for n in CONNECTORS}

    if args.json:
        print(json.dumps({
            "config_files": [p for p, _ in _config_paths()],
            "registered": sorted(registered),
            "connectors": status,
        }, indent=2))
        return

    cfgs = _config_paths()
    print("Jobsmith connector setup — you bring your own API keys; none ship with the skill.\n")
    print("Config files found:" if cfgs else "No Claude config found yet.")
    for p, label in cfgs:
        print(f"  - {label}: {p}")
    print()

    have = [n for n, ok in status.items() if ok]
    missing = [n for n, ok in status.items() if not ok]

    if have:
        print("CONFIGURED:")
        for n in have:
            print(f"  [OK] {n} — {CONNECTORS[n]['what']}")
        print()
    if missing:
        print("MISSING (optional — set up the ones you want; the skill falls back to WebSearch/crawl):")
        for n in missing:
            c = CONNECTORS[n]
            tag = "" if c["public"] else "  (server publish pending — point at its path)"
            print(f"\n  [ ] {n} — {c['what']}{tag}")
            print(f"      1. Get your own key: {c['key_url']}")
            print(f"      2. Add to your Claude config's \"mcpServers\" (replace the placeholder):")
            for line in _snippet(n).splitlines():
                print(f"         {line}")
            if c.get("note"):
                print(f"      note: {c['note']}")
    print("\nClaude.ai OAuth connectors (no local config needed):")
    for n, how in OAUTH_CONNECTORS.items():
        mark = "OK" if n in registered else "  "
        print(f"  [{mark}] {n} — {how}")

    print("\nHow to add one: sign up for the connector (Firecrawl needs a free account too), copy "
          "YOUR OWN key, then paste it to the agent in chat — it registers the MCP for you (backs up "
          "your config, merges the entry, tells you to restart). You never edit JSON by hand. "
          "Full guide: references/connector-setup.md")


if __name__ == "__main__":
    main()
