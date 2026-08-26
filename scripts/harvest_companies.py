#!/usr/bin/env python3
"""Read vacancies straight off employers' own job boards, for a list of companies.

WHY THIS EXISTS. Every source in the pipeline is a JOB BOARD, and a board only holds what an
employer chose to advertise there. A large share of vacancies — whole sectors of small firms,
and the "we're hiring" page at a company nobody syndicates from — live only on the employer's
own careers page. Sourcing hundreds of thousands of adverts from five boards still misses them.

HOW, without a per-company scraper. Most employers do not build a careers page; they embed an
applicant tracking system, and the big ATSes serve their board as PUBLIC JSON, no key, no
scraping. So this takes a company NAME, guesses slugs from it, and probes each ATS until one
answers. The resolved (company -> ats, slug) is cached, so the second run is one call, not six.

Rows come out in `import_rows.py`'s contract, which is what makes them byte-identical to a
harvested row downstream — gated, laned by rank, counted by verify_run as a real platform.

  python harvest_companies.py --workspace <ws> --out company_rows.json
  python harvest_companies.py --workspace <ws> --only agri-food
  python harvest_companies.py --self-check

INPUT: <workspace>/TARGET-COMPANIES.md (override with --companies). Format:

    # Target companies
    <!-- one employer per line; `## Sector` groups them; `#` lines are comments -->
    ## Sector name
    - Company Name
    - Company Name | careers:https://example.com/careers/   <- pin the careers page
    - Company Name | greenhouse:slug                        <- pin an ATS board

  `## Sector` heads a block (matched by --only). A `-`/`*` bullet or a bare line is a company.
  `Name | careers:<url>` / `Name | <ats>:<slug>` PINS the board, skipping slug guessing and the
  identity check — the escape hatch for a company that trades under another name. A pin is
  terminal: an empty pinned page is reported empty, never re-searched.

OUTPUT: --out (default company_rows.json; run_hunt writes it to <day>/_work/company_rows.json),
in import_rows.py's contract. Resolutions are cached in <workspace>/.company-boards.json.

MARKET: company boards are global, so rows are filtered to the profile's market (`uk` or `ca`,
read from the `market` line of the workspace profile; --market overrides; --all-locations
disables). A blank location stays in.

FIRECRAWL KEY (careers-page fallback only; the six ATS probes need no key): the FIRECRAWL_API_KEY
environment variable, else the plugin's `firecrawl_api_key` user-config (the same key the bundled
connector uses), else --keyfile <json> holding {"firecrawl_keys": [...]}. No key = no fallback,
never an error.

# ponytail: covers the six ATSes that serve public JSON (Greenhouse, Lever, Ashby, Workable,
# SmartRecruiters, Recruitee). Workday, Taleo, iCIMS, Oracle and Personio need a rendered page
# or an XML parse and are NOT covered — a company on one of those resolves to nothing and is
# reported as unresolved, never as "no vacancies". Add one more probe function if the
# unresolved list turns out to be dominated by one of them.
"""
import argparse
import datetime
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rank  # noqa: E402
from _lib import enable_utf8_io  # noqa: E402
enable_utf8_io()

UA = {"User-Agent": "Mozilla/5.0 (compatible; jobxhunter/1.0)"}
TAGS = re.compile(r"<[^>]+>")


