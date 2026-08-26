# Set up jobxhunter — five steps, about five minutes

Two readers use this file. **You**, following the steps. And **Claude Code**, when you paste this
repo's link into it and say *"set me up"* — it follows the same steps, in the same order, and asks
you one thing at a time.

## You: the five steps

**1. Install** — paste these two lines into Claude Code:

```
/plugin marketplace add soheilfallah/jobxhunter
/plugin install jobxhunter@soheil-jobxhunter
```

Claude Code will ask for API keys during install. **Leave them blank for now.** Everything works
without them; you can add them in step 5.

**2. Make your private workspace** — run:

```
/jobxhunter:setup
```

It asks where to keep your files (say a folder like `~/jobxhunter`), creates it, and stops. Nothing
in that folder is ever sent anywhere.

**3. Drop your history in.** Put your old CVs, a LinkedIn export, certificates, any notes — in any
format, any language — into the `dump/` folder it just made. Messy is fine. Then say *"done"*.

**4. Build your profile** — run:

```
/jobxhunter:intake
```

It reads everything in `dump/` and writes one master profile of your real history. Read it once and
correct anything wrong — **this file is the only thing the CVs are ever built from**, so an error
here is an error on every CV.

**5. Use it.**

| You want | Run |
|---|---|
| a CV for one job you've found | `/jobxhunter:tailor` and paste the advert |
| it to find and tailor many jobs for you | `/jobxhunter:hunt` |
| a cover letter | `/jobxhunter:cover-letter` |
| interview prep from a filed application | `/jobxhunter:interview` |

Say *"I applied to this one"* and that application locks in the tracker.

**Optional — live job boards.** Without keys, `hunt` uses web search and finds fewer roles. Two free
keys fix that: **[Adzuna](https://developer.adzuna.com/signup)** (UK + Canada jobs, salaries) and
**[Firecrawl](https://www.firecrawl.dev)** (reads full adverts on Workday/Greenhouse/Lever). Sign up,
then run `/plugin configure jobxhunter@soheil-jobxhunter` and paste them — or just tell Claude Code
*"here's my Adzuna key"* and it registers it for you. [Reed](https://www.reed.co.uk/developers/jobseeker)
is a third, UK-only.

That's it. Your history never leaves your machine; nothing is invented on a CV; you review and send.

---

## Claude Code: if the user pasted this repo and asked to be set up

Follow the five steps above **in order**, one at a time. Tell the user at the start: *"This is five
steps and about five minutes. I'll do the plumbing; you'll paste two commands and drop some files
in a folder."* Rules that matter more than speed:

- **One question at a time.** The only question step 2 needs is *where the workspace should live*.
  Suggest `~/jobxhunter` (or `Documents\jobxhunter` on Windows) and accept whatever they say.
- **Never lead with API keys.** They are step 5 and optional. If the install prompts for them, tell
  the user to leave them blank. A user who is asked for three sign-ups before seeing anything work
  stops here — that is the feedback this file exists to answer.
- **Never run `hunt` or `tailor` against an empty profile.** Step 4 must have produced a profile
  the user has looked at.
- **Verify each step before the next**, with a command, not an assumption.

The procedure, with the check for each step:

| Step | Do | Verify |
|---|---|---|
| 1 Install | Run the two `/plugin` lines (or `claude plugin marketplace add …` / `claude plugin install …` from a shell). If it is already installed, say so and move on. | `/jobxhunter:setup` is listed as a command. If not: `/reload-plugins`, then check again. |
| 2 Workspace | Ask where. Then `python "${CLAUDE_PLUGIN_ROOT}/scripts/init_workspace.py" --workspace <dir> --name <firstname>`. | The dir holds `profiles/`, `applications/`, `dump/`, `WORKSPACE-MAP.md`. Tell the user the path. |
| 3 Dump | Say exactly: *"Put your old CVs, LinkedIn export, certificates and any notes into `<dir>/dump/` — any format — then tell me 'done'."* Wait. | `dump/` is non-empty. If they have nothing, one old CV is enough; if they have no CV at all, offer to build the profile from a conversation instead (`references/profile-intake.md`). |
| 4 Profile | `/jobxhunter:intake` (the INTAKE routine in `SKILL.md`). | `profiles/<name>.md` exists. Show the user its path and the Experience headings, and ask them to correct anything wrong. Do not proceed until they have. |
| 5 Hand over | Show the four-row table above. Ask once: *"Do you want live job boards now or later?"* If later, stop — nothing breaks. If now, give the Adzuna and Firecrawl sign-up links, wait for the keys, register them (`/plugin configure …`, or the connector routine in `references/connector-setup.md`), and run `python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_connectors.py"` to show what is live. | The doctor lists each connector as configured or missing, and says which fallback covers a missing one. |

Then stop. Do not start a hunt on the user's behalf; tell them which command to run next.

**If the user is not on Claude Code** (Codex, Gemini CLI, Copilot, …): the same steps apply, minus
the slash commands — `${CLAUDE_PLUGIN_ROOT}` is the clone directory, and each `commands/*.md` file
is the task in plain language. `AGENTS.md` has the map.

## When something goes wrong

| Symptom | Fix |
|---|---|
| `/jobxhunter:…` commands not found after install | `/reload-plugins`, or restart Claude Code. |
| A script says `python-docx` or `openpyxl` is missing | `pip install python-docx openpyxl` — the script prints the exact line. |
| "No workspace resolved" | Run from inside the workspace, or set `JOBXHUNTER_DIR=<dir>` so it is found from anywhere. |
| A connector reports "credentials rejected" | The key is present but wrong. Re-copy it from the provider and run `/plugin configure jobxhunter@soheil-jobxhunter` again. |
| Running in Cowork (Claude Desktop) | Everything works except the local Reed/Adzuna/Firecrawl connectors; sourcing uses the Indeed/Dice connectors and web search there. |
