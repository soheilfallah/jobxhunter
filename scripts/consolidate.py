#!/usr/bin/env python3
"""Merge a day's per-source sweeps into one ranked shortlist.

Each sweep dedupes inside itself, but nothing dedupes ACROSS sources — and one advert
routinely appears on Reed, Adzuna and jobs.ac.uk at once, which is the long-standing
"cross-board duplicates don't self-dedupe" defect at four times the scale. The seen-jobs
ledger can't help: it keys on URL, and the same role carries a different URL per board.

Also re-applies the L1 gate. Verdicts written during a sweep reflect whatever the gate
looked like at the time, so a gate fix (e.g. distrusting typo'd salary ceilings) only
reaches already-swept rows by rescoring here.

Reads   <workspace>/tasks/daily/<date>/candidates.csv   (every row, every source)
Writes  <workspace>/tasks/daily/<date>/shortlist.csv    (unique survivors, best first)

Ranking is deliberately dumb: salary desc, then recency. It orders what survived; it does
NOT judge relevance. A high-paying role matched only because a keyword appeared in its
description will still sort to the top — the title-knockout pass is a separate step.

Usage:
  python consolidate.py --workspace <dir> [--date YYYY-MM-DD] [--min-salary 35000]
  python consolidate.py --self-check
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
from build_seen_ledger import canonical_key  # noqa: E402
from harvest import gate, load_seen  # noqa: E402
enable_utf8_io()

SHORTLIST_COLUMNS = ["rank", "source", "lane", "query", "title", "company", "location",
                     "salary_min", "salary_max", "posted", "verdict", "also_on", "url"]

# Boards pad titles; the same role reads differently per board. Strip the noise before
# comparing, or cross-board dedupe silently misses most of what it should catch.
NOISE = re.compile(r"\b(?:urgent|immediate start|new|hot job|apply now|full[- ]time|"
                   r"part[- ]time|permanent|temporary|contract|fte|remote|hybrid|"
                   r"x\d+ posts?|\d+ month[s]?|ftc|maternity cover)\b", re.I)


def norm_role(company, title):
    c = re.sub(r"\W+", " ", (company or "").lower()).strip()
    c = re.sub(r"\b(ltd|limited|llp|plc|group|recruitment|recruiting|consultancy|"
               r"consulting|associates|partners|solutions|services)\b", "", c).strip()
    t = NOISE.sub(" ", (title or "").lower())
    t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"\W+", " ", t).strip()
    return f"{c}|{t}"


# Verdicts the sweep reached using information consolidate no longer has. Recency was
# judged against the sweep's window, and the title layer against that sweep's term list;
# re-gating from scratch here silently RESURRECTS everything they dropped.
STICKY_DROPS = ("drop:older-than", "drop:title-mismatch")


def salary_key(row):
    # A ceiling the gate flagged as a typo must not decide rank — that is exactly how a
    # £1.2m "Data Protection Officer" reached the top of the list. Judge it on the floor.
    if (row.get("verdict") or "").startswith("keep:salary-suspect"):
        try:
            return float(row.get("salary_min") or 0)
        except (TypeError, ValueError):
            return 0.0
    for f in ("salary_max", "salary_min"):
        try:
            v = float(row.get(f) or 0)
        except (TypeError, ValueError):
            v = 0
        if v:
            return v
    return 0.0


def posted_key(row):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime((row.get("posted") or "").strip(), fmt).date()
        except ValueError:
            continue
    return datetime.date(1900, 1, 1)


def consolidate(rows, min_salary, today, seen):
    """-> (shortlist, stats). One entry per distinct role; `also_on` names the other boards."""
    survivors, by_role = [], {}
    stats = {"read": len(rows), "gated_out": 0, "cross_source_dupes": 0}

    for r in rows:
        prev = r.get("verdict") or ""
        if prev.startswith(STICKY_DROPS):
            stats["gated_out"] += 1
            continue
        v = gate(r, min_salary, None, today, seen)   # recency/title already decided, see above
        r["verdict"] = v
        if not v.startswith("keep"):
            stats["gated_out"] += 1
            continue
        key = norm_role(r.get("company"), r.get("title"))
        prior = by_role.get(key)
        if prior is None:
            by_role[key] = r
            r["also_on"] = ""
            survivors.append(r)
            continue
        stats["cross_source_dupes"] += 1
        # Keep whichever listing carries the most information, and remember the rest.
        others = {s for s in (prior.get("also_on") or "").split(",") if s}
        others.add(r.get("source", ""))
        prior["also_on"] = ",".join(sorted(o for o in others if o and o != prior.get("source")))
        if salary_key(r) > salary_key(prior):
            # Take the VERDICT with the figures, never the figures alone. The verdict is
            # what records how far the figure can be trusted, so importing a number
            # without it launders a distrusted salary into a trusted row: on 15 Aug a
            # `keep:salary-suspect` £312,000 was copied onto its duplicate, which was
            # flagged `keep:salary-undisclosed`, and the laundered row then ranked #1
            # ahead of every real salary because nothing downstream knew to doubt it.
            for f in ("salary_min", "salary_max", "verdict"):
                prior[f] = r.get(f)

    survivors.sort(key=lambda r: (-salary_key(r), -posted_key(r).toordinal()))
    for i, r in enumerate(survivors, 1):
        r["rank"] = i
    stats["shortlisted"] = len(survivors)
    return survivors, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace")
    ap.add_argument("--date", default=None)
    ap.add_argument("--min-salary", type=int, default=0,
                    help="0 = no floor (default). The gate is still re-run here, because it "
                         "also re-labels salary plausibility and re-applies the ledger; it "
                         "just no longer drops anything on pay.")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()

    if args.self_check:
        return self_check()

    ws = resolve_workspace_root(args.workspace)
    if not ws:
        raise SystemExit("no workspace resolved")
    date = args.date or datetime.date.today().isoformat()
    day = os.path.join(ws, "tasks", "daily", date)
    src = os.path.join(day, "candidates.csv")
    if not os.path.isfile(src):
        raise SystemExit(f"no candidates at {src} — run sweep.py first")

    with open(src, encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if (r.get("title") or "").strip()]

    shortlist, stats = consolidate(rows, args.min_salary, datetime.date.today(), load_seen(ws))
    out = os.path.join(day, "shortlist.csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SHORTLIST_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(shortlist)

    print(f"consolidated {date}")
    print(f"  rows read            {stats['read']:,}")
    print(f"  gated out (rescored) {stats['gated_out']:,}")
    print(f"  cross-source dupes   {stats['cross_source_dupes']:,}")
    print(f"  SHORTLIST            {stats['shortlisted']:,}")
    print(f"  -> {out}")
    print("  NOTE: ranked by salary only. Relevance is NOT judged here — a role matched on a "
          "description keyword still sorts high. Run the title-knockout pass before tailoring.")
    return 0


def self_check():
    today = datetime.date(2026, 8, 14)

    # cross-board: same role, three boards, padded titles and decorated company names
    rows = [
        {"source": "reed", "company": "Tiger Recruitment Ltd", "title": "EA to Founder (Permanent)",
         "salary_min": 90000, "salary_max": 100000, "posted": "2026-08-13", "url": "u1"},
        {"source": "adzuna", "company": "Tiger Recruitment", "title": "EA to Founder - Urgent",
         "salary_min": None, "salary_max": None, "posted": "2026-08-13", "url": "u2"},
        {"source": "jobsacuk", "company": "Tiger Recruitment Limited", "title": "EA to Founder",
         "salary_min": 95000, "salary_max": 110000, "posted": "2026-08-12", "url": "u3"},
        {"source": "reed", "company": "Other Co", "title": "Data Analyst",
         "salary_min": 45000, "salary_max": 50000, "posted": "2026-08-14", "url": "u4"},
        {"source": "reed", "company": "Low Pay Co", "title": "Admin",
         "salary_min": 20000, "salary_max": 22000, "posted": "2026-08-14", "url": "u5"},
    ]
    short, stats = consolidate([dict(r) for r in rows], 35000, today, set())
    assert stats["cross_source_dupes"] == 2, stats
    assert stats["gated_out"] == 1, stats            # the £22k role
    assert stats["shortlisted"] == 2, stats
    top = short[0]
    assert top["company"] == "Tiger Recruitment Ltd", top
    assert float(top["salary_max"]) == 110000, top   # best figure across the duplicates wins
    assert set(top["also_on"].split(",")) == {"adzuna", "jobsacuk"}, top
    assert short[1]["title"] == "Data Analyst"

    assert norm_role("Tiger Recruitment Ltd", "EA to Founder (Permanent)") == \
           norm_role("Tiger Recruitment", "EA to Founder - Urgent")
    assert norm_role("A Ltd", "Data Analyst") != norm_role("B Ltd", "Data Analyst")
    # a sweep-stage recency/title drop must NOT come back to life in the merge
    stale = [{"source": "reed", "company": "qed legal", "title": "Data Protection Officer",
              "salary_min": 100000, "salary_max": 1200000, "posted": "2026-06-01",
              "url": "u9", "verdict": "drop:older-than-3d"}]
    _, st = consolidate([dict(r) for r in stale], 35000, today, set())
    assert st["shortlisted"] == 0 and st["gated_out"] == 1, st

    # a typo'd ceiling is kept but ranked on its floor, so it cannot head the list
    mixed, _ = consolidate([
        {"source": "reed", "company": "Typo Co", "title": "Officer", "salary_min": 40000,
         "salary_max": 1200000, "posted": "2026-08-14", "url": "a"},
        {"source": "reed", "company": "Real Co", "title": "Lead", "salary_min": 80000,
         "salary_max": 95000, "posted": "2026-08-14", "url": "b"}], 35000, today, set())
    assert mixed[0]["company"] == "Real Co", [m["company"] for m in mixed]
    assert mixed[1]["verdict"] == "keep:salary-suspect", mixed[1]

    assert posted_key({"posted": "13/08/2026"}) == datetime.date(2026, 8, 13)
    assert posted_key({"posted": ""}) == datetime.date(1900, 1, 1)
    assert salary_key({"salary_min": 40000, "salary_max": None}) == 40000.0
    assert salary_key({"salary_min": None, "salary_max": None}) == 0.0

    # a distrusted figure must carry its distrust across a duplicate merge
    hi = {"verdict": "keep:salary-suspect", "salary_min": 40000, "salary_max": 312000}
    lo = {"verdict": "keep:salary-undisclosed", "salary_min": 0, "salary_max": 0}
    assert salary_key(hi) == 40000          # suspect ranks on its floor
    assert salary_key(lo) == 0
    if salary_key(hi) > salary_key(lo):
        for f in ("salary_min", "salary_max", "verdict"):
            lo[f] = hi.get(f)
    assert lo["verdict"] == "keep:salary-suspect", lo
    assert salary_key(lo) == 40000, lo      # ...and still ranks on the floor after merging

    print("consolidate self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
