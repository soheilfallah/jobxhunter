#!/usr/bin/env python3
"""L2 — fetch the FULL job description for the top of ranked.csv, so fit stops being a guess.

L1 judges a role on its title and its advertised salary. Both are written by the recruiter,
and both lie: a title is padded to attract applicants and a salary range is an aspiration.
Nothing about whether the work suits the candidate is knowable until the description is read, so no CV
should be tailored from a ranked.csv row alone.

Fetching is not uniform across the boards, and the cheap paths are worth exhausting first:

  reed        the API returns jobDescription in full, free and unmetered  -> always use it
  adzuna      403s a plain request. But Adzuna is an AGGREGATOR: most of its adverts are
              syndicated from boards that do answer, Reed among them. So the advert is looked
              up on Reed by exact employer + title, and only what genuinely has no mirror is
              left for a paid scraper. Every credit spent here is a credit not spent on a
              role that was free to read.
  jobsacuk    plain GET, same as the harvest
  totaljobs   plain GET, same as the harvest
  nhs         plain GET, same as the harvest
  scraper     LAST, and only when every free path above has missed. `scrape.py` calls the
              scraper services over ordinary HTTP with a rotated key, so a script can reach
              them — the MCP servers never were reachable from here. Disable with --no-scraper.

Adding that last step is the difference between reading a day's shortlist and reading half of it:
on the 22 Aug 2026 run, `needs-scraper` swallowed 76 of 150 adverts, every one of them Adzuna.
They were ranked, they were wanted, and nothing came after the free paths.

Anything still unfetched is written out as a stub carrying its URL and marked
`needs-scraper`, never silently dropped — an unread advert must stay visible as unread.

Reads   <workspace>/tasks/daily/<date>/ranked.csv
Writes  <workspace>/tasks/daily/<date>/jds/<source>-<id>.md   one advert per file
        <workspace>/tasks/daily/<date>/jds/index.csv          what was fetched, and how

Usage:
  python fetch_jds.py --workspace <dir> [--date YYYY-MM-DD] [--top 40] [--lane data-ai]
  python fetch_jds.py --self-check
"""
import argparse
import base64
import csv
import datetime
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import resolve_workspace_root, enable_utf8_io  # noqa: E402
from harvest import creds  # one credential loader, not a second one  # noqa: E402
enable_utf8_io()

INDEX_COLUMNS = ["rank", "score", "status", "via", "words", "title", "company", "location",
                 "salary_min", "salary_max", "pay_basis", "pay_note", "posted", "true_lane",
                 "source", "file", "url"]

# A DAY RATE ANNUALISED IS NOT A SALARY. Adzuna publishes £650/day as salary_max 169000 and Reed
# reports the raw 650; consolidate then keeps the bigger figure across the two duplicates, so the
# honest one loses. Ranking is salary-ordered, so four of the top ten become contracts pretending
# to be six-figure jobs. Nothing in the list response says which — but the ADVERT always says, and
# by L2 the advert has been read. So the correction happens here, where the evidence finally is.
DAY_RATE = re.compile(
    r"(?i)£\s*(\d{2,4})(?:\s*(?:-|–|to)\s*£?\s*(\d{2,4}))?\s*(?:per day|p/?d\b|a day|/day|daily)")
DAY_WORDS = re.compile(r"(?i)\b(?:inside ir35|outside ir35|day rate|per day|p/?d\b|umbrella)\b")
HOURLY = re.compile(r"(?i)£\s*(\d{1,3}(?:\.\d+)?)\s*(?:per hour|ph\b|/hour|an hour|hourly)")


