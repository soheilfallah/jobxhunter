---
name: jobxhunter
description: >-
  Agent-run job hunting for the UK and Canada. Builds one plain profile from a dump folder, writes a
  master CV per target role, runs a wide search across the job boards with agents judging every
  advert against the right master CV, and files each kept job in its own dated folder with the
  advert, an evaluation and notes. Tailoring is a separate step that rewords the role's master CV
  to one advert. Also writes cover letters, interview prep and cold emails. Use whenever the user
  wants to set up a job hunt, build or update master CVs, search for jobs, judge whether a role
  fits, tailor a CV or résumé to an advert, write a cover letter, or prepare for an interview.
---

# jobxhunter

Agents do the work that needs judgement: searching, deciding whether a role fits, writing the master
CVs and tailoring them. The only bundled script is a renderer that turns a markdown CV into a Word
file. Nothing here scores a job or a CV with code.

## The five steps

| Step | Command | What happens | Runs |
|---|---|---|---|
| 1 | `/jobxhunter:setup` | makes the workspace, copies the connector tutorials in, tests what is connected | once |
| 2 | `/jobxhunter:intake` | reads `dump/`, writes `profile.md`, agrees the target roles with the user | once, then when the history changes |
| 3 | `/jobxhunter:masters` | one master CV per target role, built from the profile alone | once per role |
| 4 | `/jobxhunter:search` | finds adverts and evaluates each one. **Never tailors.** | as often as wanted |
| 5 | `/jobxhunter:tailor` | rewords the role's master CV to one evaluated advert | per job the user picks |

Around them: `/jobxhunter:cover-letter`, `/jobxhunter:interview`, `/jobxhunter:discover`.

**Search and tailoring are separate runs.** A search ends at a ranked shortlist. It does not write a
CV, even when the user is impatient and even when only one role was kept. The user reads the
shortlist, picks, and runs tailor.

## Hard rules (every command, every agent)

1. **The profile is the only source of truth.** Never question it, fact-check it, date-check it or
   flag gaps in its history. The user is right about their own history. (The distance between an
   advert and the profile is a different thing: evaluations and interview prep exist to name it.)
2. **No cross-referencing.** A master CV is built from the profile alone. A tailored CV is built from
   its role's master CV plus the advert alone. Never read sibling masters, other jobs' CVs or old
   applications while writing.
3. **Never invent a fact.** If an advert asks for something the master CV has no basis for, leave it
   out and say so in one line in `notes.md`.
4. **Never restate a fact differently to two employers.** Tailoring may change which role leads, how
   much space a role gets, which achievements show, the summary, the skills and the target title. It
   never changes dates, job titles, employer names, team sizes or qualifications.
5. **Do only what was asked.** No extra files, no extra checks, no commentary on choices. When a
   document is done, say what was made and where in one or two lines. Analysis goes in the job's
   `notes.md` or `evaluation.md`, not in chat.
6. **Ask at most one short question at a time**, and only when the answer changes the output.
7. **Never write a machine path into the plugin**, and never guess one. Paths come from the
   workspace the user points at.
8. **ATS-safe documents.** Single column, no tables, text boxes, images or header and footer content.

## The workspace

One private folder the user chooses. Nothing in it is ever sent anywhere or committed.

```
<workspace>/
  README.md              what each folder is for
  STATE.md               last search date, counts, what to do next (read first, overwrite last)
  profile.md             the one plain profile, built by intake
  dump/                  old CVs, certificates, notes: the raw material for intake
  setup/                 step-by-step tutorials for each job-board connector and API key
  master-cvs/
    TARGETS.md           the target roles, their search titles, locations and knockouts
    <family>/<role>/
      <First Last> - CV.md      the master CV (source of record)
      <First Last> - CV.docx    rendered from it (with a .txt copy for paste-in forms)
  jobs/
    tracker.md           one row per advert ever seen: dedupe ledger and application status
    <YYYY-MM-DD>/
      SHORTLIST.md       the day's kept roles, best first, then the skipped ones with reasons
      <Company> - <Role>/
        job-description.md      the full advert text
        evaluation.md           verdict, fit, requirements against evidence, gaps
        notes.md                the user's notes, and what a CV or letter left out
        CV/
          <First Last> - CV.docx        (written by tailor)
          <First Last> - Cover Letter.docx   (written by cover-letter)
```

