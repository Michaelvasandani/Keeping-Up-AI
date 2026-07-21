# V1 Pipeline: AI Engineer Intelligence Hub

Status: ready-for-agent

## Problem Statement

AI engineers building with LLMs need to stay current with a fast-moving field, but the signal-to-noise ratio on X (the primary announcement channel for AI labs and researchers) is terrible. Manually checking dozens of accounts daily is unsustainable, and existing news aggregators don't filter for what matters to practitioners.

## Solution

A fully autonomous pipeline that runs daily via GitHub Actions, collects posts from a curated list of high-signal X accounts, uses LLM agents to select and summarize the most important updates, verifies every generated claim against the original source, and publishes a self-contained static website to GitHub Pages. The pipeline is built as a harness engineering learning project — the architecture prioritizes observable, stateful, structured agent orchestration over prompt sophistication.

## User Stories

1. As an AI engineer, I want to visit a single website each morning and see the most important AI engineering updates from the last 24 hours, so that I can stay current without checking multiple X accounts.
2. As an AI engineer, I want each story to have a short factual summary and a "why it matters" explanation, so that I can quickly assess relevance without reading the full post.
3. As an AI engineer, I want every story to link back to the original X post, so that I can verify claims and read the full thread when interested.
4. As an AI engineer, I want to filter stories by category (e.g., Models, Frameworks, Coding Agents, Papers, Agent Research), so that I can focus on the areas most relevant to my current work.
5. As an AI engineer, I want to search across all stories, so that I can find specific topics or announcements.
6. As an AI engineer, I want stories grouped by date with the newest first, so that I can distinguish today's news from yesterday's.
7. As an AI engineer, I want the site to load instantly with no backend or external dependencies, so that it works reliably regardless of network conditions.
8. As an AI engineer, I want to see source account avatars and handles on each story, so that I can gauge the authority of the source at a glance.
9. As an AI engineer, I want the site to show when it was last updated, so that I know how fresh the content is.
10. As an AI engineer, I want the pipeline to never publish a story with fabricated claims, so that I can trust what I read.
11. As an AI engineer, I want the pipeline to run automatically every day without my intervention, so that the feed stays fresh.
12. As an AI engineer, I want duplicate stories to never appear, even across multiple daily runs, so that the feed stays clean.
13. As an AI engineer, I want replies and reposts filtered out, so that I only see original announcements and substantive posts.
14. As a harness engineering learner, I want each pipeline stage to communicate through explicit JSON contracts, so that I can inspect intermediate state and understand the data flow.
15. As a harness engineering learner, I want every run to log metrics (posts collected, stories published, stories rejected, tokens used, runtime), so that I can observe system behavior over time.
16. As a harness engineering learner, I want rejected stories to be logged with rejection reasons, so that I can identify patterns in verification failures.
17. As a harness engineering learner, I want all persistent state committed to the repo, so that the repository is the system of record and state changes are version-controlled.
18. As a harness engineering learner, I want the pipeline to handle X API failures gracefully (log the error, skip the account, continue), so that a single source failure doesn't break the entire run.
19. As a harness engineering learner, I want to be able to run the pipeline locally with the same code that runs in CI, so that I can develop and debug without pushing to GitHub.

## Implementation Decisions

### Pipeline architecture

The pipeline is a single Python script that runs five sequential modules. Each module reads a JSON file and writes a JSON file. There is no inter-process communication, no message queue, no framework — just functions called in order.

### Modules

