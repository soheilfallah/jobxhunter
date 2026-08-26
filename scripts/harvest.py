#!/usr/bin/env python3
"""Enumerate a WHOLE result set, not its first page, and reduce it to a triage table.

The problem this solves: a Reed search for "executive assistant" in London reports
totalResults 512, and the connector's default page size is 20. One call sees the top 4%
and the run has no idea the other 96% exist — the total is in the response and nobody
reads it. Paging through it via the model is not an option either: 100 Reed jobs is
~107KB of JSON, which blows the tool output limit outright.

So the pagination happens here, in a script, and only a compact CSV comes back:

  L0  enumerate   every page to the reported total          -> candidates.csv (all of them)
  L1  gate        salary / recency / dedupe, structured     -> the survivors are marked
  L2  read JDs    the caller fetches full text for survivors only
  L3  tailor

L2 is the expensive layer, so L1 has to be the honest one. It gates on the fields the
list response already carries and NEVER drops a row for a reason it cannot see: a hidden
salary and a suspiciously small figure (an hourly or day rate advertised raw, which is
Reed's standard trap) both survive as `salary_unclear` rather than being silently binned.

Every run appends a measured row to queries.csv, so the funnel numbers verify_run.py
checks are counted rather than typed from memory.

Usage:
  python harvest.py --workspace <dir> --source reed   --lane pa-ea --query "executive assistant" --where London
  python harvest.py --workspace <dir> --source adzuna --lane pa-ea --phrase "executive assistant" --where london
  python harvest.py --self-check
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
from _lib import resolve_workspace_root, enable_utf8_io, secret_env  # noqa: E402
from build_seen_ledger import canonical_key  # reuse the ledger's key, never a second one
enable_utf8_io()

CANDIDATE_COLUMNS = ["source", "lane", "query", "job_id", "title", "company", "location",
                     "salary_min", "salary_max", "posted", "contract", "url", "verdict"]
QUERY_COLUMNS = ["platform", "lane", "query", "raw_hits", "after_gate", "new_vs_ledger", "note"]

# Below this, an "annual" figure is really an hourly or day rate advertised raw. Reed does
# this constantly. Gating on it as though it were a salary throws away good roles.
IMPLAUSIBLE_ANNUAL = 3000

# Above this, or absurdly wide, the advertised range is a typo rather than an offer.
# jobs.ac.uk really does carry "£43,981 to £540,198" for a Careers Consultant — the error is
# in the source, not the parse. Ranking on that ceiling puts junk at the top of the day's
# list, so the wide figure is distrusted and the LOW end is used to gate instead.
IMPLAUSIBLE_TOP = 300_000
IMPLAUSIBLE_SPREAD = 10


def load_env(path, keys):
    out = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            if k in keys:
                out[k] = v.strip().strip('"').strip("'")
    return out


def creds(source, env_file=None, store=None):
    """API credentials, in order: an explicit --env-file, the environment, then the plugin's
    user-config (the same keys `setup_connectors.py` reports on). One loader for every script."""
    want = {"reed": ["REED_API_KEY"],
            "adzuna": ["ADZUNA_APP_ID", "ADZUNA_APP_KEY"]}[source]
    found = load_env(env_file, want) if env_file else {}
    for k in want:
        if k not in found and secret_env(k, store):
            found[k] = secret_env(k, store)
    missing = [k for k in want if k not in found]
    if missing:
        raise SystemExit(f"missing credential(s) {', '.join(missing)} for {source} — set them "
                         f"in the environment, in the plugin's user-config, or pass --env-file")
    return found


class QuotaExhausted(Exception):
    """The source said stop — 429, or 403 on a metered endpoint.

    Not a bug and not something the run can work around: it is the ONLY legitimate limit on
    how much of a board we enumerate. It is a distinct exception so the sweep
    can record it as a boundary and move to the next source, instead of burying it in a bare
    `except Exception` that reads identically to a parse error.
    """


class DeadCredential(Exception):
    """401 — the key pair is PRESENT and REJECTED. Not a quota: waiting never fixes it.

    Found 23 Aug 2026: a board answered 401 to a key pair that had worked the day before.
    Before this class a 401 fell to the sweep's bare `except Exception`, was logged as
    `error: HTTPError` on every one of ~390 queries, and verify_run counted the platform as
    sourced. A distinct exception lets the sweep stop the source, write a note that names the
    cause, and exit non-zero.
    """


def _open(req, timeout=45):
    """urlopen, with a 429 handled honestly: wait once if the server says how long, then give up.

    Without this, `except Exception` in the sweep turned a dead key into `error: HTTPError` —
    which lost the status code AND satisfied verify_run's "0 hits but there's a note" check,
    so an exhausted quota read as an explained empty platform. A 401 is now
    DeadCredential; 429/403 are QuotaExhausted.
    """
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            wait = exc.headers.get("Retry-After") if exc.headers else None
            try:                    # one wait, once, capped — turns "dead" into merely "slow"
                if wait and int(wait) <= 60:
                    time.sleep(int(wait))
                    return urllib.request.urlopen(req, timeout=timeout)
            except (ValueError, TypeError, urllib.error.HTTPError):
                pass
        if exc.code == 401:
            raise DeadCredential(f"HTTP 401 {exc.reason}") from exc
        if exc.code in (429, 403):
            raise QuotaExhausted(f"HTTP {exc.code} {exc.reason}") from exc
        raise


def get_json(url, headers=None, timeout=45):
    req = urllib.request.Request(url, headers=headers or {})
    with _open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


# WHICH BOARDS CAN BE STOPPED ON DATE — and the one that absolutely cannot.
#
# A date stop only works if the board returns newest first. Verified live 22 Aug 2026:
#   adzuna     sort_by=date, plus a server-side max_days_old — filtered before it reaches us
#   nhs        sort=publicationDateDesc          -> page 1 was five adverts from that same day
#   jobsacuk   sortOrder=1                       -> 20, 20, 19, 19, 18 Aug
#   totaljobs  ?sort=2                           -> 2 hours, 2 hours, 3 hours, 1 day, 1 day
#   reed       NOTHING. No date sort, no date filter.
#
# Reed's default order is genuinely arbitrary — a real page 1 read Apr, Aug, Aug, Jul, Dec-2025.
# Stopping Reed on date would therefore discard live adverts at page 2 because page 1 happened to
# contain something from December. It must be enumerated in full and gated locally, which is what
# `gate()` already does. Reed is free and fast (1,099 calls, 343s for 95,499 adverts), so this
# costs little; being wrong here would cost roles.
#
# Reed also SILENTLY IGNORES unknown query parameters — `postedWithin=1` returned the identical
# total of 2,013. So a plausible-looking filter that does nothing is the likely failure mode if
# anyone tries to add one later. Test any new Reed parameter against the total before trusting it.
DATE_SORTED = frozenset({"adzuna", "nhs", "jobsacuk", "totaljobs"})


def date_stopper(cutoff, today=None):
    """-> an `on_page` callback that stops a query once a page is entirely older than `cutoff`.

    This is what makes an incremental run possible: having swept fully today, tomorrow only needs
    what is new, and on a date-sorted board that means reading until the dates fall past the line
    and then stopping — rather than enumerating 126,581 adverts and discarding most of them in the
    local recency gate, which is what the 22 Aug run did.

    Deliberately conservative in two ways:
      * a page with NO parseable date never stops the sweep. Unparseable dates are a scraping
        problem, and treating them as "old" would end a query on a markup change.
      * it stops only when EVERY dated row on the page is older, not the first one. Boards float
        featured and promoted adverts to the top out of date order.
    """
    today = today or datetime.date.today()

    def on_page(batch):
        dates = [parse_posted(r.get("posted") or "") for r in batch]
        dates = [d for d in dates if d]
        if not dates:
            return True                      # nothing readable: never stop on ignorance
        return max(dates) >= cutoff

    return on_page


def all_of(*callbacks):
    """Combine `on_page` callbacks: EVERY one runs, and the page stops if any says stop.

    Running all of them matters — the novelty stopper mutates its seen-id set and counts calls, so
    short-circuiting on the first False would silently stop counting.
    """
    cbs = [c for c in callbacks if c]

    def on_page(batch):
        results = [c(batch) for c in cbs]
        return False not in results

    return on_page


def novelty_stopper(seen_ids, calls, min_new=1):
    """-> an `on_page` callback that counts REAL http calls and stops a query the moment a page
    adds nothing this run has not already collected.

    This replaces the per-source call budget deleted on 22 Aug 2026. The budget was a guess
    about how much of the overlap to pay for; this measures it. ~300 queries against one board
    are ~300 overlapping questions about the same inventory — `data analyst` and `insight
    analyst` return largely the same adverts — so a page with nothing new is the SOURCE saying
    it is finished, which is a different thing from us deciding to stop early.

    `seen_ids` is run-scoped and shared across every query in the sweep; that sharing is the
    whole mechanism. A broad query pays for the overlap once and every narrow rephrasing after
    it then costs exactly one page while still contributing its uniques.
    """
    def on_page(batch):
        calls[0] += 1
        keys = [str(r.get("job_id") or "") or canonical_key(r.get("url") or "") for r in batch]
        new = sum(1 for k in keys if k and k not in seen_ids)
        seen_ids.update(k for k in keys if k)
        return new >= min_new
    return on_page


# --------------------------------------------------------------------------- sources

def harvest_reed(key, query, where, distance, max_pages, page_size=100, on_page=None):
    """-> (rows, reported_total). Pages until the reported total is exhausted."""
    auth = base64.b64encode(f"{key}:".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    rows, total, skip, pages = [], None, 0, 0
    while pages < max_pages:
        q = {"resultsToTake": page_size, "resultsToSkip": skip}
        if query:
            q["keywords"] = query
        if where:
            q["locationName"] = where
        if distance is not None:
            q["distanceFromLocation"] = distance
        data = get_json("https://www.reed.co.uk/api/1.0/search?" + urllib.parse.urlencode(q),
                        headers)
        if total is None:
            total = int(data.get("totalResults") or 0)
        batch = data.get("results") or []
        if not batch:
            break
        for j in batch:
            rows.append({
                "job_id": j.get("jobId"),
                "title": (j.get("jobTitle") or "").strip(),
                "company": (j.get("employerName") or "").strip(),
                "location": (j.get("locationName") or "").strip(),
                "salary_min": j.get("minimumSalary"),
                "salary_max": j.get("maximumSalary"),
                "posted": (j.get("date") or "").strip(),      # dd/mm/yyyy
                "url": (j.get("jobUrl") or "").strip(),
            })
        # The novelty stop. Fires once per successful HTTP response, so it is the call
        # counter as well. Returning False means this page added nothing new to the run.
        if on_page and on_page(rows[-len(batch):]) is False:
            break
        skip += len(batch)
        pages += 1
        if total is not None and skip >= total:
            break
    return rows, (total if total is not None else len(rows))


# Adzuna is per-country: gb, ca, us, au... The workspace's market decides; gb is the default.
ADZUNA_COUNTRY = (os.environ.get("ADZUNA_COUNTRY") or "gb").lower()


def harvest_adzuna(app_id, app_key, params, max_pages, page_size=50, on_page=None):
    rows, total, page = [], None, 1
    while page <= max_pages:
        q = dict(params)
        q.update({"app_id": app_id, "app_key": app_key, "results_per_page": page_size})
        url = (f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/{page}?"
               + urllib.parse.urlencode({k: v for k, v in q.items() if v not in (None, "")}))
        data = get_json(url)
        if total is None:
            total = int(data.get("count") or 0)
        batch = data.get("results") or []
        if not batch:
            break
        for j in batch:
            rows.append({
                "job_id": j.get("id"),
                "title": (j.get("title") or "").strip(),
                "company": ((j.get("company") or {}).get("display_name") or "").strip(),
                "location": ((j.get("location") or {}).get("display_name") or "").strip(),
                # a PREDICTED salary is Adzuna's guess, not the advert's claim — don't gate on it
                "salary_min": None if str(j.get("salary_is_predicted")) == "1" else j.get("salary_min"),
                "salary_max": None if str(j.get("salary_is_predicted")) == "1" else j.get("salary_max"),
                "posted": (j.get("created") or "")[:10],
                # Adzuna annualises a day rate: £650/day is published as salary_max 169000, and
                # it then outranks every real permanent salary. The figure is arithmetically
                # right and completely misleading, so carry the basis alongside it.
                "contract": (j.get("contract_type") or "").strip(),
                "url": (j.get("redirect_url") or "").strip(),
            })
        # The novelty stop. Fires once per successful HTTP response, so it is the call
        # counter as well. Returning False means this page added nothing new to the run.
        if on_page and on_page(rows[-len(batch):]) is False:
            break
        page += 1
        if total is not None and len(rows) >= total:
            break
    return rows, (total if total is not None else len(rows))


JAC_RESULT = re.compile(
    r'<div class="j-search-result__result[^"]*"\s+data-advert-id="(?P<id>\d+)">(?P<body>.*?)'
    r'(?=<div class="j-search-result__result|<div id="pagination|</main)', re.S)
JAC_LINK = re.compile(r'<a href="(?P<href>/job/[^"]+)">\s*(?P<title>.*?)\s*</a>', re.S)
JAC_EMPLOYER = re.compile(r'j-search-result__employer.*?<b>\s*(?P<v>.*?)\s*</b>', re.S)
JAC_LOCATION = re.compile(r'<div>Location:\s*(?P<v>.*?)\s*</div>', re.S)
JAC_SALARY = re.compile(r'<strong>Salary:\s*</strong>\s*(?P<v>.*?)\s*(?:per annum|</div>)', re.S)
JAC_DATE = re.compile(r'<strong>Date Placed:\s*</strong>\s*(?P<v>[^<]*)', re.S)
TAGS = re.compile(r"<[^>]+>")


def _clean(s):
    return html.unescape(TAGS.sub("", s or "")).strip()


def _txt(m):
    return _clean(m.group("v")) if m else ""


def _jac_salary(text):
    """'£36,636 to £44,746' -> (36636.0, 44746.0). Anything non-numeric -> (None, None)."""
    nums = [float(n.replace(",", "")) for n in re.findall(r"£\s*([\d,]+(?:\.\d+)?)", text or "")]
    if not nums:
        return None, None
    return min(nums), max(nums)


def _jac_date(text, today):
    """'06 Aug' -> ISO. The year is absent from the page, so infer it: a date more than a
    week ahead of today belongs to last year, not the future."""
    try:
        d = datetime.datetime.strptime(f"{text.strip()} {today.year}", "%d %b %Y").date()
    except ValueError:
        return ""
    if (d - today).days > 7:
        d = d.replace(year=today.year - 1)
    return d.isoformat()


def harvest_jobsacuk(query, max_pages, page_size=25, today=None, on_page=None):
    """jobs.ac.uk has no API and no RSS, but its search page returns 200 to a plain
    request and its result markup is stable. 83 roles all-time in this tracker came from
    here and it had no connector at all."""
    today = today or datetime.date.today()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    rows, total, start = [], None, 1
    for _ in range(max_pages):
        url = ("https://www.jobs.ac.uk/search/?"
               + urllib.parse.urlencode({"keywords": query, "sortOrder": 1,
                                         "pageSize": page_size, "startIndex": start}))
        req = urllib.request.Request(url, headers=headers)
        with _open(req, timeout=45) as resp:
            html = resp.read().decode("utf-8", "replace")
        if total is None:
            m = re.search(r'job-count">(\d+)', html)
            total = int(m.group(1)) if m else 0
        found = 0
        for m in JAC_RESULT.finditer(html):
            body = m.group("body")
            link = JAC_LINK.search(body)
            if not link:
                continue
            lo, hi = _jac_salary(_txt(JAC_SALARY.search(body)))
            rows.append({
                "job_id": m.group("id"),
                "title": _clean(link.group("title")),
                "company": _txt(JAC_EMPLOYER.search(body)),
                "location": _txt(JAC_LOCATION.search(body)),
                "salary_min": lo, "salary_max": hi,
                "posted": _jac_date(_txt(JAC_DATE.search(body)), today),
                "url": "https://www.jobs.ac.uk" + link.group("href"),
            })
            found += 1
        if not found:
            break
        # The novelty stop. Fires once per successful HTTP response, so it is the call
        # counter as well. Returning False means this page added nothing new to the run.
        if on_page and on_page(rows[-found:]) is False:
            break
        start += page_size
        if start > (total or 0):
            break
    return rows, (total if total is not None else len(rows))


# --- Stepstone family: totaljobs.com, cwjobs.co.uk, milkround.com --------------------
# One parser, three boards: they are the same platform and serve byte-identical markup.
# Together they are a large slice of UK commercial inventory that had no connector at all.
STEPSTONE_HOSTS = {"totaljobs": "www.totaljobs.com",
                   "cwjobs": "www.cwjobs.co.uk",
                   "milkround": "www.milkround.com"}
# Totaljobs' headline total is mostly padding. Its own breakdown reads
#   total:6957,main:1,semantic:6956,regional:0,...
# for `glasshouse manager` — ONE real match and 6,956 loosely-related ads it volunteered.
# Trusting the headline would flood the day with tens of thousands of near-random roles, so
# `main` is the only figure treated as the result count, and the rows are cut to it.
SS_TOTAL = re.compile(r'searchResultsTotalJobCount(?:&#34;|")\s*:\s*(\d+)')
SS_MAIN = re.compile(r"main:(\d+)")
SS_STYLE = re.compile(r"<style.*?</style>", re.S)
SS_TITLE_HREF = re.compile(r'data-at="job-item-title"[^>]*?href="(?P<href>[^"]+)"'
                           r'|href="(?P<href2>[^"]+)"[^>]*?data-at="job-item-title"')
SS_ID = re.compile(r"-(\d{6,})")


def _ss_fields(page_html, name, window=500):
    """Every value for one `data-at` field, in document order.

    Per-card slicing is not usable here: the markup interleaves emotion <style> blocks and
    the same data-at values appear inside them as CSS selectors. Stripping styles then
    reading each field as its own ordered list, and zipping, is both shorter and sturdier.
    """
    out = []
    for m in re.finditer(r'data-at="%s"' % re.escape(name), page_html):
        seg = page_html[m.end():m.end() + window]
        gt = seg.find(">")                     # step out of the tag we landed inside
        seg = seg[gt + 1:] if gt >= 0 else seg
        # The window almost always ends mid-tag; that dangling `<path fill="curr...` has no
        # closing bracket, so the tag stripper cannot see it and it lands in the text.
        seg = re.sub(r"<[^>]*$", "", seg)
        out.append(" ".join(_clean(seg).split()))
    return out


def _ss_salary(text):
    """Stepstone prints '£45,000 - £55,000 per annum' or 'Competitive' or a day rate."""
    nums = [float(n.replace(",", "")) for n in re.findall(r"£\s*([\d,]+(?:\.\d+)?)", text or "")]
    if not nums:
        return None, None
    return min(nums), max(nums)


def _ss_posted(text, today):
    """'3 days ago' / 'Today' / 'Yesterday' -> ISO. Anything else -> '' (never guessed)."""
    t = (text or "").lower().strip()
    if "today" in t or "just now" in t or "hour" in t:
        return today.isoformat()
    if "yesterday" in t:
        return (today - datetime.timedelta(days=1)).isoformat()
    m = re.search(r"(\d+)\s*(day|week|month)", t)
    if not m:
        return ""
    n, unit = int(m.group(1)), m.group(2)
    days = n * {"day": 1, "week": 7, "month": 30}[unit]
    return (today - datetime.timedelta(days=days)).isoformat()


NHS_TOTAL = re.compile(r"([\d,]+)\s+jobs?\s+found")
NHS_CARD = re.compile(r'data-test="search-result"(.*?)(?=data-test="search-result"|</ul>)', re.S)
NHS_TITLE = re.compile(r'data-test="search-result-job-title"\s*>(?P<v>.*?)</a>', re.S)
NHS_HREF = re.compile(r'href="(?P<v>/candidate/jobadvert/[^"?]+)')
NHS_LOCBLOCK = re.compile(r'data-test="search-result-location"\s*>(?P<v>.*?)</div>\s*</h3>', re.S)
NHS_INNERLOC = re.compile(r'class="location-font-size"\s*>(?P<v>.*?)$', re.S)
NHS_SALARY = re.compile(r'data-test="search-result-salary"[^>]*>(?P<v>.*?)</li>', re.S)
NHS_DATE = re.compile(r'data-test="search-result-publicationDate"[^>]*>(?P<v>.*?)</li>', re.S)


def _nhs_date(text, today):
    """'Date posted: 17 August 2026' -> date(2026, 8, 17)."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text or "")
    if not m:
        return ""
    try:
        return datetime.datetime.strptime(" ".join(m.groups()), "%d %B %Y").date().isoformat()
    except ValueError:
        return ""


