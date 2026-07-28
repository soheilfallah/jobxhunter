#!/usr/bin/env python3
"""Track what's in the dump/ folder so INTAKE is incremental and never loses a file.

The profile is built from `<workspace>/dump/`. This script is the deterministic
book-keeper that makes intake *incremental* and *format-safe*:

1. **Manifest** — enumerate dump/ and record every file in `dump/_manifest.csv`
   (rel_path, ext, size, mtime, status, ingested_date, notes). On re-run it diffs
   the folder against the manifest, so a second intake only processes what's NEW or
   CHANGED — "update the profile every time new information comes."
2. **Placeholders** — a file the intake can't auto-extract as text on this surface
   (Word/PDF/image/binary) is marked `unreadable` and gets an empty placeholder stub
   under `profiles/_intake/placeholders/` naming the source and how to ingest it, so
   nothing is ever silently skipped.

Status values: new · updated · unreadable · ingested · missing.
The agent reads the `new`/`updated`/`unreadable` files during INTAKE, writes their
facts into the profile, then records progress with `mark`.

Usage:
  python dump_manifest.py scan  [--workspace <dir>] [--name <profile>]
  python dump_manifest.py mark  --path "<rel_path>" --status ingested [--notes "..."] [--workspace <dir>]

`scan` is the default if no subcommand is given. Paths passed to `mark` are relative
to dump/ (exactly as printed by `scan`).
"""
import argparse
import csv
import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import resolve_workspace_root, profiles_dir, safe_cell, enable_utf8_io  # noqa: E402
enable_utf8_io()

MANIFEST_NAME = "_manifest.csv"
FIELDS = ["rel_path", "ext", "size", "mtime", "status", "ingested_date", "notes"]

# Plain-text formats the agent can read directly as text on ANY surface. Everything
# else (Word/PDF/image/archive/binary) needs extraction — readable in cowork/Desktop,
# and PDFs/images via Read in Claude Code — so we record it as `unreadable` (pending
# extraction) and drop a placeholder rather than assume it was captured.
TEXT_EXTS = {
    ".txt", ".md", ".markdown", ".mdown", ".csv", ".tsv", ".json", ".yaml", ".yml",
    ".html", ".htm", ".log", ".rst", ".text", ".org",
}

# Files that are book-keeping or OS droppings, not user content — never manifest
# these. Windows sprinkles Thumbs.db/desktop.ini; macOS drops .DS_Store (also caught
# by the dot-prefix skip below). Matched case-insensitively.
SKIP_NAMES = {MANIFEST_NAME, "README.md", "readme.md", ".gitignore", ".ds_store",
              "thumbs.db", "desktop.ini"}


def _dump_dir(root):
    return os.path.join(root, "dump")


def _intake_dir(root):
    return os.path.join(profiles_dir(root), "_intake")


def _placeholders_dir(root):
    return os.path.join(_intake_dir(root), "placeholders")


def _changelog_path(root):
    return os.path.join(_intake_dir(root), "CHANGELOG.md")


def _ensure_intake_area(root):
    os.makedirs(_placeholders_dir(root), exist_ok=True)
    cl = _changelog_path(root)
    if not os.path.exists(cl):
        with open(cl, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                "# Intake changelog\n\n"
                "Each intake run appends what it added or changed in the master profile.\n"
                "Newest entries at the bottom. The profile itself is the source of truth;\n"
                "this is the audit trail.\n\n"
            )


def _slug(text, maxlen=60):
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:maxlen] or "file"


def _read_manifest(path):
    """Return {rel_path: row_dict} from an existing manifest (empty if none)."""
    rows = {}
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key = row.get("rel_path")
            if key:
                rows[key] = row
    return rows


