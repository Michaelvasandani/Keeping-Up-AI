"""Tests for the full pipeline runner with state management."""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pipeline.normalizer import normalize

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str):
    return json.loads((FIXTURES_DIR / name).read_text())


def _make_curator_response(post: dict) -> MagicMock:
    """Build a mock Anthropic response for the curator."""
    curation = {
        "title": f"Title for {post['id']}",
        "summary": f"Summary of {post['text'][:30]}",
        "why_it_matters": "Relevant to AI engineers.",
        "importance": "high",
    }
    resp = MagicMock()
    resp.usage.input_tokens = 100
    resp.usage.output_tokens = 50
    resp.content = [SimpleNamespace(text=json.dumps(curation))]
    return resp


def _make_verifier_response(verdict: str = "approved", reason: str = "") -> MagicMock:
    """Build a mock Anthropic response for the verifier."""
    result = {"verdict": verdict, "reason": reason}
    resp = MagicMock()
    resp.usage.input_tokens = 80
    resp.usage.output_tokens = 30
    resp.content = [SimpleNamespace(text=json.dumps(result))]
    return resp


def _setup_run_dir(tmp_path: Path) -> Path:
    """Copy raw_posts.json fixture into a temp run directory."""
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)
    shutil.copy(FIXTURES_DIR / "raw_posts.json", run_dir / "raw_posts.json")
    return run_dir


def _mock_client_approve_all():
    """Create a mock client that curates and approves all stories."""
    client = MagicMock()

    def side_effect(**kwargs):
        system = kwargs.get("system", "")
        user_msg = kwargs["messages"][0]["content"]
        if "curator" in system.lower():
            # Parse enough to build a response
            return _make_curator_response({"id": "test", "text": user_msg[:30]})
        else:
            return _make_verifier_response("approved")

    # Simpler approach: alternate between curator and verifier responses
    # based on call count
    call_count = {"n": 0}
    normalized = normalize(_load_fixture("raw_posts.json"))
    total_posts = len(normalized)

    def smart_side_effect(**kwargs):
        idx = call_count["n"]
        call_count["n"] += 1
        if idx < total_posts:
            # Curator phase
            post = normalized[idx] if idx < len(normalized) else {"id": str(idx), "text": "test"}
            return _make_curator_response(post)
        else:
            # Verifier phase
            return _make_verifier_response("approved")

    client.messages.create.side_effect = smart_side_effect
    return client


# ── State helpers ───────────────────────────────────────────────────


class TestStateHelpers:
    def test_load_processed_ids_empty(self, tmp_path):
        from run_pipeline import load_processed_ids

        result = load_processed_ids(tmp_path)
        assert result == set()

    def test_save_and_load_processed_ids(self, tmp_path):
        from run_pipeline import load_processed_ids, save_processed_ids

        ids = {"id_1", "id_2", "id_3"}
        save_processed_ids(ids, tmp_path)
        loaded = load_processed_ids(tmp_path)
        assert loaded == ids

    def test_load_published_stories_empty(self, tmp_path):
        from run_pipeline import load_published_stories

        result = load_published_stories(tmp_path)
        assert result == []

    def test_save_and_load_published_stories(self, tmp_path):
        from run_pipeline import load_published_stories, save_published_stories

        stories = [{"id": "1", "title": "Test"}]
        save_published_stories(stories, tmp_path)
        loaded = load_published_stories(tmp_path)
        assert loaded == stories

    def test_load_run_history_empty(self, tmp_path):
        from run_pipeline import load_run_history

        result = load_run_history(tmp_path)
        assert result == []

    def test_save_and_load_run_history(self, tmp_path):
        from run_pipeline import load_run_history, save_run_history

        history = [{"timestamp": "2026-07-21T00:00:00", "posts_collected": 5}]
        save_run_history(history, tmp_path)
        loaded = load_run_history(tmp_path)
        assert loaded == history


# ── Normalizer cross-run dedup ──────────────────────────────────────


class TestCrossRunDedup:
    def test_exclude_ids_filters_known_posts(self):
        raw = _load_fixture("raw_posts.json")
        # Normalize once to find valid IDs
        all_posts = normalize(raw)
        assert len(all_posts) == 4

        # Exclude two IDs
        exclude = {all_posts[0]["id"], all_posts[1]["id"]}
        filtered = normalize(raw, exclude_ids=exclude)
        assert len(filtered) == 2
        result_ids = {p["id"] for p in filtered}
        assert result_ids.isdisjoint(exclude)

    def test_exclude_all_ids_returns_empty(self):
        raw = _load_fixture("raw_posts.json")
        all_posts = normalize(raw)
        exclude = {p["id"] for p in all_posts}
        filtered = normalize(raw, exclude_ids=exclude)
        assert filtered == []

    def test_exclude_none_returns_all(self):
        raw = _load_fixture("raw_posts.json")
        result_none = normalize(raw, exclude_ids=None)
        result_default = normalize(raw)
        assert len(result_none) == len(result_default)


# ── Full pipeline ───────────────────────────────────────────────────


