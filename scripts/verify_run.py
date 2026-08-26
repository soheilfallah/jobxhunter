#!/usr/bin/env python3
"""Verify a daily hunt actually searched broadly, instead of taking one board's word for it.

The failure this exists to catch: a run queries a single connector, surfaces a dozen
roles, and the write-up reads exactly like a run that swept every board. Nothing in the
tracker distinguishes them, because the tracker only ever records what SURVIVED. This
reads the run's query log instead — what was asked, and of whom.

Reads   <workspace>/tasks/daily/<date>/queries.csv
Columns platform,lane,query,raw_hits,after_gate,new_vs_ledger,note

Fails a run that:
  - has no query log at all (the old silent-thin-run case)
  - hit fewer than --min-platforms distinct sources
  - skipped a lane declared in JOB-LANES.md without saying why in `note`
  - logged a platform that returned nothing, with no note explaining it
  - logged a platform whose credentials were rejected (`auth:` note) and never re-swept;
    such a platform is also dropped from the platform floor

Usage:
  python verify_run.py --workspace <dir> [--date YYYY-MM-DD] [--min-platforms 4]
  python verify_run.py --self-check
"""
import argparse
import csv
import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import resolve_workspace_root, enable_utf8_io  # noqa: E402
enable_utf8_io()

COLUMNS = ["platform", "lane", "query", "raw_hits", "after_gate", "new_vs_ledger", "note"]


def declared_lanes(workspace):
    """Lane names from the workspace's JOB-LANES.md (### `lane-name` headings).

    Absent file -> empty set -> the lane check is skipped rather than guessed at, so
    this stays usable for a workspace that never defined lanes.
    """
    path = os.path.join(workspace, "JOB-LANES.md")
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8") as fh:
        return set(re.findall(r"^#{3}\s+`([a-z0-9-]+)`", fh.read(), re.M))


def read_log(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if (r.get("platform") or "").strip()]
    for r in rows:
        for k in ("raw_hits", "after_gate", "new_vs_ledger"):
            try:
                r[k] = int(str(r.get(k) or 0).strip() or 0)
            except ValueError:
                r[k] = 0
    return rows


