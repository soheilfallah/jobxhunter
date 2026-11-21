#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["python-docx"]
# ///
"""Render an ATS-safe .docx and a plain-text .txt from a structured markdown CV.

The only script in the plugin: turning markdown into a Word file is mechanical, so
it is code. Everything that needs judgement is done by agents.

ATS-safe by construction: single column, no tables, no text boxes, no images,
no headers/footers, standard fonts, conventional section headings. This is a
hold-the-line invariant of the skill — do not add tables or columns here.

Input markdown convention (assets/cv-markdown-template.md):

    # Full Name
    ## Target Role Title
    City, Country | +44 7... | email@x.com | website.com

    ## Professional Summary
    A short paragraph.

    ## Experience
    ### Job Title | Sep 2023 - Jul 2024 | Organisation, City
    - Bullet with verb + task + method + outcome.
    - Another bullet.

    ## Education
    ### MSc Something | University, City

    ## Skills
    - Category: item, item, item

    ## Certifications
    - Item

Rules:
  #    -> name (document title line, large bold)
  next non-empty, non-## line after the name -> contact line
  ##   -> section heading
  ###  -> entry sub-heading (role / degree title)
  -    -> bullet (level 1); "  -" (indented) -> bullet level 2
  other non-empty line -> normal paragraph (dates, summary text)

Usage:
  uv run render_docx.py --in "Jane Doe - CV.md" --outdir <folder>   # writes the .docx + .txt
  uv run render_docx.py --to-md "Jane Doe - CV.docx"                # Word edits back into the .md
"""
import argparse
import os
import re
import sys

# UTF-8 stdout/stderr so printing a CV path or heading with accents/£/em-dashes never
# dies with a UnicodeEncodeError on a default (cp1252) Windows console.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

try:
    from docx import Document
    from docx.shared import Pt, RGBColor, Mm, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
except ImportError:
    sys.exit("python-docx is required. Run this with `uv run` (it installs it), "
             "or: pip install python-docx")

# Page size by market. UK-first default is A4; Canada/US use US Letter. python-docx
# otherwise defaults to Letter, so UK renders needed this to be correct.
PAGE_SIZES = {
    "a4": (Mm(210), Mm(297)),         # UK and most of the world
    "letter": (Inches(8.5), Inches(11)),  # Canada, US
}

BODY_FONT = "Arial"        # widely parseable, standard
BODY_SIZE = 10.5
NAME_SIZE = 20
SECTION_SIZE = 12
ENTRY_SIZE = 11
DARK = RGBColor(0x1F, 0x1F, 0x1F)
ACCENT = RGBColor(0x30, 0x54, 0x96)


def parse(md):
    """Return a structured list of ('kind', text/level) tokens."""
    # HTML comments are how a template carries its own instructions. They MUST NOT reach the
    # rendered document: the base data/AI template carried template notes that quoted the barred
    # IELTS line, and without this they rendered into the .docx and would have been sent to an
    # employer. A CV is the one artefact where a leaked internal note is unrecoverable.
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    lines = md.replace("\r\n", "\n").split("\n")
    tokens = []
    name_seen = False
    contact_pending = False
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            if contact_pending:
                contact_pending = False
            continue
        if stripped.startswith("# ") and not stripped.startswith("## "):
            tokens.append(("name", stripped[2:].strip()))
            name_seen = True
            contact_pending = True
            continue
        if contact_pending and stripped.startswith("## "):
            # The target-role line sits between the name and the contact line. Recruiter-critics
            # flagged its absence on all six CVs of 10 Aug; without this branch it was swallowed
            # as the contact line and rendered with its literal '##'.
            tokens.append(("target", stripped[3:].strip()))
            continue
        if contact_pending:
            tokens.append(("contact", stripped))
            contact_pending = False
            continue
        if stripped.startswith("### "):
            tokens.append(("entry", stripped[4:].strip()))
            continue
        if stripped.startswith("## "):
            tokens.append(("section", stripped[3:].strip()))
            continue
        m = re.match(r"^(\s*)-\s+(.*)$", raw)
        if m:
            indent = len(m.group(1))
            level = 2 if indent >= 2 else 1
            tokens.append(("bullet", (level, m.group(2).strip())))
            continue
        tokens.append(("para", stripped))
    if not name_seen:
        sys.exit("Input has no '# Name' line — cannot render a CV.")
    return tokens


def _strip_md_inline(text):
    # keep it simple: drop ** and * emphasis markers; ATS reads plain text best
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return text