# SECURITY CLEARANCE IN THE BODY, WHICH IS THE ONLY PLACE MOST ADVERTS PUT IT.
# `rank.py` carries a CLEARANCE pattern too, but it runs before any advert is fetched, so it can
# only read the title — and a title says "AI Governance Lead" while the requirements list says
# "Must be eligible for security clearance". Found live 22 Aug 2026 on a £100k role that reached
# the shortlist clean. UK SC/DV/eDV/NPPV clearance needs a residency history many candidates do
# not have, whatever the role pays; catching it here saves the application, not just the read.
# Flagged rather than dropped — the row stays visible with its reason, and the profile decides.
CLEARANCE_BODY = re.compile(
    r"(?i)\b(?:"
    r"(?:security|sc|dv|edv|ctc|bpss|nppv)\s*(?:\d\s*)?clearance"
    r"|clearance\s*(?:is|will be|must be)?\s*(?:required|essential|mandatory)"
    r"|eligible (?:for|to obtain)\s+(?:\w+\s+){0,3}clearance"
    r"|must (?:hold|have|obtain|be able to obtain)\s+(?:\w+\s+){0,3}clearance"
    r"|(?:sc|dv|edv|ctc)[- ]cleared"
    r"|willing(?:ness)? to undergo\s+(?:\w+\s+){0,3}clearance"
    r")")


def clearance_from_text(body):
    """-> a note naming the clearance demand, or '' when the advert never asks for one."""
    if not body:
        return ""
    m = CLEARANCE_BODY.search(body)
    if not m:
        return ""
    i = max(0, m.start() - 90)
    quote = " ".join(body[i:m.end() + 90].split())
    return f"CLEARANCE REQUIRED — check eligibility against the profile. Advert says: \"...{quote}...\""


def pay_from_text(body):
    """-> (basis, note). 'annual' when the advert reads like a salary, 'day'/'hour' when it does
    not. Absence of evidence stays 'annual' — never invent a downgrade from silence."""
    if not body:
        return "", ""
    m = DAY_RATE.search(body)
    if m:
        lo, hi = m.group(1), m.group(2)
        rate = f"£{lo}–£{hi}/day" if hi else f"£{lo}/day"
        ir35 = " inside IR35" if re.search(r"(?i)inside ir35", body) else ""
        return "day", f"advert states {rate}{ir35} — the listed annual figure is that × ~260"
    m = HOURLY.search(body)
    if m:
        return "hour", f"advert states £{m.group(1)}/hour — not an annual salary"
    if DAY_WORDS.search(body):
        return "day", "advert uses day-rate/IR35 language — treat the annual figure as derived"
    return "annual", ""

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}

# Boilerplate every board wraps an advert in. Cutting it keeps the file about the job.
BOILER = re.compile(
    r"(?is)\b(?:cookie polic|privacy polic|by applying you (?:agree|consent)|"
    r"we are an equal opportunit|proud to be an equal|no agencies|recruitment agencies)\b")


