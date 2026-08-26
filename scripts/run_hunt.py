#!/usr/bin/env python3
"""One command for the whole hunt. Sources, gates, ranks, verifies and reads the JDs.

Why this exists: the pipeline was correct but manual — six scripts, four sources, in an order
written down in the playbook and re-typed by hand every run. That is exactly the shape of process
that decays. Three real sourcing defects (one platform, page-1 only, 7 of 279 queries) were all
failures to run a step, not failures of a step, and the run still produced a confident write-up
because nothing checked. So the order lives in code now, and the run FAILS LOUDLY rather
than quietly reporting a thin day.

  L0 full       every query, every source, until each source stops
                                                     -> candidates.csv + queries.csv
  L0 companies  employers' own ATS/careers boards      -> candidates.csv + queries.csv
                (harvest_companies.py -> import_rows.py; before consolidate, which reads
                 candidates.csv exactly once. --skip-companies leaves it out - it is the
                 only L0 step that spends Firecrawl credits.)
  L1 consolidate cross-source dedupe + salary labels  -> shortlist.csv
  L1 rank       judge on the TITLE, per lane          -> ranked.csv
  --- verify_run MUST PASS HERE, or the run is not reportable ---
  L2 fetch JDs  full advert, spread across lanes      -> jds/*.md + jds/index.csv
                                                     -> to-tailor.csv

Then the day is NOT done. Read each advert, tailor the ones that fit, and run daily_bundle.py.
A run that ends at a CSV has produced a spreadsheet and left the work.

What stops a source is the SOURCE. The per-source call budget is gone, along with
the count stage that existed to allocate it: a query stops when the board is exhausted, when it
returns 429/403, or when a page adds nothing this run has not already seen. `--call-budget` is
an emergency brake, off by default.

Resumable: sweep.py skips queries already logged for its platform today, and `untidy` restores
the working files daily_bundle.py moved into _work/. Stages always re-run; `--force` only
lets L2 run when verify_run failed.

Usage:
  python run_hunt.py --workspace <dir>                        # the full daily hunt
  python run_hunt.py --workspace <dir> --stage rank           # from ranking onward
  python run_hunt.py --workspace <dir> --lanes it-support     # one lane
  python run_hunt.py --workspace <dir> --dry-run              # print the plan, spend nothing
  python run_hunt.py --self-check

The day folder is <workspace>/tasks/daily/<date>, where <date> is the day AFTER the last folder
that exists (never the wall clock — see next_run_date). A dry run creates nothing.
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import resolve_workspace_root, enable_utf8_io  # noqa: E402
enable_utf8_io()

# Official boards first, aggregator LAST. Reed, jobs.ac.uk and
# NHS Jobs carry the employer's own advert; Adzuna is an aggregator, so most of what it returns
# is a second copy of a role an earlier source already gave us. With a run-scoped novelty set
# that ordering is not a preference, it is the mechanism: by the time Adzuna runs, its pages are
# largely adverts already collected, so it stops itself after one page per query and its noise
# costs almost nothing.
ALL_SOURCES = ["reed", "jobsacuk", "nhs", "totaljobs", "adzuna"]

# Indeed has no harvester and cannot have one: it is a claude.ai OAuth MCP connector, and a
# Python script cannot call MCP. The AGENT runs the searches and feeds the rows in through
# indeed_to_rows.py -> import_rows.py, which writes the same candidates.csv / queries.csv
# contract a harvester does. Civil Service Jobs is the same story for a different reason — it
# serves a bot interstitial ("Quick Check Needed") to a plain GET, so it needs a JS-rendering
# scraper, which is also MCP-only.
#
# LINKEDIN IS NOT A SOURCE AND CANNOT BE MADE ONE. LinkedIn's public API has never offered job
# search outside Talent Solutions partners, and the third-party LinkedIn toolkits expose posting,
# comments, company info and analytics — none of them searches jobs. Do not re-plan around it.
#
# None of these is listed above on purpose: --sources is validated against ALL_SOURCES, and
# admitting a source with no harvester is how you get a silent mislabelled fall-through.
AGENT_FED_SOURCES = ["indeed", "civilservice"]

# Ordered, and the order matters. A stage may only run once the stage before it has an output,
# because every one of them silently produces an empty-but-valid file when its input is missing —
# which is how a thin run used to look like a successful one.
STAGES = ["full", "companies", "consolidate", "rank", "verify", "jds"]



def _declared_lanes(ws):
    """Lanes declared in JOB-LANES.md, via verify_run's own reader so there is one definition."""
    try:
        sys.path.insert(0, HERE)
        from verify_run import declared_lanes
        return set(declared_lanes(ws))
    except Exception:                                        # noqa: BLE001
        return set()