def get_json(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def slugs_for(name):
    """-> candidate ATS slugs for a company name, most likely first.

    'Jones Food Company' -> jonesfoodcompany, jones-food-company, jonesfood.
    Legal suffixes go: an ATS slug is never 'xltd'.

    NO BARE FIRST WORD for a multi-word name. It was in here for one run and produced three
    confident wrong employers: 'Vertical Future' resolved to recruitee/`vertical`, a civils firm
    in Haute-Savoie; 'Zero Carbon Farms' to ashby/`zero`, a US construction group; 'Sterling
    Suffolk' to greenhouse/`sterling`, Sterling Brands of New York. Every one looked like a hit,
    filled the pipeline with real vacancies at the wrong company, and would have been tailored
    for. A missed employer costs a vacancy; a mis-resolved one costs an application.
    """
    n = name.lower()
    n = re.sub(u"[’'`]", "", n)
    n = re.sub(r"\s*\((.*?)\)", " ", n)
    n = n.replace("&", " and ")
    n = re.sub(r"\b(ltd|limited|plc|llp|inc|group|uk|the)\b", " ", n)
    words = [w for w in re.split(r"[^a-z0-9]+", n) if w]
    if not words:
        return []
    out = ["".join(words), "-".join(words)]
    if len(words) > 2 and len("".join(words[:2])) >= 6:
        out.append("".join(words[:2]))   # 'jonesfood'; the >=6 keeps 'S&A Produce' off 'sand'
    seen, uniq = set(), []
    for s in out:
        if s and s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


# A company board is GLOBAL: one employer's board lists Zuid-Holland, another Western Australia,
# another Mexico City and Chennai. Every board source in this pipeline is market-scoped by its
# query; this one has no query to scope it, so it is scoped here or hundreds of foreign roles enter
# the funnel and get read at L2. Blank stays IN — an employer that omits the location is more
# likely local than not. Gated by the profile's market (`uk` / `ca`), see in_market().
FOREIGN = re.compile(
    r"\b(usa|united states|u\.s\.|australia|nsw|queensland|"
    r"india|japan|china|singapore|netherlands|germany|france|spain|italy|poland|portugal|"
    r"brazil|mexico|dubai|uae|texas|california|illinois|massachusetts|virginia|colorado|"
    r"arizona|georgia|florida|washington|oregon|michigan|minnesota|tennessee|new jersey|"
    r"pennsylvania|ohio|new york|san francisco|austin|chicago|boston|seattle|"
    r"north carolina|south carolina|new hampshire|rhode island|kentucky|"
    r"sydney|melbourne|tokyo|bengaluru|chennai|mumbai|warsaw|lisbon|madrid|paris|berlin|"
    r"amsterdam|barcelona|dublin)\b|,\s*(au|us|nl|de|fr|es|it|pl|in|jp|sg|ae|br|mx)\b",
    re.I)
# Canadian adverts name the province almost without exception, so the list is provinces plus the
# big cities; "London, Ontario" is Canada here and NOT the UK.
CA = re.compile(
    r"\b(canada|ontario|quebec|qu\u00e9bec|british columbia|alberta|manitoba|saskatchewan|"
    r"nova scotia|new brunswick|newfoundland|prince edward island|yukon|nunavut|"
    r"toronto|vancouver|montreal|montr\u00e9al|calgary|edmonton|ottawa|winnipeg|halifax|"
    r"mississauga|kitchener|waterloo)\b|,\s*(ca|on|qc|bc|ab|mb|sk|ns|nb)\b", re.I)
# Country words only, not cities: the CITY list is what "London, Ontario" must not trip on.
UK_COUNTRY = re.compile(r"\b(uk|u\.k\.|united kingdom|england|scotland|wales|northern ireland|gb)\b",
                        re.I)
UK = re.compile(
    r"\b(uk|u\.k\.|united kingdom|england|scotland|wales|northern ireland|gb|"
    r"london|manchester|birmingham|leeds|glasgow|edinburgh|bristol|cardiff|belfast|liverpool|"
    r"sheffield|newcastle|nottingham|leicester|cambridge|oxford|reading|brighton|southampton|"
    r"milton keynes|york|coventry|norwich|exeter|plymouth|aberdeen|swansea|derby|hull|luton|"
    r"slough|watford|croydon|guildford|woking|basingstoke|swindon|peterborough|ipswich|"
    r"northampton|bradford|preston|bournemouth|colchester|chelmsford|maidstone|stevenage|"
    # Counties and the produce towns: a grower's advert says 'Birchington, Kent', never 'UK'.
    # Measured live: is_uk('Birchington, Kent') was False (every list missed it), so a grower's
    # only vacancy would drop as foreign before any gate. Counties go INSIDE the group: a `)\b`
    # in the wrong place removes the word boundary from every term after it.
    r"kent|essex|surrey|sussex|hampshire|berkshire|buckinghamshire|oxfordshire|"
    r"hertfordshire|bedfordshire|cambridgeshire|norfolk|suffolk|lincolnshire|yorkshire|"
    r"lancashire|cheshire|derbyshire|nottinghamshire|leicestershire|warwickshire|"
    r"worcestershire|gloucestershire|wiltshire|somerset|devon|cornwall|dorset|cumbria|"
    r"northumberland|merseyside|midlands|staffordshire|shropshire|herefordshire|"
    r"birchington|spalding|evesham|wisbech|ely|thanet|canterbury|ashford)\b",
    re.I)


# Case-SENSITIVE and deliberately so: lowercased, ", in" / ", or" / ", ma" would swallow India,
# Oregon-vs-"or", and any sentence ending in a two-letter word.
US_STATE = re.compile(r",\s*(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|"
                      r"MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|"
                      r"WA|WV|WI|WY|DC)\b")


# market -> (own regex, regexes that mark it as somewhere else). The foreign side WINS ties:
# 'London, Ontario' and 'Cambridge, MA' are the whole reason this is not just a city list.
MARKETS = {"uk": (UK, (FOREIGN, US_STATE, CA)),
           "ca": (CA, (FOREIGN, US_STATE, UK_COUNTRY))}


def in_market(loc, market="uk"):
    """-> True if this location is in `market`, unknown, or `<market>-remote`."""
    s = (loc or "").strip()
    if not s:
        return True
    own, others = MARKETS[market]
    if any(rx.search(s) for rx in others):
        return False
    return bool(own.search(s))


def is_uk(loc):
    return in_market(loc, "uk")


def market_of(ws, default="uk"):
    """The hunt's market, from a `market: uk` / `market: ca` line in the workspace profile."""
    try:
        from _lib import profiles_dir
        for name in sorted(os.listdir(profiles_dir(ws))):
            if not name.endswith(".md"):
                continue
            text = io.open(os.path.join(profiles_dir(ws), name), encoding="utf-8").read()
            m = re.search(r"(?im)^\W*market\W{0,4}(uk|ca|canada)\b", text)
            if m:
                return "ca" if m.group(1).lower().startswith("ca") else "uk"
    except OSError:
        pass
    return default


def _date(v):
    """ATS timestamps: an iso string, or Lever's epoch ms. -> YYYY-MM-DD or ''."""
    if v in (None, ""):
        return ""
    if isinstance(v, (int, float)):
        return datetime.datetime.fromtimestamp(v / 1000.0, datetime.timezone.utc).date().isoformat()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(v))
    return m.group(1) if m else ""


# --- one probe per ATS: slug -> [row], or raise ---------------------------------------------

def probe_greenhouse(slug):
    d = get_json("https://boards-api.greenhouse.io/v1/boards/%s/jobs" % slug)
    return [{"job_id": str(j.get("id") or ""), "title": j.get("title") or "",
             "location": (j.get("location") or {}).get("name") or "",
             "url": j.get("absolute_url") or "", "posted": _date(j.get("updated_at"))}
            for j in d.get("jobs") or []]


def probe_lever(slug):
    d = get_json("https://api.lever.co/v0/postings/%s?mode=json" % slug)
    return [{"job_id": str(j.get("id") or ""), "title": j.get("text") or "",
             "location": (j.get("categories") or {}).get("location") or "",
             "contract": (j.get("categories") or {}).get("commitment") or "",
             "url": j.get("hostedUrl") or "", "posted": _date(j.get("createdAt"))}
            for j in (d if isinstance(d, list) else [])]


def probe_ashby(slug):
    d = get_json("https://api.ashbyhq.com/posting-api/job-board/%s" % slug)
    return [{"job_id": str(j.get("id") or ""), "title": j.get("title") or "",
             "location": j.get("location") or "", "contract": j.get("employmentType") or "",
             "url": j.get("jobUrl") or "", "posted": _date(j.get("publishedAt"))}
            for j in d.get("jobs") or []]


def probe_workable(slug):
    d = get_json("https://apply.workable.com/api/v1/widget/accounts/%s" % slug)
    out = []
    for j in d.get("jobs") or []:
        loc = ", ".join(x for x in (j.get("city"), j.get("country")) if x)
        out.append({"job_id": str(j.get("shortcode") or ""), "title": j.get("title") or "",
                    "location": loc, "url": j.get("url") or "",
                    "posted": _date(j.get("published_on"))})
    return out


