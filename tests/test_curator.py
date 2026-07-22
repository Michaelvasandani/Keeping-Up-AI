"""Tests for the curator agent — importance assessment, categorization, and story generation."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from pipeline.curator import curate, curate_file, run as curator_run

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str):
    return json.loads((FIXTURES_DIR / name).read_text())


def _normalized_posts():
    return _load_fixture("normalized_posts.json")


def _mock_haiku_response(post):
    """Build a realistic mock Claude API response for a single post."""
    return {
        "title": f"Title for: {post['text'][:30]}",
        "summary": f"Summary of the post about {post['text'][:20]}.",
        "why_it_matters": f"This matters because {post['text'][:20]}.",
        "importance": "high",
    }


def _make_mock_client(posts):
    """Create a mock Anthropic client that returns curation responses."""
    client = MagicMock()
    responses = []
    for post in posts:
        resp = MagicMock()
        resp.content = [MagicMock()]
        resp.content[0].text = json.dumps(_mock_haiku_response(post))
        resp.usage.input_tokens = 100
        resp.usage.output_tokens = 50
        responses.append(resp)

    client.messages.create.side_effect = responses
    return client


# ── Schema ──────────────────────────────────────────────────────────


class TestCandidateStorySchema:
    def test_required_fields_present(self):
        posts = _normalized_posts()
        client = _make_mock_client(posts)
        result = curate(posts, client)

        required = {
            "id", "date", "created_at", "category", "handle",
            "author_name", "verified", "profile_image_url", "tweet_url",
            "text", "title", "summary", "why_it_matters", "importance",
        }
        for story in result["stories"]:
            assert required.issubset(story.keys()), (
                f"Missing fields: {required - story.keys()}"
            )

    def test_original_post_fields_preserved(self):
        posts = _normalized_posts()
        client = _make_mock_client(posts)
        result = curate(posts, client)

        for story in result["stories"]:
            original = next(p for p in posts if p["id"] == story["id"])
            assert story["text"] == original["text"]
            assert story["handle"] == original["handle"]
            assert story["tweet_url"] == original["tweet_url"]
            assert story["date"] == original["date"]

    def test_generated_fields_are_strings(self):
        posts = _normalized_posts()
        client = _make_mock_client(posts)
        result = curate(posts, client)

        for story in result["stories"]:
            assert isinstance(story["title"], str) and len(story["title"]) > 0
            assert isinstance(story["summary"], str) and len(story["summary"]) > 0
            assert isinstance(story["why_it_matters"], str) and len(story["why_it_matters"]) > 0

    def test_importance_is_valid_value(self):
        posts = _normalized_posts()
        client = _make_mock_client(posts)
        result = curate(posts, client)

        for story in result["stories"]:
            assert story["importance"] in {"high", "medium", "low"}


# ── Token Tracking ──────────────────────────────────────────────────


class TestCuratorTokenTracking:
    def test_usage_is_reported(self):
        posts = _normalized_posts()
        client = _make_mock_client(posts)
        result = curate(posts, client)

        assert "usage" in result
        assert result["usage"]["input_tokens"] == 100 * len(posts)
        assert result["usage"]["output_tokens"] == 50 * len(posts)

    def test_stories_count_matches_posts(self):
        posts = _normalized_posts()
        client = _make_mock_client(posts)
        result = curate(posts, client)

        assert len(result["stories"]) == len(posts)


# ── API Calls ───────────────────────────────────────────────────────


class TestCuratorAPICalls:
    def test_calls_haiku_model(self):
        posts = _normalized_posts()
        client = _make_mock_client(posts)
        curate(posts, client)

        for call in client.messages.create.call_args_list:
            assert call.kwargs["model"] == "claude-haiku-4-5-20251001"

    def test_one_call_per_post(self):
        posts = _normalized_posts()
        client = _make_mock_client(posts)
        curate(posts, client)

        assert client.messages.create.call_count == len(posts)


# ── File I/O ────────────────────────────────────────────────────────


class TestCurateFile:
    def test_writes_candidate_stories_json(self, tmp_path):
        posts = _normalized_posts()
        input_path = tmp_path / "normalized_posts.json"
        input_path.write_text(json.dumps(posts))
        output_path = tmp_path / "candidate_stories.json"

        client = _make_mock_client(posts)
        curate_file(input_path, output_path, client)

        assert output_path.exists()
        on_disk = json.loads(output_path.read_text())
        assert "stories" in on_disk
        assert "usage" in on_disk
        assert len(on_disk["stories"]) == len(posts)

    def test_creates_parent_directories(self, tmp_path):
        posts = _normalized_posts()
        input_path = tmp_path / "normalized_posts.json"
        input_path.write_text(json.dumps(posts))
        output_path = tmp_path / "data" / "runs" / "2026-07-21" / "candidate_stories.json"

        client = _make_mock_client(posts)
        curate_file(input_path, output_path, client)

        assert output_path.exists()


class TestCuratorRun:
    def test_run_reads_normalized_and_writes_candidates(self, tmp_path):
        posts = _normalized_posts()
        (tmp_path / "normalized_posts.json").write_text(json.dumps(posts))

        client = _make_mock_client(posts)
        out_path = curator_run(tmp_path, client)

        assert out_path.exists()
        assert out_path.name == "candidate_stories.json"
        data = json.loads(out_path.read_text())
        assert len(data["stories"]) == len(posts)
