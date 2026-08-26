#!/usr/bin/env python3
"""Drive the WHOLE keyword file across a connector, instead of the handful someone typed.

Third and largest of the sourcing defects. Even with every platform queried (breadth) and
every page enumerated (depth), a run still only sees what it thought to ask for — and the
runs were asking about seven things. SEARCH-KEYWORDS.md holds 259 ready-to-run queries and
2,784 title variants, built specifically so the hunt would stop missing roles advertised
under a name nobody thought of, and nothing ever read it as machine input.

Scale of the miss, measured 2026-08-12 on Adzuna alone: 18 exact AI/data titles return
14,848 live UK ads. The 10 Aug run drafted nothing from the data-ai lane.

ONE stage, since 22 Aug 2026. There used to be a `count` stage that spent one call per query
building a landscape of what was worth enumerating — ~300 queries x 5 sources, about 1,500
calls a run, to learn a number every harvester already returns free on its own first page. It
was deleted along with the per-source call budget it existed to allocate. `landscape.csv` is
still written; it is now a by-product of the sweep rather than the reason for one.

What stops a query now is the source, not a guess about the source: a board's own API limit
is the only limit that means anything, and rationing below it just leaves inventory
unenumerated. Four stops, and the sweep records which one fired:

  exhausted   the board says there are no more results
  quota       429/403 — the source refuses. The only real limit; remaining queries logged unrun
  novelty     a page added no advert this run had not already collected, i.e. this query is a
              rephrasing of one already answered. See harvest.novelty_stopper.
  auth        401 — the key pair is rejected. Source stopped, every unrun query noted, exit 3.

Truncation is always reported, never silent — a capped sweep that looks complete is the
same lie as a one-platform run that reads like seven. Queries that never ran get a row too.

Usage:
  python sweep.py --workspace <dir> --source reed --max-days-old 3
  python sweep.py --workspace <dir> --source nhs  --where London
  python sweep.py --self-check
"""
import argparse
import csv
import datetime
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import resolve_workspace_root, enable_utf8_io  # noqa: E402
from build_seen_ledger import canonical_key  # noqa: E402
from harvest import (CANDIDATE_COLUMNS, DATE_SORTED, DeadCredential,  # noqa: E402
                     QUERY_COLUMNS, QuotaExhausted,
                     all_of, append_rows, creds, date_stopper, gate, harvest_adzuna,
                     harvest_jobsacuk, harvest_nhs, harvest_reed, harvest_stepstone,
                     load_seen, novelty_stopper)
enable_utf8_io()

LANDSCAPE_COLUMNS = ["platform", "lane", "query", "total", "note"]

PLATFORM = {"reed": "Reed", "adzuna": "Adzuna", "jobsacuk": "jobs.ac.uk",
            "totaljobs": "Totaljobs", "nhs": "NHS Jobs"}
PAGE_SIZE = {"reed": 100, "adzuna": 50, "jobsacuk": 25, "totaljobs": 25, "nhs": 10}

AUTH_NOTE = "auth: 401 — credentials rejected"   # verify_run and done_queries key on the "auth:" prefix

