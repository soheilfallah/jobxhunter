#!/usr/bin/env python3
"""Connector doctor — check which jobxhunter MCP connectors are configured, and guide
the user to set up the missing ones with THEIR OWN api keys.

No keys ship with the skill. This reads the user's Claude config(s), reports which
connectors are registered, and for the missing ones prints where to get a free key
plus a ready-to-paste config snippet (placeholder key). It never writes a key and
never edits the config itself — the agent running the skill applies changes after
the user supplies a key (so JSON merge + backup happen with confirmation).

For a plugin install it also reports which of the four userConfig keys actually hold
a value. It reports lengths only, never the values, so `--json` output stays safe to
paste into a bug report.

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

# UTF-8 stdout/stderr so config paths/values with non-ASCII characters never die on a
# default (cp1252) Windows console.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

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
        "what": "UK-only job search — Reed.co.uk (skip it if you are hunting in Canada)",
        "key_url": "https://www.reed.co.uk/developers  (free Jobseeker API key)",
        "public": True,
        "config": {"command": "uv",
                   "args": ["run", "--no-config", "--locked", "--script",
                            "<jobxhunter>/connectors/reed-mcp/server.py"],
                   "env": {"REED_API_KEY": "<YOUR_REED_KEY>"}},
        "note": "Server is BUNDLED in this repo at connectors/reed-mcp/. Requires `uv` "
                "(https://docs.astral.sh/uv/) — no pip install needed: the script's PEP 723 header "
                "plus server.py.lock resolve a hash-verified environment on first launch. "
                "--no-config and --locked keep a uv.toml in the working directory from "
                "redirecting that resolution.",
    },
    "adzuna": {
        "what": "UK AND CANADA job search + salary data — the only connector covering both markets",
        "key_url": "https://developer.adzuna.com  (free app_id + app_key)",
        "public": True,
        "config": {"command": "uv",
                   "args": ["run", "--no-config", "--locked", "--script",
                            "<jobxhunter>/connectors/adzuna-mcp/server.py"],
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


def _report_runtimes():
    """Check the runtimes the bundled connectors need before blaming the keys.

    Reed and Adzuna launch via `uv run --script`, and Firecrawl via `npx`. When
    either is missing the server dies at startup with nothing useful in the log,
    which looks identical to a bad API key. Say so up front.
    """
    import shutil

    uv, npx = shutil.which("uv"), shutil.which("npx")
    if uv and npx:
        return
    print("RUNTIME CHECK:")
    if not uv:
        print("  [!] `uv` not found on PATH — the bundled Reed and Adzuna connectors cannot start.")
        print("      They launch via `uv run --script`, which resolves their dependencies for you.")
        print("      Install: https://docs.astral.sh/uv/getting-started/installation/")
    if not npx:
        print("  [!] `npx` not found on PATH — the Firecrawl connector cannot start.")
        print("      It ships with Node.js: https://nodejs.org")
    print("      Sourcing still works without these; it falls back to web search.\n")


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
    """Set of mcpServers names found across all config files.

    Only sees hand-registered, top-level entries. Plugin-provided servers are
    namespaced (`plugin:jobxhunter:reed`) and never appear here, which is why
    `_installed_as_plugin()` exists.
    """
    found = set()
    for path, _ in _config_paths():
        try:
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f)
            found.update((cfg.get("mcpServers") or {}).keys())
        except (OSError, json.JSONDecodeError):
            continue
    return found


def _installed_as_plugin():
    """Return the plugin id if jobxhunter is installed as a plugin, else None.

    When installed as a plugin the connectors ship with it: they are registered
    as `plugin:jobxhunter:<name>` and their keys come from the plugin's own
    user-config, not from a hand-edited `mcpServers` block. Without this check
    the doctor reports all three as MISSING and walks a plugin user through a
    manual merge they must not do, which is the opposite of what SETUP says.

    The API keys themselves are declared `sensitive`, so they are kept out of
    settings.json. Whether they are readable from here depends on the platform;
    `_plugin_key_status()` answers that, and says so when it cannot.
    """
    settings = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")
    try:
        with open(settings, encoding="utf-8") as f:
            enabled = json.load(f).get("enabledPlugins") or {}
    except (OSError, json.JSONDecodeError):
        return None
    for pid, on in enabled.items():
        # accept the old id too, so a user still on the previous plugin id isn't
        # told the plugin is missing during migration.
        if on and pid.split("@")[0] in ("jobxhunter", "jobsmith"):
            return pid
    return None


def _userconfig_fields():
    """userConfig field names the plugin declares, read from its own manifest.

    Derived rather than hardcoded so a new connector key added to plugin.json is
    reported here without a second edit. Falls back to the four known fields when
    the manifest is not alongside us (running the script standalone).
    """
    manifest = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            ".claude-plugin", "plugin.json")
    try:
        with open(manifest, encoding="utf-8") as f:
            fields = list((json.load(f).get("userConfig") or {}).keys())
        if fields:
            return fields
    except (OSError, json.JSONDecodeError):
        pass
    return ["reed_api_key", "adzuna_app_id", "adzuna_app_key", "firecrawl_api_key"]


def _plugin_key_status(plugin_id):
    """Which of the plugin's userConfig keys actually hold a value.

    `sensitive: true` keeps these out of settings.json, but not necessarily out of
    reach: on Windows and Linux Claude Code writes them to
    ~/.claude/.credentials.json under `pluginSecrets[<plugin@marketplace>]`, so we
    can report exactly which are set instead of sending the user to eyeball a
    dialog. On macOS they go to the OS keychain and there is nothing to read.

    Returns {field: length} (0 meaning unset), or None when the store cannot be
    read at all — an unknown status, which is not the same as "not set". Lengths
    only: a wrong-length key is the common paste error, and a length leaks nothing.
    """
    path = os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")
    try:
        with open(path, encoding="utf-8") as f:
            secrets = json.load(f).get("pluginSecrets") or {}
    except (OSError, json.JSONDecodeError):
        return None
    stored = secrets.get(plugin_id) or {}
    return {field: len(str(stored.get(field) or "")) for field in _userconfig_fields()}


def _report_plugin_keys(plugin_id):
    """Print which plugin userConfig keys are set, and the two traps around them."""
    keys = _plugin_key_status(plugin_id)
    if keys is None:
        print("KEY STATUS: unknown — could not read ~/.claude/.credentials.json.")
        print("  Expected on macOS, where sensitive values go to the OS keychain instead.")
        print("  Check the configure screen to see which keys you have set.")
        return

    print("KEY STATUS (from your credential store; values are never printed):")
    for field, size in keys.items():
        mark = "OK" if size else "  "
        detail = f"set, {size} chars" if size else "not set"
        print(f"  [{mark}] {field:<18} {detail}")

    missing = [f for f, size in keys.items() if not size]
    if missing:
        print("\n  Set the missing ones (one --config per key, your own values):")
        flags = " ".join(f"--config {f}=<YOUR_VALUE>" for f in missing)
        print(f"    claude plugin install {plugin_id} {flags}")
    print("\n  Note: a key only reaches the connector at startup, so RESTART Claude Code")
    print("  after setting one. And the connectors start happily with no key at all —")
    print("  a server that appears in your tool list proves nothing about its key. If")
    print("  sourcing returns 'Missing credentials', this is the screen that explains why.")


def _snippet(name):
    return json.dumps({name: CONNECTORS[name]["config"]}, indent=2)


def main():
    ap = argparse.ArgumentParser(description="JobXHunter connector doctor.")
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
    plugin_id = _installed_as_plugin()

    if args.json:
        keys = _plugin_key_status(plugin_id) if plugin_id else None
        print(json.dumps({
            "config_files": [p for p, _ in _config_paths()],
            # only our own connectors: the user's unrelated MCP servers are none
            # of this tool's business
            "registered": sorted(n for n in registered if n in CONNECTORS),
            "connectors": status,
            "installed_as_plugin": plugin_id,
            # null = could not read the store (unknown), NOT "nothing is set"
            "plugin_keys_set": (None if keys is None
                                else {f: bool(n) for f, n in keys.items()}),
            "plugin_key_lengths": keys,
            "note": ("Installed as a plugin: connectors ship with it and keys come from plugin "
                     "user-config, so `connectors` false here does not mean missing."
                     if plugin_id else
                     "Standalone: connectors are hand-registered in mcpServers."),
        }, indent=2))
        return

    if plugin_id:
        print(f"JobXHunter is installed as a plugin ({plugin_id}).\n")
        print("Its connectors ship with the plugin and are already registered as")
        print("  plugin:jobxhunter:reed / :adzuna / :firecrawl")
        print("You do NOT hand-edit mcpServers for these. Set the keys with:\n")
        print(f"  /plugin configure {plugin_id}            (in Claude Code)")
        print(f"  claude plugin install {plugin_id} --config KEY=VALUE   (from a terminal;")
        print("      repeatable, one flag per key. It applies the values even when it answers")
        print("      \"is already installed\", so it is the way to set keys on an existing")
        print("      install without touching the interactive dialog.)\n")
        _report_runtimes()
        _report_plugin_keys(plugin_id)
        print("\nThe hand-registration report below applies only to a standalone (non-plugin)")
        print("install. Ignore it unless you are running jobxhunter from a cloned skill folder.\n")
        print("-" * 70 + "\n")

    cfgs = _config_paths()
    print("JobXHunter connector setup — you bring your own API keys; none ship with the skill.\n")
    _report_runtimes()
    print("Config files found:" if cfgs else "No Claude config found yet.")
    for p, label in cfgs:
        print(f"  - {label}: {p}")
    print()

    have = [n for n, ok in status.items() if ok]
    missing = [n for n, ok in status.items() if not ok]

    if have:
        print("REGISTERED (an entry exists; the key itself is not validated here):")
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
    print("\nClaude.ai OAuth connectors — CANNOT be detected from here:")
    print("  This script only reads local JSON config. Claude.ai OAuth connectors live in your")
    print("  account, so these may well be active already. '?' means unknown, not missing.")
    for n, how in OAUTH_CONNECTORS.items():
        mark = "OK" if n in registered else "? "
        print(f"  [{mark}] {n} — {how}")

    print("\nHow to add one: sign up for the connector (Firecrawl needs a free account too), copy "
          "YOUR OWN key, then paste it to the agent in chat — it registers the MCP for you (backs up "
          "your config, merges the entry, tells you to restart). You never edit JSON by hand. "
          "Full guide: references/connector-setup.md inside the jobxhunter plugin/skill folder, "
          "or https://github.com/soheilfallah/jobxhunter/blob/main/references/connector-setup.md")


if __name__ == "__main__":
    main()