Every CV file carries the same name, `<First Last> - CV`, taken from the name line of the profile.
That is why each one sits in its own `CV/` folder: the employer sees a clean filename and the folder
says which job it belongs to.

**Finding the workspace.** Use the path the user gave. Otherwise look for a folder holding both
`master-cvs/` and `jobs/`, starting from the current directory and walking up. If neither works, ask
where it is (one question) or offer `/jobxhunter:setup`.

Template files for a new workspace live in `<plugin folder>/assets/workspace/`.

## The plugin folder

The plugin folder is `${CLAUDE_PLUGIN_ROOT}`.

Every `references/`, `assets/`, `agents/` and `scripts/` path in this file is inside it, and
`<plugin folder>` means that path. If the line above shows a variable name and not a real path, use
the folder this file was loaded from. Write the real path into shell commands, because the shell
does not know it, and hand it to every agent you dispatch.

## The agents

| Agent | Job | Model | Effort | Why |
|---|---|---|---|---|
| `job-scout` | search every board for ONE role, return raw adverts | `sonnet` | `low` | wide and repetitive, little judgement |
| `job-evaluator` | read each full advert against the role's master CV, keep or skip, file the folder | `sonnet` | `medium` | the relevance call, made many times |
| `master-builder` | write ONE master CV from the profile | `opus` | `high` | every later CV inherits its quality |
| `cv-tailor` | reword ONE master CV to ONE advert | `opus` | `high` | the document an employer reads |

**Models are named by alias, never by version.** `sonnet`, `opus` and `haiku` always resolve to the
newest model in that family, so the agents move forward with every Claude release without an edit.
`scripts/check_release.py` fails the build if an agent pins a dated model id or drops its `model` or
`effort` line. To retune, change the frontmatter in `agents/*.md` and this table together.

Where the surface has no subagents, do the same work in the main conversation, one role or one
advert at a time, holding the same rules.

## Market

`master-cvs/TARGETS.md` names the market (`uk` or `ca`). It picks three things:

- **CV conventions:** `references/uk-conventions.md` or `references/ca-conventions.md`.
- **Boards:** `references/job-search-guide.md`.
- **Connectors:** `uk` uses Indeed, Reed and Adzuna (`gb`). `ca` uses Indeed (`CA`) and Adzuna
  (`ca`); Reed is UK only. Dice is optional in both and only worth using for software, data and AI
  roles; a missing or untested Dice is noted, never counted as a failed source.

## Surfaces

- **Claude Code:** everything works. The bundled Reed, Adzuna and Firecrawl connectors run locally.
- **Cowork / Claude Desktop:** the bundled connectors are local processes and do not connect there.
  Search with the claude.ai connectors (Indeed, Dice) plus web search, and render with the native
  `docx` skill. Everything else is the same.
- **Other agent CLIs:** see `AGENTS.md`.

Tool names differ by surface. Resolve them from the tools actually present, never from memory:
`references/tools-and-connectors.md`.

---

## SETUP

Goal: a working folder and an honest report of what is connected. Keys come last and are optional.

1. If no path was given, ask where the workspace should live (suggest `~/jobxhunter`). One question.
2. Copy `<plugin folder>/assets/workspace/` into it. Never overwrite a file that exists.
3. Test each connector with one small live call (`setup/README.md` lists the call for each, web
   search included). Where two servers offer the same tool, test the plugin's own. Write the result
   and today's date to `setup/STATUS.md`, one of four states per connector:
   - **working**: the call returned results
   - **failing**: it answered with an error; quote the error. An auth error means not connected,
     whatever the tool list says
   - **not tested**: the call was blocked before it ran (a permission prompt was declined)
   - **not set up**: the tool is not present on this surface