def probe_smartrecruiters(slug):
    d = get_json("https://api.smartrecruiters.com/v1/companies/%s/postings?limit=100" % slug)
    out = []
    for j in d.get("content") or []:
        loc = j.get("location") or {}
        out.append({"job_id": str(j.get("id") or ""), "title": j.get("name") or "",
                    "location": ", ".join(x for x in (loc.get("city"), loc.get("country")) if x),
                    "url": "https://jobs.smartrecruiters.com/%s/%s" % (slug, j.get("id")),
                    "posted": _date(j.get("releasedDate"))})
    return out


def probe_recruitee(slug):
    d = get_json("https://%s.recruitee.com/api/offers/" % slug)
    return [{"job_id": str(j.get("id") or ""), "title": j.get("title") or "",
             "location": j.get("location") or j.get("city") or "",
             "contract": j.get("employment_type") or "",
             "url": j.get("careers_url") or j.get("careers_apply_url") or "",
             "posted": _date(j.get("published_at"))}
            for j in d.get("offers") or []]


PROBES = [("greenhouse", probe_greenhouse), ("workable", probe_workable),
          ("lever", probe_lever), ("ashby", probe_ashby),
          ("recruitee", probe_recruitee), ("smartrecruiters", probe_smartrecruiters)]
PROBE_BY_NAME = dict(PROBES)


# --- the fallback: the company's OWN careers page, read by Firecrawl --------------------------
#
# Most companies on a real target list publish no JSON board at all, and they are not a random
# subset: Greenhouse, Ashby and Lever are what VC-backed tech buys, so the ATS probe reaches tech
# and misses every grower, packer, nursery and FM firm on the list. Those employers have a
# careers page and nothing else. This finds it and reads it.
JOB_SCHEMA = {
    "type": "object",
    "properties": {
        # asked for so the page can be CHECKED against the company we searched for — see
        # same_company(). It costs nothing: same call, one more field.
        "company": {"type": "string"},
        "jobs": {"type": "array", "items": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "location": {"type": "string"},
                           "url": {"type": "string"}, "posted": {"type": "string"}},
            "required": ["title"]}}},
    "required": ["jobs"]}

# Words that may differ between how a company is listed and how it names itself. 'Winterwood' and
# 'Winterwood Farms' are one employer; 'Jones Food Company' and 'NEIL Jones Food Company' are two.
GENERIC = frozenset("""ltd limited plc llp inc incorporated group holdings company co the uk gb
    global international farms farm nurseries nursery produce salads foods food fresh growers
    partnership limited services solutions""".split())


def _tokens(name):
    n = re.sub(u"[’'`]", "", (name or "").lower())
    return set(w for w in re.split(r"[^a-z0-9]+", n) if w)


def same_company(target, on_page, url=""):
    """-> True if the careers page really belongs to `target`.

    THE SEARCH STEP HAS ITS OWN WRONG-COMPANY FAILURE, and it is worse than the slug one because
    a web search always returns something plausible. Measured on one live sector block: a
    'Nursery' (grower) resolved to a childcare chain, a food company to a differently-named food
    company, a one-word name to a care home sharing the word. Six of the thirteen "resolved"
    companies were somebody else.

    The rule: one name's significant tokens must contain the other's, and every extra token must be
    generic. 'Winterwood' vs 'Winterwood Farms' passes on `farms`; 'Jones Food Company' vs 'Neil
    Jones Food Company' fails on `neil`, which is exactly the distinction that matters.
    """
    # THE DOMAIN IS IDENTITY EVIDENCE TOO. 'Intelligent Growth Solutions' was rejected
    # against its own site because the page calls itself 'IGS' — but the URL was
    # intelligentgrowthsolutions.com, which spells every significant token of the name. A
    # domain that contains the concatenated significant tokens passes outright; it cannot
    # weaken the check that caught Suffolk County Council, because a wrong company's domain
    # does not spell the target's name.
    if url:
        host = re.sub(r"^https?://(?:www\.)?", "", url.lower()).split("/")[0]
        # first label only, alnum-only: intelligentgrowthsolutions.com -> that label.
        # EQUALITY below, not containment: 'dalgety' is a PREFIX of dalgetybaycare.co.uk and
        # containment would have passed the care home this check exists to reject.
        label = re.sub(r"[^a-z0-9]", "", host.split(".")[0])
        words = [w for w in re.split(r"[^a-z0-9]+",
                                     re.sub(u"[’'`]", "", target.lower())) if w]
        LEGAL = {"ltd", "limited", "plc", "llp", "inc"}
        sig = "".join(w for w in words if w not in GENERIC)
        full = "".join(w for w in words if w not in LEGAL)
        if label in ((sig,) if len(sig) >= 6 else ()) or                 (len(full) >= 6 and label == full):
            return True
    if not on_page:
        return True                       # nothing claimed on the page — the URL check stands alone
    a, b = _tokens(target), _tokens(on_page)
    if not a or not b:
        return True
    # spacing is not identity: 'Flavourfresh' and 'Flavour Fresh' are one company, and the token
    # sets never intersect. Compare the concatenations before anything else.
    if "".join(sorted(a)) == "".join(sorted(b)) or \
            "".join(_tokens(target)) == "".join(_tokens(on_page)):
        return True
    sa, sb = a - GENERIC, b - GENERIC
    if not sa or not sb:                  # a name that is ALL generic words proves nothing
        return bool(a & b)
    if sa == sb:
        return True
    small, big = (sa, sb) if len(sa) <= len(sb) else (sb, sa)
    return small < big and not (big - small - GENERIC)

# The image clause is not decoration. One grower's only live vacancy was a PNG called
# `Section-Leader-Aug-2026.png` with an "apply by email" line — no job text on the page at all.
# Text-only extraction returned zero and would have recorded a hiring employer as empty.
JOB_PROMPT = (
    "List every open job vacancy advertised on this page. A vacancy may appear only as an image "
    "or a PDF whose FILENAME carries the role, e.g. .../Section-Leader-Aug-2026.png means an open "
    "Section Leader role — include those, using the image or PDF link as the url. Return an empty "
    "list if the page advertises no current vacancies. Never invent a role. Also return "
    "`company`: the name of the organisation whose careers page this is, exactly as the page "
    "gives it.")