def harvest_nhs(query, where, max_pages, page_size=10, today=None, on_page=None):
    """-> (rows, reported_total). NHS Jobs answers a plain GET — no API, no key.

    Verified live 22 Aug 2026: 200, 84KB, "3354 jobs found", stable `data-test="search-result-*"`
    attributes, `&page=N` pagination, page size fixed at 10. It is the only place NHS band roles
    are advertised in full — Reed and Adzuna carry a thin slice.

    Parsed CARD BY CARD rather than by zipping parallel field lists the way harvest_stepstone
    does. That zip is positional: one card missing a salary shifts company, location and salary
    against title for every row after it, silently. Scoping each field to its own card costs a
    regex and removes the whole failure mode.
    """
    today = today or datetime.date.today()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    rows, total, page = [], None, 1
    while page <= max_pages:
        # sort=publicationDateDesc is what makes the date stop valid here; without it the
        # default order is relevance and page 1 mixes 7 Aug with 19 Aug.
        q = {"keyword": query or "", "language": "en", "page": page,
             "sort": "publicationDateDesc"}
        if where:
            q["location"] = where
        url = "https://www.jobs.nhs.uk/candidate/search/results?" + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers=headers)
        with _open(req, timeout=45) as resp:
            page_html = resp.read().decode("utf-8", "replace")
        if total is None:
            m = NHS_TOTAL.search(page_html)
            total = int(m.group(1).replace(",", "")) if m else 0
        found = 0
        for card in NHS_CARD.findall(page_html):
            href = NHS_HREF.search(card)
            if not href:
                continue
            loc_block = _txt(NHS_LOCBLOCK.search(card))
            inner = NHS_INNERLOC.search(NHS_LOCBLOCK.search(card).group("v")
                                        if NHS_LOCBLOCK.search(card) else "")
            location = _clean(inner.group("v")) if inner else ""
            # the employer is the h3 text BEFORE the nested location div
            employer = loc_block[:-len(location)].strip() if location and loc_block.endswith(location) \
                else loc_block
            lo, hi = _ss_salary(_txt(NHS_SALARY.search(card)))
            rows.append({
                "job_id": href.group("v").rsplit("/", 1)[-1],
                "title": _txt(NHS_TITLE.search(card)),
                "company": employer,
                "location": location,
                "salary_min": lo, "salary_max": hi,
                "posted": _nhs_date(_txt(NHS_DATE.search(card)), today),
                "url": "https://www.jobs.nhs.uk" + href.group("v"),
            })
            found += 1
        if not found:
            break
        if on_page and on_page(rows[-found:]) is False:
            break
        page += 1
        if len(rows) >= (total or 0):
            break
    return rows, (total if total is not None else len(rows))


