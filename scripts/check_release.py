#!/usr/bin/env python3
"""Release consistency check for the jobxhunter plugin.

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
  6. Every `<owner>/<repo>` reference agrees, and matches the git remote. A
     transfer or rename that misses one ships an install command resolving to
     nothing, which is the most expensive typo here: it is the first line a
     new user copies.
  7. No absolute path from a real machine is committed. This repo is public
     (GitHub Pages serves `docs/` from it), so a hardcoded home directory
     publishes a username and workspace layout — and is wrong as documentation
     anyway, since no reader shares that path.

Run it before opening a PR, and in CI:

    python scripts/check_release.py

Exits 0 when clean, 1 with a list of problems otherwise.
"""

import collections
import json
import pathlib
import re
import subprocess
import sys

# UTF-8 stdout/stderr so non-ASCII diff output never dies on a default (cp1252)
# Windows console (this also runs in CI).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")

# Only patterns that actually break something. Deliberately NOT flagged:
#   "job-hunting"        — the activity, correct English, used throughout the copy
#   JOBSMITH_DIR / JOBHUNT_DIR — documented backward-compatible env vars (old names)
#   career/job-hunt/     — the user's private data workspace, not the plugin
#   references/*.md      — "(UK-first)" doc titles describe real content
# The plugin was named job-hunt (pre-1.2), then jobsmith (1.2.x), then jobxhunter
# (1.3+). Flag any dead reference to EITHER old name so an install command never 404s.
STALE_PATTERNS = [
    (r"soheilfallah/job-hunt\b",  "dead repo URL — the web URL 404s after the rename"),
    (r"soheil-job-hunt\b",        "dead marketplace id"),
    (r"/job-hunt:",               "dead command namespace"),
    (r"skills/job-hunt\b",        "dead install path"),
    (r"job-hunt@",                "dead install target"),
    (r"soheilfallah/jobsmith\b",  "dead repo URL — 404s after the jobsmith->jobxhunter rename"),
    (r"soheil-jobsmith\b",        "dead marketplace id (was jobsmith)"),
    (r"/jobsmith:",               "dead command namespace (was jobsmith)"),
    (r"skills/jobsmith\b",        "dead install path (was jobsmith)"),
    (r"jobsmith@",                "dead install target (was jobsmith)"),
]
STALE_ALLOWED_FILES = ("CHANGELOG.md", "scripts/check_release.py")

# Absolute paths from someone's actual machine. This repo is PUBLIC — GitHub
# Pages serves docs/ from it — so a committed home directory publishes a
# username and the maintainer's folder layout. It is also simply wrong as
# documentation: no reader has that path, so a copied snippet cannot work.
# Placeholders are the correct form and never match these:
#   C:\path\to\...   %USERPROFILE%\...   ~/...   $HOME/...
#
# The backslash run MUST be a bracket expression. A Windows path appears in two
# forms — prose (C:\Users\me) and backslash-escaped inside a JSON snippet
# (C:\\Users\\me) — and `git grep -E` does not apply a quantifier to a bare
# `\\` escape the way you would expect, so `\\\\?` silently matches only the
# prose form. That exact bug shipped once and gave false assurance while the
# JSON form went right past it. `[\\]+` is unambiguous under git grep's ERE.
# _selftest_local_paths() proves this on every run; do not "simplify" it back.
LOCAL_PATH_PATTERNS = [
    (r"[A-Za-z]:[\\]+(Users|soh-workspace)", "absolute Windows path from a real machine"),
    (r"/(Users|home)/[A-Za-z0-9._-]+/", "absolute POSIX home path from a real machine"),
]
# Proof fixtures for the patterns above, checked through the same `git grep -E`
# engine the real scan uses. A pattern that cannot match what it claims to match
# is worse than no pattern, because the passing build reads as "clean".
LOCAL_PATH_MUST_MATCH = [
    r"sessions read and write files under `C:\Users\someone\Claude`",
    r'      "args": ["D:\\soh-workspace\\projects\\thing\\server.py"],',
    r'      "command": "C:\\Users\\someone\\.venv\\Scripts\\python.exe",',
    r"script lives at /home/someone/projects/thing/server.py",
]
LOCAL_PATH_MUST_NOT_MATCH = [
    r'      "args": ["C:\path\to\thing\server.py"],',
    r"%USERPROFILE%\Claude on Windows, ~/Claude on macOS",
    r"$HOME/Claude",
    r"copy it to /home/you/projects/thing/",
    r"the runner home is /home/runner/work",
]
# Generic stand-ins that read as placeholders, plus the GitHub Actions runner
# home, which is a real and correct path to document in CI notes.
LOCAL_PATH_ALLOWED_SEGMENTS = (
    "/Users/you/", "/home/you/", "/Users/user/", "/home/user/",
    "/Users/username/", "/home/username/", "/home/runner/",
)
# This file spells the patterns out; the CHANGELOG quotes fixes verbatim.
LOCAL_PATH_ALLOWED_FILES = ("CHANGELOG.md", "scripts/check_release.py")


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
    problems.extend(_check_owner_consistency())
    problems.extend(_selftest_local_paths())
    problems.extend(_check_local_paths())
    return problems


