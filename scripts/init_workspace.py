#!/usr/bin/env python3
"""Scaffold a jobsmith workspace (Setup mode).

Creates the workspace contract for a brand-new user and STOPS so they can fill
their profile. Path-agnostic: pass --workspace, set JOBSMITH_DIR, or let it use the
resolver. Idempotent and SAFE: refuses to clobber an already-populated workspace
(that is discover-and-reuse territory, not setup) unless --force.

Creates:
  <root>/profiles/<name>.md              # rich profile template: everything true about you,
                                         # far more than one CV shows. Tailoring selects from it.
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
from dump_manifest import FIELDS as MANIFEST_FIELDS  # noqa: E402

SCRIPT_FILES = ["_lib.py", "tracker.py", "new_application.py", "render_docx.py",
                "build_seen_ledger.py", "dump_manifest.py"]

SEEN_LEDGER_HEADER = "job_key,status,category,company,role,link,folder_path,last_seen\n"
MANIFEST_HEADER = ",".join(MANIFEST_FIELDS) + "\n"

CHANGELOG_TEMPLATE = """\
# Intake changelog

Each intake run appends what it added or changed in the master profile.
Newest entries at the bottom. The profile itself is the source of truth;
this is the audit trail.
"""

DUMP_README = """\
# Dump everything about yourself here

Drop ANY files about you into this folder, in any format — the skill reads them all and builds your
master profile for you (the INTAKE command; best in cowork). Messy is fine.

Good things to add:
- Old CVs / résumés (any version) and cover letters
- Your LinkedIn export (Profile -> Save to PDF, or the full data-export archive)
- Certificates, licences, transcripts, degree certificates (PDF or photo)
- Brag docs, notes, brain-dumps — freeform is welcome
- Performance reviews, reference letters, portfolio/project write-ups
- Job ads you liked (helps infer your target roles + market/country)
- A short note: your location, work authorisation, salary floor, and where you want to work