def day_dir(ws, date):
    return os.path.join(ws, "tasks", "daily", date)


def next_run_date(ws, today=None):
    """-> the date a new run files itself under: the day AFTER the last day folder.

    The wall clock is the wrong source for this. A run can start before midnight and finish
    after it, and a machine picked up days later would silently skip the numbering. Deriving
    the date from the folders makes the sequence contiguous and idempotent: each run gets the
    next unused day, whatever the clock says. Falls back to today when there are no day
    folders yet. Never returns a date already in use, so a run cannot overwrite a finished
    day's work — which is also why NO path in this script may create a day folder
    speculatively: an empty folder left by a dry run would advance the sequence.
    """
    root = os.path.join(ws, "tasks", "daily")
    try:
        dates = sorted(n for n in os.listdir(root)
                       if re.fullmatch(r"\d{4}-\d{2}-\d{2}", n)
                       and os.path.isdir(os.path.join(root, n)))
    except OSError:
        dates = []
    if not dates:
        return (today or datetime.date.today()).isoformat()
    return (datetime.date.fromisoformat(dates[-1]) + datetime.timedelta(days=1)).isoformat()


def last_run_date(ws, before):
    """-> the most recent earlier date that actually completed a sweep, or None.

    "Completed" means it left a queries.csv, which is only written by the full stage. A day
    folder alone is not evidence — an aborted run creates one before spending a single call.
    """
    root = os.path.join(ws, "tasks", "daily")
    if not os.path.isdir(root):
        return None
    dates = []
    for name in os.listdir(root):
        if name >= before or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", name):
            continue
        for cand in (os.path.join(root, name, "queries.csv"),
                     os.path.join(root, name, "_work", "queries.csv")):
            if os.path.isfile(cand):
                dates.append(name)
                break
    return max(dates) if dates else None


def untidy(day):
    """Bring the working files back up out of _work/ before re-running a day.

    daily_bundle.py moves them down there at the end of a run so the day folder shows only the
    applications. Every stage here reads and writes them at the TOP of the day folder, so a
    second run on the same date would otherwise find nothing, conclude the day was empty, and
    re-spend the whole sweep. Cheap to undo, expensive to discover.
    """
    work = os.path.join(day, "_work")
    if not os.path.isdir(work):
        return 0
    moved = 0
    for name in os.listdir(work):
        src, dst = os.path.join(work, name), os.path.join(day, name)
        if os.path.exists(dst):
            continue
        shutil.move(src, dst)
        moved += 1
    if moved:
        print(f"  (restored {moved} working file(s) from _work/ so this run can resume)")
    try:
        os.rmdir(work)
    except OSError:
        pass
    return moved


def run(cmd, dry, label):
    printable = " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd)
    print(f"\n>>> {label}\n    {printable}", flush=True)
    if dry:
        return 0
    t0 = time.time()
    proc = subprocess.run([sys.executable] + cmd[1:] if cmd[0] == "python" else cmd,
                          capture_output=False)
    print(f"    ({time.time() - t0:.0f}s, exit {proc.returncode})", flush=True)
    return proc.returncode


def auth_banner(src, date):
    """sweep.py exits 3 when the source REJECTED the key pair (HTTP 401, harvest.DeadCredential)."""
    print(f"\n!! {src.upper()}: CREDENTIALS REJECTED (HTTP 401). Nothing was sourced from it - the"
          f" run has one connector fewer than it appears and verify_run will fail it by name.\n"
          f"   Re-key the connector's key (setup_connectors.py shows where it is read from), then:"
          f" run_hunt.py --stage full --sources {src} --date {date} --skip-companies"
          f"  (its auth rows do not count as done)", flush=True)


