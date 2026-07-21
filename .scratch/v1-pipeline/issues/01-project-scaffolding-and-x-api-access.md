# 01 — Project scaffolding and X API access

**What to build:** Set up the Python project structure with dependencies (Anthropic SDK, any X API client needed), create `config/sources.json` seeded with ~10-15 high-signal AI engineering X accounts, confirm X API credentials are working, and save sample raw API responses as test fixtures. By the end, a script fetches real posts from one account and prints them.

**Blocked by:** None — can start immediately.

**Status:** done

- [x] Python project with a `requirements.txt` (or `pyproject.toml`) including the `anthropic` package and any X API dependency
- [x] `config/sources.json` exists with ~10-15 curated accounts (handle, category hint per account)
- [x] X API credentials are confirmed working — a script successfully retrieves posts from at least one account
- [x] Sample raw API responses saved to `tests/fixtures/` as JSON files for use by downstream tests
- [x] Project runs with `python` — no build step, no framework