def _write_manifest(path, rows):
    """Write rows (list of dicts) to the manifest CSV, formula-injection-safe."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: safe_cell(r.get(k, "")) for k in FIELDS})


def _enumerate_dump(dump):
    """Yield (rel_path, size, mtime, ext) for each real content file under dump/."""
    for cur, dirs, files in os.walk(dump):
        # prune hidden dirs (e.g. .git) in place
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name.lower() in SKIP_NAMES or name.startswith("."):
                continue
            full = os.path.join(cur, name)
            rel = os.path.relpath(full, dump).replace("\\", "/")
            try:
                st = os.stat(full)
            except OSError:
                continue
            ext = os.path.splitext(name)[1].lower()
            yield rel, st.st_size, int(st.st_mtime), ext


def _placeholder_stub(rel_path, ext, size):
    return (
        "<!-- INTAKE PLACEHOLDER — auto-created by dump_manifest.py. "
        "Delete once the file's facts are in the profile. -->\n"
        f"# Unread dump file: {os.path.basename(rel_path)}\n\n"
        f"- Source: `dump/{rel_path}`\n"
        f"- Type: `{ext or '(no extension)'}`  ·  Size: {size} bytes\n"
        "- Status: **not yet ingested** into the master profile.\n\n"
        "## Why this stub exists\n"
        "This is a format intake couldn't auto-read as text on the current surface "
        "(Word / PDF / image / binary). It's recorded here so nothing is silently lost.\n\n"
        "## How to ingest it (pick one)\n"
        "- Run **INTAKE in cowork / Claude Desktop**, where the agent reads PDFs, DOCX and "
        "images directly (PDFs and images also read in Claude Code).\n"
        "- Or convert it to text/markdown, drop the text version into `dump/`, and re-run intake.\n\n"
        "Once its real facts are in `profiles/<name>.md`, mark it done and delete this stub:\n\n"
        "```\n"
        f'python scripts/dump_manifest.py mark --path "{rel_path}" --status ingested\n'
        "```\n"
    )


def _write_placeholder(root, rel_path, ext, size):
    """Create the placeholder stub if absent. Returns the relative stub path or None."""
    pdir = _placeholders_dir(root)
    os.makedirs(pdir, exist_ok=True)
    stub = os.path.join(pdir, _slug(rel_path) + ".md")
    if not os.path.exists(stub):
        with open(stub, "w", encoding="utf-8", newline="\n") as f:
            f.write(_placeholder_stub(rel_path, ext, size))
    return os.path.relpath(stub, root).replace("\\", "/")


def cmd_scan(root):
    dump = _dump_dir(root)
    if not os.path.isdir(dump):
        sys.exit(f"No dump/ folder at {dump}. Run SETUP (init_workspace.py) first.")
    _ensure_intake_area(root)
    manifest_path = os.path.join(dump, MANIFEST_NAME)
    prev = _read_manifest(manifest_path)

    seen = set()
    rows = []
    counts = {"new": 0, "updated": 0, "unreadable": 0, "ingested": 0, "missing": 0}
    to_read, made_stubs = [], []

    for rel, size, mtime, ext in sorted(_enumerate_dump(dump)):
        seen.add(rel)
        is_text = ext in TEXT_EXTS
        old = prev.get(rel)
        if old is None:
            # brand-new file
            status = "new" if is_text else "unreadable"
            row = {"rel_path": rel, "ext": ext, "size": str(size), "mtime": str(mtime),
                   "status": status, "ingested_date": "", "notes": ""}
            if not is_text:
                _write_placeholder(root, rel, ext, size)
                made_stubs.append(rel)
            else:
                to_read.append(rel)
            counts[status] += 1
        else:
            changed = (old.get("size") != str(size)) or (old.get("mtime") != str(mtime))
            prev_status = old.get("status", "")
            if changed:
                status = "updated"
                if not is_text:
                    _write_placeholder(root, rel, ext, size)
                    made_stubs.append(rel)
                else:
                    to_read.append(rel)
            elif prev_status == "ingested":
                status = "ingested"
            elif prev_status == "unreadable" or not is_text:
                status = "unreadable"
                # re-create the stub if the user deleted it while still un-ingested
                _write_placeholder(root, rel, ext, size)
            else:
                # unchanged, previously new/blank text file still awaiting read
                status = "new"
                to_read.append(rel)
            row = {"rel_path": rel, "ext": ext, "size": str(size), "mtime": str(mtime),
                   "status": status, "ingested_date": old.get("ingested_date", ""),
                   "notes": old.get("notes", "")}
            counts[status] = counts.get(status, 0) + 1
        rows.append(row)

    # rows in the manifest whose file has vanished — keep for audit, flag missing
    for rel, old in prev.items():
        if rel not in seen:
            old["status"] = "missing"
            old["notes"] = (old.get("notes", "") + " | file removed from dump/").strip(" |")
            rows.append(old)
            counts["missing"] += 1

    rows.sort(key=lambda r: r["rel_path"])
    _write_manifest(manifest_path, rows)

    # report
    print(f"Dump manifest: {os.path.relpath(manifest_path, root)}")
    print("  " + "  ".join(f"{k}={counts.get(k, 0)}" for k in
                           ["new", "updated", "unreadable", "ingested", "missing"]))
    if to_read:
        print("\nREAD THESE (new/changed text files) and extract facts into the profile:")
        for rel in to_read:
            print(f"  - dump/{rel}")
    if made_stubs:
        print("\nUNREADABLE HERE — placeholder stubs created under "
              f"{os.path.relpath(_placeholders_dir(root), root)}/ :")
        for rel in made_stubs:
            print(f"  - dump/{rel}")
        print("  (read these in cowork/Desktop, or convert to text and re-scan.)")
    if not to_read and not made_stubs:
        print("\nNothing new since last scan — profile is up to date with dump/.")


def cmd_mark(root, rel_path, status, notes):
    dump = _dump_dir(root)
    manifest_path = os.path.join(dump, MANIFEST_NAME)
    prev = _read_manifest(manifest_path)
    key = rel_path.replace("\\", "/")
    if key not in prev:
        sys.exit(f"'{key}' is not in the manifest. Run `scan` first, or check the path "
                 f"(it must be relative to dump/, e.g. 'old-cv.pdf').")
    row = prev[key]
    row["status"] = status
    if status == "ingested" and not row.get("ingested_date"):
        row["ingested_date"] = datetime.date.today().isoformat()
    if notes:
        row["notes"] = notes
    _write_manifest(manifest_path, sorted(prev.values(), key=lambda r: r["rel_path"]))
    print(f"marked  dump/{key}  ->  {status}"
          + (f"  ({row['ingested_date']})" if row.get("ingested_date") else ""))
    if status == "ingested":
        stub = os.path.join(_placeholders_dir(root), _slug(key) + ".md")
        if os.path.exists(stub):
            print(f"  note: placeholder still present — delete {os.path.relpath(stub, root)} "
                  "now its facts are in the profile.")


def main():
    # --workspace must work BEFORE or AFTER the subcommand. argparse's footgun: if a
    # shared parent option is on both the top parser and the subparser with the same
    # default, the subparser's default clobbers a value parsed at top level (so
    # `--workspace X scan` silently became None). Fix: top-level owns the real default;
    # the subparser copy uses SUPPRESS so it only sets the attr when actually passed.
    sub_common = argparse.ArgumentParser(add_help=False)
    sub_common.add_argument("--workspace", default=argparse.SUPPRESS,
                            help="workspace root (else JOBXHUNTER_DIR / discovery)")

    ap = argparse.ArgumentParser(
        description="Dump-folder manifest for incremental, format-safe intake.")
    ap.add_argument("--workspace", default=None,
                    help="workspace root (else JOBXHUNTER_DIR / discovery); "
                         "may be given before or after the subcommand")
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("scan", parents=[sub_common],
                   help="enumerate dump/, update the manifest, create placeholders")
    mp = sub.add_parser("mark", parents=[sub_common], help="update one file's ingest status")
    mp.add_argument("--path", required=True, help="file path relative to dump/ (as printed by scan)")
    mp.add_argument("--status", required=True,
                    choices=["new", "updated", "unreadable", "ingested", "missing"])
    mp.add_argument("--notes", default="")
    args = ap.parse_args()

    root = resolve_workspace_root(getattr(args, "workspace", None))
    if not root:
        sys.exit("No workspace resolved. Pass --workspace <dir>, set JOBXHUNTER_DIR, or run SETUP first.")
    root = os.path.abspath(root)

    if args.cmd == "mark":
        cmd_mark(root, args.path, args.status, args.notes)
    else:  # default to scan
        cmd_scan(root)


if __name__ == "__main__":
    main()
