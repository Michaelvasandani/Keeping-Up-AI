# 05 — Full pipeline with state management

**What to build:** A single `run_pipeline.py` entry point that executes all five modules (Collector, Normalizer, Curator, Verifier, Publisher) in sequence. Adds durable state: `processed_ids.json` for cross-run deduplication, `published_stories.json` as a running story archive, and `run_history.json` with per-run metrics. Running the pipeline twice with the same input data produces no duplicate stories. The pipeline is runnable locally end-to-end with inspectable state files afterward.

**Blocked by:** 04 — Publish to static HTML.

**Status:** ready-for-agent

- [ ] `run_pipeline.py` executes all five modules in sequence
- [ ] `data/state/processed_ids.json` tracks all seen post IDs across runs — the Normalizer consults it for deduplication
- [ ] `data/state/published_stories.json` accumulates all published stories across runs — the Publisher merges new stories into it
- [ ] `data/state/run_history.json` records per-run metrics: posts collected, stories published, stories rejected, total tokens used, runtime in seconds, errors encountered
- [ ] Running the pipeline twice with identical source data produces no duplicate stories in the output
- [ ] The pipeline can be run locally with `python run_pipeline.py` using the same code path as CI
- [ ] Failures in individual modules are logged and recorded in run history
