# Search: find every advert, then judge each one

A search has two halves and two kinds of agent. **Scouts** collect adverts widely and do not judge.
**Evaluators** read each advert in full against the role's master CV and decide. Nothing in a search
writes a CV: that is `/jobxhunter:tailor`, a separate run.

The orchestrator (the main conversation) only dispatches, merges and writes the day's files. It does
not read adverts itself, so a long search does not wear its context down.

## 0. Massive or incremental

| | When | Date limit | Breadth |
|---|---|---|---|
| **Massive** | `jobs/tracker.md` has no rows, or the user said `full` | none | every title of every role, every working source, every page |
| **Incremental** | any later run | adverts posted since the last search date in `STATE.md`, minus one day of overlap | the same queries |

The first search is always massive. It is the one that maps the market, so it is allowed to be slow
and large. Say so before starting: how many roles, how many sources, and that it will take a while.

## 1. Preflight

1. Read `STATE.md` and `master-cvs/TARGETS.md`. A role in `TARGETS.md` with no master CV cannot be
   evaluated: name it, skip it, and tell the user to run `/jobxhunter:masters`.
2. List the search tools this surface really has (`references/tools-and-connectors.md`), and make
   one small live call on each. Sort them into working and failing. An auth error means failing,
   even though the tool is listed.
3. Tell the user which sources are in and which are out, in one line, **before** the search runs. A
   search missing a major board is still worth running, but the user decides knowing it. A source
   whose test call was blocked before it ran is "not tested": say so, and do not search it.
4. Write the result of the live tests to `setup/STATUS.md`, with today's date.
5. Create `jobs/<YYYY-MM-DD>/` and `jobs/<YYYY-MM-DD>/_found/`.

## 2. Scout

Dispatch one `job-scout` per role, all in a single message so they run together. Give each:

- the plugin folder path
- that role's block from `TARGETS.md`
- the market, the locations, and the target employers if any are listed
- the mode and, when incremental, the since-date
- the working sources
- its output file: `jobs/<date>/_found/<role>.md`

**Source order inside a scout.** Boards with their own detail tool first (Indeed, Reed), then
sector boards reached by search and page reading (`references/job-search-guide.md` lists them by
market), then the employers' own boards, and the aggregator (Adzuna) last because it repeats the
others.

**Paging rule.** A query keeps paging until a page adds nothing the scout has not already recorded.
Page one is never the whole result. Where a source gives one page per query and no date filter
(Indeed does), breadth comes from running every title and every location as its own query, and the
since-date is applied by reading each result's posted date.

**Employers' own boards.** Most company career pages sit on a handful of systems that publish their
vacancies as open JSON. For each target employer, a scout reads the matching feed and keeps the
roles whose titles fit:

| System | Open feed |
|---|---|
| Greenhouse | `https://boards-api.greenhouse.io/v1/boards/<company>/jobs` |
| Lever | `https://api.lever.co/v0/postings/<company>?mode=json` |
| Ashby | `https://api.ashbyhq.com/posting-api/job-board/<company>` |
| Workable | `https://apply.workable.com/api/v1/widget/accounts/<company>` |
| SmartRecruiters | `https://api.smartrecruiters.com/v1/companies/<company>/postings` |
| Recruitee | `https://<company>.recruitee.com/api/offers/` |

Check the board really belongs to that employer (the company name on the feed matches) before
trusting it. An empty feed means unresolved, not "no vacancies".

## 3. Merge

Read the scouts' files and reduce them to one list of new adverts:

1. **Already seen.** Drop any advert whose link is in `jobs/tracker.md`. Compare links without their
   tracking parameters. Indeed hands out a different short link for the same job on every call, so
   match Indeed adverts on employer, title and location instead.
2. **Left over from last time.** Rows in the tracker with status `Found` were collected by an earlier
   run that stopped before judging them. They go to the evaluators first.
3. **Same job, several places.** One employer, one title, one location is one job, however many
   boards or agencies carry it. Keep the copy with the best full text (the employer's own page
   first) and note the others as "also on".
4. **Found by two roles.** Give it to the role listed first in `TARGETS.md`.

## 4. Evaluate

Dispatch `job-evaluator` agents in parallel. Each gets up to 10 adverts of **one** role, the path to
that role's master CV, the knockouts and filters from `TARGETS.md`, the plugin folder path and the
day folder. Larger sets are split; a role with 35 new adverts gets four evaluators.

Each evaluator fetches the full advert, decides, and files a folder for every kept job (`SKILL.md`
shows the layout; `agents/job-evaluator.md` holds the file formats).

**The bar for a skip is a wall.** An advert is skipped only for a fact that makes applying
pointless: a hard knockout the user set, a licence or clearance or right to work they do not hold, a
different trade under a similar title, an expired advert, a duplicate. Salary, location, contract
type and a stretch in seniority are not skip reasons unless `TARGETS.md` marks them as hard filters.
A role the candidate is half qualified for is a `B`, not a skip.

**Unread is its own verdict.** When the full text cannot be fetched, the advert is `unread`. It goes
in the tracker and the shortlist so the user can open the link themselves. It is never judged from a
snippet.

## 5. Write up

**`jobs/tracker.md`**: one row per advert the evaluators returned, whatever the verdict. This file is
the dedupe ledger, so a skipped advert is recorded as carefully as a kept one.

```
| found | company | role | location | source | link | role family | verdict | status | folder |
```

- `verdict` is the evaluator's call and never changes: `A`, `B`, `skip: <reason>` or `unread`.
- `status` is where the application stands. It starts as `Kept`, `Skipped` or `Unread`, and later
  moves to `Tailored`, `Applied`, `Interview`, `Offer` or `Rejected`. An `Applied` row is never
  rewritten by a search.
- `folder` is the job folder's path from the workspace root, or `-` when there is none.

**If the run stops before every advert has been judged** (a limit was hit, the session ended), add
the unjudged adverts to the tracker with status `Found` and an empty verdict. The next search
evaluates them first. A found advert is never silently dropped.

**`jobs/<date>/SHORTLIST.md`**: what the user reads.

1. Kept roles, best first: tier `A` before `B`. Inside a tier, the one with more requirements marked
   `strong` in its evaluation comes first, then the better pay, then the more senior title, then the
   sooner closing date. One line each with company, role, location, pay, closing date and the folder.
2. Closing within seven days: listed again at the top as a short warning block.
3. Unread adverts, with their links.
4. Not judged yet: adverts left as `Found`, with their links. The next search judges them first.
5. Skipped adverts, grouped by reason.
6. One closing line: the listings were retrieved by AI-powered search, and details should be checked
   with the employer before applying.

**`STATE.md`**: overwrite it, keeping the template's lines: the search date, the mode of the next
search, sources working, failing and not tested, the counts (found, new, kept `A` and `B`, skipped,
unread, left as `Found`), any role that was not searched and why, and the next step.

Delete `jobs/<date>/_found/` once the tracker is written: it is working material.

## 6. Report and stop

A few lines in chat:

- sources that worked, and each source that failed with its error
- adverts found, new after merging, kept (`A` and `B`), skipped, unread
- the shortlist path
- the next step: read the shortlist, then `/jobxhunter:tailor`

If a source failed or a role had no master CV, the search was thinner than it looks. Say that
plainly. Never describe a partial search as complete.

**Do not tailor.** Not the top role, not "just one to save time".
