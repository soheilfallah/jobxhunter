# -*- coding: utf-8 -*-
"""Assemble a CV from shared blocks whose every fact is BOUND to the master profile.

A batch of CVs written one at a time lets the same fact drift in wording from document to
document. Assembling the invariant parts from shared blocks fixes that by construction — and
`bind()` asserts that every load-bearing fact a block prints EXISTS in the profile, so a stale
block aborts before anything is written. The profile's rules block (parsed by
validate_profile) then decides per lane: which overlap role prints (MENU: at most one), which
degrees print and in what order, and which blocks and lines the lane/JD gates allow.

Blocks are curated, not parsed out of the profile's prose (profile entries carry guidance a
CV must not print). They live in a WORKSPACE file beside the profile:

    profiles/<name>.blocks.md          for profiles/<name>.md

FORMAT of the blocks file (see assets/sample-profile.blocks.md for a complete example):

    ```cvgen
    fact: <string that must appear in the profile>[ | <alternate spelling>]
    lane-blocks: <lane>, <lane> -> <block key>, OVERLAP, <block key>     print order
    lane-blocks: * -> ...                                               default
    ```
    ## contact                       one line: the contact line under the name
    ## block: <role key>             an Experience entry; its `### ` heading MUST contain the
                                     role key (the profile's `role:` line) or the validator's
                                     overlap and evidence checks cannot see it
    ## education: <degree key>       an Education entry, keyed as in `education-for-lane`
    ## education-detail: <degree key>  optional richer variant, printed when its text passes
                                     the lane gates (e.g. a `forbid-unless-lane: GPA` rule)
    ## section: <name> -> <lanes>    an extra `## <name>` section after Education, on those
                                     lanes only (omit ` -> ` for every lane)
    ## additional                    lines for the final `## Additional` section; the last
                                     line should be the profile's `require-cv:` line

OVERLAP in a lane's block list is replaced by the first key on the lane's `overlap-print`
menu. Gating is automatic: a block, education entry, section or additional line that contains
a `forbid-unless-lane` phrase is skipped on a lane that rule does not allow, and one that
contains a `forbid-unless-jd-mentions` phrase is skipped unless the advert mentions the
group — the same tests the validator applies, so the build passes by construction.

The bespoke parts — target title, summary, skills, cover letter — are never generated here.

    import cvgen
    blocks = cvgen.load_blocks(cvgen.blocks_path_for(profile_path))
    cv = cvgen.build(ptext, rules, lane, target, summary, skills, jd_text, blocks)
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import validate_profile as vp  # noqa: E402
from _lib import enable_utf8_io  # noqa: E402
enable_utf8_io()

CONFIG_RE = re.compile(r"```cvgen\s*\n(.*?)\n```", re.S)
CONFIG_VERBS = ("fact", "lane-blocks")


def blocks_path_for(profile_path):
    stem, _ = os.path.splitext(profile_path)
    return stem + ".blocks.md"


def load_blocks(path):
    """-> dict: facts [[alts]], lanes {lane: [keys]}, contact, block {key: text},
    education {key: text}, education_detail {key: text}, section [(name, lanes|None, text)],
    additional [lines]. Unknown config verb or duplicate key -> ValueError."""
    text = vp.COMMENT_RE.sub("", io.open(path, encoding="utf-8").read())
    out = {"facts": [], "lanes": {}, "contact": "", "block": {}, "education": {},
           "education_detail": {}, "section": [], "additional": []}
    m = CONFIG_RE.search(text)
    if m:
        for n, line in enumerate(m.group(1).splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if key not in CONFIG_VERBS:
                raise ValueError("%s line %d: unknown cvgen verb %r; known: %s"
                                 % (path, n, key, ", ".join(CONFIG_VERBS)))
            if key == "fact":
                out["facts"].append([a.strip() for a in val.split(" | ") if a.strip()])
            else:
                lhs, arrow, rhs = val.partition(" -> ")
                if not arrow:
                    raise ValueError("%s line %d: lane-blocks needs ' -> '" % (path, n))
                keys = [k.strip() for k in rhs.split(",") if k.strip()]
                for lane in (t.strip() for t in lhs.split(",") if t.strip()):
                    out["lanes"][lane] = keys
        text = text[:m.start()] + text[m.end():]

    for part in re.split(r"^## ", text, flags=re.M)[1:]:
        head, _, body = part.partition("\n")
        kind, _, key = head.strip().partition(":")
        kind, key, body = kind.strip(), key.strip(), body.strip("\n")
        if kind == "contact":
            out["contact"] = body.strip()
        elif kind == "additional":
            out["additional"] = [l for l in body.splitlines() if l.strip()]
        elif kind == "section":
            name, arrow, lanes = key.partition(" -> ")
            out["section"].append((name.strip(),
                                   [t.strip() for t in lanes.split(",")] if arrow else None,
                                   body))
        elif kind in ("block", "education", "education-detail"):
            store = out[kind.replace("-", "_")]
            if not key or key in store:
                raise ValueError("%s: missing or duplicate %s key %r" % (path, kind, key))
            if kind == "block" and vp._norm(key) not in vp._norm(body.split("\n", 1)[0]):
                raise ValueError("%s: block %r heading does not contain its key" % (path, key))
            store[key] = body
        else:
            raise ValueError("%s: unknown block section %r" % (path, head.strip()))
    return out


def bind(profile_text, blocks):
    """-> [] when every declared fact traces to the profile; else the list of misses."""
    norm = vp._norm(profile_text)
    return [alts[0] for alts in blocks["facts"] if not any(vp._norm(a) in norm for a in alts)]


def candidate_name(profile_text):
    m = (re.search(r"^#\s+(.+)$", profile_text, re.M)
         or re.search(r"^-\s*Name:\s*(.+)$", profile_text, re.M))
    return m.group(1).strip() if m else "Candidate"


def permitted(text, rules, lane, jd_text=""):
    """The validator's two gates, applied to one piece of text with `allow:` blanked."""
    gated = text
    for a in rules["allow"]:
        gated = re.sub(re.escape(a), " ", gated, flags=re.I)
    for phrases, lanes in rules["forbid-unless-lane"]:
        if lane not in lanes and any(vp.present(p, gated) for p in phrases):
            return False
    for group in rules["forbid-unless-jd-mentions"]:
        if any(vp.present(p, gated) for p in group) and \
                not any(vp.present(p, jd_text or "") for p in group):
            return False
    return True


