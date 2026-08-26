#!/usr/bin/env python3
"""Read a page a plain GET cannot get, using whichever scraper key still has credit.

WHY THIS EXISTS. `fetch_jds.py` returned the string "needs-scraper" and nothing consumed it.
On the 22 Aug 2026 run that swallowed **76 of 150 adverts** — every one of them Adzuna, which is
roughly half the survivor pool. The adverts existed, were ranked, were worth reading, and were
silently skipped because the reader had no second gear.

Scripts cannot call MCP tools, which is why the scraper MCP servers were no use here. But every one
of those services is an ordinary HTTP API behind a key, so this calls the API directly, trying each
key in turn until one returns real content. No MCP, no second credential path.

Order: Firecrawl first (returns markdown, so nothing has to strip HTML), then ScraperAPI, then
scrape.do, then Zyte (all raw HTML, stripped here). Each rotates across its keys; the first with
credit wins.

KEYS — environment variables, one key each (a comma-separated list rotates):

  FIRECRAWL_API_KEY    also read from the plugin's `firecrawl_api_key` user-config
  SCRAPERAPI_KEY
  SCRAPEDO_TOKEN
  ZYTE_API_KEY

Optional `--keyfile <path>` (or $JOBXHUNTER_SCRAPER_KEYFILE) overrides them with a JSON file of
key LISTS, for people who rotate several accounts:

  {"firecrawl_keys": ["fc-..."], "scraperapi_keys": ["..."],
   "scrapedo_keys": ["..."], "zyte_keys": ["..."]}

Every key may be absent. With none at all, `fetch` raises NoScraper and the caller records the
advert as `needs-scraper` — a run never dies on a missing key.

Usage:
  python scrape.py [--keyfile k.json] <url>     # print the readable text
  python scrape.py --self-check
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import enable_utf8_io, secret_env  # noqa: E402
enable_utf8_io()

TAGS = re.compile(r"<[^>]+>")
# provider -> (env var, keyfile list name)
KEY_SOURCES = {"firecrawl": ("FIRECRAWL_API_KEY", "firecrawl_keys"),
               "scraperapi": ("SCRAPERAPI_KEY", "scraperapi_keys"),
               "scrapedo": ("SCRAPEDO_TOKEN", "scrapedo_keys"),
               "zyte": ("ZYTE_API_KEY", "zyte_keys")}


class NoScraper(Exception):
    """No usable key. Distinct from a fetch failure so the caller can say which happened."""


def keyfile_path(explicit=None):
    return explicit or os.environ.get("JOBXHUNTER_SCRAPER_KEYFILE") or ""


def load_keys(keyfile=None):
    """-> {provider: [keys]} for every provider in KEY_SOURCES. A keyfile, when given, replaces
    the environment. A missing or malformed keyfile is not fatal: the caller degrades to
    'needs-scraper' rather than crashing a whole run."""
    raw = {}
    path = keyfile_path(keyfile)
    if path:
        try:
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh) or {}
        except (OSError, ValueError):
            raw = {}
    out = {}
    for name, (env, listname) in KEY_SOURCES.items():
        if path:
            out[name] = [str(k) for k in (raw.get(listname) or []) if k]
        else:
            out[name] = [k.strip() for k in secret_env(env).split(",") if k.strip()]
    return out


def _post_json(url, payload, headers, timeout=90):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def firecrawl_fetch(key, url, timeout=90):
    """-> markdown, or '' if the response carried none."""
    d = _post_json("https://api.firecrawl.dev/v2/scrape",
                   {"url": url, "formats": ["markdown"], "onlyMainContent": True},
                   {"Authorization": f"Bearer {key}"}, timeout)
    return ((d.get("data") or {}).get("markdown") or "").strip()


def scraperapi_fetch(key, url, timeout=90):
    """-> text stripped out of the returned HTML."""
    q = urllib.parse.urlencode({"api_key": key, "url": url})
    req = urllib.request.Request("https://api.scraperapi.com/?" + q)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        html = r.read().decode("utf-8", "replace")
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    text = TAGS.sub("\n", html)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _strip(html):
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    text = TAGS.sub("\n", html)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def scrapedo_fetch(key, url, timeout=90):
    q = urllib.parse.urlencode({"token": key, "url": url})
    req = urllib.request.Request("https://api.scrape.do/?" + q)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return _strip(r.read().decode("utf-8", "replace"))


def zyte_fetch(key, url, timeout=90):
    import base64
    auth = base64.b64encode(f"{key}:".encode()).decode()
    d = _post_json("https://api.zyte.com/v1/extract", {"url": url, "httpResponseBody": True},
                   {"Authorization": f"Basic {auth}"}, timeout)
    body = base64.b64decode(d.get("httpResponseBody") or b"").decode("utf-8", "replace")
    return _strip(body)


PROVIDERS = (("firecrawl", firecrawl_fetch), ("scraperapi", scraperapi_fetch),
             ("scrapedo", scrapedo_fetch), ("zyte", zyte_fetch))


def fetch(url, keys=None, min_chars=400):
    """-> (text, provider). Tries every key of every provider until one returns real content.

    `min_chars` guards against the failure that actually happens: a scraper returning 200 with a
    cookie wall or an empty shell. Short output is treated as a miss and the next key is tried,
    because a 200 carrying nothing is worse than an error — it looks like success.
    """
    keys = load_keys() if keys is None else keys
    if not any(keys.get(n) for n, _ in PROVIDERS):
        raise NoScraper("no scraper key set — see the module docstring for the variables")
    last = ""
    for name, fn in PROVIDERS:
        for i, key in enumerate(keys.get(name) or []):
            try:
                text = fn(key, url)
            except Exception as exc:                            # noqa: BLE001
                last = f"{name}[{i}]: {type(exc).__name__}"     # never log the key itself
                continue
            if is_redirect_stub(text):
                last = f"{name}[{i}]: redirect stub, not an advert"
                continue
            if len(text) >= min_chars:
                return text, name
            last = f"{name}[{i}]: {len(text)} chars"
    raise NoScraper(f"every key failed or returned too little (last: {last})")


# Adzuna wraps the advert in cookie banners, country pickers, "similar jobs" and a footer of
# popular searches. Kept whole, a fetched advert is mostly navigation, and the tailorer then reads
# 2,000 words of chrome to find 400 of job. The body sits between the H1 and the stats block.
ADZUNA_START = re.compile(r"^#\s+(?!#).+$", re.M)
ADZUNA_END = re.compile(r"##\s+Stats for this job|##\s+Similar jobs|####\s+Country selection")


# A page that only says "you are now being redirected" is NOT an advert, but it is long enough to
# pass a length check — which is how a dozen redirect stubs were recorded as successfully fetched
# on 22 Aug 2026. Short-circuit them by content, not by length.
REDIRECT_STUB = re.compile(r"(?i)you are now being redirected|if you are not redirected within")


def is_redirect_stub(text):
    """-> True when the fetched page is a click-through shim rather than a job advert."""
    return bool(text) and bool(REDIRECT_STUB.search(text[:1500]))


def trim_adzuna(md):
    """-> just the advert. Returns the input unchanged if the markers are not found."""
    if not md:
        return md
    m = ADZUNA_START.search(md)
    body = md[m.start():] if m else md
    e = ADZUNA_END.search(body)
    if e:
        body = body[:e.start()]
    body = re.sub(r"\[Apply for this job\]\([^)]*\)", "", body)
    body = re.sub(r"\[❮?\s*back to last search\]\([^)]*\)", "", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body if len(body) >= 200 else md


def self_check():
    import tempfile
    import shutil
    # key sources: environment (comma-rotated), then a keyfile that REPLACES it. Real keys are
    # never read: the env vars are swapped out for the duration.
    names = [env for env, _ in KEY_SOURCES.values()] + ["JOBXHUNTER_SCRAPER_KEYFILE"]
    bak = {n: os.environ.pop(n, None) for n in names}
    tmp = tempfile.mkdtemp()
    try:
        ks = load_keys(os.path.join(tmp, "absent.json"))
        assert set(ks) == set(KEY_SOURCES) and not any(ks.values()), ks
        os.environ["SCRAPERAPI_KEY"] = "k1, k2"
        os.environ["ZYTE_API_KEY"] = "z"
        got = load_keys()
        assert got["scraperapi"] == ["k1", "k2"] and got["zyte"] == ["z"], got
        kf = os.path.join(tmp, "k.json")
        with open(kf, "w", encoding="utf-8") as fh:
            json.dump({"firecrawl_keys": ["fc-a"], "scrapedo_keys": ["d"]}, fh)
        got = load_keys(kf)                          # a keyfile replaces the environment
        assert got == {"firecrawl": ["fc-a"], "scraperapi": [], "scrapedo": ["d"], "zyte": []}, got
        os.environ["JOBXHUNTER_SCRAPER_KEYFILE"] = kf
        assert load_keys()["firecrawl"] == ["fc-a"]
        # a missing keyfile degrades, never crashes — a whole run must not die on one absent file
        os.environ["JOBXHUNTER_SCRAPER_KEYFILE"] = os.path.join(tmp, "does-not-exist.json")
        assert not any(load_keys().values())
        try:
            fetch("https://example.test/x")
            raise AssertionError("expected NoScraper with no keys")
        except NoScraper:
            pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for n, v in bak.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v

    # a 200 carrying nothing must count as a MISS, not a success. This is the real failure mode:
    # cookie walls and empty shells return 200, and short output that reads as "fetched" is how a
    # blank advert reaches the tailorer.
    calls = []

    def ok(key, url, timeout=90):
        calls.append(key)
        return "x" * 500

    def empty(key, url, timeout=90):
        calls.append(key)
        return "too short"

    global PROVIDERS
    keep = PROVIDERS
    try:
        PROVIDERS = (("firecrawl", empty), ("scraperapi", ok))
        text, who = fetch("https://example.test/x", {"firecrawl": ["a", "b"], "scraperapi": ["c"]})
        assert who == "scraperapi" and len(text) == 500
        assert calls == ["a", "b", "c"], calls        # every key tried, in order, before moving on
    finally:
        PROVIDERS = keep

    # a redirect shim is not an advert, however long it is. Adzuna's /jobs/land/ad/ page is
    # 400+ characters of 'you are now being redirected', so a length check alone reads it as
    # a successful fetch — which is exactly how a dozen stubs were recorded as adverts.
    assert is_redirect_stub("# Adzuna. You are now being redirected to Total Jobs")
    assert is_redirect_stub("If you are not redirected within 5 seconds, view ad here")
    assert not is_redirect_stub("# IT Manager. Notre Dame School. We are seeking an ...")
    assert not is_redirect_stub("")

    # Adzuna trimming: keep the advert, drop the furniture
    md = ("## IT Manager jobs in Downside\nLeave us your email address\n\n"
          "# IT Manager\n\nNotre Dame School\n\n[Apply for this job](https://x/y)\n\n"
          + "Real advert body. " * 30 + "\n\n## Stats for this job\n\nSalary comparison:\n"
          "## Similar jobs\n\n#### Country selection\n")
    out = trim_adzuna(md)
    assert out.startswith("# IT Manager"), out[:40]
    assert "Real advert body." in out
    assert "Stats for this job" not in out and "Country selection" not in out
    assert "Apply for this job" not in out
    assert "Leave us your email" not in out
    # unrecognisable input comes back untouched rather than being emptied
    assert trim_adzuna("no markers here") == "no markers here"
    assert trim_adzuna("") == ""

    print("scrape self-check OK")
    return 0


def main():
    if "--self-check" in sys.argv:
        return self_check()
    argv, keyfile = sys.argv[1:], None
    if "--keyfile" in argv:
        i = argv.index("--keyfile")
        keyfile = argv[i + 1] if i + 1 < len(argv) else None
        argv = argv[:i] + argv[i + 2:]
    if len(argv) != 1:
        raise SystemExit("usage: scrape.py [--keyfile k.json] <url> | --self-check")
    text, who = fetch(argv[0], load_keys(keyfile))
    print(f"[{who}] {len(text)} chars", file=sys.stderr)
    print(trim_adzuna(text) if "adzuna." in argv[0] else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