def script(name):
    return os.path.join(HERE, name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace")
    ap.add_argument("--date", default=None,
                    help="YYYY-MM-DD. Default: the day AFTER the last folder in "
                         "tasks/daily, not today.")
    ap.add_argument("--sources", default=",".join(ALL_SOURCES))
    ap.add_argument("--stage", default="full", choices=STAGES,
                    help="start here; everything after it also runs")
    ap.add_argument("--lanes", default=None,
                    help="comma-separated lanes to restrict the sweep to (e.g. it-support). "
                         "Omit for every lane in the keyword file.")
    ap.add_argument("--where", default="",
                    help="location for the main sweep (e.g. London). Default: empty = a "
                         "market-wide sweep.")
    ap.add_argument("--distance", type=int, default=30, help="radius around --where")
    ap.add_argument("--relocate-lanes", default="",
                    help="comma-separated lanes you would still move for, swept a SECOND time "
                         "market-wide but held to --relocate-min-salary. Needs --where. Default: "
                         "off.")
    ap.add_argument("--relocate-min-salary", type=int, default=50000,
                    help="what a role outside --where must beat to be worth relocating for")
    ap.add_argument("--call-budget", type=int, default=0,
                    help="EMERGENCY BRAKE only, applied per source. 0 = unlimited (default). "
                         "Each source now runs until it is exhausted or refuses; it is not "
                         "given a share of a made-up global number.")
    ap.add_argument("--max-days-old", type=int, default=3)
    ap.add_argument("--since", default=None, metavar="YYYY-MM-DD",
                    help="only adverts posted on or after this date. On boards that sort "
                         "newest-first the sweep STOPS once it passes the line instead of "
                         "enumerating everything and discarding it locally.")
    ap.add_argument("--since-last-run", action="store_true",
                    help="set --since to the date of the previous completed run, so a day that "
                         "follows a full sweep only reads what is new. Falls back to "
                         "--max-days-old when there is no previous run.")
    ap.add_argument("--min-salary", type=int, default=0,
                    help="0 = no floor (default). Salary still RANKS; it just never rejects.")
    ap.add_argument("--top", type=int, default=120,
                    help="how many adverts to READ at L2, spread round-robin across lanes. Was 40, "
                         "which silently overrode fetch_jds' own default and left ~3 adverts per "
                         "lane out of thousands of survivors — far too thin to choose from once "
                         "relevance stopped rejecting.")
    ap.add_argument("--min-platforms", type=int, default=4)
    ap.add_argument("--skip-lanes", default="",
                    help="comma-separated lanes verify_run should not expect coverage for "
                         "(e.g. a cold-outreach lane that is never swept)")
    ap.add_argument("--force", action="store_true",
                    help="run L2 (fetch JDs) even though verify_run failed - the only gate this "
                         "bypasses; stages always re-run")
    ap.add_argument("--skip-companies", action="store_true",
                    help="skip the employer-board stage. It is the only L0 step that spends "
                         "Firecrawl credits, and a re-run after a 401 does not need it again.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()

    if args.self_check:
        return self_check()

    ws = resolve_workspace_root(args.workspace)
    if not ws:
        raise SystemExit("no workspace resolved")
    # NOT today. The day folder continues the sequence under tasks/daily — see next_run_date.
    # A run that crosses midnight, or a machine picked up days later, must still file itself
    # as the next unused day rather than jumping or colliding.
    date = args.date or next_run_date(ws)
    day = day_dir(ws, date)
    if not args.dry_run:
        # A dry run must leave no trace. It used to create the day folder regardless, which
        # was invisible while the date was today() and the folder already existed — and became
        # a real fault once the date is derived FROM the folders: an empty folder left by a
        # dry run advances the sequence and then becomes what daily_bundle defaults to.
        os.makedirs(day, exist_ok=True)
        untidy(day)

    since = args.since
    if args.since_last_run and not since:
        prev = last_run_date(ws, date)
        if prev:
            since = prev
            print(f"  incremental: previous completed run was {prev}; only adverts posted on or "
                  f"after that date will be read where the board can sort by date")
        else:
            print(f"  --since-last-run: no earlier completed run found, falling back to "
                  f"--max-days-old {args.max_days_old}")
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    bad = [s for s in sources if s not in ALL_SOURCES]
    if bad:
        raise SystemExit(f"unknown source(s): {', '.join(bad)}")
    start = STAGES.index(args.stage)
    todo = STAGES[start:]

    print(f"hunt {date}  sources={','.join(sources)}  stages={'>'.join(todo)}"
          f"  where={args.where or 'market-wide'}"
          + (f"  relocate:{args.relocate_lanes}>=GBP{args.relocate_min_salary:,}"
             if args.relocate_lanes and args.where else "")
          + ("  DRY RUN" if args.dry_run else ""))

    failures = []

    if "full" in todo:
        for src in sources:
            cmd = ["python", script("sweep.py"), "--workspace", ws, "--source", src,
                   "--date", date, "--call-budget", str(args.call_budget),
                   "--max-days-old", str(args.max_days_old),
                   "--min-salary", str(args.min_salary)]
            if since:
                cmd += ["--since", since]
            if args.lanes:
                cmd += ["--lanes", args.lanes]
            if args.where:
                cmd += ["--where", args.where, "--distance", str(args.distance)]
            rc = run(cmd, args.dry_run, f"L0 full · {src} · to exhaustion")
            if rc == 3:
                auth_banner(src, date)
            if rc:
                failures.append(f"full:{src}" + (":auth-401" if rc == 3 else ""))

    # LANES YOU WOULD MOVE FOR. The main sweep is --where-only, so a role in another region
    # never appears at all. Those lanes get a second, market-wide pass gated at a higher salary
    # — the bar a role must clear to be worth relocating for. It is a supplement to the main
    # sweep, not a rival to it.
    if "full" in todo and args.relocate_lanes and args.where:
        for src in sources:
            # --redo is LOAD-BEARING, not a convenience. `done_queries` keys on
            # (platform, lane, query) and cannot tell "agri-food, London" from "agri-food,
            # UK-wide" — they are the same query string. The main pass runs every agri-food
            # query first, so without --redo this pass finds nothing left to do and reports
            # "0 of 0 queries run" on every source, which reads exactly like a lane with no
            # vacancies. Observed live: the entire relocation sweep was a silent no-op, so no
            # market-wide role above the relocation bar was ever surfaced.
            rc = run(["python", script("sweep.py"), "--workspace", ws, "--source", src,
                      "--date", date, "--call-budget", str(args.call_budget),
                      "--lanes", args.relocate_lanes, "--redo",
                      "--max-days-old", str(args.max_days_old),
                      "--min-salary", str(args.relocate_min_salary)]
                     + (["--since", since] if since else []),
                     args.dry_run,
                     f"L0 relocate · {src} · {args.relocate_lanes} market-wide "
                     f"@ >=GBP{args.relocate_min_salary:,}")
            if rc == 3:
                auth_banner(src, date)
            if rc:
                failures.append(f"relocate:{src}" + (":auth-401" if rc == 3 else ""))

    # COMPANY BOARDS: employers' own ATS/careers pages, read by
    # harvest_companies.py and fed through import_rows.py so the rows are byte-identical to a
    # harvested one. It sits BEFORE consolidate, not "before rank" as the doc used to say:
    # import_rows appends to candidates.csv, which consolidate reads exactly once - any later
    # and the rows never reach shortlist.csv.
    if "companies" in todo and not args.skip_companies:
        rows_json = os.path.join(day, "_work", "company_rows.json")
        if not args.dry_run:
            os.makedirs(os.path.dirname(rows_json), exist_ok=True)
        # 30 days, not 3: these adverts were never on any board, so recency is not the filter
        # it is on Reed. A --since window narrows it like every other source.
        days = "30"
        if since:
            days = str(max(0, (datetime.date.today() - datetime.date.fromisoformat(since)).days))
        rc = run(["python", script("harvest_companies.py"), "--workspace", ws,
                  "--out", rows_json], args.dry_run, "L0 companies · employer boards")
        if rc:
            failures.append("companies:harvest")
        else:
            rc = run(["python", script("import_rows.py"), "--workspace", ws,
                      "--source", "companies", "--platform", "Company boards",
                      "--rows", rows_json, "--date", date,
                      "--min-salary", str(args.min_salary), "--max-days-old", days],
                     args.dry_run, "L0 companies · import")
            if rc:
                failures.append("companies:import")

    if "consolidate" in todo:
        rc = run(["python", script("consolidate.py"), "--workspace", ws, "--date", date,
                  "--min-salary", str(args.min_salary)], args.dry_run, "L1 consolidate")
        if rc:
            failures.append("consolidate")

    if "rank" in todo:
        rc = run(["python", script("rank.py"), "--workspace", ws, "--date", date, "--top", str(args.top)],
                 args.dry_run, "L1 rank on title")
        if rc:
            failures.append("rank")

    verified = None                 # None = verify never ran, which is NOT the same as passed
    if "verify" in todo:
        # A lane-restricted sweep deliberately does not cover every declared lane, so the
        # coverage check has to be told which lanes were never in scope. Without this a
        # `--lanes it-support` run would always fail and the failure would mean nothing.
        skip = args.skip_lanes
        if args.lanes:
            declared = _declared_lanes(ws)
            wanted = {x.strip() for x in args.lanes.split(",") if x.strip()}
            skip = ",".join(sorted(set(x.strip() for x in skip.split(",") if x.strip())
                                   | (declared - wanted)))
        rc = run(["python", script("verify_run.py"), "--workspace", ws, "--date", date,
                  "--min-platforms", str(args.min_platforms), "--skip-lanes", skip],
                 args.dry_run, "VERIFY (must pass)")
        verified = (rc == 0)
        if rc:
            failures.append("verify")

    # L2 costs scraper credits. It runs only behind a passing verify, because fetching adverts off
    # a thin, unverified shortlist is the most expensive way to be wrong.
    if "jds" in todo:
        if verified is not True and not args.force:
            print("\n!! SKIPPING L2 — verify_run did not pass. Fetching JDs off an unverified "
                  "shortlist spends scraper credits on a run you cannot report. Fix the funnel, "
                  "or pass --force if you know why it failed.")
            failures.append("jds:skipped-unverified")
        else:
            rc = run(["python", script("fetch_jds.py"), "--workspace", ws, "--date", date,
                      "--top", str(args.top)], args.dry_run, f"L2 fetch JDs · top {args.top}")
            if rc:
                failures.append("jds")

    # THE HAND-OFF. The user wants CVs ready, cover letters ready, job descriptions ready,
    # tracker ready. A run that ends at ranked.csv has not
    # finished the job -- it produced a spreadsheet and left the work. Tailoring needs
    # judgement a script cannot supply, so the script's last act is to name EXACTLY which
    # roles to tailor: the ones whose advert was actually fetched, best first. Everything
    # rejected stays in ranked.csv with its reason, and off this list.
    if "jds" in todo and not args.dry_run:
        import csv as _csv
        idxf = os.path.join(day, "jds", "index.csv")
        out = os.path.join(day, "to-tailor.csv")
        try:
            with open(idxf, encoding="utf-8-sig", newline="") as fh:
                got = [r for r in _csv.DictReader(fh) if r.get("status") == "ok"]
            got.sort(key=lambda r: int(r.get("rank") or 10**6))
            cols = ["rank", "score", "true_lane", "title", "company", "location",
                    "salary_min", "salary_max", "pay_basis", "pay_note", "posted",
                    "file", "url"]
            with open(out, "w", encoding="utf-8", newline="") as fh:
                w = _csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                w.writerows(got)
            print(f"\n  -> {out}   {len(got)} advert(s) READ and ready to tailor")
            print("     Next: judge fit from each advert, tailor CV + cover letter for the")
            print("     ones that genuinely fit, then run daily_bundle.py.")
        except OSError:
            pass

    print("\n" + "=" * 66)
    if args.dry_run:
        print("DRY RUN — nothing executed, no calls spent.")
        return 0
    for name, f in (("landscape", "landscape.csv"), ("candidates", "candidates.csv"),
                    ("shortlist", "shortlist.csv"), ("ranked", "ranked.csv")):
        p = os.path.join(day, f)
        n = (sum(1 for _ in open(p, encoding="utf-8-sig")) - 1) if os.path.isfile(p) else 0
        print(f"  {name:<12} {max(n, 0):>8,}")
    if failures:
        print(f"\n  FAILED STAGES: {', '.join(failures)}")
        print("  The run is NOT reportable. Do not write it up.")
        return 1
    docs = 0
    try:
        docs = len([f for f in os.listdir(day) if f.lower().endswith(".docx")])
    except OSError:
        pass
    if docs:
        print(f"\n  all stages OK — {docs} document(s) ready in {day}")
    else:
        print("\n  all stages OK, but NO CV OR COVER LETTER EXISTS YET for this date.")
        print("  Sourcing is finished; the day is not. Tailor from to-tailor.csv, then bundle.")
    return 0


def self_check():
    import tempfile
    import shutil
    tmp = tempfile.mkdtemp()
    try:
        d = os.path.join(tmp, "tasks", "daily", "2026-08-15")
        os.makedirs(d)
        assert day_dir(tmp, "2026-08-15") == d
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # No source's effort is a fraction of a made-up global number any more.
    # The old assertions here proved the budget arithmetic was correct; the arithmetic was
    # correct and the idea was wrong. Each source now runs until IT stops.
    assert "BUDGET_SHARE" not in globals()

    # The count stage is gone. It cost ~300 queries x 5 sources of calls to learn a total
    # every harvester already returns free on its own first page.
    assert "count" not in STAGES and STAGES[0] == "full"

    # Official boards first, aggregator last — with a run-scoped novelty set that ordering is
    # the mechanism, not a preference: Adzuna's pages are mostly adverts an earlier source
    # already produced, so it stops itself cheaply.
    assert ALL_SOURCES[0] == "reed" and ALL_SOURCES[-1] == "adzuna"
    assert "nhs" in ALL_SOURCES
    # Neither has a harvester, and admitting either here would let sweep's dispatch run
    # something else under its label. They arrive through import_rows.py instead.
    assert not (set(ALL_SOURCES) & set(AGENT_FED_SOURCES))
    assert "linkedin" not in ALL_SOURCES        # deferred to the Composio route

    # The relocation pass MUST carry --redo. Without it, done_queries treats the London pass's
    # agri-food queries as already done and the whole UK-wide sweep silently runs zero queries.
    src = open(os.path.join(HERE, "run_hunt.py"), encoding="utf-8").read()
    reloc = src[src.index("L0 relocate") - 1200:src.index("L0 relocate")]
    assert '"--redo"' in reloc, "the relocate pass lost --redo; it is now a silent no-op"

    # stage ordering: starting late must never re-run earlier stages
    assert "companies" not in ALL_SOURCES     # a STAGE, not a source: sweep has no harvester
    assert STAGES.index("companies") == STAGES.index("full") + 1
    assert STAGES.index("consolidate") == STAGES.index("companies") + 1, \
        "company rows must land in candidates.csv before consolidate reads it"
    assert STAGES.index("verify") > STAGES.index("rank") > STAGES.index("consolidate")
    assert STAGES[STAGES.index("rank"):] == ["rank", "verify", "jds"]
    # L2 is last, so a failed verify can gate it
    assert STAGES[-1] == "jds"
    # the companies stage is the documented two-command recipe: pin it by slicing, never by an
    # assert containing its own search literal (that can never fail)
    _co = 'if "companies" in todo'
    blk = src[src.index(_co):src.index('if "consolidate" in todo:')]
    assert '"Company boards"' in blk and '"--max-days-old", days' in blk
    # both sweep passes must label a 401 by name. Counted in the body only — an assert whose
    # own text contains the literal it searches for can never fail (item 32).
    body = src[:src.index("def self_check")]
    assert body.count(":auth-401") == 2, "a sweep pass lost its auth-401 label"
    # the re-key recipe must never name a path on somebody's machine
    assert not re.search(r"[A-Za-z]:[\\/]", body[body.index("def auth_banner"):
                                                 body.index("def script")])

    # THE DATE IS DERIVED FROM THE FOLDERS (item 13), and nothing may create one speculatively.
    tmp = tempfile.mkdtemp()
    try:
        for d in ("profiles", "applications"):
            os.makedirs(os.path.join(tmp, d))
        assert next_run_date(tmp, datetime.date(2026, 1, 5)) == "2026-01-05"   # no folders: today
        os.makedirs(os.path.join(tmp, "tasks", "daily", "2026-08-20"))
        os.makedirs(os.path.join(tmp, "tasks", "daily", "2026-08-22"))
        open(os.path.join(tmp, "tasks", "daily", "notes.md"), "w").close()      # not a day
        assert next_run_date(tmp, datetime.date(2026, 1, 5)) == "2026-08-23"   # last + 1, not today
        # a dry run shows the companies stage (harvest + import) and creates NO folder...
        base = [sys.executable, os.path.join(HERE, "run_hunt.py"), "--workspace", tmp, "--dry-run"]
        out = subprocess.run(base, capture_output=True, text=True, encoding="utf-8").stdout
        assert out.count("L0 companies") == 2, out
        assert "hunt 2026-08-23" in out, out
        assert sorted(os.listdir(os.path.join(tmp, "tasks", "daily"))) == \
            ["2026-08-20", "2026-08-22", "notes.md"], os.listdir(os.path.join(tmp, "tasks", "daily"))
        # ...and --skip-companies leaves it out entirely
        out = subprocess.run(base + ["--skip-companies"], capture_output=True, text=True,
                             encoding="utf-8").stdout
        assert out.count("L0 companies") == 0, out
        assert not os.path.isdir(os.path.join(tmp, "tasks", "daily", "2026-08-23"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("run_hunt self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