def build(profile_text, rules, lane, target, summary, skills, jd_text="", blocks=None,
          extras=()):
    """-> CV markdown. Shape: `# Name` / `## Target` / contact — NO blank line between name
    and title (render_docx reads the title from that exact position)."""
    assert blocks is not None, "pass blocks=load_blocks(...)"
    problems = bind(profile_text, blocks)
    assert not problems, "cvgen facts missing from the profile: %s" % problems

    menu = rules["overlap-print"].get(lane) or rules["overlap-print"].get("*") or []
    pick = menu[0] if menu else None
    order = blocks["lanes"].get(lane) or blocks["lanes"].get("*") or list(blocks["block"])

    out = ["# " + candidate_name(profile_text), "## " + target, blocks["contact"], "",
           "## Professional Summary", summary, "", "## Experience", ""]
    seen = set()
    for key in order:
        if key == "OVERLAP":
            key = pick
        text = blocks["block"].get(key)
        if not key or key in seen or not text or not permitted(text, rules, lane, jd_text):
            continue
        seen.add(key)
        out += [text, ""]

    edu_keys = (rules["education-for-lane"].get(lane) or rules["education-for-lane"].get("*")
                or list(blocks["education"]))
    out += ["## Education", ""]
    for k in edu_keys:
        detail = blocks["education_detail"].get(k)
        text = detail if detail and permitted(detail, rules, lane, jd_text) else \
            blocks["education"][k]
        out += [text, ""]

    for name, lanes, text in blocks["section"]:
        if (lanes is None or lane in lanes) and permitted(text, rules, lane, jd_text):
            out += ["## " + name, text, ""]

    out += ["## Skills"] + list(skills) + ["", "## Additional"]
    out += [l for l in blocks["additional"] if permitted(l, rules, lane, jd_text)]
    out += list(extras)
    return "\n".join(out) + "\n"