# Results that are ABOUT the company rather than its own careers page. A job board's page for
# an employer is already covered by the board sources; scraping it here would double-count.
AGGREGATOR = re.compile(
    r"(indeed|reed\.co\.uk|glassdoor|linkedin|totaljobs|cv-library|jobs\.ac\.uk|adzuna|monster|"
    r"facebook|twitter|x\.com|youtube|wikipedia|companieshouse|endole|glassdoor|jobsite|"
    r"caterer|milkround|guardianjobs|charityjob|ziprecruiter)\.", re.I)
CAREERS_HINT = re.compile(r"(career|job|vacanc|work-with-us|work-for-us|join-us|opportunities)",
                          re.I)


def _post_json(url, payload, headers, timeout=90):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def firecrawl_keys(keyfile=None):
    """-> [key, ...] for the careers-page fallback. Same precedence as the connectors: the
    FIRECRAWL_API_KEY env var, then the plugin's `firecrawl_api_key` user-config (read from the
    credential store the way setup_connectors.py does), then an explicit --keyfile
    ({"firecrawl_keys": [...]}). Never a path baked into the code."""
    env = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if env:
        return [env]
    try:
        import setup_connectors
        pid = setup_connectors._installed_as_plugin()
        store = os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")
        with open(store, encoding="utf-8") as fh:
            val = ((json.load(fh).get("pluginSecrets") or {}).get(pid) or {}).get("firecrawl_api_key")
        if val:
            return [str(val)]
    except (ImportError, OSError, ValueError, AttributeError):
        pass
    if keyfile:
        try:
            with open(keyfile, encoding="utf-8") as fh:
                return [k for k in (json.load(fh).get("firecrawl_keys") or []) if k]
        except (OSError, ValueError):
            pass
    return []


def fc_post(path, payload, keys, timeout=120):
    """POST to Firecrawl, rotating across every key until one answers. Raises if all fail."""
    last = ""
    for i, key in enumerate(keys or []):
        try:
            return _post_json("https://api.firecrawl.dev/v2" + path, payload,
                              {"Authorization": "Bearer %s" % key}, timeout)
        except Exception as exc:                              # noqa: BLE001
            last = "key[%d]: %s" % (i, type(exc).__name__)    # never log the key itself
    raise RuntimeError("firecrawl: every key failed (%s)" % (last or "no keys"))


MARKET_WORD = {"uk": "UK", "ca": "Canada"}


def careers_url_for(name, keys, market="uk"):
    """-> the company's own careers page URL, or ''. One search call, cached by the caller."""
    d = fc_post("/search", {"query": "%s careers vacancies jobs %s" % (name, MARKET_WORD[market]),
                            "limit": 5}, keys)
    data = d.get("data")
    hits = (data.get("web") if isinstance(data, dict) else data) or []
    urls = [h.get("url") or "" for h in hits if isinstance(h, dict)]
    urls = [u for u in urls if u and not AGGREGATOR.search(u)]
    if not urls:
        return ""
    # a URL that says careers/vacancies beats the company's home page
    return next((u for u in urls if CAREERS_HINT.search(u)), urls[0])


class WrongCompany(Exception):
    """The careers page found belongs to somebody else. Reported, never silently kept."""


def probe_careers_page(url, keys, expect=""):
    """-> [row] extracted from a careers page. [] means the page advertises nothing today."""
    d = fc_post("/scrape", {"url": url,
                            "formats": [{"type": "json", "schema": JOB_SCHEMA,
                                         "prompt": JOB_PROMPT}]}, keys)
    got = (d.get("data") or {}).get("json") or {}
    if expect and not same_company(expect, got.get("company"), url=url):
        raise WrongCompany("%s -> %r" % (url, got.get("company")))
    jobs = got.get("jobs") or []
    out = []
    for j in jobs:
        if not isinstance(j, dict) or not (j.get("title") or "").strip():
            continue
        link = (j.get("url") or "").strip()
        if link.startswith("/"):
            link = urllib.parse.urljoin(url, link)
        out.append({"job_id": "", "title": j["title"].strip(),
                    "location": (j.get("location") or "").strip(),
                    # no link on the page: the careers page IS the advert, and a blank url would
                    # break import_rows' dedupe key
                    "url": link or url, "posted": _date(j.get("posted"))})
    return out