Then run INTAKE. It scans this folder into `_manifest.csv` (so re-runs only pick up what's new),
reads what it can, and for any file it can't read as text here (Word/PDF/image) it leaves a placeholder
under `../profiles/_intake/placeholders/` so nothing is lost — read those in cowork/Desktop or convert
them to text and drop the text version here.

Nothing here is published — this folder stays private to your workspace.
"""

PROFILE_TEMPLATE = """\
<!--
MASTER PROFILE / DATA FEED for the jobsmith skill — a WAREHOUSE, not a CV.
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
8. **Cover letters in the autonomous run default to a scaffold** — prep it and flag "needs brain-dump"
   (no user is present to brainstorm with). The on-demand COVER LETTER command may draft a profile-only
   letter without a brain-dump (recommended, not required), flagging the "why this company" paragraph.

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

WORKSPACE_MAP_TEMPLATE = """\
# Workspace map — what every folder and file here is for

This directory is your jobsmith **workspace**: the single home for your profile, the raw material it's
built from, and every application. It's path-agnostic and private (keep it gitignored). This map is
generated at setup so the structure is always self-explaining and trustworthy.

Entries marked **[later]** do not exist yet. They are created by a command as you use it, so
an empty slot is expected rather than something you need to fix.

```
<this folder>/
  WORKSPACE-MAP.md            ← you are here
  dump/                       ← drop RAW material about yourself here (any format)
    README.md                 ← what to put in dump/
    _manifest.csv             ← INTAKE's book-keeping: one row per file, with a status
  profiles/
    {profile_line}← THE MASTER PROFILE (see below)
    _intake/                  ← intake internals (private)
      placeholders/           ← a stub for each dump file that couldn't be read as text here
      CHANGELOG.md            ← what each intake run added to the profile
  applications/
    tracker.xlsx | .csv       ← the system of record (owned ONLY by scripts/tracker.py)
    tracker-priority.xlsx     ← [later] worklist from `tracker.py priority-view`
    <category>/<YYYY-MM-DD>_<company>_<role>/   ← [later] one per job you tailor for
      job-description.md      ← the captured full JD
      notes.md                ← coverage matrix, brain-dump, recruiter scorecard, L2 delta
      CV.md  CV.docx  CV.txt  ← the tailored CV (markdown source + rendered outputs)
      cover-letter.*          ← if generated
    daily-hunt/
      _RUN-PLAYBOOK.md        ← hard rules + lessons — read FIRST every hunt
      seen-jobs.csv           ← dedupe ledger (canonical job key -> status)
      <YYYY-MM-DD>-summary.md ← [later] one dated summary per hunt run
  scripts/                    ← a portable copy of the skill's deterministic scripts
```

## About the master profile
`profiles/{name}.md` is the one file everything else reads. Keep it **richer than any single CV
needs**: every role, every skill, every number, every output, including things you would never put
on a CV. Tailoring *selects* from it rather than inventing, so the more real evidence it holds, the
better each tailored CV gets. The profile itself is never sent to an employer.

## How the profile stays current
Drop files into `dump/`, then run INTAKE. It runs `scripts/dump_manifest.py scan`, which records each
file in `dump/_manifest.csv` with a status:
`new` (read it now) · `updated` (changed, re-read) · `ingested` (already in the profile, skip) ·
`unreadable` (a format it can't read as text here — a placeholder is left under
`profiles/_intake/placeholders/`) · `missing` (removed from dump/). Because it diffs against the
manifest, re-running intake only processes genuinely new material — so the profile grows every time you
add something, without redoing old work.

## Output-format contract (Word + PDF both matter — use each for its job)
- **`CV.docx`** — the **ATS submission**. Single-column, no tables/graphics; parses cleanly. Rendered by
  `scripts/render_docx.py` (Claude Code) or the native `docx` skill (cowork).
- **`CV.txt`** — the plain-text mirror, for pasting into web forms and eyeballing what the ATS sees.
- **PDF** — a **human-facing / portfolio copy only**, produced via the `/make-pdf` skill on request.
  Do **not** submit the make-pdf PDF to an ATS (it isn't guaranteed ATS-parseable); send it only when a
  human asked for a PDF directly or a JD explicitly requires one.
- **`tracker.xlsx` + `tracker.csv`** — the application log. Always change it through `scripts/tracker.py`
  (it owns the green-fill + lock on `Applied` rows); never hand-edit.

## Trust rules
- The **master profile is the only source of truth** for any submitted document — the skill selects and
  reframes from it, never invents.
- `dump/`, `profiles/` (incl. `_intake/`) are **personal data** — keep the workspace out of any public repo.
- Every job — applied or skipped — is filed in a category folder and logged, so nothing is lost.
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
    ap = argparse.ArgumentParser(description="Scaffold a jobsmith workspace (Setup mode).")
    ap.add_argument("--workspace", help="workspace root (else JOBSMITH_DIR / discovery)")
    ap.add_argument("--name", default="profile", help="profile file basename (e.g. alex)")
    ap.add_argument("--force", action="store_true", help="scaffold even if workspace exists")
    args = ap.parse_args()

    # Sanitize --name before it becomes a filename under profiles/ (prevents traversal).
    args.name = re.sub(r"[^A-Za-z0-9._-]", "", args.name) or "profile"

    preflight()  # deps must be present so the tracker init won't half-commit

    root = resolve_workspace_root(args.workspace)
    if not root:
        sys.exit("No workspace path given. Pass --workspace <dir> or set JOBSMITH_DIR.")
    root = os.path.abspath(root)

    if is_workspace(root) and not args.force:
        print(f"Workspace already exists at {root} — discover-and-reuse, nothing scaffolded.")
        print("Run the daily hunt instead. (Use --force only to re-drop missing templates.)")
        return

    print(f"Scaffolding workspace at {root}")
    dump = os.path.join(root, "dump")
    intake = os.path.join(profiles_dir(root), "_intake")
    placeholders = os.path.join(intake, "placeholders")
    for d in (profiles_dir(root), intake, placeholders, applications_dir(root),
              daily_dir(root), scripts_dir(root), dump):
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
    _write_if_absent(os.path.join(dump, "README.md"), DUMP_README, root, args.force)
    _write_if_absent(os.path.join(dump, "_manifest.csv"), MANIFEST_HEADER, root, args.force)
    _write_if_absent(os.path.join(intake, "CHANGELOG.md"), CHANGELOG_TEMPLATE, root, args.force)
    _write_if_absent(os.path.join(root, "WORKSPACE-MAP.md"),
                     WORKSPACE_MAP_TEMPLATE.format(
                         name=args.name,
                         # every other row puts the arrow at the same column; pad to match
                         # so a long name does not knock this one out of line
                         profile_line=f"{args.name}.md".ljust(26)),
                     root, args.force)

    # Initialise the tracker (idempotent).
    init = subprocess.run([sys.executable, os.path.join(HERE, "tracker.py"),
                           "init", "--root", applications_dir(root)],
                          capture_output=True, text=True)
    sys.stdout.write("  " + init.stdout)
    if init.returncode != 0:
        sys.stderr.write(init.stderr)
        sys.exit(init.returncode)

    print("\nSETUP COMPLETE — build your profile one of two ways:")
    print("  EASY (recommended): drop your CVs / LinkedIn export / certificates / notes into")
    print(f"    dump/  (see dump/README.md), then run INTAKE — the skill builds profiles/{args.name}.md for you.")
    print(f"  MANUAL: fill in profiles/{args.name}.md by hand. Put in everything true about you,")
    print("          not just what one CV would show — tailoring selects from it.")
    print("Then run the daily hunt. Stopping here so nothing runs against an empty profile.")


if __name__ == "__main__":
    main()
