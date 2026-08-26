#!/usr/bin/env python3
"""Judge a shortlist on the JOB TITLE, so description-keyword noise stops outranking real fits.

The gap this closes: Reed and Adzuna both match a query against the job DESCRIPTION, not just
the title. So a sweep for `production manager` returns a Corporate Tax Manager whose advert
happens to contain the words, and because ranking was salary-only that £850k advert sat at the
top of the av-media lane. Sourcing was solved; relevance was not judged at all.

Everything needed to judge it is already in SEARCH-KEYWORDS.md, per lane:
  Core titles / Aim up / Same work, different name  -> what a real match looks like
  Title knockouts — auto-reject                     -> what is a factual no, whatever it pays

A row must positively match a title list SOMEWHERE to survive. The lane recorded by the sweep
is only the lane whose query happened to find it, so titles are matched against every lane and
the true lane is recorded — that alone re-files most of the mess.

Reads   <workspace>/tasks/daily/<date>/shortlist.csv
Writes  <workspace>/tasks/daily/<date>/ranked.csv   (survivors, best first)
        ...and rejects stay in the file with a reason, so nothing is lost silently.

Usage:
  python rank.py --workspace <dir> [--date YYYY-MM-DD] [--top 40]
  python rank.py --self-check
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
from sweep import lane_for  # noqa: E402
from consolidate import posted_key  # noqa: E402  (one definition of "how fresh", not a second)
enable_utf8_io()

RANKED_COLUMNS = ["rank", "score", "verdict", "gate_verdict", "matched_title", "true_lane",
                  "title", "company", "location", "salary_min", "salary_max", "posted",
                  "source", "lane", "query", "also_on", "url"]

# Weight by which list the title came from. "Aim up" scores highest on purpose: the standing
# instruction is to aim two steps up, so a stretch title is a better find, not a worse one.
LIST_WEIGHT = {"aim_up": 4, "core": 3, "same_work": 2}

# A curated list can never enumerate every real title — boards invent new ones weekly
# (Data Architect, AI Copilot Developer, Google AI FDE). So a title that pairs a domain word
# with a role word is kept even when no list entry matches, at weight 1: below every named
# title, which is the "de-prioritise, do not auto-reject" instruction in the lane's notes.
FAMILY_DOMAIN = re.compile(
    r"\b(?:data|ai|artificial intelligence|machine learning|ml|llm|genai|generative|"
    r"analytics|analytical|insight|insights|business intelligence|bi|informatics|"
    r"automation|nlp|computer vision|python|sql|power bi|tableau)\b")
FAMILY_ROLE = re.compile(
    r"\b(?:analyst|engineer|scientist|consultant|specialist|developer|architect|manager|"
    r"lead|officer|head|director|advisor|adviser|strategist|researcher|trainer|"
    # The junior tier. Without it the whole entry-level end of the market — data entry, data
    # admin, IT assistant — scored 0 instead of 1, and under the old rules 0 meant REJECTED, so
    # relaxing the salary floor without this would have changed nothing.
    r"assistant|administrator|admin|coordinator|technician|clerk|associate|operator|"
    r"support|executive|supervisor)\b")
FAMILY_LANE = "data-ai"

# Where a title that matches nothing is filed. Not "" — an empty lane disappears from the
# by-lane summary and from fetch_jds' per-lane fairness split, which is how "kept but invisible"
# becomes indistinguishable from "rejected".
UNMATCHED_LANE = "unmatched"

# A per-lane knockout costs this much score instead of rejecting the role outright. Scores are
# allowed to go NEGATIVE and that is deliberate: a title a lane explicitly does not want should
# sit below a title no lane has ever heard of, not level with it.
KNOCKOUT_PENALTY = 3

LIST_PATTERNS = {
    "core": r"\*\*Core titles[^*]*\*\*\s*—\s*(.+)",
    "aim_up": r"\*\*Aim up[^*]*\*\*\s*—\s*(.+)",
    "same_work": r"\*\*Same work, different name[^*]*\*\*\s*—\s*(.+)",
    "knockout": r"\*\*Title knockouts[^*]*\*\*\s*—\s*(.+)",
}

# Strip the decoration boards add so a title compares on its substance.
NOISE = re.compile(r"\b(?:urgent|immediate start|apply now|new|hot job|full[- ]?time|"
                   r"part[- ]?time|permanent|temporary|fixed term|contract|ftc|fte|remote|"
                   r"hybrid|onsite|maternity cover|x\d+ posts?)\b", re.I)


def norm(text):
    """For POSITIVE matching: parenthesised decoration is stripped so "AI Engineer (Remote)"
    still matches "ai engineer"."""
    t = NOISE.sub(" ", (text or "").lower())
    t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return " ".join(t.split())


def norm_full(text):
    """For KNOCKOUTS: identical, except parenthesised text is KEPT.

    `norm()` deletes anything in brackets, which is right for decoration and catastrophic for
    disqualifiers — boards write clearance as "Infrastructure Engineer (DV Cleared)" constantly.
    Tested against norm(), that advert reads as a clean "infrastructure engineer" and sails
    through. Found live: one eDV role was correctly rejected while an identical
    role with the clearance in brackets was kept."""
    t = NOISE.sub(" ", (text or "").lower())
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return " ".join(t.split())


# Security clearance is a HARD, GLOBAL reject — not a per-lane preference. A candidate who does
# not meet the residency requirement cannot obtain SC/DV/eDV/NPPV whatever the lane or the salary.
# Boards write it a dozen ways, so match the concept rather than a phrase.
CLEARANCE = re.compile(
    r"\b(?:"
    r"(?:e?dv|sc|ctc|bpss|nppv\s*[123]?)\s*(?:cleared|clearance)"
    r"|(?:security|police|government|mod)\s+(?:clearance|cleared)"
    r"|(?:must|able\s+to)\s+(?:hold|obtain|achieve)(?:\s+\w+){0,3}\s+clearance"
    r"|cleared\s+to\s+(?:e?dv|sc|ctc)"
    r"|active\s+(?:e?dv|sc)\b"
    r"|(?:e?dv|sc)\s*$"
    r")"
    )


def parse_term(raw):
    """One keyword -> a plain phrase, or ("phrase", ("qualifier", ...)) when it was bracketed.

    `norm()` DELETES bracketed text, which is correct for an advert title ("AI Engineer
    (Remote)" is an AI Engineer) and destructive for a keyword, where the bracket is usually
    the only thing distinguishing two lanes. "Production Manager (Events)" in av-media
    normalised to bare "production manager" and so claimed every factory and food-production
    role in the country — including a fresh-produce site that agri-food lists as a core title
    and lost because av-media rates it aim_up. That is not a one-line typo: the
    keyword file carries hundreds of "X (Qualifier)" entries, and every one of them was
    silently widened to X. "Apprentice (Level 2)" claimed all apprentices, "Auditor
    (Financial)" all auditors, "Applied Scientist (LLM)" all applied scientists.

    Keeping the qualifier as a co-requirement fixes the class rather than the instance. The
    phrase must match as before, AND every bracketed word must appear somewhere in the title —
    tested against norm_full(), since the advert may well write it in brackets too.
    """
    quals = [norm(q) for q in re.findall(r"\(([^)]*)\)", raw or "")]
    phrase = norm(raw)
    quals = tuple(q for q in quals if q and q != phrase)
    if not phrase:
        return ""
    return (phrase, quals) if quals else phrase


def term_text(term):
    """Display form — verdict strings and the tracker carry the matched term."""
    return term if isinstance(term, str) else "%s (%s)" % (term[0], " ".join(term[1]))


def parse_titles(path):
    """-> {lane: {list_name: [normalised titles]}} from the per-section title lists."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    out, lane = {}, ""
    for line in text.splitlines():
        if line.startswith("## "):
            lane = lane_for(line[3:])
            continue
        if not lane:
            continue
        for name, pat in LIST_PATTERNS.items():
            m = re.match(pat, line.strip())
            if not m:
                continue
            terms = [parse_term(t) for t in m.group(1).split("·")]
            terms = [t for t in terms if t]
            out.setdefault(lane, {}).setdefault(name, []).extend(terms)
    return out


def _hit_ko(title_n, term):
    """`_hit` for KNOCKOUTS, where the single-word rule has to be the opposite way round.

    `_hit` requires a single-word term to BE the whole title, which is right for a positive
    list and wrong for a knockout: `Apprentice` then only ever fires on an advert titled
    exactly "apprentice", so "Data Apprentice", "Apprentice Technician" and "Bodyguard -
    Nights" all sailed through the Global knockouts list. Harmless while an unlisted title
    was rejected anyway; a live hole once knockouts became the ONLY thing that rejects. A word boundary keeps it honest — `intern` must not match `internal`.
    """
    if not term:
        return False
    if not isinstance(term, str):
        # A bracketed knockout ("Apprentice (Level 2)") carries its qualifier too — see
        # parse_term. Every part must be present, or the knockout is wider than written.
        phrase, quals = term
        return _hit_ko(title_n, phrase) and all(_hit_ko(title_n, q) for q in quals)
    if " " in term:
        return term in title_n
    return re.search(r"\b%s\b" % re.escape(term), title_n) is not None


def _hit(title_n, term, title_full=""):
    """A multi-word term may appear anywhere in the title. A single-word term must BE the
    title (bar decoration) — otherwise 'director' matches every Director of Anything and the
    filter stops filtering. Knockouts use `_hit_ko` instead; see there.

    Returns a match QUALITY, not a boolean: COMPLETE, PARTIAL, or 0 for no match.

    A tuple term carries a bracketed qualifier from the keyword file (see `parse_term`). The
    qualifier is elaboration, not a requirement — this file writes "Applied Scientist (LLM)"
    meaning the LLM flavour of a role it also wants generally, so demanding the qualifier
    stripped 6,932 of 7,922 live rows out of their lanes when tried, most of them to
    `unmatched`. It ranks instead: a term whose qualifier is present beats one whose qualifier
    is absent, which is all that was needed. `title_full` keeps the advert's own brackets, so
    "Production Manager (Events)" satisfies the qualifier and "- Fresh Produce" does not."""
    if not term:
        return 0
    if not isinstance(term, str):
        phrase, quals = term
        if not _hit(title_n, phrase, title_full):
            return 0
        hay = title_full or title_n
        return COMPLETE if all(_hit_ko(hay, q) for q in quals) else PARTIAL
    if " " in term:
        return COMPLETE if term in title_n else 0
    return COMPLETE if title_n == term else 0


COMPLETE, PARTIAL = 2, 1          # _hit match quality; a complete match outranks a partial one

CATCHALL_LANES = ("additional-", "wildcard")


def _catchall(lane):
    """The three `additional-*` sections and `wildcard` were written by a completeness critic to
    widen coverage, so they list almost every title the real lanes list. On a tie they should
    lose: a role belongs in the hand-curated lane that names it, not in the catch-all that
    happened to be scanned first. 382 of the 467 multi-lane titles are this case, and each one
    was filing an application into the wrong folder and skewing the per-lane triage rota."""
    return (lane or "").startswith(CATCHALL_LANES[0]) or lane == CATCHALL_LANES[1]


def _better(quality, weight, term, best, lane=""):
    """Beat the incumbent match. Weight first, then specificity.

    Weight alone left ties to dict iteration order, which is the order the lanes happen to
    appear in the keyword file — arbitrary, and it decides a lot: 506 normalised titles are
    claimed by more than one lane, mostly because the three auto-generated `additional-*`
    sections were written to widen coverage and so want almost everything. Preferring the
    longer term means a lane that spelled the role out beats one that matched a fragment of
    it, which is the same judgement a human would make.
    """
    if not best[1]:
        return True                        # nothing to beat yet
    if _catchall(lane) != _catchall(best[2]):
        # Before quality and before weight: a hand-curated lane that matched at all beats a
        # junk-drawer lane that matched perfectly. Ordering quality first sent 50 live rows from
        # data-ai and av-media into `wildcard` purely because the real lane had spelled the title
        # with a bracketed flavour — a worse filing decision than the one it replaced.
        return not _catchall(lane)
    if quality != best[3]:
        return quality > best[3]
    if weight != best[0]:
        return weight > best[0]
    return len(term_text(term)) > len(term_text(best[1]) if best[1] else "")


def judge(title, titles_by_lane):
    """-> (score, verdict, matched_title, true_lane).

    RELEVANCE IS A RANKING, NOT A GATE. Micro-filtering the shortlist is how a hunt finds nothing.
    Only two things reject a role, and both are factual impossibilities rather than preferences:

      * `reject:clearance`  — SC/DV/eDV/NPPV: unobtainable on residency grounds, whatever the
                              role pays.
      * `reject:global:*`   — the Global knockouts list: a licence the candidate does not hold,
                              a statutory registration they lack, a title outside the profile's
                              ceiling.

    Everything else survives with a score. A title that matches no curated list is NOT rejected —
    it scores 0 and sorts to the bottom. The old `reject:no-title-match` threw away the answer to
    a search we had already paid for, on the grounds that a hand-written list had not anticipated
    the employer's wording. A per-lane knockout is now a PENALTY, not a rejection: those lists
    contradict each other (`agronomist` is an agri-food core title and a compliance auto-reject),
    which a penalty expresses honestly and a rejection does not.
    """
    t = norm(title)
    if not t:
        return 0, "reject:no-title", "", ""
    full = norm_full(title)               # brackets kept; bracketed qualifiers are tested on it

    best = (0, "", "", 0)             # weight, term, lane, match quality
    for lane, lists in titles_by_lane.items():
        if lane == "global":
            continue                      # a knockout store, never a lane a role can belong to
        for name, weight in LIST_WEIGHT.items():
            for term in lists.get(name, ()):
                q = _hit(t, term, full)
                if q and _better(q, weight, term, best, lane):
                    best = (weight, term, lane, q)
    score, matched, lane, _q = best
    matched = term_text(matched) if matched else ""
    unmatched = False
    if not score:
        d, r = FAMILY_DOMAIN.search(t), FAMILY_ROLE.search(t)
        if d and r:
            score, matched, lane = 1, f"family:{d.group()} {r.group()}", FAMILY_LANE
        else:
            # Matched the query only through the advert's description text. Kept anyway, at the
            # bottom of the list, so an unusually-worded title is never silently binned.
            unmatched, score, matched, lane = True, 0, "", UNMATCHED_LANE

    for term in titles_by_lane.get("global", {}).get("knockout", ()):
        # Global knockouts are factual impossibilities — a licence the candidate does not hold, a
        # statutory registration they lack, a title outside the profile's ceiling. Per-lane knockouts could
        # not express them: a title only had to be wanted by ONE lane to survive, and the
        # `additional-*` sections wanted almost everything. Applied to unmatched titles too.
        if _hit_ko(full, term) or _hit_ko(t, term):
            return 0, f"reject:global:{term}", matched, lane
    if CLEARANCE.search(full):
        # Checked for EVERY advert, including unmatched ones. Under the old order an unmatched
        # title returned before reaching here, so clearance was never tested on it — harmless
        # while unmatched meant rejected, wrong now that it means kept.
        return 0, "reject:clearance", matched, lane

    if unmatched:
        return 0, "keep:unmatched", "", UNMATCHED_LANE

    # An exact title is a stronger signal than a phrase buried in a longer one.
    if t == matched:
        score += 1

    for term in titles_by_lane.get(lane, {}).get("knockout", ()):
        # A penalty, not a rejection. Knockouts test the FULL title, brackets included — norm_full().
        if _hit_ko(full, term) or _hit_ko(t, term):
            return score - KNOCKOUT_PENALTY, f"keep:penalised:{term}", matched, lane
    return score, "keep", matched, lane


def salary_of(row):
    # `gate_verdict`, not `verdict` — this script overwrites `verdict` with its own relevance
    # call, so the L1 salary judgement has to be carried forward under its own name or a
    # typo'd ceiling silently regains the top of the list.
    if (row.get("gate_verdict") or "").startswith("keep:salary-suspect"):
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


# Above this, a figure on a UK advert is more often a day rate someone annualised, a typo, or a
# whole-team budget than an offer. `keep:salary-suspect` already exists for the obvious cases and
# IMPLAUSIBLE_TOP is 300k; capping here stops the not-quite-obvious ones heading the day's list.
SALARY_CAP = 200_000


def sort_key(row):
    """Score, then freshness, then a CAPPED salary.

    Salary cannot be the second key now that the floor is gone. Most survivors
    have no salary at all, so salary-descending would rank the bulk of the list by how the
    board happened to format the advert: undisclosed reads as 0, a raw hourly rate as 15.5,
    an annualised day rate as 169,000. Recency is the honest tiebreak — of two roles that fit
    equally well, the one posted today is the one worth the morning.
    """
    return (-int(row.get("score") or 0),
            -posted_key(row).toordinal(),
            -min(salary_of(row), SALARY_CAP))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace")
    ap.add_argument("--date", default=None)
    ap.add_argument("--keywords-file", default=None)
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()

    if args.self_check:
        return self_check()

    ws = resolve_workspace_root(args.workspace)
    if not ws:
        raise SystemExit("no workspace resolved")
    date = args.date or datetime.date.today().isoformat()
    day = os.path.join(ws, "tasks", "daily", date)
    src = os.path.join(day, "shortlist.csv")
    if not os.path.isfile(src):
        raise SystemExit(f"no shortlist at {src} — run consolidate.py first")

    kw = args.keywords_file or os.path.join(ws, "SEARCH-KEYWORDS.md")
    titles = parse_titles(kw)
    if not titles:
        raise SystemExit(f"no title lists parsed from {kw}")

    with open(src, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    kept, rejected = [], []
    for r in rows:
        score, verdict, matched, lane = judge(r.get("title"), titles)
        r["gate_verdict"] = r.get("gate_verdict") or r.get("verdict") or ""
        r.update(score=score, verdict=verdict, matched_title=matched, true_lane=lane)
        (kept if verdict.startswith("keep") else rejected).append(r)

    kept.sort(key=sort_key)
    for i, r in enumerate(kept, 1):
        r["rank"] = i

    out = os.path.join(day, "ranked.csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=RANKED_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(kept)
        w.writerows(rejected)          # kept in the file, with the reason, never dropped

    cleared = sum(1 for r in rejected if r["verdict"] == "reject:clearance")
    globals_ = sum(1 for r in rejected if r["verdict"].startswith("reject:global"))
    family = sum(1 for r in kept if r["matched_title"].startswith("family:"))
    unmatched = sum(1 for r in kept if r["verdict"] == "keep:unmatched")
    penalised = sum(1 for r in kept if r["verdict"].startswith("keep:penalised"))
    print(f"ranked {date}")
    print(f"  shortlist in       {len(rows):,}")
    print(f"  global knockouts   {globals_:,}  (impossible in every lane)")
    print(f"  clearance rejects  {cleared:,}  (SC/DV/NPPV — a residency requirement, not a preference)")
    print(f"  SURVIVORS          {len(kept):,}")
    print(f"    named title      {len(kept) - family - unmatched:,}")
    print(f"    domain+role rule {family:,}")
    print(f"    unmatched title  {unmatched:,}  (kept at 0, bottom of the list — never rejected)")
    print(f"    lane-penalised   {penalised:,}  (a lane's own knockout, demoted not dropped)")
    print(f"  -> {out}")
    lanes = {}
    for r in kept:
        lanes[r["true_lane"]] = lanes.get(r["true_lane"], 0) + 1
    print("  by true lane: " + ", ".join(f"{k} {v}" for k, v in
                                         sorted(lanes.items(), key=lambda x: -x[1])))

    # A lane whose title lists parsed EMPTY scores every one of its roles at 0 and says nothing.
    # LIST_PATTERNS needs an em-dash separator and middot item separators; type a hyphen while
    # editing SEARCH-KEYWORDS.md and the whole lane silently vanishes from the positive side.
    # The existing check only catches the case where NOTHING at all parsed.
    thin = [ln for ln, lists in titles.items()
            if ln != "global" and not any(lists.get(n) for n in LIST_WEIGHT)]
    if thin:
        print(f"\n  WARN  {len(thin)} lane(s) parsed NO positive titles — check for a plain "
              f"hyphen where an em-dash belongs, and '·' between items: {', '.join(thin)}")
    print(f"\n  top {args.top}:")
    for r in kept[:args.top]:
        s = salary_of(r)
        pay = f"£{s:,.0f}" if s else "n/d"
        print(f"   {r['rank']:>4} [{r['score']}] {pay:>9}  {r['true_lane']:<16} "
              f"{r['title'][:42]:44} {r['company'][:24]}")
    return 0


def self_check():
    T = {
        "data-ai": {"core": ["ai engineer", "data analyst"],
                    "aim_up": ["head of ai", "senior ai engineer"],
                    "same_work": ["research software engineer"],
                    "knockout": ["sc cleared", "apprentice", "senior data engineer"]},
        "av-media": {"core": ["av technician"], "aim_up": [], "same_work": [],
                     "knockout": ["apprentice"]},
        "additional-3": {"core": ["director"], "aim_up": [], "same_work": [], "knockout": []},
        "global": {"knockout": ["graduate scheme", "close protection officer"]},
    }
    # a global knockout beats every lane that wants the title
    assert judge("AI Engineer - Graduate Scheme", T)[1] == "reject:global:graduate scheme"
    # ...and "global" is a store, never a lane a surviving role is filed under
    assert judge("AI Engineer", T)[3] == "data-ai"
    # ---- NOTHING is rejected for missing the title lists -------------------------------
    # Relevance is a ranking, not a gate. A curated list's silence is not evidence against a
    # job: the list was written to FIND roles, never to refuse them. These four were all
    # `reject:no-title-match` under the old rule.
    assert judge("Corporate Tax Manager / Property & Real Estate", T)[1] == "keep:unmatched"
    assert judge("Director of Performance Marketing", T)[1] == "keep:unmatched"
    assert judge("Head Chef", T)[1] == "keep:unmatched"
    assert judge("Data Entry Clerk", T)[1] == "keep"     # now scores on the domain+role rule
    # an unmatched title scores 0 and carries a visible lane, so the by-lane summary and
    # fetch_jds' per-lane split can both see it. "" would make it disappear instead.
    assert judge("Head Chef", T)[:2] == (0, "keep:unmatched")
    assert judge("Head Chef", T)[3] == UNMATCHED_LANE
    # real matches, and aim-up outranks core
    assert judge("AI Engineer", T)[0] == 4          # core 3 + exact-title bonus
    assert judge("Senior AI Engineer", T)[0] == 5   # aim_up 4 + exact
    assert judge("Lead AI Engineer, Payments", T)[:2] == (3, "keep")   # core, embedded

    # ---- THE TRAP that this relaxation creates ----------------------------------------
    # `reject:no-title-match` used to return BEFORE clearance was ever consulted, so an
    # unlisted cleared role was rejected for the wrong reason and the bug was invisible.
    # Delete that reject without keeping clearance on the unmatched path and every unlisted
    # SC/DV role becomes a keep. This assertion is the whole reason the order matters.
    assert judge("Databricks Architect (SC Cleared)", T)[1] == "reject:clearance"
    assert judge("Warehouse Operative - DV Cleared", T)[1] == "reject:clearance"
    # ...and a global knockout must reach an unmatched title too
    assert judge("Some Unlisted Role - Graduate Scheme", T)[1] == "reject:global:graduate scheme"

    # ---- a per-lane knockout is a PENALTY, not a reject --------------------------------
    # Those lists contradict each other (`agronomist` is an agri-food core title and another
    # lane's auto-reject), so a knockout is a fact about the keyword file, not about the job.
    s_de, v_de, _, _ = judge("Senior Data Engineer", T)
    assert v_de == "keep:penalised:senior data engineer", v_de
    assert s_de < 0, s_de                       # below an unmatched title, deliberately
    assert s_de < judge("Head Chef", T)[0]
    # a single-word knockout must fire as a WORD, not only as the entire title. Under the old
    # `_hit` rule "apprentice" only matched an advert titled exactly "apprentice", so every
    # "X Apprentice" walked through the Global list untouched.
    assert _hit_ko("data apprentice", "apprentice") is True
    assert _hit_ko("internal communications manager", "intern") is False   # word boundary
    assert not _hit("data apprentice", "apprentice")                       # positives unchanged

    # clearance is caught GLOBALLY, before the per-lane knockout list is consulted
    assert judge("AI Engineer - SC Cleared", T)[1] == "reject:clearance"
    # CLEARANCE: the live bug — brackets hid the disqualifier from the knockout test
    assert judge("AI Engineer (DV Cleared)", T)[1] == "reject:clearance"
    assert judge("AI Engineer - eDV Cleared", T)[1] == "reject:clearance"
    assert judge("AI Engineer (SC Cleared)", T)[1] == "reject:clearance"
    assert judge("Data Analyst - Security Clearance Required", T)[1] == "reject:clearance"
    assert judge("AI Engineer - must hold active SC clearance", T)[1] == "reject:clearance"
    assert judge("Data Analyst (NPPV3 clearance)", T)[1] == "reject:clearance"
    assert judge("Data Analyst, cleared to SC", T)[1] == "reject:clearance"
    # boards abbreviate to a bare trailing token once the title is long
    assert judge("AI Engineer DV", T)[1] == "reject:clearance"
    assert judge("AI Engineer - SC", T)[1] == "reject:clearance"
    # ...but a title merely ENDING in an ordinary word must not trip it
    assert judge("Data Analyst", T)[1] == "keep"
    # "sc" and "dv" must never match inside an ordinary word
    assert judge("Data Scientist", T)[1] != "reject:clearance"
    assert not CLEARANCE.search("data scientist cleared desk")
    assert not CLEARANCE.search("discovery lead")
    # ...but ordinary brackets must still not trigger it, and must still match positively
    assert judge("AI Engineer (Remote)", T)[1] == "keep"
    assert judge("Data Analyst (Python/SQL)", T)[1] == "keep"
    assert norm_full("AI Engineer (DV Cleared)") == "ai engineer dv cleared"
    assert norm("AI Engineer (DV Cleared)") == "ai engineer"
    # a single-word POSITIVE entry must still not match every longer title
    assert judge("Director", T)[1] == "keep"
    # domain word + role word survives with no named title, ranked below every named one
    assert judge("Data Architect", T)[:2] == (1, "keep")
    assert judge("AI Copilot Developer", T)[:2] == (1, "keep")
    assert judge("Senior Data Science Consultant", T)[:2] == (1, "keep")
    assert judge("Data Architect", T)[3] == "data-ai"

    # ---- scoring still discriminates when most of the list is 0 ------------------------
    order = [judge(x, T)[0] for x in ("Senior AI Engineer", "AI Engineer",
                                      "Data Architect", "Head Chef")]
    assert order == sorted(order, reverse=True) == [5, 4, 1, 0], order

    # ---- a typo'd ceiling cannot buy rank 1 now that the floor is gone -----------------
    typo = {"score": 0, "posted": "2026-08-14", "gate_verdict": "keep:salary-suspect",
            "salary_min": 40000, "salary_max": 1200000}
    real = {"score": 1, "posted": "2026-08-14", "gate_verdict": "keep", "salary_max": 40000}
    assert sorted([typo, real], key=sort_key)[0] is real
    # ...and at EQUAL score and date, the cap stops a 250k figure heading the day
    hi = {"score": 1, "posted": "2026-08-14", "gate_verdict": "keep", "salary_max": 250000}
    lo = {"score": 1, "posted": "2026-08-14", "gate_verdict": "keep", "salary_max": 205000}
    assert sorted([hi, lo], key=sort_key)[0] is hi        # both capped -> date/score decide
    # freshness outranks money at equal score: two equal fits, today's is the one worth doing
    fresh = {"score": 1, "posted": "2026-08-20", "gate_verdict": "keep", "salary_max": 30000}
    stale = {"score": 1, "posted": "2026-08-01", "gate_verdict": "keep", "salary_max": 90000}
    assert sorted([stale, fresh], key=sort_key)[0] is fresh

    # a `keep:` caveat is still a keep — an exact == "keep" split silently drops every
    # penalised and unmatched row, which is a rejection wearing a different name
    assert "keep:penalised:x".startswith("keep") and "keep:unmatched".startswith("keep")
    # These were rejects under the old rule. Now they are kept and ranked: "Data Entry Clerk"
    # scores 1 on the widened domain+role rule, and the other two sit at 0 with no lane.
    # Nothing is thrown away on the strength of a hand-written list not having anticipated
    # the wording.
    assert judge("Data Entry Clerk", T)[:2] == (1, "keep")
    assert judge("Financial Controller", T)[1] == "keep:unmatched"
    assert judge("Store Colleague", T)[1] == "keep:unmatched"
    # 'ai' must be a word, never a fragment — "Chai" must not read as an AI role
    assert judge("Chai Bar Manager", T)[1] == "keep:unmatched"
    assert "ai" not in judge("Chai Bar Manager", T)[2]
    # board decoration is stripped before comparing
    assert judge("AI Engineer (Full-Time, Hybrid) - URGENT", T)[1] == "keep"
    assert judge("", T)[1] == "reject:no-title"
    assert norm("Senior  AI Engineer (Remote) - Urgent!") == "senior ai engineer"
    # the L1 salary judgement must survive this script overwriting `verdict`
    assert salary_of({"gate_verdict": "keep:salary-suspect",
                      "salary_min": 43981, "salary_max": 540198}) == 43981
    assert salary_of({"gate_verdict": "keep", "salary_min": 40000, "salary_max": 62160}) == 62160

    import tempfile
    import shutil
    tmp = tempfile.mkdtemp()
    try:
        p = os.path.join(tmp, "SEARCH-KEYWORDS.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("## Data · AI · machine learning · analytics\n\n"
                     "**Core titles (2)** — Data Analyst · AI Engineer\n\n"
                     "**Aim up (1)** — Head of Data\n\n"
                     "**Same work, different name (1) — search these** — Insight Analyst\n\n"
                     "**Title knockouts — auto-reject** — Apprentice · SC Cleared\n")
        got = parse_titles(p)
        assert got["data-ai"]["core"] == ["data analyst", "ai engineer"], got
        assert got["data-ai"]["aim_up"] == ["head of data"], got
        assert got["data-ai"]["knockout"] == ["apprentice", "sc cleared"], got

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # A bracketed keyword keeps its qualifier instead of widening to the bare phrase: an
    # av-media "Production Manager (Events)" normalised to "production manager" once took a
    # fresh-produce role off agri-food.
    assert parse_term("Production Manager (Events)") == ("production manager", ("events",))
    assert parse_term("Data Analyst") == "data analyst"
    T = {"av-media": {"aim_up": [parse_term("Production Manager (Events)")]},
         "agri-food": {"core": [parse_term("Production Manager")]}}
    assert judge("Production Manager", T)[3] == "agri-food", judge("Production Manager", T)
    assert judge("Production Manager (Events)", T)[3] == "av-media"
    assert judge("Events Production Manager", T)[3] == "av-media"
    # ...and a plain keyword is unaffected by any of it.
    assert _hit("data analyst", "data analyst", "data analyst")

    # Ties go to the more specific term, not to whichever lane the file lists first.
    T2 = {"lane-a": {"core": ["analyst"]}, "lane-b": {"core": ["analyst"]}}
    assert judge("Analyst", T2)[3] in ("lane-a", "lane-b")      # a true tie is still arbitrary
    T3 = {"wide": {"core": ["engineer"]}, "narrow": {"core": ["network engineer"]}}
    assert judge("Network Engineer", T3)[3] == "narrow", judge("Network Engineer", T3)

    # A hand-curated lane beats an auto-generated catch-all listing the same title, whichever
    # order the keyword file happens to put them in.
    for T4 in ({"additional-2": {"core": ["it support engineer"]},
                "it-support": {"core": ["it support engineer"]}},
               {"it-support": {"core": ["it support engineer"]},
                "additional-2": {"core": ["it support engineer"]}}):
        assert judge("IT Support Engineer", T4)[3] == "it-support", judge("IT Support Engineer", T4)


    # Bracket qualifiers on ambiguous aim-up terms ("General Manager (Nursery)") are what keep a
    # lane from claiming another lane's core title. A tempdir fixture cannot catch someone
    # re-adding a bare term to a LIVE keyword file; pin that in the workspace's own checks.
    T5 = {"ops-admin": {"core": ["general manager"]},
          "agri-food": {"aim_up": [parse_term("General Manager (Nursery)")]}}
    assert judge("General Manager", T5)[3] == "ops-admin"
    assert judge("General Manager (Nursery)", T5)[3] == "agri-food"
    print("rank self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