def verify(workspace, date, min_platforms, skip_lanes=()):
    """-> (list_of_failures, list_of_warnings, summary_lines)"""
    log = os.path.join(workspace, "tasks", "daily", date, "queries.csv")
    if not os.path.isfile(log):
        return ([f"no query log at {log} — a run without one cannot be shown to be thorough"],
                [], [])

    rows = read_log(log)
    fails, warns, out = [], [], []
    if not rows:
        return ([f"{log} is empty"], [], [])

    by_platform, by_lane = {}, {}
    for r in rows:
        by_platform.setdefault(r["platform"].strip(), []).append(r)
        lane = (r.get("lane") or "").strip()
        if lane:
            by_lane.setdefault(lane, []).append(r)

    # AUTH FAILURES (23 Aug 2026). A row whose note starts "auth:" is a query that never ran
    # because the key pair was rejected. A platform with no other rows sourced nothing and
    # cannot count toward the floor; and any auth row not recovered by a later non-auth row
    # for the same lane+query (i.e. not re-swept after re-keying) fails the run by name, so a
    # dead key can never read as a fifth connector.
    def _auth(r):
        return (r.get("note") or "").startswith("auth:")
    unrecovered = {}
    for name, rs in by_platform.items():
        ran = {(r.get("lane") or "", r.get("query") or "") for r in rs if not _auth(r)}
        unrecovered[name] = sum(1 for r in rs if _auth(r)
                                and (r.get("lane") or "", r.get("query") or "") not in ran)
    live = {name for name, rs in by_platform.items() if any(not _auth(r) for r in rs)}
    if len(live) < min_platforms:
        fails.append(f"only {len(live)} platform(s) actually sourced "
                     f"({', '.join(sorted(live))}); floor is {min_platforms}")
    for name, n in sorted(unrecovered.items()):
        if n:
            fails.append(f"platform '{name}' rejected the credentials (HTTP 401) on {n} "
                         f"quer(y/ies) never re-run — re-key it, then re-sweep that source")

    for name, rs in sorted(by_platform.items()):
        if sum(r["raw_hits"] for r in rs) == 0 and not any((r.get("note") or "").strip() for r in rs):
            fails.append(f"platform '{name}' returned 0 hits across {len(rs)} quer(y/ies) "
                         f"and no `note` says why (dead key? blocked? genuinely empty?)")

    # A lane is COVERED only if at least one of its queries actually ran. From 22 Aug 2026 the
    # sweep writes a queries.csv row for queries it skipped (emergency brake) or never reached
    # (the source hit its quota) — which it must, or the hole is invisible. But that created a
    # new false pass: a lane whose every query was skipped now appears in `by_lane` and would
    # read as swept. A row that says "skipped" is not a row that says "searched".
    covered = {ln for ln, rs in by_lane.items()
               if any(r["raw_hits"] or not (r.get("note") or "").startswith(("skipped", "quota", "auth"))
                      for r in rs)}
    lanes = declared_lanes(workspace) - set(skip_lanes)
    missing = sorted(lanes - covered)
    if missing:
        fails.append(f"lane(s) never queried: {', '.join(missing)}")

    raw = sum(r["raw_hits"] for r in rows)
    gated = sum(r["after_gate"] for r in rows)
    fresh = sum(r["new_vs_ledger"] for r in rows)
    if raw and fresh == raw:
        warns.append("new_vs_ledger == raw_hits: nothing was deduped or gated, which usually "
                     "means the funnel columns were filled in from memory, not measured")
    if gated > raw:
        fails.append(f"after_gate ({gated}) exceeds raw_hits ({raw}) — the funnel is impossible")

    out.append(f"queries      {len(rows)}")
    out.append(f"platforms    {len(by_platform)}  ({', '.join(sorted(by_platform))})")
    out.append(f"lanes        {len(by_lane)}" + (f" of {len(lanes)} declared" if lanes else ""))
    out.append(f"funnel       {raw} raw -> {gated} past the gate -> {fresh} new vs ledger")
    return fails, warns, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace")
    ap.add_argument("--date", default=None, help="defaults to today")
    ap.add_argument("--min-platforms", type=int, default=4)
    ap.add_argument("--skip-lanes", default="",
                    help="comma-separated lanes that are filing tags rather than searchable lanes "
                         "(e.g. cold-outreach) and so are exempt from the lane-coverage check")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()

    if args.self_check:
        return self_check()

    ws = resolve_workspace_root(args.workspace)
    if not ws:
        print("no workspace resolved", file=sys.stderr)
        return 1
    date = args.date or datetime.date.today().isoformat()

    skip = [s.strip() for s in args.skip_lanes.split(",") if s.strip()]
    fails, warns, summary = verify(ws, date, args.min_platforms, skip)
    print(f"--- hunt verification {date} ---")
    for line in summary:
        print("  " + line)
    for w in warns:
        print(f"  WARN  {w}")
    for f in fails:
        print(f"  FAIL  {f}")
    print("PASS — the run can be shown to be broad" if not fails
          else f"FAIL — {len(fails)} problem(s); this run is thin, do not write it up as thorough")
    return 1 if fails else 0


