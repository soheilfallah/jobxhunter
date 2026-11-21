# Firecrawl (free key)

Firecrawl reads the full text of an advert behind any link: company career sites, Workday,
Greenhouse, Lever, PDFs. Without it some adverts can only be read as a short snippet, and those are
marked `unread` instead of being judged.

1. Go to <https://www.firecrawl.dev> and sign up (there is a free tier).
2. Open the dashboard, then **API Keys**. Copy the key that starts with `fc-`.
3. In Claude Code run `/plugin configure jobxhunter@soheil-jobxhunter` and paste it into
   **Firecrawl API key**.
4. Restart Claude Code.
5. Run `/jobxhunter:setup` again. `STATUS.md` should show Firecrawl as working.

**If it still does not start**, register it yourself, once, from a terminal:

```
claude mcp add firecrawl --scope user -e FIRECRAWL_API_KEY=your-key -- npx -y firecrawl-mcp
```

Firecrawl needs Node.js installed, because it runs through `npx`.
