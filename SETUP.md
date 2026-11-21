# Set up jobxhunter: five steps

Two readers use this file. **You**, following the steps. And **Claude Code**, when you paste this
repo's link into it and say *"set me up"*: it follows the same steps in the same order and asks you
one thing at a time.

## You: the five steps

**1. Install.** Paste these into Claude Code:

```
/plugin marketplace add soheilfallah/jobxhunter
/plugin install jobxhunter@soheil-jobxhunter
```

Claude Code asks for API keys during install. **Leave them blank.** Everything works without them
and you can add them later.

**2. Make your workspace.**

```
/jobxhunter:setup
```

It asks where to keep your files (a folder like `~/jobxhunter`), creates it, and tells you which job
boards are connected right now. Nothing in that folder is ever sent anywhere.

**3. Drop your history in, then build your profile.** Put your old CVs, a LinkedIn export,
certificates and any notes into the `dump/` folder. Any format, any language, messy is fine. Then:

```
/jobxhunter:intake
```

It writes one plain profile of your real history and agrees with you which roles you are going
for. Read the profile once and correct anything wrong: every CV is built from it.

**4. Build your master CVs.**

```
/jobxhunter:masters
```

One master CV per role. Open them and edit them until they sound like you. Every tailored CV starts
from the master for its role, so time spent here pays back on every application.

**5. Search, choose, tailor.**

| You want | Run |
|---|---|
| to find jobs and have each one judged | `/jobxhunter:search` |
| a CV for a job from the shortlist | `/jobxhunter:tailor` and name the job |
| a CV for an advert you found yourself | `/jobxhunter:tailor` and paste the advert |
| a cover letter | `/jobxhunter:cover-letter` |
| interview prep | `/jobxhunter:interview` |

The first search is a big one and takes a while: it covers every title on every board. It ends at a
shortlist in `jobs/<date>/SHORTLIST.md`. It does not write CVs. You read the shortlist, pick, and
tailor those.

**Optional: connect the job boards.** Without connectors the search uses web search and finds fewer
roles. Your workspace has a `setup/` folder with a step-by-step guide for each one, in order of
value: Indeed (no key), Adzuna, Firecrawl, Reed. Or say *"set up Adzuna"* and Claude walks you
through it.

---

## Claude Code: if the user pasted this repo and asked to be set up

Follow the five steps above **in order**, one at a time. Tell the user at the start: *"This is five
steps. I'll do the plumbing; you'll paste two commands and drop some files in a folder."*

- **One question at a time.** Step 2 needs only one: where the workspace should live.
- **Never lead with API keys.** They are optional and come after something has worked. If the
  install prompts for them, tell the user to leave them blank.
- **Verify each step before the next,** by looking, not by assuming.
- **Never search or tailor against an empty profile or with no master CV.**

| Step | Do | Verify |
|---|---|---|
| 1 Install | The two `/plugin` lines (or `claude plugin marketplace add ...` and `claude plugin install ...` from a shell). If already installed, say so and move on. | `/jobxhunter:setup` is listed. If not: `/reload-plugins`, then check again. |
| 2 Workspace | Ask where. Copy `<plugin folder>/assets/workspace/` there without overwriting anything. Test each connector with a live call and write `setup/STATUS.md`. | The folder holds `dump/`, `setup/`, `master-cvs/TARGETS.md` and `jobs/tracker.md`. Tell the user the path and what is connected. |
| 3 Profile | Say: *"Put your old CVs, LinkedIn export, certificates and notes into `<dir>/dump/`, then tell me 'done'."* Wait. Then run the INTAKE routine. | `profile.md` exists and the user has read it. `TARGETS.md` lists at least one role with its titles. |
| 4 Masters | The MASTERS routine. | Each role in `TARGETS.md` has a `<First Last> - CV.md` and `.docx`. Tell the user to read and edit them. |
| 5 Hand over | Show the table above. Ask once: *"Do you want to connect job boards now or later?"* If now, open the guides in `setup/` one at a time, Indeed first. | `setup/STATUS.md` reflects what really works. |

Then stop. Do not start a search on the user's behalf; tell them the command.

**If the user is not on Claude Code** (Codex, Gemini CLI, Copilot): the same steps apply without
the slash commands. The plugin folder is the clone directory, and each `commands/*.md` file is
the task in plain language. `AGENTS.md` has the map.

## When something goes wrong

| Symptom | Fix |
|---|---|
| `/jobxhunter:...` commands not found after install | `/reload-plugins`, or restart Claude Code. |
| A connector says the key is missing, but you set it | Restart Claude Code first. If it persists, put the key in `~/.jobxhunter/.env` (the connector's guide in `setup/` gives the exact lines). |
| A connector says the credentials were rejected | The key is present but wrong. Copy it again from the provider. |
| The Word file is not created | Install `uv` (<https://docs.astral.sh/uv/>). The renderer runs through it. |
| The search found very little | Check `setup/STATUS.md` for failing boards, then widen the "same work, different name" titles in `master-cvs/TARGETS.md`. |
| Running in Cowork (Claude Desktop) | The local Reed, Adzuna and Firecrawl connectors do not run there. The search uses Indeed, Dice and web search. |