4. Check the optional skills: `humanizer` (final wording pass) and `docx` (Word files without the
   bundled renderer). A skill counts under any prefix, for example `anthropic-skills:docx`. Say
   which are present. Neither is required.
5. Tell the user what works now and name the one next step: drop files in `dump/`, then run
   `/jobxhunter:intake`. For a connector they want, open its tutorial in `setup/` and walk it one
   step per message. Never block on a key.

## INTAKE

Goal: `profile.md` and `master-cvs/TARGETS.md`. Method: `references/profile-intake.md`.

1. Read everything in `dump/`. Extract facts only.
2. Write `profile.md` as plain prose and lists: no schema. On a later run, merge new facts in and
   never rewrite what the user already confirmed.
3. Ask about the thin spots (an achievement with no number, a skill with no project behind it) in
   small batches, and write the answers into the profile. A question nobody answered is dropped,
   or noted in `STATE.md`. It never goes into `profile.md`.
4. Ask what jobs the user is going for. From the answer and the profile, propose the target roles
   grouped by family, and for each role its search titles. Once the user agrees, fill in the
   workspace's `master-cvs/TARGETS.md`, keeping its layout, with the market, locations and any hard
   filters.
5. Show the user the profile's path and its job headings and ask them to correct anything wrong.
   Hard rule 1 starts here: once they have confirmed it, nothing questions the profile again.
6. Stop. Next step: `/jobxhunter:masters`.

## MASTERS

Goal: one master CV per role in `TARGETS.md`. One master is never enough: a data role and an
operations role need different evidence up front, and a tailored CV is only as good as the master
it starts from.

1. Create `master-cvs/<family>/<role>/` for each role that has no master yet (or only the role the
   user named).
2. Dispatch one `master-builder` per role, all in one message so they run in parallel. Each gets the
   plugin folder path, the profile path, its own role block from `TARGETS.md`, the market and its
   output folder. **No adverts**: a master built against one advert is biased towards it.
3. Each writes `<First Last> - CV.md`, renders it (see Rendering) and stops.
4. Tell the user where the masters are and that they are theirs to edit. The edited master is the
   base for every tailored CV in that role.

## SEARCH

Goal: every new advert found, read in full, judged and filed. Method: `references/search.md`.

- **The first search is always massive.** With an empty `jobs/tracker.md`, run every title in every
  role across every working source with no date limit, paging until a page brings nothing new.
- **Later searches are incremental.** The same queries, limited to adverts posted since the last
  search date in `STATE.md`. `full` as an argument forces a massive run again.

1. **Preflight.** Read `STATE.md` and `TARGETS.md`. Test each connector with one live call and name
   any that fail. Create `jobs/<today>/`.
2. **Scout.** One `job-scout` per role, all in one message. Each writes its raw finds to
   `jobs/<today>/_found/<role>.md`.
3. **Merge.** Drop adverts already in `tracker.md`, and collapse the same job posted on several
   boards or by several agencies into one entry.
4. **Evaluate.** `job-evaluator` agents in parallel, each given up to 10 adverts of one role and the
   path to that role's master CV. Each reads the full advert, decides, and files a folder for every
   kept job.
5. **Write up.** Add every advert to `tracker.md` (kept, skipped or unread). Write `SHORTLIST.md`.
   Overwrite `STATE.md`.
6. **Report and stop.** Sources that worked and failed, counts found, new, kept, skipped and unread,
   and the shortlist path. Do not tailor.

Relevance is an agent's judgement made on the full advert text. A snippet is never enough to judge,
and a title match is never a verdict.

## TAILOR

Goal: one CV for one advert, written from that role's master CV. Method: `references/cv-craft.md`.

Input is a job folder under `jobs/`, several folders, `top N` from the latest shortlist, or an
advert the user pastes. For a pasted advert, file it first: create today's folder and the job folder
with `job-description.md`, and ask which role's master to use if it is not obvious.

Dispatch one `cv-tailor` per job (parallel when there are several). Each one:

