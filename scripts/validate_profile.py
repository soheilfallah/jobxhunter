#!/usr/bin/env python3
"""Validate a document against the master profile.

This replaced the old "truth sweep", and the change is more than a rename.

"Is this claim true?" is not a question this skill can answer. It has no access to the world —
only to the profile. Asking an agent to certify truth asks it to decide whether something *feels*
true, which is exactly how a plausible invention survives a review. "Does this line trace to the
profile?" is decidable, it fails closed, and a script can run it.

The rules live in the PROFILE, not in this file, so the skill stays portable: a different user
with a different profile gets their own rules for free. The profile declares them in a fenced
block (see `--emit-template`); the checker falls back to parsing a "never claim" section for
profiles written before the block existed.

GRAMMAR — eight verbs, and an unknown verb is a HARD ERROR, exit 2. An earlier parser silently
dropped unrecognised verbs, so a rules block rewritten with new verbs enforced nothing and
said nothing.

  forbid: P                      P may never appear in a submitted document (whole word,
                                 dash-normalised: – and — compare equal to -)
  require-cv: L                  exact line every CV must contain, in its LAST `## ` section
  allow: P                       the candidate's vocabulary — never an unknown-noun warning,
                                 and blanked before the LANE/JD gates run (never before forbid)
  role: K                        declares an employer: K must match exactly one `### ` heading
                                 under the profile's `## Experience`
  forbid-unless-lane: P1, P2 -> lane1, lane2
  forbid-unless-jd-mentions: P1, P2      (one group: any Pi on the page needs any Pi in the JD)
  education-for-lane: lane1, lane2 -> K1, K2   (only these degrees, in this order; `*` = default)
  overlap-print: lane1, lane2 -> K1, K2  MENU semantics: a CV prints AT MOST ONE role from the
                                 whole overlap group, and it must be on the lane's menu

Lane tokens must be lanes declared in <workspace>/JOB-LANES.md (or `*`). The lane and the
advert normally come from the application folder: applications/<lane>/<folder>/job-description.md.

    python validate_profile.py --profile <profile.md> --doc <CV.md> [--lane L] [--jd <jd.md>]
    python validate_profile.py --profile <profile.md> --folder <application dir>
    python validate_profile.py --profile <profile.md> --all <applications dir>
    python validate_profile.py --emit-template
    python validate_profile.py --self-check

Exit code 0 = clean, 1 = at least one FAIL, 2 = the RULES themselves are broken (unknown verb,
undeclared lane, a role/degree key matching no profile heading) — nothing is certified until
the rules parse. Warnings never fail the run.
"""
import argparse
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import enable_utf8_io  # noqa: E402
enable_utf8_io()

BLOCK_RE = re.compile(r"```profile-rules\s*\n(.*?)\n```", re.S | re.I)
NEVER_SECTION_RE = re.compile(r"^#{2,4}\s*.*never\s+claim.*$", re.I | re.M)

VERBS = ("forbid", "require-cv", "allow", "role", "forbid-unless-lane",
         "forbid-unless-jd-mentions", "education-for-lane", "overlap-print")

TEMPLATE = """```profile-rules
# Machine-readable rules for validate_profile.py. Everything here is checked mechanically,
# so a rule written down is a rule that is actually enforced rather than hoped for.
# An UNKNOWN verb is a hard error (exit 2) — a typo cannot silently disable a rule.
# Phrases match whole words; – and — compare equal to -. Lane tokens must be lanes declared
# in JOB-LANES.md, or * for "every lane without its own line".

forbid: <phrase that must never appear in a submitted document>
forbid: <one per line>

require-cv: <exact line every CV must contain, in its LAST section>

# The candidate's vocabulary: never an unknown-noun warning, and blanked before the
# lane/JD gates run (never before forbid).
allow: <proper noun the profile does not spell out but which is fine to use>

# One line per `### ` entry under ## Experience. The key is a substring of the heading
# here AND of the heading that prints it on a CV.
role: <substring of one Experience heading>

# Lane gates. Need --lane (or a --folder under applications/<lane>/).
forbid-unless-lane: <phrase>, <phrase> -> <lane>, <lane>
forbid-unless-jd-mentions: <phrase>, <phrase>

# Education is SELECTED per lane: only the listed degrees may print, in this order.
education-for-lane: <lane> -> <degree key>, <degree key>
education-for-lane: * -> <degree key>

# A lane's list is a MENU of permitted alternatives, not a print order. A CV prints AT
# MOST ONE role from this whole block.
overlap-print: <lane> -> <role key>, <role key>
overlap-print: * -> <role key>
```"""

