#!/usr/bin/env python3
"""Track which fetched adverts have actually been JUDGED, so "I finished triage" stops being an opinion.

WHY THIS EXISTS. On 22 Aug 2026 the sweep enumerated 126,581 adverts and produced 8,078 ranked
survivors. 134 were fetched. **Seven applications came out**, and the user's response was the
correct one: "from all these you found 6 jobs?"

The sourcing was not the problem. The reading was. Of 134 fetched adverts, four lanes were triaged
properly and the rest — agri-food, av-media, security-premium, wildcard and the three `additional`
lanes, 82 adverts — were skimmed. The best fit of the entire run (an AI Enablement Lead role naming
the exact platform the user works in daily) was sitting in `wildcard`, already fetched and paid
for, and was found only because the user pushed back.

Nothing in the pipeline could catch that, because "have I read everything?" lived only in the
agent's head. This file moves it onto disk:

  * every fetched advert gets a row, `pending` until a verdict is recorded
  * `--next` hands them out ROUND-ROBIN BY LANE, so breadth comes before depth and no lane can be
    starved by whichever one the agent finds most interesting
  * `--status` exits NON-ZERO while anything is pending, which is what makes it usable as the
    completion gate of a `/ralph-loop` — a loop whose exit condition is the agent's own judgement
    is just the agent stopping when it feels finished, which is the failure being fixed

Verdicts are `applied` or `skipped`, and a skip REQUIRES a reason. That is the honest part: it is
completely fine to skip 120 of 134 adverts, and it is not fine to leave them unlooked-at while
reporting the day as done.

Usage:
  python triage.py --workspace <dir> [--date D] --init          # seed from jds/index.csv
  python triage.py --workspace <dir> [--date D] --next [--n 5]  # next pending, round-robin by lane
  python triage.py --workspace <dir> [--date D] --mark <url> --verdict applied --reason "..."
  python triage.py --workspace <dir> [--date D] --status        # exits 1 while any remain
  python triage.py --self-check
"""
import argparse
import csv
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import resolve_workspace_root, enable_utf8_io  # noqa: E402
enable_utf8_io()

COLUMNS = ["rank", "lane", "title", "company", "location", "salary", "url", "file",
           "verdict", "reason", "decided"]
VERDICTS = ("pending", "applied", "skipped")


def day_dir(ws, date):
    return os.path.join(ws, "tasks", "daily", date)


def paths(ws, date):
    """The day folder, or its _work/ subfolder once daily_bundle.py has tidied."""
    day = day_dir(ws, date)
    for base in (day, os.path.join(day, "_work")):
        idx = os.path.join(base, "jds", "index.csv")
        if os.path.isfile(idx):
            return base, idx
    return day, os.path.join(day, "jds", "index.csv")