def resolve(name, cache, probes=PROBES, log=None, fc_keys=None, market="uk"):
    """-> (ats, slug, rows). A cached company skips straight to the one call that works.

    ONLY A NON-EMPTY BOARD COUNTS AS A RESOLUTION. This looks over-strict and is not: on the
    first live run all 32 companies in one sector "resolved" to SmartRecruiters with 0 roles, because
    `/v1/companies/<anything>/postings` answers `200 {"totalFound":0,"content":[]}` for a slug
    that does not exist. Treating that as a hit resolved every company to a fictional board, cached
    it, and would have reported an empty source as fully covered forever. An empty response is not
    evidence of an employer. The cost of the rule is that a real board with no vacancies today gets
    re-probed tomorrow — six cheap GETs, once a day, which is the right price for not lying.
    """
    hit = cache.get(name)
    if hit:
        if hit.get("ats") == "careers":
            try:
                # A PIN OVERRIDES THE IDENTITY CHECK. That is what a pin is for: it exists
                # precisely for the companies whose page name cannot match (a firm trading
                # under another name), so re-applying the check to a pinned URL rejects it
                # again and the pin does nothing.
                rows = probe_careers_page(hit["slug"], fc_keys,
                                          expect="" if hit.get("pinned") else name)
                if rows:
                    return "careers", hit["slug"], rows
                if hit.get("pinned"):
                    # A PIN IS TERMINAL, empty or not. Falling through on an empty pinned page
                    # sent the search off again and it came back with somebody else's careers
                    # page — which is what the pin was written to stop. A pinned company was
                    # still logged WRONG COMPANY after being pinned, for exactly this reason.
                    if log:
                        log("  %-30s pinned careers page, no vacancies" % name[:30])
                    return "", hit["slug"], []
            except Exception:
                if hit.get("pinned"):
                    # a pinned page that errors is a fault to see, not a licence to go looking
                    # for a different company
                    if log:
                        log("  %-30s pinned careers page unreadable" % name[:30])
                    return "", hit["slug"], None
                pass          # unpinned: fall through and search again
        fn = PROBE_BY_NAME.get(hit.get("ats"))
        if fn:
            try:
                rows = fn(hit["slug"])
                if rows:
                    return hit["ats"], hit["slug"], rows
            except Exception:
                pass                      # a cached board can move; fall through and re-probe
    for slug in slugs_for(name):
        for ats, fn in probes:
            try:
                rows = fn(slug)
            except Exception:
                continue                  # 404/403/JSON error = not this ATS, not this slug
            if not rows:
                continue                  # empty proves nothing — see the docstring
            cache[name] = {"ats": ats, "slug": slug}
            if log:
                log("  %-30s %s/%s  %d role(s)" % (name[:30], ats, slug, len(rows)))
            return ats, slug, rows

    # No JSON board. Fall back to the company's own careers page.
    if fc_keys:
        try:
            url = (hit or {}).get("careers_url") or careers_url_for(name, fc_keys, market)
            if url:
                rows = probe_careers_page(url, fc_keys, expect=name)
                # cache the URL even when the page is empty today: the search call is the
                # expensive half and the page will not move. `ats` stays unset until it yields
                # something, so an empty careers page is still reported honestly as no result.
                cache[name] = {"ats": "careers" if rows else "", "slug": url,
                               "careers_url": url}
                if rows:
                    if log:
                        log("  %-30s careers/%s  %d role(s)" % (name[:30], url[:34], len(rows)))
                    return "careers", url, rows
                if log:
                    log("  %-30s careers page, no vacancies" % name[:30])
                return "", url, []
        except WrongCompany as exc:
            # never cached: tomorrow's search may do better, and a wrong page cached is a wrong
            # employer applied to
            if log:
                log("  %-30s WRONG COMPANY %s" % (name[:30], str(exc)[:60]))
        except Exception as exc:                              # noqa: BLE001
            if log:
                log("  %-30s firecrawl failed: %s" % (name[:30], type(exc).__name__))
    if log:
        log("  %-30s unresolved" % name[:30])
    return "", "", None


def parse_companies(path):
    """-> [(sector, name, pin)]. `## Sector` heads a block; `-`/`*` or a bare line is a company;
    `#` comments and blanks are ignored.

    `Name | careers:https://...` or `Name | greenhouse:slug` PINS the board. That is the escape
    hatch for the identity check's false negatives — a firm that trades under another name, which
    no name comparison can be expected to know. Pin it once and it is settled.
    """
    out, sector = [], ""
    for line in io.open(path, encoding="utf-8").read().splitlines():
        s = line.strip()
        if not s or s.startswith("<!--"):
            continue
        if s.startswith("#"):
            if s.startswith("## "):
                sector = s[3:].strip()
            continue
        s = re.sub(r"^[-*]\s*", "", s)
        if not s:
            continue
        pin = None
        if "|" in s:
            s, _, spec = (x.strip() for x in s.partition("|"))
            ats, _, slug = (x.strip() for x in spec.partition(":"))
            if ats and slug:
                pin = {"ats": ats, "slug": slug, "pinned": True}
                if ats == "careers":
                    pin["careers_url"] = slug
        out.append((sector, s, pin))
    return out


def relevant(title, titles_by_lane):
    """-> (keep, lane). Judged by rank.py against SEARCH-KEYWORDS.md — the user's own authority,
    not a second opinion invented here.

    RELEVANCE GATES ON THIS SOURCE, AND ONLY ON THIS SOURCE. Everywhere else in the pipeline a
    score of 0 is kept and sorted to the bottom, deliberately: the advert only exists because one
    of the user's queries returned it, so it is already about them and an unmatched TITLE is just
    wording nobody anticipated. A company board has no query behind it. It hands over everything
    the employer is hiring for — a chip firm's board is 100 silicon-compiler roles — so with no
    gate the source contributes mostly noise and buys it L2 reads. Unmatched here means unrelated.
    """
    score, verdict, _matched, lane = rank.judge(title or "", titles_by_lane)
    return (score > 0 and not verdict.startswith("reject")), lane


