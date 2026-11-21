# Adzuna (free app id and key)

Adzuna covers both the UK and Canada and is the source of the salary figures.

1. Go to <https://developer.adzuna.com/signup> and register. This is a developer account, separate
   from a jobseeker login.
2. Create an app (**Create app**).
3. Copy two values: the **App ID** (8 characters) and the **App Key** (32 characters).
4. In Claude Code run `/plugin configure jobxhunter@soheil-jobxhunter` and paste them into
   **Adzuna app id** and **Adzuna app key**.
5. Restart Claude Code.
6. Run `/jobxhunter:setup` again. `STATUS.md` should show Adzuna as working.

**If it still says the credentials are missing after a restart**, create the file
`~/.jobxhunter/.env` with these two lines and restart again:

```
ADZUNA_APP_ID=your-app-id
ADZUNA_APP_KEY=your-app-key
```

**If it says the credentials were rejected**, the values are present but wrong. The two are easy to
swap: the id is the short one.
