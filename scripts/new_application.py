#!/usr/bin/env python3
"""Create a per-job application folder and log a tracker row.

Folder layout created:
  <root>/<category>/<YYYY-MM-DD>_<company-slug>_<role-slug>/
      job-description.md   (from --jd / --jd-file, or a stub)
      notes.md             (stub: brain-dump, recruiter scorecard, delta go here)

Then calls tracker.add so the row exists (default status Drafted, or Skipped).
Category folders are created on demand.

Usage:
  python new_application.py --root <apps_dir> --category ai --company "Acme" \
      --role "ML Engineer" --date 2026-07-06 [--jd-file jd.txt] \
      [--location London] [--link URL] [--source Indeed] [--ats Greenhouse] \
      [--pay "£40k"] [--level L1] [--status Drafted] [--notes "..."]

Prints the created folder path on the last line (stdout) so the caller can use it.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import preflight, enable_utf8_io  # noqa: E402
enable_utf8_io()


def slug(text, maxlen=40):
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:maxlen] or "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="applications directory")
    ap.add_argument("--category", required=True)
    ap.add_argument("--company", required=True)
    ap.add_argument("--role", required=True)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--jd-file")
    ap.add_argument("--jd", help="JD text inline (alternative to --jd-file)")
    ap.add_argument("--location", default="")
    ap.add_argument("--link", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--ats", default="")
    ap.add_argument("--pay", default="")
    ap.add_argument("--level", default="")
    ap.add_argument("--status", default="Drafted")
    ap.add_argument("--notes", default="")
    ap.add_argument("--no-track", action="store_true", help="skip tracker row (folder only)")
    args = ap.parse_args()

    # Fail loudly BEFORE creating any folder if the tracker can't be written —
    # otherwise a missing openpyxl leaves an orphan folder with no tracker row.
    if not args.no_track:
        preflight([("openpyxl", "openpyxl", "tracker.xlsx read/write (tracker.py)")])

    # Sanitize --date before it's interpolated raw into the folder name (company/role
    # are slugged, date wasn't) — keep only digits + hyphens so a value like '../../x'
    # cannot traverse out of the workspace.
    args.date = re.sub(r"[^0-9-]", "", args.date)[:10] or datetime.date.today().isoformat()

    cat_dir = os.path.join(args.root, slug(args.category, 30))
    folder = os.path.join(cat_dir, f"{args.date}_{slug(args.company, 24)}_{slug(args.role, 30)}")
    os.makedirs(folder, exist_ok=True)

    jd_text = ""
    if args.jd_file and os.path.exists(args.jd_file):
        with open(args.jd_file, encoding="utf-8") as f:
            jd_text = f.read()
    elif args.jd:
        jd_text = args.jd
    jd_path = os.path.join(folder, "job-description.md")
    if not os.path.exists(jd_path):
        header = f"# {args.role} — {args.company}\n\n"
        meta = f"- Location: {args.location}\n- Link: {args.link}\n- Source: {args.source}\n- ATS: {args.ats}\n- Pay: {args.pay}\n\n---\n\n"
        with open(jd_path, "w", encoding="utf-8") as f:
            f.write(header + meta + (jd_text or "_JD text not captured yet._\n"))

    notes_path = os.path.join(folder, "notes.md")
    if not os.path.exists(notes_path):
        with open(notes_path, "w", encoding="utf-8") as f:
            f.write(
                f"# Notes — {args.company} / {args.role}\n\n"
                "## Brain-dump (for cover letter)\n\n_(your own words on why you want this role)_\n\n"
                "## Coverage matrix\n\n_(requirement -> evidence, strong/partial/adjacent-provisional/hard-gap)_\n\n"
                "## Pending confirmation (end-of-run yes/no batch)\n\n_(provisional skills added on a plausible basis — confirm before the CV is final; not accusations, just memory-jogs)_\n\n"
                "## Recruiter scorecard\n\n_(scores + fixes from the recruiter loop)_\n\n"
                "## L2 delta (if run)\n\n_(the gap between you and the alternative-world persona)\n\n"
                + (f"## Misc\n\n{args.notes}\n" if args.notes else "")
            )

    print(f"Folder: {folder}")

    if not args.no_track:
        data = {
            "logged_date": args.date, "category": args.category, "company": args.company,
            "role": args.role, "location": args.location, "link": args.link,
            "source": args.source, "ats_platform": args.ats, "pay": args.pay,
            "level_used": args.level, "status": args.status,
            "cv_path": os.path.join(folder, "CV.docx"),
            "cover_letter_path": "", "folder_path": folder, "notes": args.notes,
        }
        # Auto-init the tracker on first use so the row is never silently dropped
        # (tracker.py add refuses to run without an existing tracker; init is idempotent).
        if not os.path.exists(os.path.join(args.root, "tracker.xlsx")):
            init = subprocess.run(
                [sys.executable, os.path.join(HERE, "tracker.py"), "init", "--root", args.root],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            sys.stdout.write(init.stdout)
            if init.returncode != 0:
                sys.stderr.write(init.stderr)
                sys.exit(init.returncode)
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "tracker.py"), "add",
             "--root", args.root, "--data", json.dumps(data)],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        sys.stdout.write(r.stdout)
        if r.returncode != 0:
            sys.stderr.write(r.stderr)
            sys.exit(r.returncode)

    # last line = folder path, for programmatic capture
    print(folder)


if __name__ == "__main__":
    main()
