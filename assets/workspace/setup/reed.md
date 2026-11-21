# Reed (free key, UK only)

Reed is strong for UK agency, admin, data and security roles and returns the full advert. Skip it
if you are searching in Canada.

1. Go to <https://www.reed.co.uk/developers/jobseeker> and register.
2. Open **Jobseeker API** and copy the **API key** (36 characters).
3. In Claude Code run `/plugin configure jobxhunter@soheil-jobxhunter` and paste it into
   **Reed API key**.
4. Restart Claude Code.
5. Run `/jobxhunter:setup` again. `STATUS.md` should show Reed as working.

**If it still says the key is missing after a restart**, create the file `~/.jobxhunter/.env` with
this line and restart again:

```
REED_API_KEY=your-key
```