# ---------------------------------------------------------------------------------------------
# helpers

DASH_RE = re.compile("[\u2013\u2014]")


def _norm(s):
    """Lowercase + en/em dashes to '-'. Real headings use U+2014; a rule typed with a plain
    hyphen would otherwise match nothing, silently."""
    return DASH_RE.sub("-", (s or "").lower())


def present(phrase, text):
    """Whole-word, dash-normalised, case-insensitive containment."""
    return re.search(r"(?<!\w)" + re.escape(_norm(phrase)) + r"(?!\w)", _norm(text)) is not None


def entries(text, section):
    """-> ([(heading, body)], orphan_bullets) for the `## <section>` part of a document."""
    out, orphans = [], []
    h2, heading, body = "", None, []
    for line in text.splitlines():
        if line.startswith("## ") and not line.startswith("### "):
            if heading is not None:
                out.append((heading, "\n".join(body)))
                heading, body = None, []
            h2 = line[3:].strip().lower()
            continue
        if section not in h2:
            continue
        if line.startswith("### "):
            if heading is not None:
                out.append((heading, "\n".join(body)))
            heading, body = line[4:].strip(), []
        elif heading is not None:
            body.append(line)
        elif line.strip().startswith("- "):
            orphans.append(line.strip())
    if heading is not None:
        out.append((heading, "\n".join(body)))
    return out, orphans


def shingles(text, n=8):
    # ponytail: 8-gram shingles catch lifted text, not paraphrase; drop n or anchor on named
    # facts if misattribution ever survives this.
    w = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def employer_from_jd(jd_text):
    """The employer name a cover letter must carry. `- **Company** X` is on every JD header;
    the fallback is the part after the last dash of the title line."""
    m = re.search(r"^- \*\*Company\*\*\s+(.+)$", jd_text or "", re.M)
    if m:
        return m.group(1).strip()
    m = re.search(r"^#\s+(.+)$", jd_text or "", re.M)
    if m and " - " in _norm(m.group(1)):
        return m.group(1).strip().rsplit("—", 1)[-1].rsplit(" - ", 1)[-1].strip()
    return ""


# AI-tell vocabulary, distilled from the `humanizer` skill's word list. WARN only. "key" is
# deliberately absent:
# "key skills" / "key requirements" is ordinary CV language and the noise drowned the signal.
AI_TELLS = ("actually", "additionally", "align with", "crucial", "delve", "emphasize",
            "emphasise", "enduring", "enhance", "foster", "garner", "interplay", "intricate",
            "intricacies", "landscape", "pivotal", "showcase", "tapestry", "testament",
            "underscore", "vibrant", "seamless", "leverage", "utilize", "utilise")
AI_TELL_RE = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in AI_TELLS)
                        + r")(?:s|es|ed|ing|d)?\b", re.I)


def declared_lanes(workspace):
    """Lane names from <workspace>/JOB-LANES.md (### `lane-name` headings). Absent file ->
    empty set -> the lane check is skipped rather than guessed at."""
    try:
        from verify_run import declared_lanes as _dl     # the pipeline's single definition
        return _dl(workspace)
    except ImportError:
        pass
    path = os.path.join(workspace, "JOB-LANES.md")
    if not os.path.isfile(path):
        return set()
    return set(re.findall(r"^#{3}\s+`([a-z0-9-]+)`", io.open(path, encoding="utf-8").read(),
                          re.M))


def lanes_for(profile_path):
    """The lane registry for a profile at <workspace>/profiles/<file>."""
    return declared_lanes(os.path.dirname(os.path.dirname(os.path.abspath(profile_path))))


def find_profile(workspace):
    """-> the workspace's profile path or None: profiles/profile.md, else the first
    profiles/*.md whose name does not start with '_'."""
    d = os.path.join(workspace, "profiles")
    p = os.path.join(d, "profile.md")
    if os.path.isfile(p):
        return p
    found = [f for f in sorted(glob.glob(os.path.join(d, "*.md")))
             if not os.path.basename(f).startswith("_")
             and not os.path.basename(f).endswith(".blocks.md")]
    return found[0] if found else None