def to_groups(results, uk_only=True, titles_by_lane=None, market="uk"):
    """-> import_rows.py's contract: one group per company, lane blank so rank assigns it.
    `uk_only` is the historical name: it means "filter to `market`"."""
    groups = []
    for name, ats, slug, rows in results:
        if rows is None:
            groups.append({"lane": "", "query": name, "total": 0, "rows": [],
                           "note": "no public ATS board found"})
            continue
        seen_all = len(rows)
        if uk_only:
            rows = [r for r in rows if in_market(r.get("location"), market)]
        dropped = seen_all - len(rows)
        off_topic = 0
        if titles_by_lane:
            if len(rows) > 20:
                # A 205-role tech board floods the funnel; a grower with 3 vacancies cannot.
                # Small boards pass WHOLE (do not micro-filter), except the two
                # factual impossibilities, which reject everywhere.
                kept = [r for r in rows if relevant(r.get("title"), titles_by_lane)[0]]
            else:
                kept = [r for r in rows
                        if not rank.judge(r.get("title") or "", titles_by_lane)[1].startswith("reject")]
            off_topic = len(rows) - len(kept)
            rows = kept
        for r in rows:
            r.setdefault("company", name)
            r.setdefault("salary_min", None)
            r.setdefault("salary_max", None)
        note = "company board via %s/%s" % (ats, slug)
        if dropped or off_topic:
            # verify_run reads this note. "12 off-market dropped" is a covered source; a bare 0
            # is an unexplained dead one.
            note += " - of %d: %d off-market, %d off-lane" % (seen_all, dropped, off_topic)
        groups.append({"lane": "", "query": name, "total": len(rows), "rows": rows, "note": note})
    return groups


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace")
    ap.add_argument("--companies", default=None,
                    help="defaults to <workspace>/TARGET-COMPANIES.md")
    ap.add_argument("--cache", default=None,
                    help="defaults to <workspace>/.company-boards.json")
    ap.add_argument("--out", default="company_rows.json")
    ap.add_argument("--only", default=None, help="substring filter on sector or name")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--all-locations", action="store_true",
                    help="keep roles outside the market. Company boards are global; the default "
                         "keeps only the profile's market.")
    ap.add_argument("--market", default=None, choices=sorted(MARKETS),
                    help="uk or ca. Default: the `market` line of the workspace profile, else uk.")
    ap.add_argument("--keyfile", default=None,
                    help='optional JSON {"firecrawl_keys": [...]} - used only when neither '
                         "FIRECRAWL_API_KEY nor the plugin's firecrawl_api_key is set")
    ap.add_argument("--keep-unmatched", action="store_true",
                    help="keep roles matching no lane in SEARCH-KEYWORDS.md. A company board has "
                         "no query scoping it, so the default is to drop them.")
    ap.add_argument("--keywords-file", default=None,
                    help="defaults to <workspace>/SEARCH-KEYWORDS.md")
    ap.add_argument("--no-firecrawl", action="store_true",
                    help="skip the careers-page fallback for companies with no JSON board")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()
    if args.self_check:
        return self_check()

    from _lib import resolve_workspace_root
    ws = resolve_workspace_root(args.workspace) if args.workspace else ""
    if not ws:
        raise SystemExit("no workspace resolved")
    cpath = args.companies or os.path.join(ws, "TARGET-COMPANIES.md")
    cache_path = args.cache or os.path.join(ws, ".company-boards.json")
    cache = json.load(io.open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}

    companies = parse_companies(cpath)
    if args.only:
        k = args.only.lower()
        companies = [c for c in companies if k in c[0].lower() or k in c[1].lower()]
    if args.limit:
        companies = companies[:args.limit]

    # A pin from TARGET-COMPANIES.md goes into the cache BEFORE anything is probed — that is how
    # resolve() sees it, and it overrides whatever the cache file learned on an earlier run.
    # Without this the pins parsed fine and did nothing at all.
    for _sector, _name, _pin in companies:
        if _pin:
            cache[_name] = _pin

    # Threaded because it is pure network wait: up to 18 GETs per company, ~1s each, and a
    # sequential pass over 150 companies took 45 minutes for what 8 workers do in six.
    market = args.market or market_of(ws)
    fc_keys = [] if args.no_firecrawl else firecrawl_keys(args.keyfile)
    if fc_keys:
        print("careers-page fallback ON (%d firecrawl key(s))" % len(fc_keys), flush=True)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as pool:
        out = list(pool.map(lambda c: (c[1],) + resolve(c[1], cache, fc_keys=fc_keys, market=market,
                                                        log=lambda m: print(m, flush=True)),
                            companies))
    results = [(n, a, s, r) for n, a, s, r in out]
    resolved = sum(1 for _, _, _, r in results if r is not None)
    roles = sum(len(r) for _, _, _, r in results if r is not None)

    json.dump(cache, io.open(cache_path, "w", encoding="utf-8"), indent=1, sort_keys=True)
    titles = None
    if not args.keep_unmatched:
        titles = rank.parse_titles(args.keywords_file or os.path.join(ws, "SEARCH-KEYWORDS.md"))
    groups = to_groups(results, uk_only=not args.all_locations, titles_by_lane=titles,
                       market=market)
    json.dump(groups, io.open(args.out, "w", encoding="utf-8"), indent=1)
    kept = sum(len(g["rows"]) for g in groups)
    print("\n%d compan(ies) - %d with a readable board - %d role(s) -> %d in-market (%s) and "
          "on-lane -> %s" % (len(companies), resolved, roles, kept, market, args.out))
    print("cache -> %s" % cache_path)
    print("\nnext:  python import_rows.py --workspace <ws> --source companies "
          "--platform \"Company boards\" --rows %s --max-days-old 30" % args.out)
    return 0


