#!/usr/bin/env python3
"""Release consistency check for the jobsmith plugin.

The plugin pins an explicit `version`, which means users receive changes ONLY
when that field is bumped — pushing commits alone does nothing. That is the
right trade for a published plugin, but it has one failure mode: you ship a
fix, forget the bump, and nobody ever gets it.

This check makes that failure loud instead of silent. It verifies:

  1. plugin.json declares a version, and it is valid semver.
  2. The marketplace entry's version matches plugin.json exactly. (Claude Code
     resolves plugin.json first, so a stale marketplace entry is not fatal at
     runtime — but it misreports the version in listings.)
  3. CHANGELOG.md has a section for that exact version, so every release users
     can receive is documented.
  4. plugin.json and marketplace.json agree on the plugin `name`.
  5. Nothing still references the pre-1.2.0 `job-hunt` name outside the
     private-workspace paths that are deliberately kept.

Run it before opening a PR, and in CI:

    python scripts/check_release.py

Exits 0 when clean, 1 with a list of problems otherwise.
"""

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")

# Only patterns that actually break something. Deliberately NOT flagged:
#   "job-hunting"      — the activity, correct English, used throughout the copy
#   JOBHUNT_DIR        — the documented backward-compatible env var
#   career/job-hunt/   — the user's private data workspace, not the plugin
#   references/*.md    — "(UK-first)" doc titles describe real content
STALE_PATTERNS = [
    (r"soheilfallah/job-hunt\b",  "dead repo URL — the web URL 404s after the rename"),
    (r"soheil-job-hunt\b",        "dead marketplace id"),
    (r"/job-hunt:",               "dead command namespace"),
    (r"skills/job-hunt\b",        "dead install path"),
    (r"job-hunt@",                "dead install target"),
]
STALE_ALLOWED_FILES = ("CHANGELOG.md", "scripts/check_release.py")


def _load(rel):
    path = ROOT / rel
    if not path.is_file():
        return None, f"{rel} is missing"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"{rel} is not valid JSON: {exc}"


def check():
    problems = []

    plugin, err = _load(".claude-plugin/plugin.json")
    if err:
        return [err]
    market, err = _load(".claude-plugin/marketplace.json")
    if err:
        return [err]

    version = plugin.get("version")
    if not version:
        problems.append(
            "plugin.json has no `version`. That is a valid choice — it makes "
            "every commit an update — but then remove it from the marketplace "
            "entry too, or the entry's version wins and pins users."
        )
    elif not SEMVER.match(version):
        problems.append(f"plugin.json version {version!r} is not valid semver (MAJOR.MINOR.PATCH).")

    entries = market.get("plugins") or []
    if not entries:
        problems.append("marketplace.json lists no plugins.")
        return problems
    entry = entries[0]

    entry_version = entry.get("version")
    if version and entry_version and entry_version != version:
        problems.append(
            f"version mismatch: plugin.json says {version!r}, marketplace entry says "
            f"{entry_version!r}. plugin.json wins at runtime, so listings would misreport."
        )

    if plugin.get("name") != entry.get("name"):
        problems.append(
            f"name mismatch: plugin.json {plugin.get('name')!r} vs marketplace entry "
            f"{entry.get('name')!r}. The marketplace entry name is what `/plugin` and "
            "`enabledPlugins` key on."
        )

    changelog = ROOT / "CHANGELOG.md"
    if not changelog.is_file():
        problems.append("CHANGELOG.md is missing.")
    elif version:
        text = changelog.read_text(encoding="utf-8")
        if not re.search(rf"^##\s*\[?{re.escape(version)}\]?", text, re.M):
            problems.append(
                f"CHANGELOG.md has no `## [{version}]` section. Bumping the version without "
                "documenting it means users receive a change they cannot read about."
            )

    problems.extend(_check_stale_name())
    return problems


def _check_stale_name():
    """Catch pre-rename references that would send users to a dead URL."""
    problems = []
    for pattern, why in STALE_PATTERNS:
        try:
            out = subprocess.run(
                ["git", "grep", "-n", "-I", "-E", pattern],
                cwd=ROOT, capture_output=True, text=True,
            ).stdout
        except (OSError, subprocess.SubprocessError):
            return []  # not a git checkout; skip rather than fail the build

        hits = [
            line for line in out.splitlines()
            if line.strip() and not any(line.startswith(f) for f in STALE_ALLOWED_FILES)
        ]
        if hits:
            shown = "\n    ".join(hits[:5])
            more = f"\n    ... and {len(hits) - 5} more" if len(hits) > 5 else ""
            problems.append(f"stale reference ({why}):\n    {shown}{more}")
    return problems


def main():
    problems = check()
    if problems:
        print("Release check FAILED:\n", file=sys.stderr)
        for p in problems:
            print(f"  - {p}\n", file=sys.stderr)
        return 1
    plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    print(f"Release check OK — {plugin['name']} {plugin['version']}, manifests and changelog agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
