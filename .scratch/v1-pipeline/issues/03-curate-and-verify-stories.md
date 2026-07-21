# 03 — Curate and verify stories

**What to build:** The Curator Agent reads normalized posts, calls Claude API (Haiku 4.5) to assess importance, assign a category, generate a factual title, a concise summary, and a "why it matters" explanation — writes `candidate_stories.json`. The Verifier Agent reads candidate stories alongside the original post text, calls Claude API (Haiku 4.5) to compare every generated claim against the source, and approves or rejects each story with a reason. Rejected stories are dropped and logged, not retried. Writes `verified_stories.json`. Running the agents on fixture data produces inspectable candidate and verified story JSON.

**Blocked by:** 02 — Collect and normalize posts.

**Status:** ready-for-agent

- [ ] Curator Agent reads normalized posts and calls Haiku 4.5 via the Anthropic Python SDK
- [ ] Each candidate story has: category, factual title, concise summary, "why it matters" explanation, original post URL
- [ ] Curator does not publish — it only proposes candidates
- [ ] Verifier Agent reads candidates alongside original post text and calls Haiku 4.5
- [ ] Verifier approves or rejects each story with a logged reason
- [ ] Rejected stories are dropped from the output, not retried
- [ ] Both agents track token usage for observability
- [ ] Tests use fixture normalized posts and assert on output schema, that approved stories are faithful to sources, and that rejection reasons are logged