def strip_html(raw):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw or "")
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", t)
    t = re.sub(r"(?i)<li[^>]*>", "\n- ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r"\n\s*\n\s*\n+", "\n\n", t)
    return "\n".join(line.strip() for line in t.splitlines()).strip()


def job_id(url, source):
    """The numeric advert id, which every one of these boards puts in the path."""
    nums = re.findall(r"/(\d{5,})", url or "")
    if nums:
        return nums[-1]
    m = re.search(r"[?&](?:jobId|id|advert)=(\d+)", url or "")
    if m:
        return m.group(1)
    return "x" + str(abs(hash(url or source)) % 10**9)


def readable_url(url, source):
    """Adzuna's `/jobs/land/ad/<id>` is a click-through interstitial: it carries no advert
    text, and a scraper pointed at it returns a page titled "Adzuna Jobs Search" from which an
    extractor will happily invent a plausible job description. `/jobs/details/<id>` is the same
    advert and does render. Always hand the readable form on."""
    if source == "adzuna" and "/jobs/land/ad/" in (url or ""):
        return f"https://www.adzuna.co.uk/jobs/details/{job_id(url, source)}"
    return url


def norm_name(s):
    """Compare an employer or a title on its substance, not its punctuation."""
    s = re.sub(r"\(.*?\)", " ", (s or "").lower())
    s = re.sub(r"\b(?:ltd|limited|llp|plc|group|uk|recruitment|recruiting|consultancy|"
               r"consulting|associates|partners|people|solutions|inc|the)\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(s.split())


# --------------------------------------------------------------------------- fetchers

def get(url, headers=None, timeout=45):
    req = urllib.request.Request(url, headers=headers or UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def reed_headers(key):
    return {"Authorization": "Basic " + base64.b64encode((key + ":").encode()).decode(),
            **UA}


def fetch_reed(jid, headers):
    d = json.loads(get(f"https://www.reed.co.uk/api/1.0/jobs/{jid}", headers))
    body = strip_html(d.get("jobDescription"))
    meta = {"salary": d.get("salary"), "salary_type": d.get("salaryType"),
            "contract": d.get("contractType"), "posted": d.get("datePosted"),
            "closes": d.get("expirationDate"), "applicants": d.get("applicationCount"),
            "apply": d.get("externalUrl") or d.get("jobUrl")}
    return body, meta


def reed_mirror(title, company, headers, pause=0.3):
    """Find the same advert on Reed. Reed's search ignores employerName as a filter, so the
    match is made here on the returned rows — a loose match would hand back a different job's
    description, which is worse than no description at all."""
    q = urllib.parse.urlencode({"keywords": title, "resultsToTake": 100})
    try:
        d = json.loads(get(f"https://www.reed.co.uk/api/1.0/search?{q}", headers))
    except Exception:
        return None
    time.sleep(pause)
    want_c, want_t = norm_name(company), norm_name(title)
    for r in d.get("results", []):
        if norm_name(r.get("employerName")) != want_c:
            continue
        got_t = norm_name(r.get("jobTitle"))
        if got_t == want_t or want_t in got_t or got_t in want_t:
            return str(r.get("jobId"))
    return None


def fetch_plain(url):
    body = strip_html(get(url))
    # The advert is the long run of prose in the middle; the nav and footer are short lines.
    return body, {}


def spread(rows, top, per_lane=0):
    """Take the best from each lane in turn, not the best `top` overall.

    Necessary from 22 Aug 2026, when rank.py stopped rejecting. The survivor set went from
    ~25-100 to thousands, score-ordered, so a plain head() spends the entire JD budget on
    aim-up titles from whichever lane scored highest — and the GBP30k data-entry role this
    relaxation exists to surface sits at rank 900 and is never read. Round-robin keeps every
    lane on the page, including `unmatched`, which is exactly where a role the keyword file
    never imagined turns up.

    Input must already be in rank order. dict insertion order means the best-scoring lane
    leads each round, so rank 1 overall is still first.
    """
    by_lane = {}
    for r in rows:
        by_lane.setdefault(r.get("true_lane") or "unmatched", []).append(r)
    if per_lane:
        for lane in by_lane:
            by_lane[lane] = by_lane[lane][:per_lane]
    out, tier = [], 0
    while len(out) < top:
        got = [q[tier] for q in by_lane.values() if len(q) > tier]
        if not got:
            break
        out.extend(got)
        tier += 1
    return out[:top]


def via_scraper(url, src):
    """Last resort, and the reason it exists: "needs-scraper" used to be where an advert died.

    On the 22 Aug 2026 run it swallowed 76 of 150 adverts, all Adzuna — ranked, wanted, and never
    read, because the free paths (Reed API, Reed mirror, plain GET) had all missed and nothing came
    after them. `scrape.py` calls the scraper services over plain HTTP with a rotated key, so a
    script can finally use them; MCP was never reachable from here.

    Costs credit, so it runs only after every free path has failed.
    """
    try:
        from scrape import NoScraper, fetch, trim_adzuna
    except ImportError:
        return "needs-scraper", "", "", {}
    # ALWAYS the readable form. `/jobs/land/ad/<id>` is a click-through interstitial carrying no
    # advert text — a scraper pointed at it returns "You are now being redirected to Total Jobs",
    # which is 400+ characters and therefore passes the length check as a successful fetch. Found
    # 22 Aug 2026 during triage: a dozen adverts had been "read" and were pure redirect stubs.
    # readable_url() has existed for exactly this since 15 Aug; the scraper path never called it.
    url = readable_url(url, src)
    try:
        text, who = fetch(url)
    except NoScraper as exc:
        return "needs-scraper", "", "", {"scraper_note": str(exc)}
    except Exception as exc:                                   # noqa: BLE001
        return f"error:{type(exc).__name__}", "", "", {}
    if src == "adzuna":
        text = trim_adzuna(text)
    return ("ok", f"scraper-{who}", text, {}) if len(text) > 400 else \
           ("needs-scraper", "", "", {})


def fetch_one(row, headers, use_scraper=True):
    """-> (status, via, body, meta). Free paths first; the scraper only if they all miss."""
    src, url = row["source"], row["url"]
    jid = job_id(url, src)
    try:
        if src == "reed":
            body, meta = fetch_reed(jid, headers)
            if body:
                return "ok", "reed-api", body, meta
            return via_scraper(url, src) if use_scraper else ("empty", "reed-api", "", meta)
        if src == "adzuna":
            # Reed carries a large share of Adzuna's agency listings and its API is free, so the
            # mirror is always worth a look before spending a scraper credit.
            mirror = reed_mirror(row["title"], row["company"], headers)
            if mirror:
                body, meta = fetch_reed(mirror, headers)
                meta["mirrored_from"] = url
                if body:
                    return "ok", "reed-mirror", body, meta
            return via_scraper(url, src) if use_scraper else ("needs-scraper", "", "", {})
        if src in ("jobsacuk", "totaljobs", "nhs"):
            body, meta = fetch_plain(url)
            if len(body) > 400:
                return "ok", src + "-html", body, meta
            return via_scraper(url, src) if use_scraper else ("needs-scraper", "", "", {})
    except urllib.error.HTTPError as e:
        return f"http-{e.code}", "", "", {}
    except Exception as e:                                     # noqa: BLE001
        return f"error:{type(e).__name__}", "", "", {}
    return via_scraper(url, src) if use_scraper else ("needs-scraper", "", "", {})


def write_jd(path, row, status, via, body, meta):
    lines = [f"# {row['title']}", "",
             f"- **Company** {row['company']}",
             f"- **Location** {row['location']}",
             f"- **Advertised** {row['salary_min']}–{row['salary_max']}  ({row['gate_verdict']})",
             f"- **Posted** {row['posted']}   **Source** {row['source']}   "
             f"**Lane** {row['true_lane']}   **Rank** {row['rank']} (score {row['score']})",
             f"- **URL** {readable_url(row['url'], row['source'])}",
             f"- **Fetched via** {via or 'NOT FETCHED'}   **Status** {status}"]
    for k, v in (meta or {}).items():
        if v not in (None, "", 0):
            lines.append(f"- **{k}** {v}")
    lines += ["", "---", ""]
    lines.append(body if body else
                 "_No description retrieved — open the URL above by hand, or run a scraper._")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace")
    ap.add_argument("--date", default=None)
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--per-lane", type=int, default=0,
                    help="0 = round-robin across lanes (default). Set a number to cap how "
                         "many adverts any single lane may contribute.")
    ap.add_argument("--lane", default=None, help="only this true_lane")
    ap.add_argument("--min-score", type=int, default=0)
    ap.add_argument("--no-scraper", action="store_true",
                    help="do not fall back to a paid scraper when the free paths miss; adverts "
                         "that would have been scraped are reported as needs-scraper instead")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()

    if args.self_check:
        return self_check()

    ws = resolve_workspace_root(args.workspace)
    if not ws:
        raise SystemExit("no workspace resolved")
    date = args.date or datetime.date.today().isoformat()
    day = os.path.join(ws, "tasks", "daily", date)
    src = os.path.join(day, "ranked.csv")
    if not os.path.isfile(src):
        raise SystemExit(f"no ranked.csv at {src} — run rank.py first")

    with open(src, encoding="utf-8-sig", newline="") as fh:
        # `startswith`, not `==`. rank.py now emits keep:unmatched and keep:penalised
        # alongside plain keep; an equality test silently drops both, which is a rejection
        # wearing a different name.
        rows = [r for r in csv.DictReader(fh) if r["verdict"].startswith("keep")]
    if args.lane:
        rows = [r for r in rows if r["true_lane"] == args.lane]
    if args.min_score:
        rows = [r for r in rows if int(r["score"] or 0) >= args.min_score]
    rows = spread(rows, args.top, args.per_lane)
    if not rows:
        raise SystemExit("nothing selected")

    out_dir = os.path.join(day, "jds")
    os.makedirs(out_dir, exist_ok=True)
    # Only load Reed credentials if a row actually needs them. Loading unconditionally made
    # a pure jobs.ac.uk / NHS run hard-fail on a missing REED_API_KEY it never used.
    headers = UA
    if any(r["source"] in ("reed", "adzuna") for r in rows):
        headers = reed_headers(creds("reed", None)["REED_API_KEY"])

    index, counts = [], {}
    cleared = []
    for i, r in enumerate(rows, 1):
        status, via, body, meta = fetch_one(r, headers, use_scraper=not args.no_scraper)
        counts[status] = counts.get(status, 0) + 1
        basis, note = pay_from_text(body)
        if note:
            meta = {**(meta or {}), "PAY BASIS": note}
        clr = clearance_from_text(body)
        if clr:
            meta = {**(meta or {}), "CLEARANCE": clr}
            cleared.append((r.get("title", ""), r.get("company", "")))
        name = f"{r['source']}-{job_id(r['url'], r['source'])}.md"
        write_jd(os.path.join(out_dir, name), r, status, via, body, meta)
        index.append({**{k: r.get(k, "") for k in INDEX_COLUMNS if k in r},
                      "status": status, "via": via, "file": name,
                      "pay_basis": basis, "pay_note": note,
                      "words": len(body.split())})
        print(f"  {i:>3}/{len(rows)}  {status:<14} {via:<12} {len(body.split()):>5}w  "
              f"{r['title'][:44]}")

    with open(os.path.join(out_dir, "index.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=INDEX_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(index)

    ok = sum(1 for r in index if r["status"] == "ok")
    print(f"\nfetched {ok}/{len(rows)} full descriptions -> {out_dir}")
    if cleared:
        print(f"  {len(cleared)} advert(s) DEMAND SECURITY CLEARANCE in the body — do NOT "
              f"tailor these. The title never says so, so rank.py cannot catch them:")
        for _t, _c in cleared[:8]:
            print(f"    {_t[:46]:48} {_c[:26]}")
    print("  " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])))
    notsalary = [r for r in index if r["pay_basis"] in ("day", "hour")]
    if notsalary:
        print(f"  {len(notsalary)} of these are NOT annual salaries — the ranked figure is a "
              f"day/hourly rate the board annualised:")
        for r in notsalary:
            print(f"    rank {r['rank']:>3}  listed £{float(r['salary_max'] or 0):,.0f}  "
                  f"{r['title'][:38]:40} {r['pay_note']}")
    short = [r for r in index if r["status"] == "ok" and r["words"] < 120]
    if short:
        print(f"  {len(short)} fetched but SHORT (<120 words) — check these read like a real "
              f"advert before tailoring from them")
    return 0


def self_check():
    assert job_id("https://www.reed.co.uk/jobs/senior-business-analyst/57224848", "reed") \
        == "57224848"
    assert job_id("https://www.adzuna.co.uk/jobs/land/ad/5840672428?se=x", "adzuna") \
        == "5840672428"
    assert job_id("https://www.adzuna.co.uk/jobs/details/5836452717?utm_medium=api", "adzuna") \
        == "5836452717"
    # no id in the path must not collide across two different adverts
    assert job_id("https://x.test/a", "totaljobs") != job_id("https://x.test/b", "totaljobs")

    assert strip_html("<p>One</p><p>Two</p>") == "One\nTwo"
    assert strip_html("<ul><li>A</li><li>B</li></ul>") == "- A\n- B"
    assert strip_html("<p>&#163;80,000 &amp; up</p>") == "£80,000 & up"
    assert strip_html("<style>p{color:red}</style><p>Real</p>") == "Real"
    assert strip_html("<script>var a='<p>fake</p>'</script><p>Real</p>") == "Real"

    # an employer matches through its suffixes, so the mirror is found...
    assert norm_name("Bright Purple Resourcing Ltd") == norm_name("Bright Purple Resourcing")
    assert norm_name("Harnham - Data & Analytics") == "harnham data analytics"
    # ...but two different employers must never be treated as one
    assert norm_name("Experis") != norm_name("Excelsior")

    # the interstitial must never be the URL a scraper is pointed at
    assert readable_url("https://www.adzuna.co.uk/jobs/land/ad/5836479733?se=x&v=y", "adzuna") \
        == "https://www.adzuna.co.uk/jobs/details/5836479733"
    assert readable_url("https://www.adzuna.co.uk/jobs/details/123456?utm=x", "adzuna") \
        == "https://www.adzuna.co.uk/jobs/details/123456?utm=x"
    assert readable_url("https://www.reed.co.uk/jobs/x/99", "reed") \
        == "https://www.reed.co.uk/jobs/x/99"

    # the day-rate correction: the exact adverts that ranked 3rd and 9th on fake six figures
    b, n = pay_from_text("Senior Data Engineer\nRate: To £650 p/d Inside IR35\nDuration: 6 months")
    assert b == "day" and "£650/day" in n and "inside IR35" in n, (b, n)
    b, n = pay_from_text("Edinburgh (Hybrid) Inside IR35 £525 - £600 per day")
    assert b == "day" and "£525–£600/day" in n, (b, n)
    assert pay_from_text("£400 - £450 per day, immediate start")[0] == "day"
    assert pay_from_text("Paying £17.50 per hour, 40 hours a week")[0] == "hour"
    assert pay_from_text("Outside IR35 contract, rate negotiable")[0] == "day"
    # a real salary must NOT be downgraded, and neither must silence
    assert pay_from_text("Salary £80,000-£100,000 DoE plus bonus")[0] == "annual"
    assert pay_from_text("£100,000 + 50% bonus + £6,500 car allowance")[0] == "annual"
    assert pay_from_text("Competitive salary, 25 days holiday a year")[0] == "annual"
    assert pay_from_text("")[0] == ""

    import tempfile
    import shutil
    tmp = tempfile.mkdtemp()
    try:
        row = {"title": "AI Engineer", "company": "Acme", "location": "London",
               "salary_min": "60000", "salary_max": "80000", "gate_verdict": "keep",
               "posted": "2026-08-13", "source": "reed", "true_lane": "data-ai",
               "rank": "1", "score": "4", "url": "https://x.test/1"}
        p = os.path.join(tmp, "t.md")
        write_jd(p, row, "ok", "reed-api", "Body text here", {"closes": "2026-09-01",
                                                              "applicants": 0})
        got = open(p, encoding="utf-8").read()
        assert "# AI Engineer" in got and "Body text here" in got
        assert "**closes** 2026-09-01" in got
        assert "applicants" not in got          # empty metadata is omitted, not printed as 0
        # an unfetched advert still gets a file, and says so
        write_jd(p, row, "needs-scraper", "", "", {})
        got = open(p, encoding="utf-8").read()
        assert "NOT FETCHED" in got and "https://x.test/1" in got
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # A `keep:` caveat is still a keep. An exact == "keep" filter silently drops every
    # unmatched and lane-penalised row rank.py now deliberately keeps.
    assert "keep:unmatched".startswith("keep") and "keep:penalised:x".startswith("keep")

    # The JD budget is SPREAD across lanes, not spent on one lane's aim-up titles. Without
    # this the whole relaxation achieves nothing: the survivor set is now thousands deep and
    # a plain head() never reaches the junior roles it was relaxed to surface.
    rows = ([{"true_lane": "data-ai", "rank": i} for i in range(1, 21)]
            + [{"true_lane": "it-support", "rank": 21}, {"true_lane": "", "rank": 22}])
    got = spread(rows, 6)
    assert {r["true_lane"] or "unmatched" for r in got} == {"data-ai", "it-support", "unmatched"}
    assert got[0]["rank"] == 1                      # best of the best lane still leads
    assert len(got) == 6
    assert len(spread(rows, 100)) == len(rows)      # nothing lost when top exceeds the set
    assert spread([], 10) == []
    # a per-lane cap, when asked for, must bound the loud lane and not the quiet ones
    capped = spread(rows, 100, per_lane=2)
    assert sum(1 for r in capped if r["true_lane"] == "data-ai") == 2
    assert sum(1 for r in capped if r["true_lane"] == "it-support") == 1

    print("fetch_jds self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