# A runaway guard, NOT a budget: roughly 2,500 adverts from any one query whatever the page
# size, hard-capped at 60 pages so a single query matching the whole board cannot own the
# clock. The novelty stop normally ends a query far sooner; this only fires when a query
# genuinely keeps producing adverts nothing else has seen.
MAX_PAGES = {src: min(60, max(6, 2500 // n)) for src, n in PAGE_SIZE.items()}

# Section heading -> lane. A heading that carries its lane token in backticks — the same
# convention JOB-LANES.md uses, e.g. `## Data · AI (\`data-ai\`)` — is explicit and wins.
# Otherwise the prefix table below maps common role families; a wrong guess would silently
# file a whole lane under the wrong name, so anything unmatched maps to "" and verify_run
# reports the lane as never queried rather than inventing a name.
SECTION_LANES = [
    ("agri-food", "agri-food"),
    ("data ", "data-ai"),
    ("research", "research"),
    ("operations", "ops-admin"),
    ("pa ", "pa-ea"),
    ("premium security", "security-premium"),
    ("av ", "av-media"),
    ("it support", "it-support"),
    ("ai adoption", "ai-adoption"),
    ("retail", "retail-hospitality"),
    ("global knockouts", "global"),
    ("wildcard", "wildcard"),
    ("additional role families 1", "additional-1"),
    ("additional role families 2", "additional-2"),
    ("additional role families 3", "additional-3"),
]


def lane_for(heading):
    m = re.search(r"`([a-z0-9][a-z0-9-]*)`", heading)
    if m:
        return m.group(1)
    h = heading.strip().lower()
    for prefix, lane in SECTION_LANES:
        if h.startswith(prefix):
            return lane
    return ""


def parse_queries(path):
    """-> [(lane, query)] from each section's `Ready-to-run queries` line.

    Those lines are backtick-quoted terms separated by middots, directly under a
    **Ready-to-run queries** marker inside a `## ` section. Deduplicated on (lane, query),
    order preserved so a resumed sweep repeats the same sequence.
    """
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    out, seen, lane, armed = [], set(), "", False
    for line in lines:
        if line.startswith("## "):
            lane, armed = lane_for(line[3:]), False
            continue
        if re.match(r"^\*\*Ready-to-run queries\*\*", line.strip()):
            armed = True
            continue
        if armed:
            stripped = line.strip()
            if not stripped:
                continue                  # a blank line between the marker and the queries
            if stripped.startswith("**"):
                armed = False             # the next bold marker ends the block
                continue
            for term in re.findall(r"`([^`]+)`", line):
                term = term.strip()
                key = (lane, term.lower())
                if term and key not in seen:
                    seen.add(key)
                    out.append((lane, term))
            # Deliberately NOT `armed = False` here. The block ran to exactly one line when
            # this was written, so stopping after the first line was invisible — and it stays
            # invisible right up until someone widens a lane and the list wraps. Consume until
            # the next bold marker instead. (The `## Master query list` block is NOT read: it
            # is a de-duplicated copy of these same lines, and its heading maps to no lane, so
            # parsing it would file every query under lane "" — the column verify_run's
            # coverage check reads.)
    return out


def order_queries(pairs):
    """Broad queries first, narrow ones after — shortest query is the broadest, for free.

    This reverses the old cheapest-first order, and the reversal is load-bearing. The novelty
    stopper shares one id set across the whole sweep, so whichever query runs first is credited
    with all the inventory it and its rephrasings have in common. Cheapest-first therefore let a
    12-hit niche query claim the shared pool, after which the broad query that had the most to
    give stopped on page one having "found nothing new". Broad-first pays for the overlap once
    and every narrow rephrasing then costs a single page while still contributing its uniques.
    """
    return sorted(pairs, key=lambda lq: (len(lq[1].split()), len(lq[1]), lq[1]))


def read_landscape(path, platform):
    """Counts for ONE platform. All sources append to the same landscape.csv, so keying
    without the platform would silently hand jobs.ac.uk Reed's totals."""
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = {}
    for r in rows:
        if r.get("platform") != platform:
            continue
        try:
            out[(r.get("lane", ""), r.get("query", ""))] = int(r.get("total") or 0)
        except ValueError:
            pass
    return out


def done_queries(path, platform):
    """(lane, query) already enumerated today FOR THIS PLATFORM — lets a sweep resume
    without a finished Reed run making jobs.ac.uk look already done."""
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8-sig", newline="") as fh:
        # An `auth:` row is a query that never ran — after re-keying, a plain re-run
        # must pick it up.
        return {(r.get("lane", ""), r.get("query", "")) for r in csv.DictReader(fh)
                if r.get("platform") == platform
                and not (r.get("note") or "").startswith("auth:")}


def run_one(source, c, query, where, distance, max_days_old, max_pages, page_size=None,
            on_page=None):
    """Dispatch one query to one board. `on_page` is the novelty stopper; see harvest."""
    if source == "nhs":
        # No API and no key. Page size is fixed at 10 by the site.
        return harvest_nhs(query, where, max_pages, page_size=page_size or 10, on_page=on_page)
    if source == "totaljobs":
        # cwjobs.co.uk and milkround.com are the same platform and REDIRECT here — their
        # results carry totaljobs.com URLs, so adding them would duplicate, not extend.
        return harvest_stepstone("totaljobs", query, where, distance, max_pages,
                                 page_size=page_size or 25, on_page=on_page)
    if source == "jobsacuk":
        # No API and no key — the public search page, paginated. Its page size is fixed at 25.
        return harvest_jobsacuk(query, max_pages, page_size=page_size or 25, on_page=on_page)
    if source == "reed":
        return harvest_reed(c["REED_API_KEY"], query, where, distance, max_pages,
                            page_size=page_size or 100, on_page=on_page)
    if source != "adzuna":
        # Adzuna used to be the fall-through, so a typo'd or unbuilt source name silently ran
        # an Adzuna search and filed the rows under the other source's label.
        raise SystemExit(f"unknown source {source!r}")
    return harvest_adzuna(
        c["ADZUNA_APP_ID"], c["ADZUNA_APP_KEY"],
        # what_phrase, never what_or: what_or ORs individual WORDS, so a two-word title
        # matches every advert containing either of them (16,772 hits vs 497).
        {"what_phrase": query, "where": where or None, "distance": distance,
         "max_days_old": max_days_old, "sort_by": "date"},
        max_pages, page_size=page_size or 50, on_page=on_page)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace")
    ap.add_argument("--source", choices=["reed", "adzuna", "jobsacuk", "totaljobs", "nhs"])
    ap.add_argument("--stage", choices=["full"], default="full",
                    help="the `count` stage was deleted on 22 Aug 2026 — see the module "
                         "docstring. argparse rejects it loudly rather than silently.")
    ap.add_argument("--keywords-file", default=None, help="defaults to <workspace>/SEARCH-KEYWORDS.md")
    ap.add_argument("--lanes", default="", help="comma-separated lane filter; default all")
    ap.add_argument("--where", default="")
    ap.add_argument("--distance", type=int, default=None)
    ap.add_argument("--min-salary", type=int, default=0,
                    help="0 = no floor (default). Nothing is rejected on pay; the salary "
                         "plausibility LABELS are still computed either way.")
    ap.add_argument("--max-days-old", type=int, default=3)
    ap.add_argument("--max-pages", type=int, default=0,
                    help="page cap PER QUERY. 0 = use MAX_PAGES for the source. This is a "
                         "runaway guard, not a budget: the novelty stop normally ends a "
                         "query long before it.")
    ap.add_argument("--call-budget", type=int, default=0,
                    help="EMERGENCY BRAKE only. 0 = unlimited (default). Every source runs "
                         "until it is exhausted or refuses. Queries not run because of this "
                         "still get a queries.csv row saying so.")
    ap.add_argument("--since", default=None, metavar="YYYY-MM-DD",
                    help="stop paginating once a page is entirely older than this. Only applied "
                         "to boards that can sort newest-first (adzuna, nhs, jobsacuk, totaljobs) "
                         "- Reed has no date sort and is enumerated in full. Defaults to "
                         "today minus --max-days-old.")
    ap.add_argument("--min-new-per-page", type=int, default=1,
                    help="stop paginating a query when a page yields fewer than this many "
                         "adverts unseen in this run")
    ap.add_argument("--redo", action="store_true",
                    help="re-run queries already logged for this platform today")
    ap.add_argument("--throttle", type=float, default=0.25, help="seconds between calls")
    ap.add_argument("--date", default=None)
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()

    if args.self_check:
        return self_check()
    if not args.source:
        raise SystemExit("--source is required")

    ws = resolve_workspace_root(args.workspace)
    if not ws:
        raise SystemExit("no workspace resolved")
    kw = args.keywords_file or os.path.join(ws, "SEARCH-KEYWORDS.md")
    if not os.path.isfile(kw):
        raise SystemExit(f"no keyword file at {kw}")

    queries = parse_queries(kw)
    if args.lanes:
        want = {s.strip() for s in args.lanes.split(",") if s.strip()}
        queries = [(ln, q) for ln, q in queries if ln in want]
    if not queries:
        raise SystemExit("no queries parsed — check the keyword file's section headings")

    date = args.date or datetime.date.today().isoformat()
    today = datetime.date.today()
    out = os.path.join(ws, "tasks", "daily", date)
    platform = PLATFORM[args.source]
    c = ({} if args.source in ("jobsacuk", "totaljobs", "nhs")
         else creds(args.source, args.env_file))

    # ---- full stage -------------------------------------------------------------
    already = set() if args.redo else done_queries(os.path.join(out, "queries.csv"), platform)
    seen = load_seen(ws)
    todo = [(ln, q) for ln, q in queries if (ln, q) not in already]

    # The same term is listed under two lanes ("office manager" is both ops-admin and pa-ea),
    # and running it twice buys nothing but API calls. Search once, file under the first lane.
    _qseen, _deduped = set(), []
    for ln, q in todo:
        if q.lower() in _qseen:
            continue
        _qseen.add(q.lower())
        _deduped.append((ln, q))
    cross_lane_dupes = len(todo) - len(_deduped)
    todo = _deduped
    todo = order_queries(todo)

    page_size = PAGE_SIZE[args.source]
    max_pages = args.max_pages or MAX_PAGES[args.source]
    # THE DATE STOP. Once a full sweep has been done, tomorrow only needs what is new — so on
    # a board that sorts newest-first, read until the dates fall past the line and stop, rather
    # than enumerating everything and discarding most of it in the local gate. Reed is excluded
    # because it has no date sort at all; see harvest.DATE_SORTED.
    cutoff = None
    if args.since:
        cutoff = datetime.date.fromisoformat(args.since)
    elif args.max_days_old:
        cutoff = today - datetime.timedelta(days=args.max_days_old)
    stop_on_date = date_stopper(cutoff, today) if (cutoff and args.source in DATE_SORTED) else None

    # The gate must use the SAME cutoff as the stop, or the two disagree and the sweep quietly
    # does two different things: measured live 22 Aug 2026, --since 2026-08-22 with the gate still
    # on --max-days-old 3 stopped paginating at the 22nd while the gate was still accepting the
    # 19th, so adverts it wanted were cut off unread. One line, one meaning.
    gate_days = args.max_days_old
    if cutoff:
        gate_days = max(0, (today - cutoff).days)

    calls = [0]                       # a list so the on_page closure can mutate it
    enumerated, kept_total, fresh_total = 0, 0, 0
    land_rows, stopped, dead = [], "", False
    # A sweep asks ~300 overlapping questions, so the SAME advert comes back under several
    # of them ("data scientist" and "data analyst" both return it), and the same ROLE comes
    # back from several agencies as distinct ads. The ledger cannot catch either: it keys on
    # URL and only knows about previous runs. Both are deduped here, within the sweep.
    #
    # TWO id sets, deliberately, and they must not be merged:
    #   novel_ids  — the novelty stopper's memory. Filled as each PAGE arrives, before any
    #                gating, because its job is to answer "did this page tell us anything new".
    #   kept_ids   — in-sweep dedupe. Filled only when a row actually SURVIVES the gate.
    # Sharing one set looks tempting and is fatal: the stopper adds every id on arrival, so a
    # dedupe check against it would find every row already present and mark the entire sweep
    # `drop:dup-in-sweep`.
    novel_ids, kept_ids, sweep_roles, dup_total = set(), set(), set(), 0

    def log(lane, q, raw, after=0, fresh=0, note=""):
        append_rows(os.path.join(out, "queries.csv"), QUERY_COLUMNS, [{
            "platform": platform, "lane": lane, "query": q, "raw_hits": raw,
            "after_gate": after, "new_vs_ledger": fresh, "note": note}])

    for i, (lane, q) in enumerate(todo):
        if args.call_budget and calls[0] >= args.call_budget:
            # Not a `break`: every query that did not run still gets a row, or the hole is
            # invisible to verify_run and a truncated sweep reads exactly like a complete one.
            log(lane, q, 0, note="skipped: --call-budget emergency brake")
            continue
        before = calls[0]
        try:
            rows, total = run_one(args.source, c, q, args.where, args.distance,
                                  args.max_days_old, max_pages, page_size=page_size,
                                  on_page=all_of(
                                      novelty_stopper(novel_ids, calls, args.min_new_per_page),
                                      stop_on_date))
        except DeadCredential as exc:
            # The key pair is present and REJECTED. Not a quota: every remaining query would
            # spend a call to learn the same thing and log `error: HTTPError`, which verify_run
            # counted as a sourced platform (23 Aug 2026). Stop the source, name the cause on
            # every unrun query, and exit 3 so run_hunt fails the stage by name.
            # 3, not 2: argparse.error() already exits 2.
            dead = True
            log(lane, q, 0, note=f"{AUTH_NOTE} ({exc}) after {calls[0]} calls")
            for rest_lane, rest_q in todo[i + 1:]:
                log(rest_lane, rest_q, 0, note=AUTH_NOTE)
            break
        except QuotaExhausted as exc:
            # The source's OWN limit — the only legitimate reason to stop enumerating it.
            stopped = str(exc)
            log(lane, q, 0, note=f"quota: {exc} after {calls[0]} calls")
            for rest_lane, rest_q in todo[i + 1:]:
                log(rest_lane, rest_q, 0, note=f"quota: {exc} — source stopped before this query")
            break
        except Exception as exc:                      # a dead query must not kill the sweep
            log(lane, q, 0, note=f"error: {type(exc).__name__}")
            continue
        pages = calls[0] - before

        for r in rows:
            v = gate(r, args.min_salary, gate_days, today, seen)
            if v.startswith("keep"):
                jid = str(r.get("job_id") or "")
                role = (re.sub(r"\W+", " ", (r.get("company") or "").lower()).strip() + "|"
                        + re.sub(r"\W+", " ", (r.get("title") or "").lower()).strip())
                if jid and jid in kept_ids:
                    v, dup_total = "drop:dup-in-sweep", dup_total + 1
                elif role != "|" and role in sweep_roles:
                    v, dup_total = "drop:dup-role-reposted", dup_total + 1
                else:
                    kept_ids.add(jid)
                    sweep_roles.add(role)
            r.update(source=args.source, lane=lane, query=q, verdict=v)
        kept = [r for r in rows if r["verdict"].startswith("keep")]
        fresh = [r for r in kept if canonical_key(r.get("url") or "") not in seen]
        truncated = len(rows) < total
        append_rows(os.path.join(out, "candidates.csv"), CANDIDATE_COLUMNS, rows)
        note = f"{pages}p"
        if truncated:
            note += f" · truncated: {len(rows)} of {total}"
        log(lane, q, total, len(kept), len(fresh), note)
        land_rows.append({"platform": platform, "lane": lane, "query": q,
                          "total": total, "note": note})
        enumerated += len(rows)
        kept_total += len(kept)
        fresh_total += len(fresh)
        time.sleep(args.throttle)

    # landscape.csv is now a BY-PRODUCT of the sweep rather than a stage that cost ~300 calls
    # per source to build. Every harvester already reports the total on its first page.
    append_rows(os.path.join(out, "landscape.csv"), LANDSCAPE_COLUMNS, land_rows)

    ran = len(land_rows)
    print(f"{platform} sweep · {ran} of {len(todo)} queries run · {calls[0]} real API calls"
          + (f" · {cross_lane_dupes} cross-lane duplicate queries collapsed"
             if cross_lane_dupes else ""))
    print(f"  enumerated     {enumerated:,}")
    print(f"  deduped away   {dup_total:,}  (same ad under several queries, or one role "
          f"advertised by several agencies)")
    print(f"  past the gate  {kept_total:,}")
    print(f"  new vs ledger  {fresh_total:,}   <- fetch JDs for these only")
    if stopped:
        print(f"  STOPPED BY THE SOURCE: {stopped}. Nothing to be done about it; the "
              f"remaining queries are logged as unrun.")
    print(f"  -> {os.path.join(out, 'candidates.csv')}")
    if dead:
        print(f"  !! {platform}: CREDENTIALS REJECTED (HTTP 401). Nothing was sourced from it. "
              f"Re-key it, then re-run this source for {date} — its auth rows do not count as done.")
        return 3
    return 0


def self_check():
    import tempfile
    import shutil
    tmp = tempfile.mkdtemp()
    try:
        p = os.path.join(tmp, "SEARCH-KEYWORDS.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(
                "# Search keywords\n\n"
                "## How to use it\n\nProse with `backticks` that must NOT become queries.\n\n"
                "## Data · AI · machine learning · analytics\n\n"
                "**Ready-to-run queries**\n\n"
                "`data analyst` · `AI engineer` · `data analyst`\n"
                "`prompt engineer` · `MLOps engineer`\n\n"
                "**Core titles (3)** — `not a query`\n\n"
                "## PA · EA · private office · household\n\n"
                "**Ready-to-run queries**\n\n"
                "`executive assistant` · `chief of staff`\n\n"
                "## Master query list\n\n"
                "```\ndata analyst\nsomething only in the master list\n```\n")
        got = parse_queries(p)
        # A Ready-to-run block may run to SEVERAL lines. It ran to exactly one when this was
        # written, so `armed = False` after line one was invisible — and stays invisible right
        # up until a lane is widened and the list wraps, which is happening now.
        assert ("data-ai", "prompt engineer") in got and ("data-ai", "MLOps engineer") in got
        # ...and the next bold marker still ends the block
        assert ("data-ai", "not a query") not in got
        assert got == [("data-ai", "data analyst"), ("data-ai", "AI engineer"),
                       ("data-ai", "prompt engineer"), ("data-ai", "MLOps engineer"),
                       ("pa-ea", "executive assistant"), ("pa-ea", "chief of staff")], got
        # The `## Master query list` block is a DERIVED, de-duplicated copy of the same lines.
        # Parsing it adds nothing and files every query under lane "" — the column
        # verify_run's coverage check reads.
        assert not any(lane == "" for lane, _ in got), got
        assert ("", "something only in the master list") not in got

        assert lane_for("Premium security · concierge") == "security-premium"
        assert lane_for("Agri-food · plant science") == "agri-food"
        assert lane_for("AI adoption · enablement · transformation consulting") == "ai-adoption"
        assert lane_for("Retail · hospitality · venue management") == "retail-hospitality"
        assert lane_for("Research · academic") == "research"  # 'retail' prefix must not shadow it
        assert lane_for("What the critics said") == ""
        # an explicit backticked token beats every prefix guess — a second user's lanes need
        # no edit to this table
        assert lane_for("Marine engineering (`marine-eng`)") == "marine-eng"
        assert lane_for("Retail · but really `venue-ops`") == "venue-ops"
        assert lane_for("Master query list") == ""

        # broad-to-narrow, for free and with no landscape call. Cheapest-first did the exact
        # opposite and starved the queries with the most to give — see order_queries.
        o = order_queries([("a", "senior data quality analyst"), ("a", "data analyst")])
        assert o[0][1] == "data analyst", o

        # every source must have a page size, a platform label and a page cap, or a sweep
        # KeyErrors halfway through a run rather than at startup
        assert set(PLATFORM) == set(PAGE_SIZE) == set(MAX_PAGES)
        assert "nhs" in PLATFORM

        # landscape round-trip and resume set
        land_p = os.path.join(tmp, "landscape.csv")
        append_rows(land_p, LANDSCAPE_COLUMNS,
                    [{"platform": "Adzuna", "lane": "data-ai", "query": "AI engineer",
                      "total": 146, "note": ""}])
        assert read_landscape(land_p, "Adzuna") == {("data-ai", "AI engineer"): 146}

        q_p = os.path.join(tmp, "queries.csv")
        append_rows(q_p, QUERY_COLUMNS, [{"platform": "Adzuna", "lane": "data-ai",
                                          "query": "AI engineer", "raw_hits": 146,
                                          "after_gate": 9, "new_vs_ledger": 9, "note": ""}])
        assert done_queries(q_p, "Adzuna") == {("data-ai", "AI engineer")}
        # an auth row is NOT done: after re-keying, a plain re-run must redo exactly those
        append_rows(q_p, QUERY_COLUMNS, [{"platform": "Adzuna", "lane": "data-ai",
                                          "query": "AI lead", "raw_hits": 0, "after_gate": 0,
                                          "new_vs_ledger": 0, "note": AUTH_NOTE}])
        assert done_queries(q_p, "Adzuna") == {("data-ai", "AI engineer")}
        assert AUTH_NOTE.startswith("auth:")          # the prefix verify_run keys on

        # --- the date stop: incremental runs ---------------------------------------------
        import datetime as _dt
        from harvest import date_stopper as _ds, all_of as _all, DATE_SORTED as _DS
        cut = _dt.date(2026, 8, 20)
        stop = _ds(cut, _dt.date(2026, 8, 22))
        # a page with something recent keeps going
        assert stop([{"posted": "22/08/2026"}, {"posted": "01/01/2020"}]) is True
        # ...and it takes the NEWEST on the page, not the first: boards float featured adverts
        # to the top out of date order, so first-row logic would end a query on a promoted ad
        assert stop([{"posted": "01/01/2020"}, {"posted": "21/08/2026"}]) is True
        # every dated row older than the cutoff -> stop
        assert stop([{"posted": "19/08/2026"}, {"posted": "01/01/2020"}]) is False
        # NO parseable date must never stop a sweep — unparseable dates are a scraping problem,
        # and treating them as "old" would silently end every query after a markup change
        assert stop([{"posted": ""}, {"posted": "not a date"}]) is True
        assert stop([]) is True

        # REED MUST NEVER BE DATE-STOPPED. Its default order is arbitrary (a real page 1 read
        # Apr, Aug, Aug, Jul, Dec-2025), so stopping on date would discard live adverts.
        assert "reed" not in _DS
        assert {"adzuna", "nhs", "jobsacuk", "totaljobs"} <= _DS

        # all_of runs EVERY callback even once one has said stop, or the novelty set stops
        # being updated and the call counter stops counting
        seen = []
        c = _all(lambda b: (seen.append("a"), False)[1], lambda b: (seen.append("b"), True)[1])
        assert c([]) is False and seen == ["a", "b"], seen

        print("sweep self-check OK")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
