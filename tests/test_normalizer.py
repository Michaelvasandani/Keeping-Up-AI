"""Tests for the normalizer module — filtering, dedup, and schema."""

import json
from pathlib import Path

from pipeline.normalizer import normalize, normalize_file, run as normalizer_run

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str):
    return json.loads((FIXTURES_DIR / name).read_text())


def _raw_posts():
    return _load_fixture("raw_posts.json")


def _normalized():
    return normalize(_raw_posts())


# ── Filtering ────────────────────────────────────────────────────────


class TestFiltering:
    def test_replies_are_filtered_out(self):
        """Posts with referenced_tweets type 'replied_to' are removed."""
        result = _normalized()
        ids = {p["id"] for p in result}
        # These two are self-replies in the fixture
        assert "2078243670265041038" not in ids
        assert "2077807981715128702" not in ids

    def test_retweets_are_filtered_out(self):
        """Posts with referenced_tweets type 'retweeted' are removed."""
        result = _normalized()
        ids = {p["id"] for p in result}
        assert "9999999999999999999" not in ids

    def test_quote_tweets_are_kept(self):
        """Posts with referenced_tweets type 'quoted' are original content."""
        result = _normalized()
        ids = {p["id"] for p in result}
        assert "2078223217773474134" in ids

    def test_original_posts_are_kept(self):
        """Posts with no referenced_tweets pass through."""
        result = _normalized()
        ids = {p["id"] for p in result}
        assert "2078243667081617826" in ids
        assert "2077446718728425686" in ids

    def test_in_reply_to_user_id_filtered(self):
        """Defensive: posts with in_reply_to_user_id are filtered."""
        raw = [
            {
                "source": {"handle": "test", "category": "Test"},
                "user": {"id": "1", "name": "Test", "username": "test",
                         "profile_image_url": "", "verified": False},
                "posts": {
                    "data": [
                        {
                            "id": "111",
                            "author_id": "1",
                            "created_at": "2026-07-15T00:00:00.000Z",
                            "text": "reply via legacy field",
                            "in_reply_to_user_id": "999",
                        }
                    ],
                    "meta": {"result_count": 1},
                },
            }
        ]
        result = normalize(raw)
        assert len(result) == 0


# ── Deduplication ────────────────────────────────────────────────────


class TestDeduplication:
    def test_duplicate_ids_are_removed(self):
        """Post ID 2077501603050033634 appears in both accounts; keep one."""
        result = _normalized()
        ids = [p["id"] for p in result]
        assert ids.count("2077501603050033634") == 1

    def test_total_count_after_dedup_and_filter(self):
        """
        Fixture has 8 posts total:
        - 2 replied_to → removed
        - 1 retweeted  → removed
        - 1 duplicate  → removed
        Leaves 4 unique posts.
        """
        result = _normalized()
        assert len(result) == 4


# ── Schema ───────────────────────────────────────────────────────────


class TestNormalizedSchema:
    def test_required_fields_present(self):
        result = _normalized()
        required = {
            "id", "date", "created_at", "category", "handle",
            "author_name", "verified", "profile_image_url", "tweet_url",
            "text",
        }
        for post in result:
            assert required.issubset(post.keys()), (
                f"Missing fields: {required - post.keys()}"
            )

    def test_date_is_yyyy_mm_dd(self):
        result = _normalized()
        for post in result:
            assert len(post["date"]) == 10
            parts = post["date"].split("-")
            assert len(parts) == 3
            assert len(parts[0]) == 4  # year

    def test_created_at_is_iso(self):
        result = _normalized()
        for post in result:
            assert post["created_at"].endswith("Z") or "+" in post["created_at"]

    def test_tweet_url_format(self):
        result = _normalized()
        for post in result:
            expected = f"https://x.com/{post['handle']}/status/{post['id']}"
            assert post["tweet_url"] == expected

    def test_category_from_source(self):
        result = _normalized()
        openai_posts = [p for p in result if p["handle"] == "OpenAI"]
        for post in openai_posts:
            assert post["category"] == "Models"

    def test_author_metadata_from_user(self):
        result = _normalized()
        openai_posts = [p for p in result if p["handle"] == "OpenAI"]
        for post in openai_posts:
            assert post["author_name"] == "OpenAI"
            assert post["verified"] is True
            assert post["profile_image_url"].startswith("https://")


# ── File I/O ─────────────────────────────────────────────────────────


class TestNormalizeFile:
    def test_writes_normalized_json(self, tmp_path):
        raw_path = FIXTURES_DIR / "raw_posts.json"
        out_path = tmp_path / "normalized_posts.json"

        result = normalize_file(raw_path, out_path)

        assert out_path.exists()
        on_disk = json.loads(out_path.read_text())
        assert len(on_disk) == len(result)
        assert len(on_disk) == 4

    def test_creates_parent_directories(self, tmp_path):
        raw_path = FIXTURES_DIR / "raw_posts.json"
        out_path = tmp_path / "data" / "runs" / "2026-07-21" / "normalized_posts.json"

        normalize_file(raw_path, out_path)

        assert out_path.exists()


class TestNormalizerRun:
    def test_run_reads_raw_and_writes_normalized(self, tmp_path):
        """run() reads raw_posts.json from run_dir and writes normalized_posts.json."""
        import shutil

        shutil.copy(FIXTURES_DIR / "raw_posts.json", tmp_path / "raw_posts.json")

        out_path = normalizer_run(tmp_path)

        assert out_path.exists()
        assert out_path.name == "normalized_posts.json"
        data = json.loads(out_path.read_text())
        assert len(data) == 4
