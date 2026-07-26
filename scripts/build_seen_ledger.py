#!/usr/bin/env python3
"""Build the de-duplication ledger for the daily hunt.

Derives <workspace>/applications/daily-hunt/seen-jobs.csv from the tracker, keyed
on a CANONICAL job key (normalised job ref or URL), NEVER a folder-name slug. The
daily hunt reads this to skip roles it has already seen, and regenerates it at the
start and end of every run.

Reads the tracker's CSV mirror (applications/tracker.csv) so it needs no openpyxl.

Canonical key: prefer the listing `link` (scheme/host/query stripped, lowercased);
fall back to the normalised folder_path only when there is no link.

Usage:
  python build_seen_ledger.py --workspace <dir>
  python build_seen_ledger.py --applications <apps_dir>   # explicit
"""
import argparse
import csv
import os
import sys
import datetime
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import resolve_workspace_root, applications_dir, daily_dir, safe_cell  # noqa: E402

LEDGER_COLUMNS = ["job_key", "status", "category", "company", "role", "link",
                  "folder_path", "last_seen"]


def canonical_key(link, folder_path=""):
    """Stable key for a job. URL: drop scheme, leading www., query, fragment,
    trailing slash; lowercase. No link -> normalised folder_path (last resort)."""
    link = (link or "").strip()
    if link:
        s = urlsplit(link if "://" in link else "http://" + link)
        host = (s.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        path = (s.path or "").rstrip("/").lower()
        return f"{host}{path}" or link.lower()
    fp = (folder_path or "").strip().replace("\\", "/").rstrip("/").lower()
    return f"folder:{fp}" if fp else ""


def main():
    ap = argparse.ArgumentParser(description="Build the daily-hunt dedupe ledger.")
    ap.add_argument("--workspace", help="workspace root (else JOBSMITH_DIR / discovery)")
    ap.add_argument("--applications", help="explicit applications dir (overrides workspace)")
    ap.add_argument("--today", help="date stamp for last_seen (YYYY-MM-DD); default today")
    args = ap.parse_args()

    if args.applications:
        apps = os.path.abspath(args.applications)
        root = os.path.dirname(apps)
    else:
        root = resolve_workspace_root(args.workspace)
        if not root:
            sys.exit("No workspace resolved. Pass --workspace or --applications.")
        apps = applications_dir(root)

    tracker_csv = os.path.join(apps, "tracker.csv")
    dh = daily_dir(root)
    os.makedirs(dh, exist_ok=True)
    out = os.path.join(dh, "seen-jobs.csv")
    today = args.today or datetime.date.today().isoformat()

    if not os.path.exists(tracker_csv):
        # No tracker yet -> empty ledger (header only), so the hunt has a clean slate.
        with open(out, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(LEDGER_COLUMNS)
        print(f"No tracker.csv at {tracker_csv} — wrote empty ledger {out}")
        return

    seen = {}
    with open(tracker_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = canonical_key(row.get("link", ""), row.get("folder_path", ""))
            if not key:
                continue
            # keep the row we last logged for this key (later rows overwrite = latest state)
            seen[key] = {
                "job_key": key,
                "status": row.get("status", ""),
                "category": row.get("category", ""),
                "company": row.get("company", ""),
                "role": row.get("role", ""),
                "link": row.get("link", ""),
                "folder_path": row.get("folder_path", ""),
                "last_seen": today,
            }

    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)
        w.writeheader()
        for rec in seen.values():
            w.writerow({k: safe_cell(v) for k, v in rec.items()})

    print(f"Ledger rebuilt: {out} ({len(seen)} unique job keys from {tracker_csv})")


if __name__ == "__main__":
    main()
