#!/usr/bin/env python3
"""Scaffold a job-hunt workspace (Setup mode).

Creates the workspace contract for a brand-new user and STOPS so they can fill
their profile. Path-agnostic: pass --workspace, set JOBHUNT_DIR, or let it use the
resolver. Idempotent and SAFE: refuses to clobber an already-populated workspace
(that is discover-and-reuse territory, not setup) unless --force.

Creates:
  <root>/profiles/<name>.md              # rich profile template (warehouse, not a CV)
  <root>/applications/                   # tracker lives here
  <root>/applications/daily-hunt/
        _RUN-PLAYBOOK.md                 # hard rules + live-connector board list
        seen-jobs.csv                    # empty dedupe ledger (header only)
  <root>/scripts/                        # copy of the skill's scripts (portable)
  <root>/applications/tracker.xlsx+csv   # via tracker.py init

Usage:
  python init_workspace.py --workspace <dir> [--name alex] [--force]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import (  # noqa: E402
    preflight, is_workspace, resolve_workspace_root,
    applications_dir, daily_dir, profiles_dir, scripts_dir,
)

SCRIPT_FILES = ["_lib.py", "tracker.py", "new_application.py", "render_docx.py",
                "build_seen_ledger.py"]

SEEN_LEDGER_HEADER = "job_key,status,category,company,role,link,folder_path,last_seen\n"

PROFILE_TEMPLATE = """\
<!--
MASTER PROFILE / DATA FEED for the job-hunt skill — a WAREHOUSE, not a CV.
The tailorer SELECTS from this per role and NEVER invents facts. Put EVERYTHING
true here (even things you won't use often); mark anything you must NEVER claim.
Fill every section, then re-run the daily hunt. Keep this file private (gitignored).
-->

# Master profile — {name}

## Identity
- Full name:
- Location (base + willing-to-relocate?):
- Right to work (UK status / visa / sponsorship needed?):
- Contact (email / phone / LinkedIn / portfolio):
- Driving licence / own transport:

## Positioning by target
_One tight positioning line per target family — how you want to be read for each._
- Plant science / CEA:
- Data / AI / ML research:
- (add your families…):

## Experience
_Every role: employer, title, dates, what you actually did, methods, quantified outcomes.
Mark concurrent roles. This is the evidence the tailorer draws bullets from._
-

## Skills warehouse
_Everything you can genuinely do — tools, techniques, languages, domains. Group loosely._
-

### NEVER claim (hard gaps — truth guardrail)
_Techniques/tools you have NOT performed. The tailorer must never assert these, even if a
JD asks. A CV that can't survive the interview question is worse than a shorter honest one._
-

## Education
_Degree, institution, country, years (real years), classification/grade._
-

## Certifications & training
-

## Outputs
_Publications (with real DOIs), talks, projects, portfolio pieces, open-source._
-

## References
-

## Career targets
- Priority order (1 = most wanted; the hunt sources in this order):
  1.
  2.
  3.
- Bridge / fallback lanes (acceptable stepping-stone roles):
- Last-resort lanes:
- Salary floor (won't go below):
- Geography (locations / remote / hybrid / relocation):
- Work pattern (full-time / part-time / contract):

## Confidential hold
_NDA'd products, private references, anything to describe only as capability, never by
protected specifics. The tailorer respects these holds._
-

## Conflicts to resolve
_Open questions the tailorer should flag rather than guess: timeline gaps, ambiguous dates,
overlapping roles, missing licences, etc._
-
"""

PLAYBOOK_TEMPLATE = """\
# Daily hunt — RUN PLAYBOOK (read first, every run)

This is the hard-rules + lessons-learned file the hunt reads before doing anything.
Edit the lessons section as you learn what works for this profile.

## Hard rules (do not weaken)
1. **Read this playbook, then read the profile fresh.** If the profile is missing or empty,
   STOP and report — do nothing else.
2. **Truth first.** Never claim a skill/technique the profile lists under "NEVER claim".
   Respect confidential holds — describe capability, never protected specifics.
3. **Only LIVE roles.** Expired/withdrawn listings (redirect, "no longer advertised") are
   never tailored — file them Skipped with a "watch for re-post" reason.
4. **Only NEW roles.** Dedupe on the canonical job key (job ref or full URL), never on a
   folder-name slug. Skip anything whose key is already in seen-jobs.csv.
5. **No cap on tailoring.** Tailor EVERY strong, new, live match — best-fit-first,
   soonest-closing-first. Don't stop at N.
6. **The tracker is owned only by tracker.py.** All state changes route through it.
   Applied rows are final/locked — never touch them.
7. **File everything** — Drafted (tailored) or Skipped (with a reason + source link), so the
   ledger key always resolves.
8. **Cover letters are never cold-generated** — prep the scaffold, flag "needs brain-dump".

## Sourcing lanes (live connectors first)
Board choice follows the profile's target priority order. Connectors available now
(prefer these over raw WebSearch — they give structured, filterable, live/expired signals):
- **Commercial roles** → Adzuna + Reed MCP connectors (UK, salary-aware). Also Indeed.
- **Academic / research** → jobs.ac.uk (search EACH discipline facet SEPARATELY — multi-facet
  queries silently drop one), plus institute career pages.
- **Niche / company careers pages** → Firecrawl scrape/crawl.
- **Tech (US-leaning)** → Dice, for AI/data families only.
- **Fallback** → WebSearch → Firecrawl/WebFetch, only where no connector covers a board.

## Knockout criteria (profile-driven — record the reason on every Skip)
Compare each JD's essentials against the profile: languages, licences (e.g. SIA), right-to-work,
degree field, wet-lab/technique requirements listed under "NEVER claim". A hard knockout the
candidate cannot truthfully meet → Skip with the reason.

## Lessons learned (append as you go)
- (e.g. "Harper Adams reposts CCES RA roles ~quarterly — keep on watch-list.")
"""


def _rel(path, base):
    """relpath that survives cross-drive paths on Windows (workspace on a
    different drive than cwd would otherwise raise ValueError)."""
    try:
        return os.path.relpath(path, base)
    except ValueError:
        return path


def _write_if_absent(path, content, base, force=False):
    if os.path.exists(path) and not force:
        print(f"  kept    {_rel(path, base)}")
        return
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"  wrote   {_rel(path, base)}")


def main():
    ap = argparse.ArgumentParser(description="Scaffold a job-hunt workspace (Setup mode).")
    ap.add_argument("--workspace", help="workspace root (else JOBHUNT_DIR / discovery)")
    ap.add_argument("--name", default="profile", help="profile file basename (e.g. alex)")
    ap.add_argument("--force", action="store_true", help="scaffold even if workspace exists")
    args = ap.parse_args()

    # Sanitize --name before it becomes a filename under profiles/ (prevents traversal).
    args.name = re.sub(r"[^A-Za-z0-9._-]", "", args.name) or "profile"

    preflight()  # deps must be present so the tracker init won't half-commit

    root = resolve_workspace_root(args.workspace)
    if not root:
        sys.exit("No workspace path given. Pass --workspace <dir> or set JOBHUNT_DIR.")
    root = os.path.abspath(root)

    if is_workspace(root) and not args.force:
        print(f"Workspace already exists at {root} — discover-and-reuse, nothing scaffolded.")
        print("Run the daily hunt instead. (Use --force only to re-drop missing templates.)")
        return

    print(f"Scaffolding workspace at {root}")
    for d in (profiles_dir(root), applications_dir(root), daily_dir(root), scripts_dir(root)):
        os.makedirs(d, exist_ok=True)
        print(f"  dir     {os.path.relpath(d, root)}/")

    # Copy the skill's scripts into the workspace so it's self-contained/portable.
    for fn in SCRIPT_FILES:
        src = os.path.join(HERE, fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(scripts_dir(root), fn))
            print(f"  script  scripts/{fn}")

    _write_if_absent(os.path.join(profiles_dir(root), f"{args.name}.md"),
                     PROFILE_TEMPLATE.format(name=args.name), root, args.force)
    _write_if_absent(os.path.join(daily_dir(root), "_RUN-PLAYBOOK.md"),
                     PLAYBOOK_TEMPLATE, root, args.force)
    _write_if_absent(os.path.join(daily_dir(root), "seen-jobs.csv"),
                     SEEN_LEDGER_HEADER, root, args.force)

    # Initialise the tracker (idempotent).
    init = subprocess.run([sys.executable, os.path.join(HERE, "tracker.py"),
                           "init", "--root", applications_dir(root)],
                          capture_output=True, text=True)
    sys.stdout.write("  " + init.stdout)
    if init.returncode != 0:
        sys.stderr.write(init.stderr)
        sys.exit(init.returncode)

    print("\nSETUP COMPLETE — next step is YOURS:")
    print(f"  1. Fill in profiles/{args.name}.md (it's a warehouse, not a CV).")
    print("  2. Then run the daily hunt against this workspace.")
    print("Stopping here so the profile isn't hunted against while empty.")


if __name__ == "__main__":
    main()
