#!/usr/bin/env python3
"""Let the AGENT contribute rows from a source no script can reach.

Some boards have no harvester and cannot have one:

  Indeed              a claude.ai OAuth MCP connector. A Python script cannot call MCP.
                      Use indeed_to_rows.py to convert its markdown into the contract below.
  Civil Service Jobs  serves a bot interstitial ("Quick Check Needed") to a plain GET,
                      verified 22 Aug 2026. Needs a JS-rendering scraper, which is also MCP.

NOT LinkedIn. The Composio LinkedIn connection is live, but that toolkit has no job-search
tool — its 13 actions are posting, comments, company info, ad targeting and page analytics.
LinkedIn's public API does not expose job search outside Talent Solutions partners. Verified
22 Aug 2026; nothing routes through here from LinkedIn, now or later.

The agent CAN call those, so it does, and hands the rows over here. This exists rather than the
agent appending to candidates.csv directly, because a row has to go through `gate()`, the seen
ledger and a matching queries.csv row — miss any of those and consolidate double-counts, rank
sees an ungated row, and verify_run reads the platform as a dead source that returned nothing.

Downstream, an imported row is byte-identical to a harvested one.

Input: ONE json file, grouped by query, so a whole Indeed sweep is one invocation:

  [
    {"lane": "data-ai", "query": "data analyst", "total": 412, "note": "",
     "rows": [
       {"job_id": "abc123", "title": "Data Analyst", "company": "NHS Digital",
        "location": "London", "salary_min": 31049, "salary_max": 37796,
        "posted": "2026-08-21", "contract": "permanent",
        "url": "https://uk.indeed.com/viewjob?jk=abc123"}
     ]}
  ]

Rules, all defaulted rather than enforced, because the agent will omit fields:
  * any missing key becomes ""
  * `posted` is YYYY-MM-DD or dd/mm/yyyy (what harvest.parse_posted accepts). Anything else
    parses to None and simply never trips the recency drop.
  * `salary_min` / `salary_max` are NUMBERS or null — never "£31,049". A string with a currency
    symbol reaches float(), fails, and lands as "no salary", which is a silent wrong answer.
  * `total` defaults to len(rows); `note` defaults to "via MCP connector", so verify_run's
    "0 hits and no note says why" check is satisfied honestly rather than accidentally.

Usage:
  python import_rows.py --workspace <dir> --source indeed --platform Indeed --rows rows.json
  python import_rows.py --self-check
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import resolve_workspace_root, enable_utf8_io  # noqa: E402
from build_seen_ledger import canonical_key  # noqa: E402
from harvest import (CANDIDATE_COLUMNS, QUERY_COLUMNS, append_rows, gate,  # noqa: E402
                     load_seen)
enable_utf8_io()

ROW_KEYS = ("job_id", "title", "company", "location", "salary_min", "salary_max",
            "posted", "contract", "url")

DEFAULT_NOTE = "via MCP connector"


def _num(v):
    """-> float, or None. A currency string is None, never 0: 0 reads as 'advertised at zero'."""
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def clean_row(raw):
    out = {k: ("" if raw.get(k) is None else raw.get(k, "")) for k in ROW_KEYS}
    out["salary_min"] = _num(raw.get("salary_min"))
    out["salary_max"] = _num(raw.get("salary_max"))
    return out


def import_groups(groups, out_dir, source, platform, min_salary, max_days_old, today, seen):
    """-> (candidate rows written, query rows written, kept count)."""
    cand_rows, query_rows, kept_total = [], [], 0
    batch_ids, batch_roles = set(), set()
    for g in groups:
        lane = str(g.get("lane") or "")
        query = str(g.get("query") or "")
        rows = [clean_row(r) for r in (g.get("rows") or [])]
        for r in rows:
            v = gate(r, min_salary, max_days_old, today, seen)
            if v.startswith("keep"):
                # job_id OR the canonical URL, whichever exists. Indeed's MCP connector hands
                # back ids like "JOBSEARCH_523" that are a per-response counter, not a job
                # identifier — the same advert gets a different one in the next call, and two
                # different adverts can share one across sessions. Keying dedupe on that alone
                # would both miss real duplicates and, worse, merge unrelated roles.
                jid = str(r.get("job_id") or "") or canonical_key(r.get("url") or "")
                if jid and jid in batch_ids:
                    v = "drop:dup-in-sweep"
                else:
                    batch_ids.add(jid)
            r.update(source=source, lane=lane, query=query, verdict=v)
        kept = [r for r in rows if r["verdict"].startswith("keep")]
        fresh = [r for r in kept if canonical_key(r.get("url") or "") not in seen]
        kept_total += len(kept)
        cand_rows.extend(rows)
        query_rows.append({
            "platform": platform, "lane": lane, "query": query,
            "raw_hits": int(g.get("total") or len(rows)),
            "after_gate": len(kept), "new_vs_ledger": len(fresh),
            "note": str(g.get("note") or DEFAULT_NOTE)})
    if cand_rows:
        append_rows(os.path.join(out_dir, "candidates.csv"), CANDIDATE_COLUMNS, cand_rows)
    if query_rows:
        append_rows(os.path.join(out_dir, "queries.csv"), QUERY_COLUMNS, query_rows)
    return cand_rows, query_rows, kept_total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace")
    ap.add_argument("--source", help="e.g. indeed, civilservice, linkedin")
    ap.add_argument("--platform", default=None, help="display name; defaults to --source")
    ap.add_argument("--rows", help="path to the json file described above")
    ap.add_argument("--date", default=None)
    ap.add_argument("--min-salary", type=int, default=0)
    ap.add_argument("--max-days-old", type=int, default=3)
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()

    # Not `required=True` on --source/--rows: argparse would then reject --self-check on its
    # own, which is how a self-check quietly stops being runnable.
    if args.self_check:
        return self_check()
    missing = [f for f, v in (("--source", args.source), ("--rows", args.rows)) if not v]
    if missing:
        raise SystemExit(f"missing required argument(s): {', '.join(missing)}")

    ws = resolve_workspace_root(args.workspace)
    if not ws:
        raise SystemExit("no workspace resolved")
    date = args.date or datetime.date.today().isoformat()
    out_dir = os.path.join(ws, "tasks", "daily", date)
    os.makedirs(out_dir, exist_ok=True)

    with open(args.rows, encoding="utf-8") as fh:
        groups = json.load(fh)
    if isinstance(groups, dict):
        groups = [groups]

    platform = args.platform or args.source
    cand, queries, kept = import_groups(
        groups, out_dir, args.source, platform, args.min_salary, args.max_days_old,
        datetime.date.today(), load_seen(ws))

    print(f"{platform} import · {len(queries)} query group(s) · {len(cand)} row(s)")
    print(f"  past the gate  {kept:,}")
    print(f"  -> {os.path.join(out_dir, 'candidates.csv')}")
    return 0


def self_check():
    import tempfile
    import shutil
    tmp = tempfile.mkdtemp()
    try:
        today = datetime.date(2026, 8, 22)
        seen = set()
        groups = [{"lane": "data-ai", "query": "data analyst", "total": 412, "rows": [
            {"job_id": "1", "title": "Data Analyst", "company": "X",
             "url": "https://x.test/1", "salary_min": 30000, "salary_max": 35000,
             "posted": "2026-08-22"}]}]
        cand, queries, kept = import_groups(groups, tmp, "indeed", "Indeed", 0, 3, today, seen)

        # THE CONTRACT: an imported row must be indistinguishable downstream from a harvested
        # one, or consolidate/rank/verify quietly treat Indeed as a second class of source.
        assert set(cand[0]) >= set(CANDIDATE_COLUMNS), sorted(set(CANDIDATE_COLUMNS) - set(cand[0]))
        assert cand[0]["source"] == "indeed"
        # a GBP30k role is KEPT — there is no salary floor at 0
        assert cand[0]["verdict"] == "keep", cand[0]["verdict"]
        assert kept == 1

        # a queries.csv row must exist WITH a note, or verify_run reads Indeed's zero as an
        # unexplained dead platform and fails the whole run
        assert queries[0]["platform"] == "Indeed" and queries[0]["note"] == DEFAULT_NOTE
        assert queries[0]["raw_hits"] == 412 and queries[0]["after_gate"] == 1

        # the agent WILL omit fields. A missing key is empty, never a crash.
        c2, q2, _ = import_groups([{"lane": "x", "query": "y", "rows": [{"title": "T"}]}],
                                  tmp, "indeed", "Indeed", 0, 3, today, seen)
        assert c2[0]["company"] == "" and c2[0]["url"] == ""
        assert q2[0]["raw_hits"] == 1                 # total defaults to the row count

        # a currency STRING must read as "no salary", never as zero pay — float("£31,049")
        # raises, and swallowing that as 0 would label a real salary undisclosed... or worse,
        # drop it if a floor were ever reinstated.
        assert _num("£31,049") is None and _num("") is None and _num(None) is None
        assert _num("31049") == 31049.0 and _num(31049) == 31049.0
        c3, _, _ = import_groups([{"lane": "x", "query": "y", "rows": [
            {"title": "T", "salary_min": "£31,049"}]}], tmp, "indeed", "Indeed", 0, 3,
            today, seen)
        assert c3[0]["verdict"] == "keep:salary-undisclosed", c3[0]["verdict"]

        # a duplicate id inside one import is dropped, exactly as sweep.py does within a sweep
        c4, _, kept4 = import_groups([{"lane": "x", "query": "y", "rows": [
            {"job_id": "9", "title": "A", "url": "https://x.test/9"},
            {"job_id": "9", "title": "A", "url": "https://x.test/9"}]}],
            tmp, "indeed", "Indeed", 0, 3, today, seen)
        assert kept4 == 1 and c4[1]["verdict"] == "drop:dup-in-sweep"

        print("import_rows self-check OK")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
