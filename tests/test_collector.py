"""Tests validating saved X API fixture structure for downstream use."""

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
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
