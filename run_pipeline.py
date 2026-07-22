"""Full pipeline runner — executes all five modules with durable state."""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from src.pipeline import collector, normalizer, curator, verifier, publisher

logger = logging.getLogger(__name__)

STATE_DIR = Path("data/state")
PROCESSED_IDS_PATH = STATE_DIR / "processed_ids.json"
PUBLISHED_STORIES_PATH = STATE_DIR / "published_stories.json"
RUN_HISTORY_PATH = STATE_DIR / "run_history.json"


def _load_json(path: Path, default):
    """Load JSON from path, returning default if the file doesn't exist."""
    if path.exists():
        return json.loads(path.read_text())
    return default


def _save_json(path: Path, data) -> None:
    """Write data as JSON, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_processed_ids(state_dir: Path | None = None) -> set[str]:
    """Load the set of previously processed post IDs."""
    path = (state_dir / "processed_ids.json") if state_dir else PROCESSED_IDS_PATH
    return set(_load_json(path, []))


def save_processed_ids(ids: set[str], state_dir: Path | None = None) -> None:
    """Save the set of processed post IDs."""
    path = (state_dir / "processed_ids.json") if state_dir else PROCESSED_IDS_PATH
    _save_json(path, sorted(ids))


def load_published_stories(state_dir: Path | None = None) -> list[dict]:
    """Load the accumulated published stories."""
    path = (state_dir / "published_stories.json") if state_dir else PUBLISHED_STORIES_PATH
    return _load_json(path, [])


def save_published_stories(stories: list[dict], state_dir: Path | None = None) -> None:
    """Save the accumulated published stories."""
    path = (state_dir / "published_stories.json") if state_dir else PUBLISHED_STORIES_PATH
    _save_json(path, stories)


def load_run_history(state_dir: Path | None = None) -> list[dict]:
    """Load the run history."""
    path = (state_dir / "run_history.json") if state_dir else RUN_HISTORY_PATH
    return _load_json(path, [])


def save_run_history(history: list[dict], state_dir: Path | None = None) -> None:
    """Save the run history."""
    path = (state_dir / "run_history.json") if state_dir else RUN_HISTORY_PATH
    _save_json(path, history)


def run(
    sources_path: str = "config/sources.json",
    bearer_token: str | None = None,
    since: datetime | None = None,
    output_dir: str | Path | None = None,
    state_dir: str | Path | None = None,
    client=None,
) -> Path:
    """Run the full pipeline: collect, normalize, curate, verify, publish.

    Manages durable state across runs for deduplication and metrics.
    Returns the path to the run directory.
    """
    start_time = time.monotonic()
    now = datetime.now(timezone.utc)

    if bearer_token is None:
        bearer_token = os.environ["X_BEARER_TOKEN"]

    if client is None:
        client = anthropic.Anthropic()

    if output_dir is None:
        output_dir = Path("data/runs") / now.strftime("%Y-%m-%d")
    else:
        output_dir = Path(output_dir)

    if state_dir is not None:
        state_dir = Path(state_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load state
    processed_ids = load_processed_ids(state_dir)
    published_stories = load_published_stories(state_dir)
    run_history = load_run_history(state_dir)

    errors: list[str] = []
    posts_collected = 0
    stories_published = 0
    stories_rejected = 0
    total_tokens = 0
    normalized_posts: list[dict] = []
    verified: dict | None = None

    try:
        # 1. Collect
        print("[pipeline] collecting posts...")
        try:
            collector.run(
                sources_path=sources_path,
                bearer_token=bearer_token,
                since=since,
                output_dir=output_dir,
            )
        except Exception as exc:
            errors.append(f"collector: {exc}")
            raise

        raw_path = output_dir / "raw_posts.json"
        raw_data = json.loads(raw_path.read_text())
        posts_collected = sum(
            len(entry.get("posts", {}).get("data", []))
            for entry in raw_data
        )

        # 2. Normalize (with cross-run deduplication)
        print("[pipeline] normalizing posts...")
        try:
            normalizer.run(output_dir, exclude_ids=processed_ids)
        except Exception as exc:
            errors.append(f"normalizer: {exc}")
            raise

        normalized_path = output_dir / "normalized_posts.json"
        normalized_posts = json.loads(normalized_path.read_text())

        # 3. Curate
        print("[pipeline] curating stories...")
        try:
            curator.run(output_dir, client)
        except Exception as exc:
            errors.append(f"curator: {exc}")
            raise

        candidates_path = output_dir / "candidate_stories.json"
        candidates = json.loads(candidates_path.read_text())
        total_tokens += candidates["usage"]["input_tokens"] + candidates["usage"]["output_tokens"]

        # 4. Verify
        print("[pipeline] verifying stories...")
        try:
            verifier.run(output_dir, client)
        except Exception as exc:
            errors.append(f"verifier: {exc}")
            raise

        verified_path = output_dir / "verified_stories.json"
        verified = json.loads(verified_path.read_text())
        stories_published = len(verified["stories"])
        stories_rejected = len(verified["rejections"])
        total_tokens += verified["usage"]["input_tokens"] + verified["usage"]["output_tokens"]

        # 5. Merge new stories into accumulated list and publish
        existing_ids = {s["id"] for s in published_stories}
        for story in verified["stories"]:
            if story["id"] not in existing_ids:
                published_stories.append(story)

        print("[pipeline] publishing feed...")
        try:
            all_stories_path = output_dir / "verified_stories_all.json"
            _save_json(all_stories_path, {"stories": published_stories})
            publisher.publish_file(all_stories_path, output_dir / "feed.html")
            n = len(published_stories)
            print(f"  [done] published feed: {n} stories to {output_dir / 'feed.html'}")
        except Exception as exc:
            errors.append(f"publisher: {exc}")
            raise

    except Exception:
        logger.exception("Pipeline failed")
    finally:
        # Save state for any work completed before failure
        if normalized_posts:
            new_ids = {p["id"] for p in normalized_posts}
            processed_ids.update(new_ids)
            save_processed_ids(processed_ids, state_dir)

        save_published_stories(published_stories, state_dir)

        # Record run metrics
        elapsed = time.monotonic() - start_time
        run_record = {
            "timestamp": now.isoformat(),
            "run_dir": str(output_dir),
            "posts_collected": posts_collected,
            "stories_published": stories_published,
            "stories_rejected": stories_rejected,
            "total_tokens": total_tokens,
            "runtime_seconds": round(elapsed, 2),
            "errors": errors,
        }
        run_history.append(run_record)
        save_run_history(run_history, state_dir)

    status = "with errors" if errors else "successfully"
    print(f"[pipeline] completed {status} in {elapsed:.1f}s")
    return output_dir


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    output_dir = run()
    if not (output_dir / "feed.html").exists():
        sys.exit(1)
