---
description: Run the autonomous daily hunt — source, triage, tailor, and file every new live role.
argument-hint: "[optional: workspace path]"
---

Use the **jobxhunter** skill's **DAILY HUNT** routine against the populated workspace.

Read the playbook → read the profile fresh → **`python "$root/scripts/run_hunt.py" --workspace "$w"`**
(sweep every source across the whole keyword file, company boards, consolidate, rank, verify, fetch
JDs → `to-tailor.csv`) → triage every fetched advert on disk → tailor every role you can defend →
**write each cover letter in full, finished and send-ready** → write the L2 alternative-world CV per
role → track & file every job (Drafted/Skipped) → **`daily_bundle.py --root <apps>`** → verify.

**The day is not done when the script exits.** `run_hunt.py` ends at `to-tailor.csv`; if the day's
bundle folder holds no `.docx`, the day produced a spreadsheet and left the work.

**Triage is tracked on disk, not in your head.** A run that reads the loudest lane properly and skims
the rest leaves the best fit unread.

```bash
python "$root/scripts/triage.py" --workspace "$w" --init       # one row per fetched advert
python "$root/scripts/triage.py" --workspace "$w" --next --n 5  # ROUND-ROBIN BY LANE, not by rank
python "$root/scripts/triage.py" --workspace "$w" --mark <url> --verdict applied|skipped --reason "..."
python "$root/scripts/triage.py" --workspace "$w" --status      # EXITS NON-ZERO while any pending
```

`--next` hands out work round-robin across lanes on purpose. A **skip needs a reason** — skipping most
of the adverts is fine, leaving no record of why is not. **The day is not finished until `--status`
exits 0.**

**Every tailored folder must pass `scripts/validate_profile.py --folder <dir>`** (exit 0; exit 2 =
broken rules, stop) and the humanizer pass (the installed `humanizer` skill, if present) before
bundling.

**Sources the script cannot reach** (an OAuth MCP connector such as Indeed, or a board that serves a
bot interstitial to a plain GET): query them yourself, then hand the rows over so they go through the
same gate, ledger and query log as everything else — `indeed_to_rows.py` + `import_rows.py`, any time
before `--stage consolidate`. See `references/daily-hunt.md`.

**Relevance is a ranking, not a gate.** The pipeline rejects only security-clearance titles and the
Global knockouts list in `SEARCH-KEYWORDS.md`; an unmatched title scores 0 and sorts last, never
dropped. Judge fit yourself from the advert — do not expect the pipeline to have judged it for you.

**Before writing anything up:** `python "$root/scripts/verify_run.py" --workspace "$w" --date <DATE>`.
A FAIL means the run is thin — go back and search more; never write it up as thorough.

Follow `SKILL.md` ("Command: DAILY HUNT") and `references/daily-hunt.md`. Only LIVE, only NEW roles;
dedupe on the canonical link key; never touch `Applied` rows. `STATE.md` at the workspace root is the
handover: read it first, overwrite it last, keep it short.
