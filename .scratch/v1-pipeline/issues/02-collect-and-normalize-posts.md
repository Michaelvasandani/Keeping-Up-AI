# 02 — Collect and normalize posts

**What to build:** The Collector module fetches posts from all configured X accounts and writes `raw_posts.json`. The Normalizer module reads raw posts, filters out replies and reposts, deduplicates by post ID, standardizes the schema (consistent timestamps, canonical URLs, author metadata), and writes `normalized_posts.json`. Tests use saved fixtures from Ticket 01 — no live API call needed. Running these two modules produces inspectable normalized JSON output.

**Blocked by:** 01 — Project scaffolding and X API access.

**Status:** done

- [x] Collector module reads `config/sources.json`, calls the X API for each account, writes `data/runs/<date>/raw_posts.json`
- [x] Collector handles individual account failures gracefully — logs the error, skips the account, continues
- [x] Normalizer reads raw posts and writes `data/runs/<date>/normalized_posts.json` in the standard story schema
- [x] Replies and reposts are filtered out (including defensive checks for `in_reply_to_user_id` and `referenced_tweets` of type `replied_to` or `retweeted`)
- [x] Posts are deduplicated by post ID
- [x] Timestamps are standardized to ISO format, canonical X URLs are constructed
- [x] Tests run against fixture data and assert on the normalized output schema, filtering behavior, and deduplication
