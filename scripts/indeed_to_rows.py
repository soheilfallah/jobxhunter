#!/usr/bin/env python3
"""Turn the Indeed MCP connector's markdown into the import_rows.py JSON contract.

The Indeed connector (claude.ai OAuth) returns MARKDOWN, not JSON, and a script cannot call
it — so the agent runs the searches, saves each response to a file, and this converts the batch.
Then `import_rows.py` puts the rows through the same gate, ledger and query log a harvester's
rows go through.

WHAT THE CONNECTOR ACTUALLY GIVES YOU — measured 22 Aug 2026, and each of these shapes the
pipeline around it:

  * ~10 results per call, and NO pagination parameter. One call is one page, permanently.
  * NO salary. Every row comes back `Compensation: N/A`; the figure is in the advert body,
    which `fetch_jds` picks up at L2. So salary_min/max are null here, never 0.
  * NO recency filter, and the results are mostly OLD. Of 30 rows pulled across three queries,
    ONE was posted within three days. Expect the standard --max-days-old 3 to drop almost all
    of it; that is the source being stale, not the gate being wrong.
  * `Job Id` is a per-response COUNTER — "JOBSEARCH_510", then 511, 512... It is not a job
    identifier: the same advert gets a different number in the next call. It is dropped here,
    and the URL is the key. `import_rows` dedupes on the canonical URL when job_id is empty.
  * The id IS resolvable by `get_job_details` within the same session, so if you want the full
    advert text from Indeed, fetch it in the SAME agent pass as the search. Do not defer it.
  * The location filter is loose. "London" returns Chertsey, Sevenoaks, Dartford and Brentwood.
    Let the ranker sort it out rather than trying to tighten the query.

Usage:
  1. Agent runs mcp__claude_ai_Indeed__search_jobs and saves each response body to a .md file.
  2. Write a manifest: [["path.md", "<lane>", "<query>"], ...]
  3. python indeed_to_rows.py <manifest.json> <out.json>
  4. python import_rows.py --workspace <dir> --source indeed --platform Indeed --rows <out.json>

  python indeed_to_rows.py --self-check
"""
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import enable_utf8_io  # noqa: E402
enable_utf8_io()

FIELD = re.compile(
    r"\*\*Job Title:\*\*\s*(?P<title>.*?)\n"
    r"\s*\*\*Job Id:\*\*\s*(?P<jid>.*?)\n"
    r"\s*\*\*Company:\*\*\s*(?P<company>.*?)\n"
    r"\s*\*\*Location:\*\*\s*(?P<location>.*?)\n"
    r"\s*\*\*Posted on:\*\*\s*(?P<posted>.*?)\n"
    r"\s*\*\*Job Type:\*\*\s*(?P<jobtype>.*?)\n"
    r"\s*\*\*Compensation:\*\*\s*(?P<pay>.*?)\n"
    r"\s*\*\*View Job URL:\*\*\s*(?P<url>\S+)", re.S)

BLANK = ("none", "n/a", "")


def _clean(v):
    v = (v or "").strip()
    return "" if v.lower() in BLANK else v


def iso(text):
    """'August 18, 2026' -> '2026-08-18'. Anything unparseable -> '' — never a guessed date.

    An empty `posted` simply never trips the recency drop, which is the safe failure: a role
    kept with an unknown date costs one read, a role dropped on a misparsed date is invisible.
    """
    try:
        return datetime.datetime.strptime((text or "").strip(), "%B %d, %Y").date().isoformat()
    except ValueError:
        return ""


def parse(md, lane, query):
    rows = []
    for m in FIELD.finditer(md or ""):
        d = m.groupdict()
        rows.append({
            "job_id": "",          # deliberately dropped — see the module docstring
            "title": _clean(d["title"]),
            "company": _clean(d["company"]),
            "location": _clean(d["location"]),
            "salary_min": None,    # never in the search response; null, never 0
            "salary_max": None,
            "posted": iso(d["posted"]),
            "contract": _clean(d["jobtype"]),
            "url": _clean(d["url"]),
        })
    return {"lane": lane, "query": query, "total": len(rows),
            "note": "via Indeed MCP connector", "rows": rows}


def self_check():
    md = ("**Job Title:** Data Analyst\n"
          "            **Job Id:** JOBSEARCH_512\n"
          "            **Company:** ITV\n"
          "            **Location:** London\n"
          "            **Posted on:** August 18, 2026\n"
          "            **Job Type:** Full-time\n"
          "            **Compensation:** N/A\n"
          "            **View Job URL:** https://to.indeed.com/aalj7sc8w78z\n"
          "\n"
          "**Job Title:** IT Support Apprentice\n"
          "            **Job Id:** JOBSEARCH_529\n"
          "            **Company:** None\n"
          "            **Location:** Staines-upon-Thames\n"
          "            **Posted on:** not a date\n"
          "            **Job Type:** N/A\n"
          "            **Compensation:** N/A\n"
          "            **View Job URL:** https://to.indeed.com/aam8cqt4zvh9\n")
    g = parse(md, "data-ai", "data analyst")
    assert g["total"] == 2 and g["lane"] == "data-ai"
    a, b = g["rows"]
    assert a["title"] == "Data Analyst" and a["company"] == "ITV"
    assert a["posted"] == "2026-08-18"
    assert a["url"] == "https://to.indeed.com/aalj7sc8w78z"
    # the per-response counter must NOT become the job id — it is reused across calls, so
    # keying on it would merge unrelated adverts and miss real duplicates
    assert a["job_id"] == "" and b["job_id"] == ""
    # salary is null, never 0: 0 would read as "advertised at zero pay"
    assert a["salary_min"] is None and a["salary_max"] is None
    # "None" / "N/A" are the connector's empties, not values
    assert b["company"] == "" and b["contract"] == ""
    # an unparseable date is empty, never guessed — it then never trips the recency drop
    assert b["posted"] == ""
    # a note is always present, or verify_run reads Indeed's zero as an unexplained dead source
    assert g["note"]
    assert parse("", "x", "y")["total"] == 0
    print("indeed_to_rows self-check OK")
    return 0


def main():
    if "--self-check" in sys.argv:
        return self_check()
    if len(sys.argv) < 3:
        raise SystemExit("usage: indeed_to_rows.py <manifest.json> <out.json>  |  --self-check")
    manifest, out = sys.argv[1], sys.argv[2]
    base = os.path.dirname(os.path.abspath(manifest))
    groups = []
    with open(manifest, encoding="utf-8") as fh:
        for path, lane, query in json.load(fh):
            full = path if os.path.isabs(path) else os.path.join(base, path)
            with open(full, encoding="utf-8") as f:
                groups.append(parse(f.read(), lane, query))
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(groups, fh, indent=1)
    print(f"{len(groups)} group(s), {sum(len(g['rows']) for g in groups)} row(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
