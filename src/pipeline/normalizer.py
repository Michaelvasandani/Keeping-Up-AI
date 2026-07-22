"""Normalizer module — filters, deduplicates, and standardizes raw posts."""

import json
from pathlib import Path

FILTERED_REF_TYPES = {"replied_to", "retweeted"}


def _is_reply_or_repost(post: dict) -> bool:
    """Return True if this post is a reply or repost that should be filtered."""
    if "in_reply_to_user_id" in post:
        return True
    for ref in post.get("referenced_tweets", []):
        if ref.get("type") in FILTERED_REF_TYPES:
            return True
    return False


def normalize(raw_results: list[dict], exclude_ids: set[str] | None = None) -> list[dict]:
    """Normalize raw collector output into the standard story schema.

    Takes the list of dicts produced by collect_all() (each containing
    source, user, and posts keys) and returns a flat list of normalized
    post dicts, filtered and deduplicated.

    If exclude_ids is provided, posts with IDs in that set are skipped
    (used for cross-run deduplication).
    """
    seen_ids: set[str] = set(exclude_ids) if exclude_ids else set()
    normalized: list[dict] = []

    for entry in raw_results:
        source = entry["source"]
        user = entry["user"]
        posts = entry["posts"].get("data", [])

        for post in posts:
            post_id = post["id"]

            if _is_reply_or_repost(post):
                continue

            if post_id in seen_ids:
                continue
            seen_ids.add(post_id)

            created_at = post["created_at"]
            date = created_at[:10]

            normalized.append({
                "id": post_id,
                "date": date,
                "created_at": created_at,
                "category": source["category"],
                "handle": user["username"],
                "author_name": user["name"],
                "verified": user.get("verified", False),
                "profile_image_url": user.get("profile_image_url", ""),
                "tweet_url": f"https://x.com/{user['username']}/status/{post_id}",
                "text": post["text"],
            })

    return normalized


def normalize_file(
    raw_path: str | Path,
    output_path: str | Path,
    exclude_ids: set[str] | None = None,
) -> list[dict]:
    """Read raw_posts.json, normalize, and write normalized_posts.json."""
    raw_path = Path(raw_path)
    output_path = Path(output_path)

    raw_results = json.loads(raw_path.read_text())
    normalized = normalize(raw_results, exclude_ids=exclude_ids)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False))

    return normalized


def run(run_dir: str | Path, exclude_ids: set[str] | None = None) -> Path:
    """Read raw_posts.json from a run directory and write normalized_posts.json.

    Returns the path to the written normalized_posts.json file.
    """
    run_dir = Path(run_dir)
    raw_path = run_dir / "raw_posts.json"
    output_path = run_dir / "normalized_posts.json"

    result = normalize_file(raw_path, output_path, exclude_ids=exclude_ids)

    print(f"  [done] normalized {len(result)} posts to {output_path}")
    return output_path