1. **Collector** — Calls the X API (via the Anthropic SDK's tool-use interface or direct HTTP, depending on how the X MCP server is accessed from a script context) to retrieve recent posts from the configured source accounts. Writes `data/runs/<date>/raw_posts.json`. Never summarizes or transforms content.

2. **Normalizer** — Reads raw posts, converts to a consistent schema, removes replies and reposts, deduplicates by post ID against `data/state/processed_ids.json`, standardizes timestamps, constructs canonical URLs. Writes `data/runs/<date>/normalized_posts.json`.

3. **Curator Agent** — Reads normalized posts, calls Claude API (Haiku 4.5) to assess importance, categorize, generate a factual title, a concise summary, and a "why it matters" explanation. Writes `data/runs/<date>/candidate_stories.json`. The Curator cannot publish — it only proposes.

4. **Verifier Agent** — Reads candidate stories alongside their original post text, calls Claude API (Haiku 4.5) to compare every generated claim against the source. Approves or rejects each story with a reason. Rejected stories are dropped and logged — no retries. Writes `data/runs/<date>/verified_stories.json`.

5. **Publisher** — Reads verified stories, merges with `data/state/published_stories.json` (the running archive), renders a self-contained `feed.html` with inline CSS/JS, writes it to the deployment directory. Updates `data/state/published_stories.json` and `data/state/run_history.json`.

### JSON contracts

Each inter-stage JSON file has an explicit schema. The normalized post schema matches the one defined in the X Agent Intelligence skill. The candidate and verified story schemas extend it with curation and verification metadata.

### Model choice

Haiku 4.5 via the Claude API (Anthropic Python SDK) for both agent stages. Chosen for cost efficiency and speed — the summarization and verification tasks don't require a frontier model.

### State management

All state lives in `data/state/` and is committed to the repo after each run:
- `processed_ids.json` — set of post IDs already seen, prevents cross-run duplicates
- `published_stories.json` — archive of all published stories
- `run_history.json` — per-run metrics (posts collected, stories published/rejected, tokens used, runtime, errors)

### Source configuration

A `config/sources.json` file lists the X accounts to follow, with handle and category hints. Seeded with ~10-15 high-signal accounts. Editable without touching pipeline code.

### Scheduling and deployment

GitHub Actions workflow runs daily on a cron schedule. Secrets (`ANTHROPIC_API_KEY`, X API credentials) injected via GitHub Actions secrets. The workflow runs the pipeline, commits state changes, and deploys `feed.html` to GitHub Pages.

### Frontend

A single self-contained HTML file with inline CSS and JavaScript. Features: search, category filters, date grouping, source handles with avatars, original post links, last-updated timestamp. No framework, no build step, no external runtime dependencies. The skill's `reference-artifact.html` (once created) serves as the design reference.

## Testing Decisions

### What makes a good test

Tests assert on external behavior at the JSON contract boundaries, not on implementation details. A test feeds fixture data into a module's input and asserts on the shape, content, and correctness of its output. Tests never mock internal functions — only the external X API boundary is stubbed with fixture data.

### Testing seam

The primary seam is the pipeline's input/output boundary. Raw X API responses are saved as JSON fixtures. Tests feed these fixtures into the pipeline (or individual modules) and assert on the output files and state changes. This is one seam applied at different granularities:

- **Module-level:** Feed a module its input JSON fixture, assert on its output JSON.
- **End-to-end:** Feed raw post fixtures into the full pipeline, assert on the final `feed.html` content and state files.

### What to test

- **Normalizer:** Filters replies/reposts, deduplicates against processed IDs, standardizes schema.
- **Curator Agent:** Produces valid candidate story schema, assigns categories, generates titles/summaries.
- **Verifier Agent:** Correctly approves faithful summaries, rejects fabricated claims, logs rejection reasons.
- **Publisher:** Renders valid HTML with correct story count, search/filter functionality, no leaked credentials.
- **Pipeline end-to-end:** Full run from fixture input to published output, state files updated correctly.

### Testing framework

pytest with the standard library. No additional test frameworks or dependencies.

## Out of Scope

- Multiple data sources (GitHub Releases, research papers, blogs, RSS) — deferred to Phase 2+
- Personalized relevance ranking
- Self-modifying prompts or feedback-driven improvements
- Retry logic for rejected stories
- User accounts or authentication on the website
- Real-time updates or streaming
- Mobile-optimized frontend (nice-to-have but not a V1 requirement)
- A separate frontend framework (React, Next.js, etc.)
- Claude Code as the pipeline orchestrator (the pipeline is authored Python code calling the Claude API directly)

## Further Notes

- The X MCP server has not been set up yet. This is a prerequisite before any pipeline code can be tested against real data. The first implementation step should be confirming X API access and saving sample responses as fixtures.
- The starter source list (~10-15 accounts) needs to be curated. This can be done as a separate task.
- The `references/` and `assets/` directories referenced by the X Agent Intelligence skill don't exist yet. These should be created as part of initial project scaffolding.
- The project idea doc mentions `AGENTS.md` as an expected artifact, but `CLAUDE.md` was chosen instead. The idea doc should be updated to reflect this.
