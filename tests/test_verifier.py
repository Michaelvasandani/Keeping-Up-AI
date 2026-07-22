"""Tests for the verifier agent — claim verification, approval/rejection, and logging."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from pipeline.verifier import verify, verify_file, run as verifier_run

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str):
    return json.loads((FIXTURES_DIR / name).read_text())


def _make_candidate_stories(posts):
    """Build candidate stories that look like curator output."""
    stories = []
    for post in posts:
        stories.append({
            **post,
            "title": f"Title for: {post['text'][:30]}",
            "summary": f"Summary about {post['text'][:20]}.",
            "why_it_matters": f"Matters because {post['text'][:20]}.",
            "importance": "high",
        })
    return {"stories": stories, "usage": {"input_tokens": 400, "output_tokens": 200}}


def _make_mock_client(verdicts):
    """Create a mock Anthropic client returning verification verdicts.

    verdicts: list of (verdict, reason) tuples, e.g. [("approved", ""), ("rejected", "fabricated claim")]
    """
    client = MagicMock()
    responses = []
    for verdict, reason in verdicts:
        resp = MagicMock()
        resp.content = [MagicMock()]
        resp.content[0].text = json.dumps({
            "verdict": verdict,
            "reason": reason,
        })
        resp.usage.input_tokens = 150
        resp.usage.output_tokens = 30
        responses.append(resp)

    client.messages.create.side_effect = responses
    return client


# ── Approval / Rejection ────────────────────────────────────────────


class TestVerification:
    def test_approved_stories_in_output(self):
        posts = _load_fixture("normalized_posts.json")
        candidates = _make_candidate_stories(posts)
        verdicts = [("approved", "")] * len(posts)
        client = _make_mock_client(verdicts)

        result = verify(candidates, client)

        assert len(result["stories"]) == len(posts)

    def test_rejected_stories_excluded_from_output(self):
        posts = _load_fixture("normalized_posts.json")
        candidates = _make_candidate_stories(posts)
        # Reject the second story
        verdicts = [
            ("approved", ""),
            ("rejected", "Summary contains a claim not in the source text."),
            ("approved", ""),
            ("approved", ""),
        ]
        client = _make_mock_client(verdicts)

        result = verify(candidates, client)

        assert len(result["stories"]) == 3
        ids = {s["id"] for s in result["stories"]}
        assert posts[1]["id"] not in ids

    def test_all_rejected_produces_empty_output(self):
        posts = _load_fixture("normalized_posts.json")
        candidates = _make_candidate_stories(posts)
        verdicts = [("rejected", "fabricated")] * len(posts)
        client = _make_mock_client(verdicts)

        result = verify(candidates, client)

        assert len(result["stories"]) == 0

    def test_rejected_stories_are_logged(self):
        posts = _load_fixture("normalized_posts.json")
        candidates = _make_candidate_stories(posts)
        verdicts = [
            ("approved", ""),
            ("rejected", "Title introduces information not in the original post."),
            ("approved", ""),
            ("rejected", "Summary fabricates a release date."),
        ]
        client = _make_mock_client(verdicts)

        result = verify(candidates, client)

        assert len(result["rejections"]) == 2
        assert result["rejections"][0]["id"] == posts[1]["id"]
        assert "not in the original post" in result["rejections"][0]["reason"]
        assert result["rejections"][1]["id"] == posts[3]["id"]
        assert "fabricates" in result["rejections"][1]["reason"]


# ── Schema ──────────────────────────────────────────────────────────


class TestVerifiedStorySchema:
    def test_verified_story_has_all_candidate_fields(self):
        posts = _load_fixture("normalized_posts.json")
        candidates = _make_candidate_stories(posts)
        verdicts = [("approved", "")] * len(posts)
        client = _make_mock_client(verdicts)

        result = verify(candidates, client)

        required = {
            "id", "date", "created_at", "category", "handle",
            "author_name", "verified", "profile_image_url", "tweet_url",
            "text", "title", "summary", "why_it_matters", "importance",
        }
        for story in result["stories"]:
            assert required.issubset(story.keys()), (
                f"Missing fields: {required - story.keys()}"
            )

    def test_rejection_log_has_id_and_reason(self):
        posts = _load_fixture("normalized_posts.json")
        candidates = _make_candidate_stories(posts)
        verdicts = [
            ("approved", ""),
            ("rejected", "Fabricated claim."),
            ("approved", ""),
            ("approved", ""),
        ]
        client = _make_mock_client(verdicts)

        result = verify(candidates, client)

        for rejection in result["rejections"]:
            assert "id" in rejection
            assert "reason" in rejection
            assert isinstance(rejection["reason"], str)
            assert len(rejection["reason"]) > 0


# ── Token Tracking ──────────────────────────────────────────────────


class TestVerifierTokenTracking:
    def test_usage_is_reported(self):
        posts = _load_fixture("normalized_posts.json")
        candidates = _make_candidate_stories(posts)
        verdicts = [("approved", "")] * len(posts)
        client = _make_mock_client(verdicts)

        result = verify(candidates, client)

        assert "usage" in result
        assert result["usage"]["input_tokens"] == 150 * len(posts)
        assert result["usage"]["output_tokens"] == 30 * len(posts)


# ── API Calls ───────────────────────────────────────────────────────


class TestVerifierAPICalls:
    def test_calls_haiku_model(self):
        posts = _load_fixture("normalized_posts.json")
        candidates = _make_candidate_stories(posts)
        verdicts = [("approved", "")] * len(posts)
        client = _make_mock_client(verdicts)

        verify(candidates, client)

        for call in client.messages.create.call_args_list:
            assert call.kwargs["model"] == "claude-haiku-4-5-20251001"

    def test_one_call_per_story(self):
        posts = _load_fixture("normalized_posts.json")
        candidates = _make_candidate_stories(posts)
        verdicts = [("approved", "")] * len(posts)
        client = _make_mock_client(verdicts)

        verify(candidates, client)

        assert client.messages.create.call_count == len(posts)


# ── File I/O ────────────────────────────────────────────────────────


class TestVerifyFile:
    def test_writes_verified_stories_json(self, tmp_path):
        posts = _load_fixture("normalized_posts.json")
        candidates = _make_candidate_stories(posts)
        input_path = tmp_path / "candidate_stories.json"
        input_path.write_text(json.dumps(candidates))
        output_path = tmp_path / "verified_stories.json"

        verdicts = [("approved", "")] * len(posts)
        client = _make_mock_client(verdicts)
        verify_file(input_path, output_path, client)

        assert output_path.exists()
        on_disk = json.loads(output_path.read_text())
        assert "stories" in on_disk
        assert "rejections" in on_disk
        assert "usage" in on_disk

    def test_creates_parent_directories(self, tmp_path):
        posts = _load_fixture("normalized_posts.json")
        candidates = _make_candidate_stories(posts)
        input_path = tmp_path / "candidate_stories.json"
        input_path.write_text(json.dumps(candidates))
        output_path = tmp_path / "data" / "runs" / "2026-07-21" / "verified_stories.json"

        verdicts = [("approved", "")] * len(posts)
        client = _make_mock_client(verdicts)
        verify_file(input_path, output_path, client)

        assert output_path.exists()


class TestVerifierRun:
    def test_run_reads_candidates_and_writes_verified(self, tmp_path):
        posts = _load_fixture("normalized_posts.json")
        candidates = _make_candidate_stories(posts)
        (tmp_path / "candidate_stories.json").write_text(json.dumps(candidates))

        verdicts = [("approved", "")] * len(posts)
        client = _make_mock_client(verdicts)
        out_path = verifier_run(tmp_path, client)

        assert out_path.exists()
        assert out_path.name == "verified_stories.json"
        data = json.loads(out_path.read_text())
        assert len(data["stories"]) == len(posts)