def harvest_stepstone(board, query, where, distance, max_pages, page_size=25, today=None, on_page=None):
    today = today or datetime.date.today()
    host = STEPSTONE_HOSTS[board]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/125 Safari/537.36"}
    slug = re.sub(r"[^a-z0-9]+", "-", (query or "").lower()).strip("-")
    loc = re.sub(r"[^a-z0-9]+", "-", (where or "").lower()).strip("-")
    rows, total = [], None
    for page in range(1, max_pages + 1):
        path = f"/jobs/{slug}" + (f"/in-{loc}" if loc else "")
        q = {"page": page, "sort": 2}      # 2 = newest first
        if distance is not None and loc:
            q["radius"] = distance
        url = f"https://{host}{path}?" + urllib.parse.urlencode(q)
        try:
            req = urllib.request.Request(url, headers=headers)
            with _open(req, timeout=45) as resp:
                page_html = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:          # slug has no landing page — not an error worth raising
                break
            raise
        if total is None:
            main = SS_MAIN.search(page_html)
            if main:
                total = int(main.group(1))
            else:
                m = SS_TOTAL.search(page_html)
                total = int(m.group(1)) if m else 0
        page_html = SS_STYLE.sub("", page_html)
        titles = _ss_fields(page_html, "job-item-title")
        # the company name sits behind an inline SVG, so it needs a wider window than the rest
        # the company name sits after a long inline SVG, so it needs a much wider window
        companies = _ss_fields(page_html, "job-item-company-name", 3000)
        locations = _ss_fields(page_html, "job-item-location", 300)
        salaries = _ss_fields(page_html, "job-item-salary-info", 200)
        ages = _ss_fields(page_html, "job-item-timeago", 200)
        links = [(a or b) for a, b in SS_TITLE_HREF.findall(page_html)]
        found = 0
        for i, raw_title in enumerate(titles):
            title = raw_title.split("  ")[0].strip()
            if not title:
                continue
            href = links[i] if i < len(links) else ""
            link = href if href.startswith("http") else (f"https://{host}{href}" if href else "")
            jid = SS_ID.search(href or "")
            lo, hi = _ss_salary(salaries[i] if i < len(salaries) else "")
            rows.append({
                "job_id": jid.group(1) if jid else "",
                "title": title,
                "company": (companies[i].split("  ")[0].strip() if i < len(companies) else ""),
                "location": (locations[i].split("  ")[0].strip() if i < len(locations) else ""),
                "salary_min": lo, "salary_max": hi,
                "posted": _ss_posted(ages[i] if i < len(ages) else "", today),
                "url": link,
            })
            found += 1
        if not found or len(rows) >= (total or 0):
            break
        # The novelty stop. Fires once per successful HTTP response, so it is the call
        # counter as well. Returning False means this page added nothing new to the run.
        if on_page and on_page(rows[-found:]) is False:
            break
    # Semantic padding is appended after the genuine matches, so cutting to `main` keeps the
    # real ones and discards the volunteered near-misses.
    if total is not None:
        rows = rows[:total]
    return rows, (total if total is not None else len(rows))


