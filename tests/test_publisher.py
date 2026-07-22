"""Tests for the publisher module — HTML rendering, search, filters, and safety."""

import json
from pathlib import Path

from pipeline.publisher import publish, publish_file, run as publisher_run

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str):
    return json.loads((FIXTURES_DIR / name).read_text())


def _verified_stories():
    return _load_fixture("verified_stories.json")


# ── HTML Structure ─────────────────────────────────────────────────


class TestHTMLStructure:
    def test_returns_html_string(self):
        html = publish(_verified_stories())
        assert isinstance(html, str)
        assert html.strip().startswith("<!DOCTYPE html>")

    def test_contains_all_stories(self):
        data = _verified_stories()
        html = publish(data)
        for story in data["stories"]:
            assert story["title"] in html

    def test_story_count_matches(self):
        data = _verified_stories()
        html = publish(data)
        # Each story gets a data-story-id attribute
        assert html.count("data-story-id") == len(data["stories"])

    def test_contains_inline_css(self):
        html = publish(_verified_stories())
        assert "<style>" in html

    def test_contains_inline_javascript(self):
        html = publish(_verified_stories())
        assert "<script>" in html

    def test_no_external_stylesheets(self):
        html = publish(_verified_stories())
        assert 'rel="stylesheet"' not in html

    def test_no_external_scripts(self):
        html = publish(_verified_stories())
        assert "src=" not in html.split("<script>")[0].split("</head>")[0]


# ── Story Content ──────────────────────────────────────────────────


class TestStoryContent:
    def test_shows_source_handle(self):
        data = _verified_stories()
        html = publish(data)
        for story in data["stories"]:
            assert f"@{story['handle']}" in html

    def test_shows_avatar(self):
        data = _verified_stories()
        html = publish(data)
        for story in data["stories"]:
            assert story["profile_image_url"] in html

    def test_shows_category(self):
        data = _verified_stories()
        html = publish(data)
        for story in data["stories"]:
            assert story["category"] in html

    def test_shows_title(self):
        data = _verified_stories()
        html = publish(data)
        for story in data["stories"]:
            assert story["title"] in html

    def test_shows_summary(self):
        data = _verified_stories()
        html = publish(data)
        for story in data["stories"]:
            assert story["summary"] in html

    def test_shows_why_it_matters(self):
        data = _verified_stories()
        html = publish(data)
        for story in data["stories"]:
            assert story["why_it_matters"] in html

    def test_shows_original_post_link(self):
        data = _verified_stories()
        html = publish(data)
        for story in data["stories"]:
            assert story["tweet_url"] in html

    def test_summaries_labeled_as_summaries(self):
        html = publish(_verified_stories())
        # The word "Summary" should appear as a label
        assert "Summary" in html


# ── Date Grouping ──────────────────────────────────────────────────


class TestDateGrouping:
    def test_stories_grouped_by_date(self):
        data = _verified_stories()
        html = publish(data)
        dates = sorted({s["date"] for s in data["stories"]}, reverse=True)
        for date in dates:
            assert date in html

    def test_newest_first(self):
        data = _verified_stories()
        html = publish(data)
        dates = sorted({s["date"] for s in data["stories"]}, reverse=True)
        positions = [html.index(d) for d in dates]
        assert positions == sorted(positions), "Dates should appear newest first"


# ── Category Filter Chips ──────────────────────────────────────────


class TestCategoryFilters:
    def test_filter_chips_present(self):
        data = _verified_stories()
        html = publish(data)
        categories = {s["category"] for s in data["stories"]}
        for cat in categories:
            assert f'data-category="{cat}"' in html

    def test_all_chip_present(self):
        html = publish(_verified_stories())
        assert 'data-category="all"' in html

    def test_no_results_element_exists_for_empty_filter(self):
        """Zero matching results case: the page must include a no-results message."""
        html = publish(_verified_stories())
        assert "no-results" in html


# ── Search ─────────────────────────────────────────────────────────


class TestSearch:
    def test_search_input_present(self):
        html = publish(_verified_stories())
        assert 'id="search"' in html or 'id="search-input"' in html

    def test_data_inlined_for_search(self):
        """All story data must be in the HTML — no runtime fetches."""
        data = _verified_stories()
        html = publish(data)
        for story in data["stories"]:
            assert story["title"] in html
            assert story["summary"] in html

    def test_no_results_element_exists_for_empty_search(self):
        """Zero matching results case: the page must include a no-results message."""
        html = publish(_verified_stories())
        assert "no-results" in html


# ── Last Updated ───────────────────────────────────────────────────


class TestLastUpdated:
    def test_last_updated_timestamp_present(self):
        html = publish(_verified_stories())
        assert "last-updated" in html.lower() or "Last updated" in html


# ── Security / Safety ─────────────────────────────────────────────


class TestSafety:
    def test_no_api_keys_in_output(self):
        html = publish(_verified_stories())
        for pattern in ["BEARER", "sk-", "api_key", "API_KEY", "secret"]:
            assert pattern not in html

    def test_no_local_paths_in_output(self):
        html = publish(_verified_stories())
        assert "/Users/" not in html
        assert "/home/" not in html
        assert "C:\\" not in html

    def test_planted_xss_in_title_is_escaped(self):
        """Malicious content in story fields must be HTML-escaped."""
        data = _verified_stories()
        data["stories"][0]["title"] = 'Breaking <script>alert("xss")</script> News'
        html = publish(data)
        assert "<script>alert" not in html
        assert "&lt;script&gt;" in html


# ── Empty Input ────────────────────────────────────────────────────


class TestEmptyInput:
    def test_zero_stories_produces_valid_html(self):
        data = {"stories": [], "rejections": [], "usage": {"input_tokens": 0, "output_tokens": 0}}
        html = publish(data)
        assert "<!DOCTYPE html>" in html
        assert html.count("data-story-id") == 0


# ── File I/O ───────────────────────────────────────────────────────


class TestPublishFile:
    def test_writes_feed_html(self, tmp_path):
        data = _verified_stories()
        input_path = tmp_path / "verified_stories.json"
        input_path.write_text(json.dumps(data))
        output_path = tmp_path / "feed.html"

        publish_file(input_path, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "<!DOCTYPE html>" in content
        assert data["stories"][0]["title"] in content

    def test_creates_parent_directories(self, tmp_path):
        data = _verified_stories()
        input_path = tmp_path / "verified_stories.json"
        input_path.write_text(json.dumps(data))
        output_path = tmp_path / "output" / "site" / "feed.html"

        publish_file(input_path, output_path)

        assert output_path.exists()


class TestPublisherRun:
    def test_run_reads_verified_and_writes_html(self, tmp_path):
        data = _verified_stories()
        (tmp_path / "verified_stories.json").write_text(json.dumps(data))

        out_path = publisher_run(tmp_path)

        assert out_path.exists()
        assert out_path.name == "feed.html"
        content = out_path.read_text()
        assert len(data["stories"]) == content.count("data-story-id")
