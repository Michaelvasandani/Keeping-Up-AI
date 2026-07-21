# 04 — Publish to static HTML

**What to build:** The Publisher module reads verified stories and renders a self-contained `feed.html` with inline CSS and JavaScript. The page includes search, category filters, date grouping (newest first), source handles with avatars, original post links, and a last-updated timestamp. It opens locally in a browser with no backend, build step, or external dependencies. Tests assert on HTML output generated from fixture verified stories.

**Blocked by:** 03 — Curate and verify stories.

**Status:** ready-for-agent

- [ ] Publisher reads verified stories JSON and writes a self-contained `feed.html`
- [ ] All story data is inlined in the HTML — no external data fetches at runtime
- [ ] Category filter chips work (including with zero matching results)
- [ ] Search works across titles and summaries (including with zero matching results)
- [ ] Stories are grouped by date, newest first
- [ ] Each story shows: source handle, avatar, category, title, summary, "why it matters", link to original X post
- [ ] Last-updated timestamp is displayed
- [ ] No API keys, tokens, secrets, or local paths appear in the output
- [ ] Generated summaries are labeled as summaries, not presented as original content
- [ ] Tests assert on HTML structure, story count, and absence of leaked credentials from fixture data