def build_docx(tokens, out_path, page="a4"):
    doc = Document()
    # base style
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(BODY_SIZE)
    normal.font.color.rgb = DARK
    width, height = PAGE_SIZES.get(page, PAGE_SIZES["a4"])
    # tight margins for two-page fit; explicit page size (A4 vs US Letter by market)
    for s in doc.sections:
        s.page_width, s.page_height = width, height
        s.top_margin = s.bottom_margin = Pt(36)      # 0.5"
        s.left_margin = s.right_margin = Pt(54)      # 0.75"

    def spacer(before=0, after=0):
        pass

    for kind, val in tokens:
        if kind == "name":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(_strip_md_inline(val))
            r.bold = True
            r.font.size = Pt(NAME_SIZE)
            r.font.color.rgb = DARK
            p.paragraph_format.space_after = Pt(2)
        elif kind == "target":
            p = doc.add_paragraph()
            r = p.add_run(_strip_md_inline(val))
            r.bold = True
            r.font.size = Pt(BODY_SIZE + 1)
            r.font.color.rgb = DARK
            p.paragraph_format.space_after = Pt(2)
        elif kind == "contact":
            p = doc.add_paragraph()
            r = p.add_run(_strip_md_inline(val))
            r.font.size = Pt(BODY_SIZE)
            r.font.color.rgb = DARK
            p.paragraph_format.space_after = Pt(8)
        elif kind == "section":
            p = doc.add_paragraph()
            r = p.add_run(_strip_md_inline(val).upper())
            r.bold = True
            r.font.size = Pt(SECTION_SIZE)
            r.font.color.rgb = ACCENT
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(2)
            # bottom border for scan-ability (still single-column, ATS-safe)
            _bottom_border(p)
        elif kind == "entry":
            p = doc.add_paragraph()
            r = p.add_run(_strip_md_inline(val))
            r.bold = True
            r.font.size = Pt(ENTRY_SIZE)
            r.font.color.rgb = DARK
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(0)
        elif kind == "bullet":
            level, text = val
            style = "List Bullet" if level == 1 else "List Bullet 2"
            try:
                p = doc.add_paragraph(_strip_md_inline(text), style=style)
            except KeyError:
                p = doc.add_paragraph(_strip_md_inline(text), style="List Bullet")
            p.paragraph_format.space_after = Pt(1)
        elif kind == "para":
            p = doc.add_paragraph()
            r = p.add_run(_strip_md_inline(val))
            r.font.size = Pt(BODY_SIZE)
            r.italic = _looks_like_dates(val)
            p.paragraph_format.space_after = Pt(6)   # a cover letter is all paragraphs
    doc.save(out_path)


def _looks_like_dates(text):
    return bool(re.search(r"\b(19|20)\d{2}\b", text) and
                re.search(r"present|–|-|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", text, re.I))


def _bottom_border(paragraph):
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pbdr = pPr.makeelement(qn("w:pBdr"), {})
    bottom = pbdr.makeelement(qn("w:bottom"), {
        qn("w:val"): "single", qn("w:sz"): "6", qn("w:space"): "1", qn("w:color"): "B0B0B0"})
    pbdr.append(bottom)
    pPr.append(pbdr)


def build_txt(tokens, out_path):
    out = []
    for kind, val in tokens:
        if kind == "name":
            out.append(_strip_md_inline(val).upper())
        elif kind == "target":
            out.append(_strip_md_inline(val))
        elif kind == "contact":
            out.append(_strip_md_inline(val))
            out.append("")
        elif kind == "section":
            out.append("")
            out.append(_strip_md_inline(val).upper())
            out.append("=" * len(val))
        elif kind == "entry":
            out.append(_strip_md_inline(val))
        elif kind == "bullet":
            level, text = val
            prefix = "  - " if level == 1 else "    * "
            out.append(prefix + _strip_md_inline(text))
        elif kind == "para":
            out += [_strip_md_inline(val), ""]     # blank line after: letters paste as paragraphs
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).rstrip() + "\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)


def docx_to_md(path):
    """Read a .docx this script rendered (and a person then edited in Word) back into markdown.

    shortcut: paragraphs are recognised by the formatting build_docx() gives them (font size,
    bold, list style), so it only understands files this renderer made. Upgrade to real Word
    styles if people start bringing their own documents.
    """
    def size(par):
        for r in par.runs:
            if r.text.strip() and r.font.size is not None:
                return r.font.size.pt, bool(r.bold)
        return None, False

    out, head = [], 0          # head: 0 = before the name, 1 = in the name/title/contact block
    for par in Document(path).paragraphs:
        text = par.text.strip()
        if not text:
            continue
        pt, bold = size(par)
        style = (par.style.name or "") if par.style is not None else ""
        if head == 0:
            out.append("# " + text)
            head = 1
        elif head == 1 and bold and pt == BODY_SIZE + 1:
            out.append("## " + text)
        elif head == 1:
            out += [text, ""]
            head = 2
        elif style.startswith("List Bullet"):
            out.append(("  - " if style.endswith("2") else "- ") + text)
        elif bold and pt == SECTION_SIZE:
            out += ["", "## " + text.title()]
        elif bold and pt == ENTRY_SIZE:
            out += ["", "### " + text]
        else:
            out.append(text)
    return "\n".join(out).strip() + "\n"