class TestFullPipeline:
    def test_pipeline_creates_all_output_files(self, tmp_path):
        """Pipeline produces all expected files in the run directory."""
        from run_pipeline import run

        run_dir = _setup_run_dir(tmp_path)
        state_dir = tmp_path / "state"
        client = _mock_client_approve_all()

        with patch("run_pipeline.collector") as mock_collector:
            mock_collector.run.return_value = run_dir / "raw_posts.json"
            run(
                output_dir=run_dir,
                state_dir=state_dir,
                bearer_token="fake-token",
                client=client,
            )

        assert (run_dir / "normalized_posts.json").exists()
        assert (run_dir / "candidate_stories.json").exists()
        assert (run_dir / "verified_stories.json").exists()
        assert (run_dir / "feed.html").exists()

    def test_pipeline_creates_state_files(self, tmp_path):
        """Pipeline creates all three state files."""
        from run_pipeline import run

        run_dir = _setup_run_dir(tmp_path)
        state_dir = tmp_path / "state"
        client = _mock_client_approve_all()

        with patch("run_pipeline.collector") as mock_collector:
            mock_collector.run.return_value = run_dir / "raw_posts.json"
            run(
                output_dir=run_dir,
                state_dir=state_dir,
                bearer_token="fake-token",
                client=client,
            )

        assert (state_dir / "processed_ids.json").exists()
        assert (state_dir / "published_stories.json").exists()
        assert (state_dir / "run_history.json").exists()

    def test_pipeline_records_run_history(self, tmp_path):
        """Run history records metrics for the pipeline run."""
        from run_pipeline import run

        run_dir = _setup_run_dir(tmp_path)
        state_dir = tmp_path / "state"
        client = _mock_client_approve_all()

        with patch("run_pipeline.collector") as mock_collector:
            mock_collector.run.return_value = run_dir / "raw_posts.json"
            run(
                output_dir=run_dir,
                state_dir=state_dir,
                bearer_token="fake-token",
                client=client,
            )

        history = json.loads((state_dir / "run_history.json").read_text())
        assert len(history) == 1
        record = history[0]
        assert "timestamp" in record
        # posts_collected counts raw posts from the collector (8 in fixture)
        assert record["posts_collected"] == 8
        assert record["stories_published"] >= 0
        assert record["stories_rejected"] >= 0
        assert record["total_tokens"] > 0
        assert record["runtime_seconds"] >= 0
        assert record["errors"] == []

    def test_duplicate_run_produces_no_new_stories(self, tmp_path):
        """Running pipeline twice with same data produces no duplicates."""
        from run_pipeline import run

        state_dir = tmp_path / "state"
        client_factory = _mock_client_approve_all

        # First run
        run_dir_1 = _setup_run_dir(tmp_path / "run1_parent")
        with patch("run_pipeline.collector") as mock_collector:
            mock_collector.run.return_value = run_dir_1 / "raw_posts.json"
            run(
                output_dir=run_dir_1,
                state_dir=state_dir,
                bearer_token="fake-token",
                client=client_factory(),
            )

        stories_after_first = json.loads(
            (state_dir / "published_stories.json").read_text()
        )
        assert len(stories_after_first) > 0

        # Second run with same data
        run_dir_2 = _setup_run_dir(tmp_path / "run2_parent")
        with patch("run_pipeline.collector") as mock_collector:
            mock_collector.run.return_value = run_dir_2 / "raw_posts.json"
            run(
                output_dir=run_dir_2,
                state_dir=state_dir,
                bearer_token="fake-token",
                client=client_factory(),
            )

        # Normalized posts in second run should be empty (all filtered by processed_ids)
        normalized_2 = json.loads((run_dir_2 / "normalized_posts.json").read_text())
        assert normalized_2 == []

        # Published stories should not have grown
        stories_after_second = json.loads(
            (state_dir / "published_stories.json").read_text()
        )
        assert len(stories_after_second) == len(stories_after_first)

        # Run history should have two entries
        history = json.loads((state_dir / "run_history.json").read_text())
        assert len(history) == 2

    def test_processed_ids_accumulate(self, tmp_path):
        """processed_ids.json grows with each run."""
        from run_pipeline import run, load_processed_ids

        state_dir = tmp_path / "state"

        run_dir = _setup_run_dir(tmp_path / "run_parent")
        client = _mock_client_approve_all()

        with patch("run_pipeline.collector") as mock_collector:
            mock_collector.run.return_value = run_dir / "raw_posts.json"
            run(
                output_dir=run_dir,
                state_dir=state_dir,
                bearer_token="fake-token",
                client=client,
            )

        ids = load_processed_ids(state_dir)
        # Should contain the 4 normalized post IDs
        assert len(ids) == 4


class TestPipelineErrorHandling:
    def test_collector_error_recorded_in_history(self, tmp_path):
        """If the collector fails, the error is recorded in run history."""
        from run_pipeline import run

        run_dir = tmp_path / "run"
        run_dir.mkdir()
        state_dir = tmp_path / "state"

        with patch("run_pipeline.collector") as mock_collector:
            mock_collector.run.side_effect = RuntimeError("API rate limited")
            run(
                output_dir=run_dir,
                state_dir=state_dir,
                bearer_token="fake-token",
                client=MagicMock(),
            )

        history = json.loads((state_dir / "run_history.json").read_text())
        assert len(history) == 1
        assert len(history[0]["errors"]) > 0
        assert "collector" in history[0]["errors"][0]
