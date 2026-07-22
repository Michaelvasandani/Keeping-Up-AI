# 06 — GitHub Actions and GitHub Pages deployment

**What to build:** A GitHub Actions workflow that runs the pipeline daily on a cron schedule, commits any state changes (processed IDs, published stories, run history) back to the repo, and deploys the generated `feed.html` to GitHub Pages. Secrets for the Anthropic API key and X API credentials are configured in the repo's GitHub Actions settings. After pushing to main, the workflow runs automatically and the site updates without manual intervention.

**Blocked by:** 05 — Full pipeline with state management.

**Status:** done

- [x] `.github/workflows/` contains a workflow that runs `run_pipeline.py` on a daily cron schedule
- [x] Workflow installs Python dependencies and injects secrets as environment variables (`ANTHROPIC_API_KEY`, X API credentials)
- [x] After a successful run, the workflow commits updated state files (`data/state/`) back to the repo
- [x] The workflow deploys `feed.html` to GitHub Pages
- [x] The workflow can also be triggered manually via `workflow_dispatch` for testing
- [x] A failed pipeline run does not deploy stale content — deployment only happens after a successful run
- [x] The site is accessible at the repo's GitHub Pages URL with the latest feed
