"""Tests validating saved X API fixture structure and collector I/O."""

import json
from pathlib import Path
from unittest.mock import patch

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str):
    return json.loads((FIXTURES_DIR / name).read_text())


class TestUserLookupFixture:
    def test_parses_user_data(self):
        resp = _load_fixture("user_lookup_response.json")
        users = resp.get("data", [])
        assert len(users) > 0
        for user in users:
            assert "id" in user
            assert "username" in user
            assert "name" in user

    def test_users_have_profile_fields(self):
        resp = _load_fixture("user_lookup_response.json")
        users = resp["data"]
        for user in users:
            # id and username are always present
            assert isinstance(user["id"], str)
            assert isinstance(user["username"], str)

    def test_errors_listed_for_missing_handles(self):
        resp = _load_fixture("user_lookup_response.json")
        # The fixture may contain errors for handles that couldn't be resolved
        if "errors" in resp:
            for error in resp["errors"]:
                assert "detail" in error or "title" in error


class TestUserPostsFixture:
    def test_parses_post_data(self):
        resp = _load_fixture("user_posts_response.json")
        posts = resp.get("data", [])
        assert len(posts) > 0
        for post in posts:
            assert "id" in post
            assert "text" in post

    def test_posts_have_expected_fields(self):
        resp = _load_fixture("user_posts_response.json")
        posts = resp["data"]
        for post in posts:
            assert "created_at" in post
            assert "author_id" in post

    def test_meta_contains_result_count(self):
        resp = _load_fixture("user_posts_response.json")
        assert "meta" in resp
        assert "result_count" in resp["meta"]
        assert resp["meta"]["result_count"] == len(resp["data"])


class TestCollectorRun:
    """Tests that collector.run() writes raw_posts.json to disk."""

    def test_writes_raw_posts_json(self, tmp_path):
        """run() should write raw_posts.json to the output directory."""
        from pipeline.collector import run

        fixture = _load_fixture("raw_posts.json")

        with patch("pipeline.collector.collect_all", return_value=fixture):
            out_path = run(
                sources_path="config/sources.json",
                bearer_token="fake-token",
                output_dir=tmp_path,
            )

        assert out_path.exists()
        assert out_path.name == "raw_posts.json"
        data = json.loads(out_path.read_text())
        assert len(data) == len(fixture)

    def test_creates_output_directory(self, tmp_path):
        """run() should create the output directory if it doesn't exist."""
        from pipeline.collector import run

        nested = tmp_path / "data" / "runs" / "2026-07-21"

        with patch("pipeline.collector.collect_all", return_value=[]):
            out_path = run(
                sources_path="config/sources.json",
                bearer_token="fake-token",
                output_dir=nested,
            )

        assert nested.exists()
        assert out_path.parent == nested
