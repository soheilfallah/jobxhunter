#!/usr/bin/env python3
"""Shared helpers for the jobxhunter skill scripts.

Two jobs, both about making the skill portable and safe:

1. **Workspace resolution** — never hard-code a machine path. Resolve the
   workspace root once (explicit arg -> JOBXHUNTER_DIR env -> discovery -> None) and
   derive every sub-path (profiles/, applications/, daily-hunt/) from it.

2. **Dependency preflight** — the tracker must never half-commit. `tracker.py`
   sys.exit()s if `openpyxl` is missing, which used to let `new_application.py`
   create a folder but write no tracker row. Preflight checks the deps up front
   and fails loudly with the exact fix, so a run either works or stops clearly.

Usable as a library (import) or a CLI:
    python _lib.py preflight            # check deps, exit 1 with fix if missing
    python _lib.py resolve [--workspace <dir>]   # print resolved workspace root
"""
import argparse
import importlib
import os
import sys

# Workspace contract sub-directory names (single source of truth).
PROFILES_DIR = "profiles"
APPLICATIONS_DIR = "applications"
DAILY_DIR = "daily-hunt"
SCRIPTS_DIR = "scripts"

# (import name, pip name, what needs it)
REQUIRED_DEPS = [
    ("openpyxl", "openpyxl", "tracker.xlsx read/write (tracker.py)"),
    ("docx", "python-docx", "CV .docx rendering (render_docx.py)"),
]

# Characters that make a spreadsheet cell execute as a formula / DDE payload when
# opened in Excel or LibreOffice. Untrusted job-ad text (company, role, notes) flows
# into the tracker, so it MUST be neutralised before it lands in a cell or CSV row.
_FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r", "|")


def safe_cell(value):
    """Neutralise spreadsheet formula/DDE injection.

    If a STRING value begins with a formula trigger (= + - @ tab CR |), prefix it
    with an apostrophe so Excel/LibreOffice treat the whole cell as literal text
    rather than a formula. Non-strings (ints, dates) and safe strings pass through
    unchanged. This is the standard OWASP CSV-injection mitigation.
    """
    if isinstance(value, str) and value and value[0] in _FORMULA_TRIGGERS:
        return "'" + value
    return value