def self_check():
    assert slugs_for("Jones Food Company Ltd")[:2] == ["jonesfoodcompany", "jones-food-company"]
    assert slugs_for("S&A Produce (UK) Limited")[0] == "sandaproduce", slugs_for("S&A Produce (UK) Limited")
    assert "thanetearth" in slugs_for("Thanet Earth")
    # a bare first word is NEVER a slug for a multi-word name — it resolves to another company
    # (item 29 false-positive class 2)
    for n in ("Vertical Future", "Zero Carbon Farms", "Sterling Suffolk", "S&A Produce Ltd"):
        got = slugs_for(n)
        assert not any(s in ("vertical", "zero", "sterling", "sand", "s") for s in got), (n, got)
    assert slugs_for("Ocado") == ["ocado"]          # a one-word name is still itself

    assert _date(1755820800000) == "2025-08-22", _date(1755820800000)
    assert _date("2026-08-21T09:00:00Z") == "2026-08-21"
    assert _date(None) == "" and _date("soon") == ""

    # AN EMPTY BOARD IS NOT A RESOLUTION (item 29 class 1). SmartRecruiters answers 200
    # {"content":[]} for any slug at all, so accepting empty resolved 32 companies to a board
    # that did not exist. Nothing empty may be cached, and the probe must keep going.
    cache = {}
    ats, slug, rows = resolve("Empty Co", cache, probes=[("smartrecruiters", lambda s: [])])
    assert rows is None and cache == {}, (rows, cache)
    # ...and it keeps probing past the empty one to a real board behind it
    cache = {}
    real = [{"title": "Head Grower", "url": "u"}]
    ats, slug, rows = resolve("Mixed Co", cache, probes=[("smartrecruiters", lambda s: []),
                                                         ("greenhouse", lambda s: real)])
    assert ats == "greenhouse" and rows == real and cache["Mixed Co"]["ats"] == "greenhouse"

    # every probe raising: uncached, and comes back as None
    def dead(_):
        raise urllib.error.HTTPError("u", 404, "nope", {}, None)
    cache2 = {}
    assert resolve("Ghost Ltd", cache2, probes=[("greenhouse", dead)])[2] is None
    assert cache2 == {}

    # the careers-page fallback fires only when no JSON board answered, and an EMPTY careers page
    # must not be reported as a resolution — but its URL is still cached, because the search call
    # is the expensive half and the page does not move.
    global careers_url_for, probe_careers_page                       # noqa: PLW0603
    _cu, _pc = careers_url_for, probe_careers_page
    try:
        careers_url_for = lambda n, k, market="uk": "https://x.test/careers"      # noqa: E731
        probe_careers_page = lambda u, k, expect="": []              # noqa: E731
        c3 = {}
        ats, url, rows = resolve("Paper Co", c3, probes=[("greenhouse", dead)], fc_keys=["k"])
        assert (ats, url, rows) == ("", "https://x.test/careers", []), (ats, url, rows)
        assert c3["Paper Co"] == {"ats": "", "slug": "https://x.test/careers",
                                  "careers_url": "https://x.test/careers"}, c3

        probe_careers_page = lambda u, k, expect="": [{"title": "Head Grower", "url": u}]  # noqa: E731
        c4 = {}
        ats, url, rows = resolve("Real Co", c4, probes=[("greenhouse", dead)], fc_keys=["k"])
        assert ats == "careers" and len(rows) == 1 and c4["Real Co"]["ats"] == "careers"
        # ...and with no keys the fallback never runs at all
        assert resolve("Real Co", {}, probes=[("greenhouse", dead)], fc_keys=[])[2] is None
    finally:
        careers_url_for, probe_careers_page = _cu, _pc

    # a careers result that is really a job board would double-count what the board sources
    # already have
    assert AGGREGATOR.search("https://uk.indeed.com/cmp/Thanet-Earth")
    assert not AGGREGATOR.search("https://www.thanetearth.com/work-with-us/current-roles/")

    # IDENTITY (item 29 class 4). Every case below is a real result from a live sector run.
    assert same_company("Winterwood Farms", "Winterwood")            # generic extra token
    assert same_company("APS Salads", "The APS Group")
    assert same_company("Driscolls", "Driscoll's")
    assert same_company("Zero Carbon Farms", "Zero Carbon Farms Ltd")
    assert same_company("Thanet Earth", "Thanet Earth")
    assert not same_company("Jones Food Company", "Neil Jones Food Company")
    assert not same_company("Cornerways Nursery", "Bright Horizons")
    assert not same_company("Dalgety", "Dalgety Bay Care Home")
    assert not same_company("Celadon Pharmaceuticals", "Celon Pharma")
    assert not same_company("Delamore", "Locinox")
    assert same_company("Anything", "")     # page claims nothing: the URL check stands alone
    # domain-as-identity: IGS's own domain spells the name even though the page says 'IGS'
    assert same_company("Intelligent Growth Solutions", "IGS",
                        url="https://www.intelligentgrowthsolutions.com/people/careers")
    assert not same_company("Dalgety", "Dalgety Bay Care Home",
                            url="https://dalgetybaycare.co.uk/careers/")
    assert not same_company("Sterling Suffolk", "Suffolk County Council",
                            url="https://www.suffolk.gov.uk/jobs-and-careers")
    # UK counties count as UK; US county-name towns do not (item 29 class 3)
    assert is_uk("Birchington, Kent") and is_uk("Ely, Cambridgeshire")
    assert not is_uk("Louisville, Kentucky") and not is_uk("Durham, North Carolina")
    # the same gate, switched to the Canadian market
    assert in_market("Toronto, ON", "ca") and in_market("London, Ontario", "ca")
    assert in_market("", "ca") and in_market("Remote - Canada", "ca")
    assert not in_market("London, UK", "ca") and not in_market("Cambridge, MA", "ca")
    assert not in_market("Austin, Texas", "ca") and not in_market("Toronto, ON", "uk")
    assert not in_market("Victoria, BC", "uk") and in_market("Victoria, BC", "ca")
    # ...and market_of reads the profile, defaulting to uk
    import tempfile as _tf0
    _ws = _tf0.mkdtemp()
    os.makedirs(os.path.join(_ws, "profiles"))
    assert market_of(_ws) == "uk"
    io.open(os.path.join(_ws, "profiles", "me.md"), "w", encoding="utf-8").write(
        "## Career targets & market\n- Market: Canada\n")
    assert market_of(_ws) == "ca", market_of(_ws)
    # keys: the env var wins over a keyfile; a keyfile is honoured when nothing else is set
    _kf = os.path.join(_ws, "keys.json")
    io.open(_kf, "w", encoding="utf-8").write('{"firecrawl_keys": ["fc-test"]}')
    _env = os.environ.pop("FIRECRAWL_API_KEY", None)
    try:
        os.environ["FIRECRAWL_API_KEY"] = "fc-env"
        assert firecrawl_keys(_kf) == ["fc-env"]
        del os.environ["FIRECRAWL_API_KEY"]
        assert firecrawl_keys(_kf) in (["fc-test"], firecrawl_keys(None))  # plugin store may win
        assert isinstance(firecrawl_keys(os.path.join(_ws, "nope.json")), list)  # never raises
    finally:
        if _env is not None:
            os.environ["FIRECRAWL_API_KEY"] = _env
    # small boards pass whole (only global knockouts/clearance reject); large boards gate
    # (item 29 class 5)
    small = [{"title": "Section Leader", "location": "London"},
             {"title": "Chief Executive", "location": "London"}]
    import tempfile as _tf2
    _kw2 = os.path.join(_tf2.mkdtemp(), "SEARCH-KEYWORDS.md")
    io.open(_kw2, "w", encoding="utf-8").write(
        u"## Agri-food · plant science · CEA\n\n"
        u"**Core titles (1)** — Head Grower\n\n"
        u"## Global knockouts — never wanted, in ANY lane\n\n"
        u"**Title knockouts — auto-reject** — Chief Executive\n")
    tbl2 = rank.parse_titles(_kw2)
    g2 = to_groups([("SmallCo", "ashby", "s", list(small))], titles_by_lane=tbl2)
    assert [r["title"] for r in g2[0]["rows"]] == ["Section Leader"], g2[0]  # CEO rejected, SL kept
    big = [{"title": "Compiler Engineer %d" % i, "location": "London"} for i in range(25)]
    g3 = to_groups([("BigCo", "ashby", "b", big)], titles_by_lane=tbl2)
    assert g3[0]["rows"] == [], g3[0]      # >20 roles: unmatched titles are gated out

    # THE CONTRACT with import_rows: a None result must still emit a group carrying a NOTE, or
    # verify_run reads the platform's zero as an unexplained dead source and fails the run.
    g = to_groups([("Ghost Ltd", "", "", None),
                   ("Real Ltd", "lever", "real", [{"title": "Head Grower", "url": "u"}])])
    assert g[0]["total"] == 0 and g[0]["note"] and g[0]["rows"] == []
    assert g[1]["rows"][0]["company"] == "Real Ltd"
    assert g[1]["rows"][0]["salary_min"] is None       # never 0 - 0 reads as "paid nothing"
    assert g[1]["lane"] == ""                          # rank assigns the lane, not this script

    # UK filter. A company board is GLOBAL, and the foreign side must beat a bare city name or
    # 'London, Ontario' and 'Cambridge, MA' walk straight into the funnel.
    assert is_uk("London") and is_uk("Bristol, UK") and is_uk("UK - Remote") and is_uk("")
    assert not is_uk("London, Ontario") and not is_uk("Cambridge, MA")
    assert not is_uk("Western Australia, au") and not is_uk("De Lier, Zuid-Holland, Netherlands")
    assert not is_uk("Chennai, India") and not is_uk("Tokyo, Japan") and not is_uk("Remote - US")
    assert is_uk("Cardiff, London or Remote (UK)")
    g = to_groups([("Mixed", "ashby", "m", [{"title": "A", "location": "London"},
                                            {"title": "B", "location": "Austin, Texas"}])])
    assert len(g[0]["rows"]) == 1 and "of 2: 1 off-market, 0 off-lane" in g[0]["note"], g[0]

    # RELEVANCE. Judged by rank.py against the keyword file, so this breaks if the two ever
    # disagree about what a lane is.
    import tempfile as _tf
    kw = os.path.join(_tf.mkdtemp(), "SEARCH-KEYWORDS.md")
    # em dashes and the exact list headings: rank.LIST_PATTERNS matches on both
    io.open(kw, "w", encoding="utf-8").write(
        u"## Agri-food · plant science · CEA\n\n"
        u"**Core titles (1)** — Head Grower\n\n"
        u"## Global knockouts — never wanted, in ANY lane\n\n"
        u"**Title knockouts — auto-reject** — Chief Executive\n")
    tbl = rank.parse_titles(kw)
    assert relevant("Head Grower", tbl)[0]
    assert not relevant("Senior Silicon Compiler Engineer", tbl)[0]   # on the board, off-lane
    assert not relevant("Chief Executive", tbl)[0]                    # global knockout
    # a SMALL board (<= 20 roles) passes whole: the unmatched title is kept, only a global
    # knockout rejects. The > 20 gate is exercised further down with the 25-role board.
    g = to_groups([("Co", "ashby", "c", [{"title": "Head Grower", "location": "London"},
                                         {"title": "Compiler Engineer", "location": "London"},
                                         {"title": "Chief Executive", "location": "London"}])],
                  titles_by_lane=tbl)
    assert [r["title"] for r in g[0]["rows"]] == ["Head Grower", "Compiler Engineer"], g[0]
    assert "1 off-lane" in g[0]["note"], g[0]
    assert len(to_groups([("M", "ashby", "m", [{"title": "B", "location": "Austin, Texas"}])],
                         uk_only=False)[0]["rows"]) == 1

    import tempfile
    p = os.path.join(tempfile.mkdtemp(), "c.md")
    io.open(p, "w", encoding="utf-8").write(
        "# Targets\n\n## Agri-food\n- Thanet Earth\n* APS Salads\n\n# a comment\n"
        "## Data\nOcado Technology\n")
    assert parse_companies(p) == [("Agri-food", "Thanet Earth", None),
                                  ("Agri-food", "APS Salads", None),
                                  ("Data", "Ocado Technology", None)], parse_companies(p)

    # a PIN is the escape hatch for an identity false negative
    io.open(p, "w", encoding="utf-8").write(
        "## Agri-food\n"
        "- Whixley Co | careers:https://example.test/careers/\n"
        "- Foo Ltd | greenhouse:foo\n")
    got = parse_companies(p)
    assert got[0][2] == {"ats": "careers", "slug": "https://example.test/careers/",
                         "pinned": True,
                         "careers_url": "https://example.test/careers/"}, got[0]
    assert got[1][2] == {"ats": "greenhouse", "slug": "foo", "pinned": True}, got[1]

    # spacing is not identity, but an extra distinctive word still is
    assert same_company("Flavourfresh", "Flavour Fresh")
    assert not same_company("Jones Food Company", "Neil Jones Food Company")

    # A PIN OVERRIDES THE IDENTITY CHECK, or it does nothing at all. The first pin written
    # failed on its first outing for exactly this reason.
    seen_expect = []
    _pc2 = probe_careers_page
    try:
        def _spy(u, k, expect=""):
            seen_expect.append(expect)
            return [{"title": "Head Grower", "url": u}]
        probe_careers_page = _spy
        pinned = {"Whixley Co": {"ats": "careers", "slug": "https://x.test/c", "pinned": True}}
        assert resolve("Whixley Co", pinned, fc_keys=["k"])[0] == "careers"
        assert seen_expect == [""], seen_expect          # identity check skipped for a pin
        seen_expect[:] = []
        unpinned = {"Other Co": {"ats": "careers", "slug": "https://x.test/c"}}
        resolve("Other Co", unpinned, fc_keys=["k"])
        assert seen_expect == ["Other Co"], seen_expect  # ...and still applied when not pinned

        # AN EMPTY PINNED PAGE IS TERMINAL. Falling through re-ran the search and returned
        # somebody else's careers page — the exact thing the pin was written to prevent.
        probe_careers_page = lambda u, k, expect="": []                      # noqa: E731
        searched = []
        _cu2 = careers_url_for
        try:
            careers_url_for = lambda n, k, market="uk": searched.append(n) or "https://wrong.test/c"  # noqa
            assert resolve("Whixley Co", pinned, fc_keys=["k"]) == ("", "https://x.test/c", [])
            assert searched == [], searched              # never went looking
        finally:
            careers_url_for = _cu2
    finally:
        probe_careers_page = _pc2
    print("harvest_companies self-check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