def self_check():
    import tempfile
    import shutil
    import render_docx
    prof = os.path.join(HERE, "..", "assets", "sample-profile.md")
    ptext = io.open(prof, encoding="utf-8").read()
    blocks = load_blocks(blocks_path_for(prof))
    lanes = {"research", "agri-food", "retail-hospitality", "ops-admin", "data-ai"}
    rules = vp.parse_rules(ptext, lanes)
    assert bind(ptext, blocks) == [], bind(ptext, blocks)

    tmp = tempfile.mkdtemp()
    try:
        for lane in sorted(lanes) + ["*"]:
            cv = build(ptext, rules, lane, "Test Target Role", "A short bespoke summary.",
                       ["- Skill one.", "- Skill two."], jd_text="A role in London.",
                       blocks=blocks)
            kinds = [k for k, _ in render_docx.parse(cv)]
            assert kinds[:3] == ["name", "target", "contact"], (lane, kinds[:3])
            app = os.path.join(tmp, lane if lane != "*" else "wildcard-x", "t")
            os.makedirs(app, exist_ok=True)
            io.open(os.path.join(app, "CV.md"), "w", encoding="utf-8",
                    newline="\n").write(cv)
            fails, _ = vp.check(os.path.join(app, "CV.md"), ptext, rules,
                                lane=(lane if lane != "*" else ""),
                                jd_text="A role in London.")
            assert fails == [], (lane, fails)
            last = [l for l in cv.splitlines() if l.strip()][-1]
            assert last == "- Eligible to work in the UK.", (lane, last)

        # JD-gated lines appear only when the advert asks
        cv = build(ptext, rules, "data-ai", "T", "S.", ["- x."], blocks=blocks,
                   jd_text="Must hold a full driving licence.")
        assert "Full driving licence." in cv, cv
        assert "driving licence" not in build(ptext, rules, "data-ai", "T", "S.", ["- x."],
                                              blocks=blocks, jd_text="No extras.").lower()
        # lane-gated block prints only where the rule allows
        assert "Farrow" in build(ptext, rules, "retail-hospitality", "T", "S.", ["- x."],
                                 blocks=blocks)
        assert "Farrow" not in build(ptext, rules, "data-ai", "T", "S.", ["- x."],
                                     blocks=blocks)
        # overlap pick follows the lane's menu; education follows the lane's table
        cv = build(ptext, rules, "research", "T", "S.", ["- x."], blocks=blocks)
        assert "### Greenhouse Operations Supervisor" in cv and \
            "### Graduate Researcher" not in cv and "## Publication" in cv
        assert cv.index("MSc Controlled Environment") < cv.index("MSc Big Data")
        cv = build(ptext, rules, "data-ai", "T", "S.", ["- x."], blocks=blocks)
        assert "### Graduate Researcher" in cv and "## Publication" not in cv
        # a stale fact aborts the build
        try:
            build(ptext.replace("MDPI Plants (2024)", "MDPI Plants (2023)"), rules,
                  "data-ai", "T", "S.", ["- x."], blocks=blocks)
            raise RuntimeError("stale fact did not abort")
        except AssertionError:
            pass
        # a blocks file with a bad verb or a heading missing its key is refused
        bad = os.path.join(tmp, "bad.blocks.md")
        for text in ("```cvgen\nfrobnicate: x\n```\n",
                     "## block: Acme\n### Manager — Somewhere Else\n- x\n"):
            io.open(bad, "w", encoding="utf-8").write(text)
            try:
                load_blocks(bad)
                raise RuntimeError("bad blocks file accepted: %r" % text)
            except ValueError:
                pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("cvgen self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(self_check() if "--self-check" in sys.argv else print(__doc__) or 0)