# ------------------------------------------------------------------ console io
def enable_utf8_io():
    """Force stdout/stderr to UTF-8 so printing non-Latin-1 job data (accented
    employer/role names, £, em-dashes, non-ASCII dump filenames) never dies with a
    UnicodeEncodeError on a default-code-page (cp1252) Windows console. No-op where
    the streams are already UTF-8 or cannot be reconfigured (e.g. redirected pipes
    on older Pythons)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


# ---------------------------------------------------------------- dependencies
def check_deps(deps=REQUIRED_DEPS):
    """Return list of (import_name, pip_name, why) for each MISSING dependency."""
    missing = []
    for imp, pip_name, why in deps:
        try:
            importlib.import_module(imp)
        except ImportError:
            missing.append((imp, pip_name, why))
    return missing


def preflight(deps=REQUIRED_DEPS, exit_on_missing=True):
    """Verify deps are importable. On missing: print the exact fix and (default)
    exit 1 so a caller never proceeds into a half-commit. Returns True if all present."""
    missing = check_deps(deps)
    if not missing:
        return True
    pkgs = " ".join(pip for _, pip, _ in missing)
    sys.stderr.write("JobXHunter preflight FAILED — missing Python dependencies:\n")
    for imp, pip_name, why in missing:
        sys.stderr.write(f"  - {pip_name}  (import '{imp}') — needed for {why}\n")
    sys.stderr.write(
        f"\nFix (one of):\n"
        f"  python -m pip install {pkgs}\n"
        f"  {sys.executable} -m pip install {pkgs}\n"
    )
    if exit_on_missing:
        sys.exit(2)
    return False


# ------------------------------------------------------------------ workspace
def is_workspace(path):
    """A directory is a jobxhunter workspace if it holds profiles/ AND applications/."""
    if not path or not os.path.isdir(path):
        return False
    return os.path.isdir(os.path.join(path, PROFILES_DIR)) and \
        os.path.isdir(os.path.join(path, APPLICATIONS_DIR))


def _discover_upward(start):
    """Discover a workspace, precisely (no sibling jumps):
       1. `start` itself is a workspace, or
       2. `start` has exactly ONE child workspace (start = repo/career root), or
       3. an ANCESTOR of `start` is a workspace (walk up).
    The child-scan runs ONLY on `start` — scanning every ancestor's children would
    let an empty dir discover an unrelated sibling workspace (wrong -> skips Setup)."""
    start = os.path.abspath(start)
    if is_workspace(start):
        return start
    try:
        hits = [os.path.join(start, d) for d in os.listdir(start)
                if is_workspace(os.path.join(start, d))]
    except OSError:
        hits = []
    if len(hits) == 1:
        return hits[0]
    cur = start
    while True:
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        if is_workspace(parent):
            return parent
        cur = parent


def resolve_workspace_root(explicit=None, start=None):
    """Resolve the workspace root, in order:
       1. `explicit` arg (a path passed by the user/agent),
       2. JOBXHUNTER_DIR environment variable. Older names are still honoured so a
          pinned workspace never silently falls back to discovery after a rename:
          JOBSMITH_DIR (the plugin was named jobsmith through 1.2.x) and JOBHUNT_DIR
          (named job-hunt before that).
       3. discovery: an existing dir (from `start`/cwd upward) that has
          profiles/ + applications/.
    Returns an absolute path, or None if nothing resolves (caller -> Setup mode).
    An explicit/env path is returned even if not yet populated, so Setup can create it."""
    if explicit:
        return os.path.abspath(explicit)
    env = (os.environ.get("JOBXHUNTER_DIR")
           or os.environ.get("JOBSMITH_DIR")
           or os.environ.get("JOBHUNT_DIR"))
    if env:
        return os.path.abspath(env)
    return _discover_upward(start or os.getcwd())


def sub(root, *parts):
    """Join a workspace sub-path from the contract dirs."""
    return os.path.join(root, *parts)


def applications_dir(root):
    return os.path.join(root, APPLICATIONS_DIR)


def daily_dir(root):
    # daily-hunt lives UNDER applications/ (workspace contract).
    return os.path.join(root, APPLICATIONS_DIR, DAILY_DIR)


def profiles_dir(root):
    return os.path.join(root, PROFILES_DIR)


def scripts_dir(root):
    return os.path.join(root, SCRIPTS_DIR)


# ------------------------------------------------------------- plugin user-config
# userConfig field -> the environment variable the connectors and scripts read.
PLUGIN_SECRET_ENV = {
    "reed_api_key": "REED_API_KEY",
    "adzuna_app_id": "ADZUNA_APP_ID",
    "adzuna_app_key": "ADZUNA_APP_KEY",
    "firecrawl_api_key": "FIRECRAWL_API_KEY",
}


def plugin_secrets(store=None):
    """-> {userConfig field: value} for this plugin, from Claude Code's credential store.

    `sensitive: true` userConfig values are written (Windows/Linux) to
    ~/.claude/.credentials.json under `pluginSecrets[<plugin@marketplace>]`; the same
    place setup_connectors.py reports from. macOS keeps them in the keychain, so this
    returns {} there and the caller falls back to environment variables. Never raises:
    an unreadable store is "no keys", not a crash.
    """
    import json
    path = store or os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")
    try:
        with open(path, encoding="utf-8") as fh:
            secrets = json.load(fh).get("pluginSecrets") or {}
    except (OSError, ValueError):
        return {}
    for pid, vals in secrets.items():
        if pid.split("@")[0] == "jobxhunter" and isinstance(vals, dict):
            return {k: str(v) for k, v in vals.items() if v}
    return {}


def secret_env(name, store=None):
    """-> the value for an env-var name such as REED_API_KEY: the environment first, then
    the plugin's user-config (see PLUGIN_SECRET_ENV). '' when neither has it."""
    if os.environ.get(name):
        return os.environ[name]
    fields = [f for f, env in PLUGIN_SECRET_ENV.items() if env == name]
    vals = plugin_secrets(store)
    return next((vals[f] for f in fields if vals.get(f)), "")


# ------------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description="JobXHunter shared helpers (preflight / resolve).")
    sub_ap = ap.add_subparsers(dest="cmd", required=True)
    sub_ap.add_parser("preflight")
    rp = sub_ap.add_parser("resolve")
    rp.add_argument("--workspace", help="explicit workspace root (overrides env/discovery)")
    rp.add_argument("--start", help="directory to start discovery from (default: cwd)")
    args = ap.parse_args()

    if args.cmd == "preflight":
        preflight()
        print("Preflight OK — openpyxl + python-docx importable.")
    elif args.cmd == "resolve":
        root = resolve_workspace_root(args.workspace, args.start)
        if not root:
            # Exit 1 is the documented signal for "no workspace yet", not a failure.
            # It is the normal first-run result; say so, because a bare non-zero exit
            # reads as an error to both humans and agents.
            print("NONE — no workspace yet. This is the expected first-run result, not an error.")
            print("  Checked: --workspace arg, JOBXHUNTER_DIR env, then upward discovery from cwd.")
            print("  Next: init_workspace.py --workspace <dir> [--name <who>]   (Setup mode)")
            sys.exit(1)
        print(root)
        print(f"  is_workspace: {is_workspace(root)}")
        # Discovery only walks upward from cwd, so running jobxhunter from an
        # unrelated folder tomorrow resolves to NONE and can scaffold a second
        # workspace. Say how to pin it while the answer is in front of them.
        if not any(os.environ.get(v) for v in ("JOBXHUNTER_DIR", "JOBSMITH_DIR", "JOBHUNT_DIR")):
            print("  tip: to reach this workspace from anywhere, set JOBXHUNTER_DIR="
                  f"{root}")


if __name__ == "__main__":
    main()