1. Reads `job-description.md` first, then the role's master CV. Of the user's files, nothing else.
   (The plugin's own references are its instructions, not sources.)
2. Takes the advert's keywords and rewords and reorders the master's existing content to carry them
   where they are true. It does not restructure the CV and does not add facts.
3. Runs the voice pass (`references/writing-voice.md`) and, when the `humanizer` skill is installed,
   that skill on the summary and bullets.
4. Writes `CV/<First Last> - CV.md`, renders it, sets `Status: Tailored` in `notes.md` and adds one
   line there for each advert requirement it left out.

Afterwards the main conversation sets the job's row in `jobs/tracker.md` to `Tailored`.

If the role has no master CV, say so in one line and stop. Do not build one on the way.

When the user says they applied, set the row's status to `Applied` in `jobs/tracker.md`. Never
change an `Applied` row's facts afterwards.

## COVER LETTER

Write the letter complete from the advert and the profile: `references/cover-letter.md`. No
placeholders, no request for a brain-dump, no "draft" label. If the user volunteers their own words,
write from them and keep their voice. Save it as `CV/<First Last> - Cover Letter.md` in the job
folder and render it. Where the employer asks written questions instead of a letter, answer those:
`references/application-answers.md`.

## INTERVIEW

From a job folder, write `interview-prep.md` into it: `references/interview-prep.md`. The gaps listed
in `evaluation.md` are the questions to prepare hardest.

## DISCOVER

For roles that are never advertised: build a target-employer list and draft a cold email to a named
person, from the user's own words. `references/company-discovery-cold-outreach.md`. Add the employers
to the `Target employers` section of `TARGETS.md` so the next search reads their own job boards.

---

## Rendering

The master of record is the markdown file, in the shape of `assets/cv-markdown-template.md`.

- **Claude Code:** `uv run --no-config --script "<plugin folder>/scripts/render_docx.py" --in "<file>.md" --outdir "<folder>" --page <a4|letter>`
  writes the `.docx` and a `.txt` (for paste-in application boxes) beside it. `a4` for `uk`,
  `letter` for `ca`. `uv` fetches the one dependency by itself.
- **Edited the Word file by hand?** If a master's `.docx` is newer than its `.md` by more than a
  minute (a fresh render leaves the two within a second of each other), pull the edits
  back first: `uv run --no-config --script "<plugin folder>/scripts/render_docx.py" --to-md "<file>.docx"`.
- **Cowork, or wherever the `docx` skill is present:** use it instead, holding the same ATS rules.
- **Own Word template:** if `master-cvs/_template.docx` exists and the `docx` skill is present, clone
  the template for every CV and never edit the template itself.

Put the real plugin folder path in the command. A "can't open file" error naming a `scripts`
folder somewhere else on the disk means the path was left as an unexpanded variable.

**The wording pass.** "The `humanizer` skill" means any installed skill named `humanizer` or
`humanise`, under any prefix. If there are several, prefer `humanizer` with no prefix. Where
that skill's advice conflicts with `references/cv-craft.md` or `references/writing-voice.md` (it may
offer a colon in place of a dash), these references win. Apply its wording checks to the summary and
the bullets only, and keep the CV format.

## Reference map (read only what the step needs)

| When you are | Read |
|---|---|
| running a search | `references/search.md` |
| choosing boards for a market | `references/job-search-guide.md` |
| resolving a tool or connector name | `references/tools-and-connectors.md` |
| reading an advert | `references/jd-analysis.md` |
| building the profile | `references/profile-intake.md` |
| writing or tailoring a CV | `references/cv-craft.md` |
| checking wording | `references/writing-voice.md`, `references/cv-mistakes.md` |
| framing a career change | `references/career-narrative.md` |
| applying country norms | `references/uk-conventions.md`, `references/ca-conventions.md` |
| checking the file parses | `references/ats-mechanics.md` |
| writing for a research or academic role | `references/academic-register.md` |
| writing a letter or form answers | `references/cover-letter.md`, `references/application-answers.md` |
| preparing an interview | `references/interview-prep.md` |
| cold outreach | `references/company-discovery-cold-outreach.md` |