def self_check():
    md = ("# Firstname Lastname\n"
          "## AI Lead\n"
          "a@b.com | london\n\n"
          "## Professional Summary\n"
          "Ships things.\n\n"
          "<!-- TEMPLATE NOTE: IELTS Academic 7.0 must never appear on a CV -->\n"
          "## Additional\n"
          "- Eligible to work in the UK.\n")
    toks = parse(md)
    kinds = [k for k, _ in toks]
    assert kinds[:3] == ["name", "target", "contact"], kinds
    assert ("target", "AI Lead") in toks
    assert ("contact", "a@b.com | london") in toks
    # the whole point: nothing from inside an HTML comment may survive into the document
    flat = " ".join(str(v) for _, v in toks)
    assert "IELTS" not in flat and "TEMPLATE NOTE" not in flat, flat
    import tempfile
    import os as _os
    d = tempfile.mkdtemp()
    try:
        p = _os.path.join(d, "CV.txt")
        build_txt(toks, p)
        got = open(p, encoding="utf-8").read()
        assert "AI Lead" in got and "IELTS" not in got and "##" not in got, got
        build_txt(parse("# A B\na@b.com\n\nDear team,\n\nFirst para.\n\nSecond para.\n"), p)
        assert "First para.\n\nSecond para.\n" in open(p, encoding="utf-8").read()
        # round trip: what we render, we can read back (the path a Word-edited master takes)
        md2 = ("# Firstname Lastname\n## AI Lead\na@b.com | london\n\n"
               "## Professional Summary\nShips things.\n\n"
               "## Experience\n### Analyst | Jan 2022 - Present | Acme, Leeds\n"
               "- Built it.\n  - Twice.\n")
        dx = _os.path.join(d, "CV.docx")
        build_docx(parse(md2), dx)
        assert parse(docx_to_md(dx)) == parse(md2), docx_to_md(dx)
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    print("render_docx self-check OK")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Render ATS-safe .docx + .txt from a markdown CV.")
    ap.add_argument("--self-check", action="store_true")
    if "--self-check" in sys.argv:
        return self_check()
    if "--to-md" in sys.argv:
        src = sys.argv[sys.argv.index("--to-md") + 1]
        dst = os.path.splitext(src)[0] + ".md"
        with open(dst, "w", encoding="utf-8") as f:
            f.write(docx_to_md(src))
        print(f"Wrote {dst}")
        return 0
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--out-docx")
    ap.add_argument("--out-txt")
    ap.add_argument("--outdir")
    ap.add_argument("--basename", default=None,
                    help="output stem inside --outdir. Defaults to the INPUT file's own stem, so "
                         "CV.md -> CV.docx and CoverLetter.md -> CoverLetter.docx. (It used to "
                         "default to 'CV', which silently overwrote the CV when rendering a letter "
                         "into the same folder.)")
    ap.add_argument("--page", choices=("a4", "letter"), default="a4",
                    help="page size: a4 (UK/world, default) or letter (Canada/US market=ca).")
    args = ap.parse_args()

    with open(args.infile, encoding="utf-8") as f:
        md = f.read()
    tokens = parse(md)

    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)
        # Derive the stem from the input unless the caller named one explicitly. Rendering
        # CoverLetter.md into a job folder must never land on CV.docx.
        stem = args.basename or os.path.splitext(os.path.basename(args.infile))[0]
        out_docx = args.out_docx or os.path.join(args.outdir, stem + ".docx")
        out_txt = args.out_txt or os.path.join(args.outdir, stem + ".txt")
    else:
        out_docx = args.out_docx or (os.path.splitext(args.infile)[0] + ".docx")
        out_txt = args.out_txt or (os.path.splitext(args.infile)[0] + ".txt")

    build_docx(tokens, out_docx, page=args.page)
    build_txt(tokens, out_txt)
    # Touch the source last, so a .docx NEWER than its .md can only mean it was edited in Word.
    os.utime(args.infile)
    print(f"Wrote {out_docx} ({args.page.upper()})")
    print(f"Wrote {out_txt}")


if __name__ == "__main__":
    main()