# ------------------------------------------------------------------------ the L1 gate

def parse_posted(text):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(text.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def gate(row, min_salary, max_days_old, today, seen, title_any=()):
    """-> verdict string. 'keep' or 'keep:<caveat>' survives to L2; anything else is filtered.

    Only ever drops on evidence actually present in the row. Absent or implausible data
    is a reason to look harder at L2, not a reason to bin the role unseen. Every row is
    written to candidates.csv whatever the verdict, so a filtered role is recoverable by
    reading the file — the gate narrows what gets a JD fetch, it never loses anything.
    """
    key = canonical_key(row.get("url") or "")
    if key and key in seen:
        return "drop:already-seen"

    # Reed and Adzuna both match the DESCRIPTION as well as the title, so a keyword search
    # drags in roles that merely mention it ("...supporting the Executive Assistant...").
    if title_any:
        title = (row.get("title") or "").lower()
        if not any(t in title for t in title_any):
            return "drop:title-mismatch"

    if max_days_old:
        posted = parse_posted(row.get("posted") or "")
        if posted and (today - posted).days > max_days_old:
            return f"drop:older-than-{max_days_old}d"

    # The salary LABEL is computed for every row; only the FLOOR COMPARISON is conditional.
    #
    # This used to read `if min_salary:`, which was fine while the floor was £35,000 and
    # catastrophic the moment it went to 0 (22 Aug 2026: "no harm in applying"). At 0 the whole
    # block was skipped, so every row returned a bare "keep" and `keep:salary-suspect` stopped
    # existing — and BOTH `consolidate.salary_key` and `rank.salary_of` key on that label to
    # judge a suspect advert on its floor instead of its ceiling. Losing it puts the £1.2m
    # typo'd Data Protection Officer back at rank 1, which is the exact bug those two functions
    # were written to kill. Relaxing a threshold must not silently disable the measurement.
    nums = []
    for v in (row.get("salary_min"), row.get("salary_max")):
        if v in (None, ""):
            continue
        try:
            nums.append(float(v))
        except (TypeError, ValueError):
            pass
    top, bottom = (max(nums), min(nums)) if nums else (0, 0)

    if top == 0:
        return "keep:salary-undisclosed"
    if top < IMPLAUSIBLE_ANNUAL:
        return "keep:salary-unclear"           # hourly/day rate advertised raw
    if top > IMPLAUSIBLE_TOP or (bottom and top > bottom * IMPLAUSIBLE_SPREAD):
        # Distrust the ceiling; judge on the floor so a typo cannot promote or bin a role.
        # With min_salary 0 the floor test is always true, so a suspect row is labelled and
        # kept rather than dropped — which is the whole point of the label.
        return ("keep:salary-suspect" if bottom >= min_salary
                else f"drop:below-{min_salary}")
    if min_salary and top < min_salary:
        return f"drop:below-{min_salary}"
    return "keep"


def append_rows(path, columns, rows):
    """Append, honouring the header the file ALREADY has. Writing today's column list into a
    file opened with yesterday's shifts every value one place left from the first new column
    on, and a CSV never complains — a salary lands in `posted` and the run looks fine."""
    new = not os.path.isfile(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not new:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            existing = next(csv.reader(fh), None)
        if existing:
            columns = existing
    with open(path, "a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerows(rows)


def load_seen(workspace):
    path = os.path.join(workspace, "applications", "daily-hunt", "seen-jobs.csv")
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return {(r.get("job_key") or "").strip() for r in csv.DictReader(fh) if r.get("job_key")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace")
    ap.add_argument("--source", choices=["reed", "adzuna"])
    ap.add_argument("--lane", default="")
    ap.add_argument("--query", default="", help="reed keywords / adzuna `what`")
    ap.add_argument("--phrase", default="", help="adzuna what_phrase — an EXACT phrase")
    ap.add_argument("--any-of", default="", help="adzuna what_or — SINGLE words only, see --help-or")
    ap.add_argument("--where", default="")
    ap.add_argument("--distance", type=int, default=None, help="reed MILES / adzuna km")
    ap.add_argument("--min-salary", type=int, default=0,
                    help="0 = no floor (default; agrees with run_hunt). The salary "
                         "plausibility labels are computed either way.")
    ap.add_argument("--max-days-old", type=int, default=None)
    ap.add_argument("--title-any", default="",
                    help="comma-separated substrings; a row whose TITLE contains none is marked "
                         "drop:title-mismatch (still written to candidates.csv, never lost). "
                         "Omit to keep every title — the safer default when hunting variants.")
    ap.add_argument("--max-pages", type=int, default=20,
                    help="ceiling on pages; a truncated harvest is reported in the note")
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
    date = args.date or datetime.date.today().isoformat()
    today = datetime.date.today()
    seen = load_seen(ws)

    if args.any_of and len(args.any_of.split()) > 1 and args.source == "adzuna":
        print("NOTE: adzuna what_or ORs individual WORDS, not phrases — "
              "'executive assistant' matches every 'assistant' advert. Use --phrase per title.",
              file=sys.stderr)

    c = creds(args.source, args.env_file)
    if args.source == "reed":
        label = args.query
        rows, total = harvest_reed(c["REED_API_KEY"], args.query, args.where,
                                   args.distance, args.max_pages)
    else:
        label = args.phrase or args.any_of or args.query
        rows, total = harvest_adzuna(
            c["ADZUNA_APP_ID"], c["ADZUNA_APP_KEY"],
            {"what": args.query or None, "what_phrase": args.phrase or None,
             "what_or": args.any_of or None, "where": args.where or None,
             "distance": args.distance, "max_days_old": args.max_days_old},
            args.max_pages)

    title_any = tuple(t.strip().lower() for t in args.title_any.split(",") if t.strip())
    for r in rows:
        r.update(source=args.source, lane=args.lane, query=label,
                 verdict=gate(r, args.min_salary, args.max_days_old, today, seen, title_any))

    kept = [r for r in rows if r["verdict"].startswith("keep")]
    fresh = [r for r in kept if canonical_key(r.get("url") or "") not in seen]
    truncated = len(rows) < total
    note = f"truncated at {args.max_pages} pages: enumerated {len(rows)} of {total}" if truncated else ""

    out = os.path.join(ws, "tasks", "daily", date)
    append_rows(os.path.join(out, "candidates.csv"), CANDIDATE_COLUMNS, rows)
    append_rows(os.path.join(out, "queries.csv"), QUERY_COLUMNS, [{
        "platform": {"reed": "Reed", "adzuna": "Adzuna"}[args.source],
        "lane": args.lane, "query": label, "raw_hits": total,
        "after_gate": len(kept), "new_vs_ledger": len(fresh), "note": note}])

    print(f"{args.source}/{args.lane}: {label!r}")
    print(f"  reported total   {total}")
    print(f"  enumerated       {len(rows)}" + ("  <-- TRUNCATED, raise --max-pages" if truncated else ""))
    print(f"  past the gate    {len(kept)}")
    print(f"  new vs ledger    {len(fresh)}   <- fetch JDs for these only")
    print(f"  -> {os.path.join(out, 'candidates.csv')}")
    return 0


def self_check():
    import tempfile
    import shutil
    today = datetime.date(2026, 8, 12)
    seen = {canonical_key("https://www.reed.co.uk/jobs/x/111")}

    def g(row, min_salary=35000, days=None):
        return gate(row, min_salary, days, today, seen)

    # --- min_salary 0: the FLOOR is gone, the plausibility LABELS are not ----------------
    # `if min_salary:` used to skip this whole block at 0, which quietly killed
    # keep:salary-suspect. consolidate.salary_key and rank.salary_of both key on that label
    # to rank a suspect advert on its floor; without it a typo'd ceiling heads the day.
    def g0(row):
        return gate(row, 0, None, today, seen)
    assert g0({"salary_min": 20000, "salary_max": 25000}) == "keep"
    assert g0({"salary_min": 15.5, "salary_max": 18.0}) == "keep:salary-unclear"
    assert g0({"salary_min": None, "salary_max": None}) == "keep:salary-undisclosed"
    assert g0({"salary_min": 43981, "salary_max": 540198}) == "keep:salary-suspect"
    assert g0({"salary_min": 20000, "salary_max": 540198}) == "keep:salary-suspect"
    # nothing whatsoever drops on pay at floor 0
    for r in ({"salary_min": 1}, {"salary_max": 5}, {"salary_min": 28000, "salary_max": 30000}):
        assert not g0(r).startswith("drop:below"), r
    # ...and the rejects that are NOT about money are untouched by the relaxation
    assert g0({"url": "https://www.reed.co.uk/jobs/x/111"}) == "drop:already-seen"
    assert gate({"posted": "01/07/2026"}, 0, 7, today, seen).startswith("drop:older-than")
    # a garbage salary string must not crash the gate, and must read as undisclosed rather
    # than as zero pay
    assert g0({"salary_min": "GBP31,049", "salary_max": None}) == "keep:salary-undisclosed"

    # a real salary below the floor goes; at or above it stays
    assert g({"salary_min": 20000, "salary_max": 25000}) == "drop:below-35000"
    assert g({"salary_min": 40000, "salary_max": 45000}) == "keep"
    # undisclosed and raw hourly/day rates SURVIVE — the whole point of the gate
    assert g({"salary_min": None, "salary_max": None}) == "keep:salary-undisclosed"
    assert g({"salary_min": 0, "salary_max": 0}) == "keep:salary-undisclosed"
    assert g({"salary_min": 15.5, "salary_max": 18.0}) == "keep:salary-unclear"
    assert g({"salary_min": 250, "salary_max": 300}) == "keep:salary-unclear"
    # a typo'd ceiling is distrusted, and judged on the floor instead of promoted
    assert g({"salary_min": 43981, "salary_max": 540198}) == "keep:salary-suspect"
    assert g({"salary_min": 20000, "salary_max": 540198}) == "drop:below-35000"
    assert g({"salary_min": 40000, "salary_max": 62160}) == "keep"      # normal wide range
    # already in the ledger
    assert g({"url": "https://www.reed.co.uk/jobs/x/111", "salary_min": 50000}) == "drop:already-seen"
    # recency, in both date formats, and a blank date never drops a row
    assert g({"posted": "01/07/2026", "salary_min": 50000}, days=7).startswith("drop:older-than")
    assert g({"posted": "2026-08-10", "salary_min": 50000}, days=7) == "keep"
    assert g({"posted": "", "salary_min": 50000}, days=7) == "keep"
    assert parse_posted("bogus") is None
    # jobs.ac.uk field parsing (no network)
    assert _jac_salary("£36,636 to £44,746") == (36636.0, 44746.0)
    assert _jac_salary("Competitive") == (None, None)
    assert _jac_date("06 Aug", today) == "2026-08-06"
    assert _jac_date("20 Dec", today) == "2025-12-20"      # future -> last year
    assert _jac_date("nonsense", today) == ""
    assert _clean("Principal Data &amp; AI <b>Trainer</b>") == "Principal Data & AI Trainer"
    # Stepstone/Totaljobs field parsing (no network)
    assert _ss_salary("£45,000 - £55,000 per annum") == (45000.0, 55000.0)
    assert _ss_salary("Competitive") == (None, None)
    assert _ss_posted("3 days ago", today) == "2026-08-09"
    assert _ss_posted("Today", today) == "2026-08-12"
    assert _ss_posted("Yesterday", today) == "2026-08-11"
    assert _ss_posted("", today) == ""
    # a window ending mid-tag must not leak the dangling fragment into the text
    frag = '<a data-at="job-item-title" href="/x">Data Scientist<span class="res-8wk'
    assert _ss_fields(frag, "job-item-title", 200) == ["Data Scientist"]
    # title layer: only bites when asked for, and matches on the title alone
    ta = ("executive assistant", "ea to", "chief of staff")
    assert gate({"title": "US UK Tax Senior Manager", "salary_min": 90000}, 35000, None,
                today, seen, ta) == "drop:title-mismatch"
    assert gate({"title": "EA to CEO & Founder", "salary_min": 90000}, 35000, None,
                today, seen, ta) == "keep"
    assert gate({"title": "US UK Tax Senior Manager", "salary_min": 90000}, 35000, None,
                today, seen, ()) == "keep"

    # predicted Adzuna salaries must not reach the gate as though advertised
    tmp = tempfile.mkdtemp()
    try:
        p = os.path.join(tmp, "a", "candidates.csv")
        append_rows(p, CANDIDATE_COLUMNS, [{"source": "reed", "title": "T", "verdict": "keep"}])
        append_rows(p, CANDIDATE_COLUMNS, [{"source": "reed", "title": "U", "verdict": "keep"}])
        with open(p, encoding="utf-8") as fh:
            got = list(csv.DictReader(fh))
        assert len(got) == 2 and got[1]["title"] == "U", got   # appends, one header
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- 401 is a DEAD CREDENTIAL: not a quota, not a generic error (23 Aug 2026) ---------
    import urllib.request as _ur

    def _raising(code):
        def _u(req, timeout=45):
            raise urllib.error.HTTPError("u", code, "nope", {}, None)
        return _u
    _real = _ur.urlopen
    try:
        for code, exc_cls in ((401, DeadCredential), (403, QuotaExhausted), (429, QuotaExhausted),
                              (500, urllib.error.HTTPError)):
            _ur.urlopen = _raising(code)
            try:
                _open(_ur.Request("https://x.test/"))
                raise AssertionError(f"HTTP {code} did not raise")
            except exc_cls:
                pass
    finally:
        _ur.urlopen = _real
    assert not issubclass(DeadCredential, QuotaExhausted)   # the sweep must tell them apart
    # a DIRECT harvest.py call must not reinstate a salary floor the orchestrator passes as 0.
    # regex, not a literal: an assert containing its own search string can never fail.
    _floors = re.findall(r'"--min-salary", type=int, default=(\d+)',
                         open(os.path.join(HERE, "harvest.py"), encoding="utf-8").read())
    assert _floors == ["0"], _floors
    # credentials: environment first, then the plugin's user-config store; a missing pair is a
    # SystemExit that NAMES the key, never a KeyError halfway through a sweep
    import json as _json
    _env_bak = {k: os.environ.pop(k, None) for k in ("REED_API_KEY", "ADZUNA_APP_ID", "ADZUNA_APP_KEY")}
    tmp = tempfile.mkdtemp()
    try:
        store = os.path.join(tmp, "creds.json")
        with open(store, "w", encoding="utf-8") as fh:
            _json.dump({"pluginSecrets": {"jobxhunter@some-marketplace": {
                "reed_api_key": "from-store", "adzuna_app_id": "id1"}}}, fh)
        from _lib import secret_env as _se
        assert _se("REED_API_KEY", store) == "from-store"
        os.environ["REED_API_KEY"] = "from-env"
        assert _se("REED_API_KEY", store) == "from-env"          # environment wins
        assert _se("ADZUNA_APP_KEY", store) == ""                # half a pair is not a pair
        assert _se("REED_API_KEY", os.path.join(tmp, "absent.json")) == "from-env"
        try:
            creds("adzuna", store=store)
            raise AssertionError("expected SystemExit for a missing Adzuna pair")
        except SystemExit as exc:
            # names exactly the missing half, not the pair
            assert "ADZUNA_APP_KEY" in str(exc) and "ADZUNA_APP_ID" not in str(exc), exc
        envf = os.path.join(tmp, "x.env")
        with open(envf, "w", encoding="utf-8") as fh:
            fh.write("ADZUNA_APP_ID='a'\nADZUNA_APP_KEY=\"b\"\n")
        assert creds("adzuna", envf) == {"ADZUNA_APP_ID": "a", "ADZUNA_APP_KEY": "b"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for k, v in _env_bak.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    print("harvest self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