# ---------------------------------------------------------------------------------------------
# rules

def parse_rules(profile_text, lanes=None):
    """-> dict keyed by verb. Declared block wins; otherwise the never-claim prose fallback
    fills only 'forbid'. An unknown verb, an undeclared lane token, or a role/degree key that
    matches no profile heading raises ValueError — the caller reports it and exits 2."""
    rules = {"forbid": [], "require-cv": [], "allow": [], "role": [],
             "forbid-unless-lane": [], "forbid-unless-jd-mentions": [],
             "education-for-lane": {}, "overlap-print": {}}
    m = BLOCK_RE.search(profile_text)
    if not m:
        nm = NEVER_SECTION_RE.search(profile_text)
        if nm:
            rest = profile_text[nm.end():]
            stop = re.search(r"^#{1,4}\s", rest, re.M)
            for line in (rest[:stop.start()] if stop else rest).splitlines():
                line = line.strip()
                if not line.startswith("- "):
                    continue
                term = re.split(r"\s+[\u2014\u2013-]\s+", line[2:], maxsplit=1)[0]
                term = term.replace("*", "").strip().rstrip(".")
                if term and len(term) < 60:
                    rules["forbid"].append(term)
        return rules

    for n, line in enumerate(m.group(1).splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if not val or "<" in val:
            continue                      # template placeholder
        if key not in VERBS:
            raise ValueError("line %d: unknown rule verb %r; known: %s"
                             % (n, key, ", ".join(VERBS)))
        if key in ("forbid", "require-cv", "allow", "role"):
            rules[key].append(val)
            continue
        lhs, arrow, rhs = val.partition(" -> ")
        if key in ("forbid-unless-lane", "education-for-lane", "overlap-print") and not arrow:
            raise ValueError("line %d: %r needs ' -> ' between values and lanes/keys" % (n, key))
        if key == "forbid-unless-lane":
            phrases = [p.strip() for p in lhs.split(",") if p.strip()]
            lns = [t.strip() for t in rhs.split(",") if t.strip()]
            rules[key].append((phrases, lns))
        elif key == "forbid-unless-jd-mentions":
            rules[key].append([p.strip() for p in val.split(",") if p.strip()])
        else:                             # education-for-lane / overlap-print
            keys = [k.strip() for k in rhs.split(",") if k.strip()]
            for token in (t.strip() for t in lhs.split(",") if t.strip()):
                rules[key][token] = keys
            # validation must see EVERY declared key: a later line for the same lane
            # overwrites the table entry, which would let a bad key vanish unvalidated
            rules.setdefault("_" + key + "-keys", set()).update(keys)

    # ---- parse-time validation: broken rules certify nothing --------------------------------
    if lanes:
        for token in ([t for _, lns in rules["forbid-unless-lane"] for t in lns]
                      + list(rules["education-for-lane"])
                      + list(rules["overlap-print"])):
            if token != "*" and token not in lanes:
                raise ValueError("lane %r is not declared in JOB-LANES.md (declared: %s)"
                                 % (token, ", ".join(sorted(lanes))))
    exp, _ = entries(profile_text, "experience")
    if rules["role"]:
        for k in rules["role"]:
            hits = [h for h, _ in exp if present(k, h) or _norm(k) in _norm(h)]
            if len(hits) != 1:
                raise ValueError("role key %r matches %d Experience headings %r"
                                 % (k, len(hits), hits))
        for h, _b in exp:
            if not any(_norm(k) in _norm(h) for k in rules["role"]):
                raise ValueError("Experience heading %r has no role: key — add one, or "
                                 "overlap-print and evidence checks cannot see it" % h)
        for k in rules.pop("_overlap-print-keys", set()):
            if k not in rules["role"]:
                raise ValueError("overlap-print key %r is not a declared role:" % k)
    else:
        rules.pop("_overlap-print-keys", None)
    edu, _ = entries(profile_text, "education")
    edu_keys = rules.pop("_education-for-lane-keys", set())
    if edu_keys and edu:
        for k in edu_keys:
            hits = [h for h, _ in edu if _norm(k) in _norm(h)]
            if len(hits) != 1:
                raise ValueError("education key %r matches %d Education headings %r"
                                 % (k, len(hits), hits))
    return rules


def profile_vocabulary(profile_text):
    """Every word the profile uses, lowercased — the set a document may draw on."""
    return set(re.findall(r"[a-z0-9][a-z0-9'&.-]*", profile_text.lower()))


CAP_RUN = re.compile(r"\b(?:[A-Z][\w&.'-]*)(?:\s+(?:of|and|for|the|de|van)?\s*[A-Z][\w&.'-]*)*\b")
NOISE = {
    "i", "a", "the", "my", "he", "his", "and", "for", "on", "in", "at", "to", "of", "it", "we",
    "dear", "hiring", "team", "yours", "sincerely", "application", "role", "post",
    "professional", "summary", "experience", "education", "skills", "additional", "publication",
    "eligible", "work", "level", "full", "driving", "licence", "linkedin", "com",
}


def candidate_words(profile_text):
    m = re.search(r"^#\s+(.+)$", profile_text, re.M)
    if not m:
        m = re.search(r"^-\s*Name:\s*(.+)$", profile_text, re.M)
    return set(re.findall(r"[a-z']+", m.group(1).lower())) if m else set()


def unknown_proper_nouns(doc_text, vocab, allow, own=()):
    allow_words = {w for a in allow for w in re.findall(r"[a-z0-9']+", a.lower())} | set(own)
    out = {}
    for line in doc_text.splitlines():
        if line.startswith("#") or "|" in line:
            continue
        for run in CAP_RUN.findall(line):
            words = re.findall(r"[a-z0-9']+", run.lower())
            words = [w for w in words if w not in NOISE and len(w) > 2]
            if not words:
                continue
            missing = [w for w in words if w not in vocab and w not in allow_words]
            if missing and len(missing) == len(words):
                out.setdefault(run.strip(), 0)
                out[run.strip()] += 1
    return out


COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


# ---------------------------------------------------------------------------------------------
# the check

def check(doc_path, profile_text, rules=None, lane="", jd_text=""):
    """-> (fails, warns) for one document. `jd_text` is TEXT, never a path."""
    rules = rules if rules is not None else parse_rules(profile_text)
    doc = io.open(doc_path, encoding="utf-8").read()
    # HTML comments never reach the rendered document, and the base CVs document the banned
    # terms inside one — checking the comment turns a documented rule into a violation of itself.
    doc = COMMENT_RE.sub("", doc)
    name = os.path.basename(doc_path).lower()
    fails, warns = [], []

    if name == "notes.md":
        if not re.search(r"^## Coverage matrix", doc, re.M):
            warns.append('notes.md has no "## Coverage matrix" section')
        return fails, warns

    # TWO haystacks. `low` for forbid/require-cv; `gated` for the lane/JD gates and the
    # unknown-noun warns, with `allow:` phrases blanked. Blanking before forbid would make
    # `forbid: IT Manager - Acme Farms` unmatchable via `allow: Acme Farms` — the single most
    # common stale-heading rule.
    low = doc
    gated = doc
    for a in rules["allow"]:
        gated = re.sub(re.escape(a), " ", gated, flags=re.I)

    for term in rules["forbid"]:
        if present(term, low):
            fails.append("forbidden by the profile: %r" % term)

    for phrases, lns in rules["forbid-unless-lane"]:
        for p in phrases:
            if present(p, gated) and lane not in lns:
                fails.append("%r is allowed only on lanes %s (this is %s)"
                             % (p, sorted(lns), lane or "no lane"))

    for group in rules["forbid-unless-jd-mentions"]:
        hit = [p for p in group if present(p, gated)]
        if hit and not any(present(p, jd_text) for p in group):
            fails.append("%s on the page but the advert never mentions %s"
                         % (", ".join(repr(h) for h in hit), " / ".join(group)))

    is_cv = name.startswith("cv")
    if is_cv:
        last_section = "## " + doc.rsplit("\n## ", 1)[-1] if "\n## " in doc else doc
        for line in rules["require-cv"]:
            if line not in doc:
                fails.append("required CV line missing: %r" % line)
            elif line not in last_section:
                fails.append("required CV line must sit in the last section: %r" % line)

        # education: only the lane's degrees, in the lane's order
        table = rules["education-for-lane"]
        allowed = table.get(lane) or table.get("*") if table else None
        if allowed:
            all_keys = sorted({k for keys in table.values() for k in keys}, key=len,
                              reverse=True)
            on_page = []
            for h, _b in entries(doc, "education")[0]:
                for k in all_keys:
                    if _norm(k) in _norm(h):
                        on_page.append(k)
                        break
            for k in on_page:
                if k not in allowed:
                    fails.append("degree %r must not print on lane %r" % (k, lane or "?"))
            seq = [allowed.index(k) for k in on_page if k in allowed]
            if seq != sorted(seq):
                fails.append("education order for lane %r is %s — the rule says %s"
                             % (lane or "?", on_page, allowed))

        # overlap: MENU semantics — at most ONE of the group, and it must be on the lane's menu
        table = rules["overlap-print"]
        if table:
            group = sorted({k for keys in table.values() for k in keys})
            cv_exp, orphans = entries(doc, "experience")
            on_page = [k for k in group
                       if any(_norm(k) in _norm(h) for h, _b in cv_exp)]
            if len(on_page) > 1:
                fails.append("two overlapping roles on one CV: %s (profile rule: print "
                             "exactly one, chosen by lane)" % ", ".join(on_page))
            menu = table.get(lane) or table.get("*") or group
            for k in on_page:
                if k not in menu:
                    fails.append("%r is not an overlap role printed for lane %r (menu: %s)"
                                 % (k, lane or "?", menu))
            for o in orphans:
                fails.append("bullet with no employer heading above it: %r" % o[:70])

            # evidence crossing: an 8-gram lifted from one employer's profile entry may not
            # appear under another employer's heading on the CV
            prof_exp, _ = entries(profile_text, "experience")
            gram_owner = {}
            for h, b in prof_exp:
                keys = {k for k in rules["role"] if _norm(k) in _norm(h)}
                for g in shingles(b):
                    gram_owner.setdefault(g, set()).update(keys)
            seen_pairs = set()
            for h, b in cv_exp:
                hkeys = {k for k in rules["role"] if _norm(k) in _norm(h)}
                for g in shingles(b):
                    owners = gram_owner.get(g)
                    if owners and not (owners & hkeys):
                        pair = (tuple(sorted(owners)), h)
                        if pair not in seen_pairs:
                            seen_pairs.add(pair)
                            fails.append("evidence from %s printed under %r"
                                         % ("/".join(sorted(owners)), h))

    if name.startswith("coverletter"):
        emp = employer_from_jd(jd_text)
        if not emp:
            warns.append("no employer name found in the JD — letter naming not checked")
        elif not any(emp.lower() in line.lower()
                     for line in doc.splitlines() if not line.startswith("Dear ")):
            fails.append("the letter never names the employer %r outside the salutation" % emp)

    own = candidate_words(profile_text)
    for run, n in sorted(unknown_proper_nouns(gated, profile_vocabulary(profile_text),
                                              rules["allow"], own).items()):
        warns.append("not in the profile: %r%s" % (run, " (x%d)" % n if n > 1 else ""))

    body = "\n".join(l for l in doc.splitlines() if not l.startswith("#"))
    body = re.sub(r'"[^"\n]*"', "", body)
    tells = {}
    for w in AI_TELL_RE.findall(body):
        w = w.lower()
        tells[w] = tells.get(w, 0) + 1
    if tells:
        warns.append("AI-tell vocabulary (humanizer list): "
                     + ", ".join("%s x%d" % (k, v) for k, v in sorted(tells.items())[:8]))

    return fails, warns


def docs_in(folder):
    return [p for p in (os.path.join(folder, n)
                        for n in ("CV.md", "CoverLetter.md", "notes.md"))
            if os.path.isfile(p)]


def check_folder(folder, profile_text, rules, lane=None, jd_text=None):
    """-> [(doc, fails, warns)]. Lane defaults to the parent directory name
    (applications/<lane>/<folder>); the JD to the folder's job-description.md."""
    folder = os.path.abspath(folder)
    if lane is None:
        lane = os.path.basename(os.path.dirname(folder))
    if jd_text is None:
        jd = os.path.join(folder, "job-description.md")
        jd_text = io.open(jd, encoding="utf-8").read() if os.path.isfile(jd) else ""
    return [(d, *check(d, profile_text, rules, lane, jd_text)) for d in docs_in(folder)]


# ---------------------------------------------------------------------------------------------

def self_check():
    import tempfile
    import shutil
    tmp = tempfile.mkdtemp()
    try:
        prof = os.path.join(tmp, "p.md")
        PTEXT = (
            "# Test Person\n\n"
            "## Experience\n\n"
            "### Greenhouse Lead \u2014 Acme Farms, Tehran, Iran\n"
            "2022 - 2023\n"
            "- ran the growing programme across four climate controlled bays measuring yield "
            "weekly against plan\n\n"
            "### Data Analyst \u2014 Northwind Ltd\n"
            "2023 - 2024\n"
            "- built the reporting pipeline that cut month end close from nine days to two "
            "for the finance team\n\n"
            "## Education\n\n"
            "### MSc Data \u2014 Uni A\nGPA 18/20\n\n"
            "### BSc Plants \u2014 Uni B\n\n"
            "```profile-rules\n"
            "forbid: qPCR\n"
            "forbid: IT Manager - Acme Farms\n"
            "require-cv: Eligible to work in the UK.\n"
            "allow: Acme Farms\n"
            "role: Acme Farms\n"
            "role: Northwind\n"
            "forbid-unless-lane: GPA -> research\n"
            "forbid-unless-jd-mentions: Tehran, Iran\n"
            "education-for-lane: data-ai -> MSc Data\n"
            "education-for-lane: * -> MSc Data, BSc Plants\n"
            "overlap-print: data-ai -> Northwind\n"
            "overlap-print: * -> Acme Farms\n"
            "```\n")
        io.open(prof, "w", encoding="utf-8", newline="\n").write(PTEXT)
        ptext = io.open(prof, encoding="utf-8").read()
        lanes = {"data-ai", "research", "agri-food"}
        rules = parse_rules(ptext, lanes)
        assert rules["forbid"] == ["qPCR", "IT Manager - Acme Farms"], rules["forbid"]
        assert rules["require-cv"] == ["Eligible to work in the UK."]
        assert rules["role"] == ["Acme Farms", "Northwind"]
        assert rules["overlap-print"]["*"] == ["Acme Farms"]
        assert rules["education-for-lane"]["data-ai"] == ["MSc Data"]

        # unknown verb / undeclared lane / bad keys are HARD errors
        for bad in ("frobid: x\n", "forbid-unless-lane: x -> nope\n",
                    "role: Nowhere\n", "education-for-lane: data-ai -> PhD Rocks\n",
                    "overlap-print: data-ai -> Unregistered\n"):
            try:
                parse_rules(PTEXT.replace("```profile-rules\n", "```profile-rules\n" + bad),
                            lanes)
                raise AssertionError("did not raise on %r" % bad)
            except ValueError:
                pass

        # dash normalisation: a rule typed with '-' matches a heading typed with U+2014
        assert present("IT Manager - Acme Farms", "### IT Manager \u2014 Acme Farms Ltd")
        assert present("acme", "necessarily acme") and not present("acme", "necessarilyacme")

        # allow-vs-forbid ordering: allow blanks the GATES, never a forbid
        cv = os.path.join(tmp, "CV.md")

        def w(text):
            io.open(cv, "w", encoding="utf-8", newline="\n").write(text)
            return cv

        base = ("# Test Person\n## Analyst\ncontact@x | 07 | London\n\n"
                "## Professional Summary\nAnalyst.\n\n"
                "## Experience\n\n### Data Analyst \u2014 Northwind Ltd\n2023 - 2024\n"
                "- built the reporting pipeline that cut month end close from nine days to two "
                "for the finance team\n\n"
                "## Education\n\n### MSc Data \u2014 Uni A\n\n"
                "## Additional\nEligible to work in the UK.\n")
        f, _ = check(w(base), ptext, rules, lane="data-ai")
        assert f == [], f
        f, _ = check(w(base.replace("Analyst.", "IT Manager \u2014 Acme Farms then qPCR.")),
                     ptext, rules, lane="data-ai")
        assert any("IT Manager - Acme Farms" in x for x in f), f     # allow: did NOT blank it
        assert any("qPCR" in x for x in f), f

        # require-cv placement
        f, _ = check(w(base.replace("## Additional\nEligible to work in the UK.\n",
                                    "")), ptext, rules, lane="data-ai")
        assert any("required CV line missing" in x for x in f), f
        f, _ = check(w("Eligible to work in the UK.\n" + base.replace(
            "Eligible to work in the UK.", "See above.")), ptext, rules, lane="data-ai")
        assert any("must sit in the last section" in x for x in f), f

        # lane gates fail closed
        f, _ = check(w(base.replace("Analyst.", "GPA 18/20 analyst.")), ptext, rules,
                     lane="data-ai")
        assert any("allowed only on lanes" in x for x in f), f
        f, _ = check(w(base.replace("Analyst.", "GPA 18/20 analyst.")), ptext, rules,
                     lane="research")
        assert not any("allowed only" in x for x in f), f
        # JD gate: Tehran on the page fails with no JD, passes when the advert says Iran;
        # 'Acme Farms, Tehran' is protected by allow-blanking only for the gate
        f, _ = check(w(base.replace("Analyst.", "Worked in Tehran.")), ptext, rules,
                     lane="data-ai", jd_text="")
        assert any("never mentions" in x for x in f), f
        f, _ = check(w(base.replace("Analyst.", "Worked in Tehran.")), ptext, rules,
                     lane="data-ai", jd_text="Our Iran desk")
        assert not any("never mentions" in x for x in f), f

        # education selection + order
        f, _ = check(w(base.replace("### MSc Data \u2014 Uni A",
                                    "### BSc Plants \u2014 Uni B")), ptext, rules,
                     lane="data-ai")
        assert any("must not print" in x for x in f), f
        f, _ = check(w(base.replace("### MSc Data \u2014 Uni A",
                                    "### BSc Plants \u2014 Uni B\n\n### MSc Data \u2014 Uni A")),
                     ptext, rules, lane="agri-food")
        assert any("education order" in x for x in f), f

        # overlap menu
        two = base.replace(
            "## Education",
            "### Greenhouse Lead \u2014 Acme Farms\n2022 - 2023\n- grew\n\n## Education")
        f, _ = check(w(two), ptext, rules, lane="data-ai")
        assert any("two overlapping roles" in x for x in f), f
        f, _ = check(w(base.replace("Data Analyst \u2014 Northwind Ltd",
                                    "Greenhouse Lead \u2014 Acme Farms")
                       .replace("- built the reporting pipeline that cut month end close from "
                                "nine days to two for the finance team", "- grew things")),
                     ptext, rules, lane="data-ai")
        assert any("not an overlap role printed for lane" in x for x in f), f

        # orphan bullet + evidence crossing
        f, _ = check(w(base.replace("## Experience\n",
                                    "## Experience\n- orphan bullet no heading\n")),
                     ptext, rules, lane="data-ai")
        assert any("no employer heading" in x for x in f), f
        crossed = base.replace(
            "- built the reporting pipeline that cut month end close from nine days to two "
            "for the finance team",
            "- ran the growing programme across four climate controlled bays measuring yield "
            "weekly against plan")
        f, _ = check(w(crossed), ptext, rules, lane="data-ai")
        assert any("evidence from Acme Farms" in x for x in f), f

        # cover letter employer naming
        letter = os.path.join(tmp, "CoverLetter.md")
        io.open(letter, "w", encoding="utf-8", newline="\n").write(
            "Dear Hiring Team,\nI am applying for the role.\nYours sincerely\n")
        jd = "# Analyst - BigCo\n- **Company** BigCo\n"
        f, _ = check(letter, ptext, rules, lane="data-ai", jd_text=jd)
        assert any("never names the employer" in x for x in f), f
        io.open(letter, "w", encoding="utf-8", newline="\n").write(
            "Dear Hiring Team,\nI am applying to BigCo for the role.\nYours sincerely\n")
        f, _ = check(letter, ptext, rules, lane="data-ai", jd_text=jd)
        assert f == [], f
        f, wn = check(letter, ptext, rules, lane="data-ai", jd_text="")
        assert f == [] and any("not checked" in x for x in wn), (f, wn)

        # notes.md
        notes = os.path.join(tmp, "notes.md")
        io.open(notes, "w", encoding="utf-8", newline="\n").write("## L2 delta\nx\n")
        f, wn = check(notes, ptext, rules)
        assert f == [] and any("Coverage matrix" in x for x in wn), (f, wn)
        io.open(notes, "w", encoding="utf-8", newline="\n").write("## Coverage matrix\n|a|b|\n")
        f, wn = check(notes, ptext, rules)
        assert f == [] and wn == [], (f, wn)

        # AI tells warn, never fail
        f, wn = check(w(base.replace("Analyst.", "We delve into pivotal landscapes.")),
                      ptext, rules, lane="data-ai")
        assert f == [], f
        assert any("AI-tell" in x for x in wn), wn

        # check_folder infers lane from the parent dir
        app = os.path.join(tmp, "apps", "research", "2026-01-01_x_y")
        os.makedirs(app)
        io.open(os.path.join(app, "CV.md"), "w", encoding="utf-8", newline="\n").write(
            base.replace("Analyst.", "GPA 18/20 analyst."))
        got = check_folder(app, ptext, rules)
        assert got and not any("allowed only" in x for _, fs, _ in got for x in fs), got

        # find_profile: profile.md wins, .blocks.md never counts, '_' files skipped
        pd = os.path.join(tmp, "ws", "profiles")
        os.makedirs(pd)
        for n in ("_draft.md", "zed.md", "zed.blocks.md"):
            io.open(os.path.join(pd, n), "w").write("x")
        assert os.path.basename(find_profile(os.path.join(tmp, "ws"))) == "zed.md"
        io.open(os.path.join(pd, "profile.md"), "w").write("x")
        assert os.path.basename(find_profile(os.path.join(tmp, "ws"))) == "profile.md"
        assert find_profile(os.path.join(tmp, "nowhere")) is None
        io.open(os.path.join(tmp, "ws", "JOB-LANES.md"), "w", encoding="utf-8").write(
            "### `data-ai`\n### `research`\n")
        assert lanes_for(os.path.join(pd, "profile.md")) == {"data-ai", "research"}

        # prose fallback still yields forbids
        io.open(prof, "w", encoding="utf-8", newline="\n").write(
            "# Profile\n### Technique gaps \u2014 never claim these\n"
            "- **qPCR** \u2014 conceptual knowledge only.\n\n## Next\n")
        fb = parse_rules(io.open(prof, encoding="utf-8").read())
        assert fb["forbid"] == ["qPCR"], fb["forbid"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("validate_profile self-check OK")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile")
    ap.add_argument("--doc", action="append", default=[])
    ap.add_argument("--folder")
    ap.add_argument("--all", dest="all_dir")
    ap.add_argument("--lane", default="", help="lane for the gate verbs; --folder infers it")
    ap.add_argument("--jd", help="path to the advert; --folder infers job-description.md")
    ap.add_argument("--quiet", action="store_true", help="failures only; hide warnings")
    ap.add_argument("--emit-template", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()

    if args.self_check:
        return self_check()
    if args.emit_template:
        print(TEMPLATE)
        return 0
    if not args.profile:
        ap.error("--profile is required")

    ptext = io.open(args.profile, encoding="utf-8").read()
    try:
        rules = parse_rules(ptext, lanes_for(args.profile))
    except ValueError as e:
        print("RULES ERROR: %s" % e)
        print("Nothing was checked; nothing is certified until the profile-rules block parses.")
        return 2
    if not rules["forbid"] and not rules["require-cv"]:
        print("WARNING: the profile declares no rules. Add the block from --emit-template.")

    jdtext = io.open(args.jd, encoding="utf-8").read() if args.jd else ""

    results = []
    for d in args.doc:
        results.append((d, *check(d, ptext, rules, args.lane, jdtext)))
    if args.folder:
        results += check_folder(args.folder, ptext, rules,
                                args.lane or None, jdtext or None)
    if args.all_dir:
        for d in sorted(glob.glob(os.path.join(args.all_dir, "*", "*"))):
            if os.path.isdir(d) and docs_in(d):
                results += check_folder(d, ptext, rules)
    if not results:
        ap.error("nothing to check: pass --doc, --folder or --all")

    bad = warned = 0
    for d, fails, warns in results:
        if fails:
            bad += 1
            print("FAIL %s" % d)
            for f in fails:
                print("       %s" % f)
        if warns and not args.quiet:
            warned += 1
            print("warn %s" % d)
            for w in warns[:6]:
                print("       %s" % w)
            if len(warns) > 6:
                print("       ...and %d more" % (len(warns) - 6))
    print("\n%d document(s) checked · %d failed · %d with warnings"
          % (len(results), bad, 0 if args.quiet else warned))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