def load(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def save(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _salary(r):
    for f in ("salary_max", "salary_min"):
        try:
            v = float(r.get(f) or 0)
        except (TypeError, ValueError):
            v = 0
        if v:
            return f"{v:,.0f}"
    return ""


def init(idx_rows, existing):
    """Seed a row per FETCHED advert, preserving any verdict already recorded.

    Only `status == ok` rows: an advert nobody could read is a fetch problem, not a triage
    decision, and putting it here would let an unreadable page block the completion gate forever.
    """
    keep = {r["url"]: r for r in existing}
    out = []
    for r in idx_rows:
        if r.get("status") != "ok":
            continue
        prior = keep.get(r.get("url", ""), {})
        out.append({
            "rank": r.get("rank", ""), "lane": r.get("true_lane") or "unmatched",
            "title": r.get("title", ""), "company": r.get("company", ""),
            "location": r.get("location", ""), "salary": _salary(r),
            "url": r.get("url", ""), "file": r.get("file", ""),
            "verdict": prior.get("verdict") or "pending",
            "reason": prior.get("reason", ""), "decided": prior.get("decided", ""),
        })
    return out


def next_up(rows, n=1):
    """Pending adverts, ROUND-ROBIN ACROSS LANES.

    Straight rank order is what produced the failure: the agent works down from rank 1, the
    highest-scoring lane dominates the top, and it stops before reaching the lanes it finds less
    interesting. Round-robin means lane 13 gets its first advert before lane 1 gets its second.
    """
    by_lane = {}
    for r in rows:
        if r.get("verdict") == "pending":
            by_lane.setdefault(r.get("lane") or "unmatched", []).append(r)
    for q in by_lane.values():
        q.sort(key=lambda r: int(r.get("rank") or 10 ** 6))
    out, tier = [], 0
    while len(out) < n:
        got = [q[tier] for q in by_lane.values() if len(q) > tier]
        if not got:
            break
        out.extend(got)
        tier += 1
    return out[:n]


def mark(rows, url, verdict, reason):
    """-> (rows, hit). A skip without a reason is refused: unexplained skips are how a thin day
    reads like a thorough one afterwards."""
    if verdict not in ("applied", "skipped"):
        raise SystemExit(f"--verdict must be applied or skipped, got {verdict!r}")
    if verdict == "skipped" and not (reason or "").strip():
        raise SystemExit("a skip needs --reason: it is fine to skip most adverts, "
                         "not fine to leave no record of why")
    hit = 0
    for r in rows:
        if r.get("url") == url:
            r["verdict"] = verdict
            r["reason"] = reason or ""
            r["decided"] = datetime.date.today().isoformat()
            hit += 1
    return rows, hit


def status(rows):
    """-> (pending, applied, skipped, per-lane dict)."""
    lanes = {}
    for r in rows:
        d = lanes.setdefault(r.get("lane") or "unmatched", {"pending": 0, "applied": 0, "skipped": 0})
        d[r.get("verdict", "pending")] = d.get(r.get("verdict", "pending"), 0) + 1
    tot = {k: sum(d.get(k, 0) for d in lanes.values()) for k in ("pending", "applied", "skipped")}
    return tot["pending"], tot["applied"], tot["skipped"], lanes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace")
    ap.add_argument("--date", default=None)
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--next", action="store_true")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--mark", default=None, metavar="URL")
    ap.add_argument("--verdict", default=None, choices=("applied", "skipped"))
    ap.add_argument("--reason", default="")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()

    if args.self_check:
        return self_check()

    ws = resolve_workspace_root(args.workspace)
    if not ws:
        raise SystemExit("no workspace resolved")
    date = args.date or datetime.date.today().isoformat()
    base, idx_path = paths(ws, date)
    ledger = os.path.join(base, "triage.csv")
    rows = load(ledger)

    if args.init or not rows:
        idx_rows = load(idx_path)
        if not idx_rows:
            raise SystemExit(f"no fetched adverts at {idx_path} — run fetch_jds first")
        rows = init(idx_rows, rows)
        save(ledger, rows)
        print(f"triage ledger: {len(rows)} fetched advert(s) -> {ledger}")

    if args.mark:
        rows, hit = mark(rows, args.mark, args.verdict, args.reason)
        if not hit:
            raise SystemExit(f"no advert with url {args.mark}")
        save(ledger, rows)
        print(f"marked {hit} row(s) {args.verdict}")

    if args.next:
        sel = next_up(rows, args.n)
        if not sel:
            print("nothing pending — every fetched advert has a verdict")
            return 0
        for r in sel:
            pay = f"£{r['salary']}" if r["salary"] else "n/d"
            print(f"\n--- {r['lane']} · rank {r['rank']} · {pay} · {r['location']}")
            print(f"    {r['title']} — {r['company']}")
            print(f"    advert: {os.path.join(base, 'jds', r['file'])}")
            print(f"    url:    {r['url']}")
        return 0

    if args.status or not (args.mark or args.next):
        pend, app, skip, lanes = status(rows)
        print(f"triage {date}: {app} applied · {skip} skipped · {pend} PENDING  (of {len(rows)})")
        for lane, d in sorted(lanes.items(), key=lambda x: -x[1]["pending"]):
            flag = "  <-- unread" if d["pending"] else ""
            print(f"  {lane:<16} pending {d['pending']:>3}   applied {d['applied']:>2}   "
                  f"skipped {d['skipped']:>3}{flag}")
        if pend:
            print(f"\nNOT FINISHED: {pend} fetched advert(s) have never been judged. "
                  f"Every one of them was already paid for.")
            return 1
        print("\nAll fetched adverts judged.")
        return 0
    return 0


def self_check():
    idx = [
        {"status": "ok", "rank": "1", "true_lane": "data-ai", "title": "A", "company": "C1",
         "location": "London", "salary_max": "60000", "url": "u1", "file": "f1.md"},
        {"status": "ok", "rank": "2", "true_lane": "data-ai", "title": "B", "company": "C2",
         "location": "London", "salary_max": "", "url": "u2", "file": "f2.md"},
        {"status": "ok", "rank": "9", "true_lane": "wildcard", "title": "C", "company": "C3",
         "location": "London", "salary_max": "40000", "url": "u3", "file": "f3.md"},
        # an advert nobody could read is a FETCH problem, not a triage decision — it must not be
        # allowed into the ledger, or it blocks the completion gate for ever
        {"status": "needs-scraper", "rank": "3", "true_lane": "data-ai", "title": "D",
         "company": "C4", "url": "u4", "file": "f4.md"},
    ]
    rows = init(idx, [])
    assert len(rows) == 3 and all(r["verdict"] == "pending" for r in rows)
    assert "u4" not in {r["url"] for r in rows}

    # ROUND-ROBIN: the second advert handed out must be the OTHER lane, not data-ai rank 2.
    # Rank order is exactly what starved wildcard on 22 Aug and hid the best role of the run.
    first_two = next_up(rows, 2)
    assert [r["url"] for r in first_two] == ["u1", "u3"], [r["url"] for r in first_two]
    assert [r["url"] for r in next_up(rows, 3)] == ["u1", "u3", "u2"]
    assert len(next_up(rows, 99)) == 3            # never invents work

    # a skip REQUIRES a reason
    try:
        mark(rows, "u1", "skipped", "")
        raise AssertionError("expected a skip with no reason to be refused")
    except SystemExit:
        pass
    rows, hit = mark(rows, "u1", "skipped", "construction commercial role, not defensible")
    assert hit == 1
    rows, _ = mark(rows, "u3", "applied", "")     # an APPLY needs no reason
    pend, app, skip, lanes = status(rows)
    assert (pend, app, skip) == (1, 1, 1), (pend, app, skip)
    assert lanes["data-ai"]["pending"] == 1

    # marking is idempotent and re-init preserves decisions — the loop re-runs --init every
    # iteration, and losing verdicts would make it grind for ever
    again = init(idx, rows)
    assert {r["url"]: r["verdict"] for r in again} == {"u1": "skipped", "u2": "pending",
                                                      "u3": "applied"}
    assert next_up(again, 5)[0]["url"] == "u2"

    # the completion gate: pending > 0 must be a NON-ZERO exit, or a ralph loop cannot use it
    assert status(again)[0] == 1
    done, _ = mark(again, "u2", "skipped", "too senior")
    assert status(done)[0] == 0

    print("triage self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
