#!/usr/bin/env python3
"""Shared helpers for the job-hunt skill scripts.

Two jobs, both about making the skill portable and safe:

1. **Workspace resolution** — never hard-code a machine path. Resolve the
   workspace root once (explicit arg -> JOBHUNT_DIR env -> discovery -> None) and
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
    sys.stderr.write("Job-hunt preflight FAILED — missing Python dependencies:\n")
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
    """A directory is a job-hunt workspace if it holds profiles/ AND applications/."""
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
       2. JOBHUNT_DIR environment variable,
       3. discovery: an existing dir (from `start`/cwd upward) that has
          profiles/ + applications/.
    Returns an absolute path, or None if nothing resolves (caller -> Setup mode).
    An explicit/env path is returned even if not yet populated, so Setup can create it."""
    if explicit:
        return os.path.abspath(explicit)
    env = os.environ.get("JOBHUNT_DIR")
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


# ------------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description="Job-hunt shared helpers (preflight / resolve).")
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
            print("NONE — no workspace resolved (arg/JOBHUNT_DIR/discovery all empty). Setup mode.")
            sys.exit(1)
        print(root)
        print(f"  is_workspace: {is_workspace(root)}")


if __name__ == "__main__":
    main()