def self_check():
    import tempfile
    import shutil
    tmp = tempfile.mkdtemp()
    try:
        d = os.path.join(tmp, "tasks", "daily", "2026-01-01")
        os.makedirs(d)
        with open(os.path.join(tmp, "JOB-LANES.md"), "w", encoding="utf-8") as fh:
            fh.write("### `pa-ea`\n### `research`\n")

        def write(rows):
            with open(os.path.join(d, "queries.csv"), "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=COLUMNS)
                w.writeheader()
                w.writerows(rows)

        # the exact 10 Aug shape: two platforms, one lane -> must fail on both counts
        write([{"platform": "Adzuna", "lane": "pa-ea", "query": "EA", "raw_hits": 12,
                "after_gate": 6, "new_vs_ledger": 5, "note": ""},
               {"platform": "Reed", "lane": "pa-ea", "query": "EA", "raw_hits": 1,
                "after_gate": 1, "new_vs_ledger": 1, "note": ""}])
        fails, _, _ = verify(tmp, "2026-01-01", 4)
        assert any("only 2 platform" in f for f in fails), fails
        assert any("research" in f for f in fails), fails

        # broad run, every lane covered -> passes
        write([{"platform": p, "lane": ln, "query": "q", "raw_hits": 9, "after_gate": 4,
                "new_vs_ledger": 2, "note": ""}
               for p in ("Adzuna", "Reed", "Indeed", "jobs.ac.uk") for ln in ("pa-ea", "research")])
        fails, _, _ = verify(tmp, "2026-01-01", 4)
        assert not fails, fails

        # a platform that returned nothing and never said why
        write([{"platform": p, "lane": ln, "query": "q",
                "raw_hits": 0 if p == "Indeed" else 9, "after_gate": 0 if p == "Indeed" else 4,
                "new_vs_ledger": 0 if p == "Indeed" else 2, "note": ""}
               for p in ("Adzuna", "Reed", "Indeed", "jobs.ac.uk") for ln in ("pa-ea", "research")])
        fails, _, _ = verify(tmp, "2026-01-01", 4)
        assert any("'Indeed' returned 0 hits" in f for f in fails), fails

        # ... but an explained zero is fine
        write([{"platform": p, "lane": ln, "query": "q",
                "raw_hits": 0 if p == "Indeed" else 9, "after_gate": 0 if p == "Indeed" else 4,
                "new_vs_ledger": 0 if p == "Indeed" else 2,
                "note": "403 credits exhausted" if p == "Indeed" else ""}
               for p in ("Adzuna", "Reed", "Indeed", "jobs.ac.uk") for ln in ("pa-ea", "research")])
        fails, _, _ = verify(tmp, "2026-01-01", 4)
        assert not fails, fails

        AUTH = "auth: 401 — credentials rejected"

        def arow(p, ln, auth=False):
            return {"platform": p, "lane": ln, "query": "q", "raw_hits": 0 if auth else 9,
                    "after_gate": 0 if auth else 4, "new_vs_ledger": 0 if auth else 2,
                    "note": AUTH if auth else ""}
        # a 401-dead platform: the floor loses it AND the run fails by name (23 Aug 2026)
        write([arow(p, ln, auth=(p == "Adzuna"))
               for p in ("Adzuna", "Reed", "Indeed", "jobs.ac.uk")
               for ln in ("pa-ea", "research")])
        fails, _, _ = verify(tmp, "2026-01-01", 4)
        assert any("only 3 platform(s) actually sourced" in f for f in fails), fails
        assert any("'Adzuna' rejected the credentials (HTTP 401) on 2" in f for f in fails), fails
        assert not any("returned 0 hits" in f for f in fails), fails  # the auth note explains it
        # five platforms, one dead: the floor holds, the auth failure alone still fails the run
        write([arow(p, ln, auth=(p == "Adzuna"))
               for p in ("Adzuna", "Reed", "Indeed", "jobs.ac.uk", "NHS Jobs")
               for ln in ("pa-ea", "research")])
        fails, _, _ = verify(tmp, "2026-01-01", 4)
        assert len(fails) == 1 and "rejected the credentials" in fails[0], fails
        # re-keyed and re-swept: the auth rows stay in the log, later real rows recover them
        write([arow(p, ln, auth=(p == "Adzuna"))
               for p in ("Adzuna", "Reed", "Indeed", "jobs.ac.uk")
               for ln in ("pa-ea", "research")]
              + [arow("Adzuna", ln) for ln in ("pa-ea", "research")])
        fails, _, _ = verify(tmp, "2026-01-01", 4)
        assert not fails, fails
        # a lane whose only row is an auth failure was never searched
        write([arow(p, "pa-ea") for p in ("Adzuna", "Reed", "Indeed", "jobs.ac.uk")]
              + [arow("Totaljobs", "research", auth=True)])
        fails, _, _ = verify(tmp, "2026-01-01", 4)
        assert any("never queried: research" in f for f in fails), fails

        # a lane exempted as a filing tag is not demanded
        write([{"platform": p, "lane": "pa-ea", "query": "q", "raw_hits": 9, "after_gate": 4,
                "new_vs_ledger": 2, "note": ""}
               for p in ("Adzuna", "Reed", "Indeed", "jobs.ac.uk")])
        fails, _, _ = verify(tmp, "2026-01-01", 4)
        assert any("research" in f for f in fails), fails
        fails, _, _ = verify(tmp, "2026-01-01", 4, ["research"])
        assert not fails, fails

        # missing log entirely
        os.remove(os.path.join(d, "queries.csv"))
        fails, _, _ = verify(tmp, "2026-01-01", 4)
        assert any("no query log" in f for f in fails), fails

        print("verify_run self-check OK")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