def _selftest_local_paths():
    """Prove LOCAL_PATH_PATTERNS still match what they claim, before trusting them.

    Runs the patterns over known-bad and known-good fixtures through
    `git grep --no-index -E` — the same engine and flags as the real scan, which
    matters because git grep's ERE differs from Python's `re` on backslash
    quantifiers. Without this, a subtly wrong pattern reports a clean tree and
    the check becomes a rubber stamp.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        bad = pathlib.Path(tmp, "bad.txt")
        good = pathlib.Path(tmp, "good.txt")
        bad.write_text("\n".join(LOCAL_PATH_MUST_MATCH) + "\n", encoding="utf-8")
        good.write_text("\n".join(LOCAL_PATH_MUST_NOT_MATCH) + "\n", encoding="utf-8")

        def scan(name):
            hit = set()
            for pattern, _ in LOCAL_PATH_PATTERNS:
                try:
                    out = subprocess.run(
                        ["git", "grep", "--no-index", "-n", "-I", "-E", pattern, "--", name],
                        cwd=tmp, capture_output=True, text=True,
                    ).stdout
                except (OSError, subprocess.SubprocessError):
                    return None
                hit.update(int(l.split(":")[1]) for l in out.splitlines() if ":" in l)
            return hit

        caught, false_pos = scan("bad.txt"), scan("good.txt")
        if caught is None or false_pos is None:
            return []  # no usable git; the real scan skips too

    problems = []
    missed = [LOCAL_PATH_MUST_MATCH[i - 1] for i in
              sorted(set(range(1, len(LOCAL_PATH_MUST_MATCH) + 1)) - caught)]
    if missed:
        shown = "\n    ".join(missed)
        problems.append(
            "LOCAL_PATH_PATTERNS self-test failed — these leak examples are NOT "
            f"caught, so the local-path check cannot be trusted:\n    {shown}"
        )
    # allowlisted segments are applied by the real scan, so discount them here
    fp = [LOCAL_PATH_MUST_NOT_MATCH[i - 1] for i in sorted(false_pos)]
    fp = [l for l in fp if not any(seg in l for seg in LOCAL_PATH_ALLOWED_SEGMENTS)]
    if fp:
        shown = "\n    ".join(fp)
        problems.append(
            "LOCAL_PATH_PATTERNS self-test failed — these are legitimate "
            f"placeholders but the patterns flag them:\n    {shown}"
        )
    return problems


def _check_local_paths():
    """Catch absolute paths from a real machine leaking into the public repo.

    Found in the wild: connector READMEs shipped the maintainer's home and
    workspace paths inside otherwise copy-pasteable `.mcp.json` snippets, so
    the snippets published a username *and* could not work for anyone who
    copied them. Both failure modes have the same fix — use a placeholder.
    """
    problems = []
    for pattern, why in LOCAL_PATH_PATTERNS:
        try:
            out = subprocess.run(
                ["git", "grep", "-n", "-I", "-E", pattern],
                cwd=ROOT, capture_output=True, text=True,
            ).stdout
        except (OSError, subprocess.SubprocessError):
            return []  # not a git checkout; skip rather than fail the build

        hits = [
            line for line in out.splitlines()
            if line.strip()
            and not any(line.startswith(f) for f in LOCAL_PATH_ALLOWED_FILES)
            and not any(seg in line for seg in LOCAL_PATH_ALLOWED_SEGMENTS)
        ]
        if hits:
            shown = "\n    ".join(hits[:5])
            more = f"\n    ... and {len(hits) - 5} more" if len(hits) > 5 else ""
            problems.append(
                f"local path committed ({why}) — this repo is public; use a "
                f"placeholder such as C:\\path\\to\\ or ~/ instead:\n    {shown}{more}"
            )
    return problems


def _check_owner_consistency():
    """Every `<owner>/<repo>` reference must agree, and match the git remote.

    A repository transfer or rename changes the owner in the URL. Miss one and
    the README ships an install command that resolves to nothing, which is the
    single most expensive typo in the repo: it is the first thing a new user
    copies.
    """
    slug = re.compile(r"github\.com[:/]([A-Za-z0-9-]+)/([A-Za-z0-9._-]+?)(?:\.git)?(?=[/\s\)\"'`]|$)")
    found = collections.defaultdict(set)

    try:
        out = subprocess.run(["git", "grep", "-I", "-h", "-E", r"github\.com[:/][A-Za-z0-9-]+/"],
                             cwd=ROOT, capture_output=True, text=True).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    for owner, repo in slug.findall(out):
        if repo.lower() in ("sponsors", "orgs"):
            continue
        found[f"{owner}/{repo}"].add(owner)

    # bare `<owner>/<repo>` in the /plugin marketplace add line has no github.com prefix
    try:
        bare = subprocess.run(["git", "grep", "-I", "-h", "-oE", r"marketplace add [A-Za-z0-9-]+/[A-Za-z0-9._-]+"],
                              cwd=ROOT, capture_output=True, text=True).stdout
    except (OSError, subprocess.SubprocessError):
        bare = ""
    for line in bare.splitlines():
        found[line.split()[-1]].add(line.split()[-1].split("/")[0])

    owners = {o for slugs in found.values() for o in slugs}
    if len(owners) > 1:
        return [f"conflicting repo owners referenced: {sorted(owners)}. "
                "A transfer or rename left some URLs behind."]

    # cross-check against the actual remote, when there is one
    try:
        remote = subprocess.run(["git", "remote", "get-url", "origin"],
                                cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return []
    m = slug.search(remote)
    if not m or not owners:
        return []
    actual = f"{m.group(1)}/{m.group(2)}"
    referenced = {s for s in found if "/" in s}
    wrong = {s for s in referenced if s.lower() != actual.lower()}
    if wrong:
        return [f"docs reference {sorted(wrong)} but origin is {actual}. "
                "Update every owner/repo reference after a transfer or rename."]
    return []


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
