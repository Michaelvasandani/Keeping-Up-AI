"""Fetch sample posts from X API and save as test fixtures."""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow running from repo root: `python scripts/fetch_sample.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.collector import collect_all, fetch_user_posts, resolve_users

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = REPO_ROOT / "config" / "sources.json"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


def load_env(env_path: Path) -> None:
    """Load key=value pairs from a .env file into os.environ."""
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main():
    load_env(REPO_ROOT / ".env")

    bearer_token = os.environ.get("X_BEARER_TOKEN")
    if not bearer_token:
        print("Error: X_BEARER_TOKEN not found in .env or environment.")
        sys.exit(1)

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    # --- Step 1: Resolve users and save fixture ---
    sources = json.loads(SOURCES_PATH.read_text())
    handles = [s["handle"] for s in sources]
    print(f"Resolving {len(handles)} handles...")
    users_resp = resolve_users(handles, bearer_token)

    fixture_path = FIXTURES_DIR / "user_lookup_response.json"
    fixture_path.write_text(json.dumps(users_resp, indent=2))
    print(f"Saved user lookup fixture to {fixture_path}")

    users = users_resp.get("data", [])
    if not users:
        print("No users resolved. Check your handles and API credentials.")
        sys.exit(1)

    print(f"Resolved {len(users)} users:")
    for u in users:
        print(f"  @{u['username']} (id={u['id']})")

    # --- Step 2: Fetch posts from first resolved user and save fixture ---
    first_user = users[0]
    since = datetime.now(timezone.utc) - timedelta(days=7)
    print(f"\nFetching posts from @{first_user['username']}...")
    posts_resp = fetch_user_posts(first_user["id"], bearer_token, since=since)

    fixture_path = FIXTURES_DIR / "user_posts_response.json"
    fixture_path.write_text(json.dumps(posts_resp, indent=2))
    print(f"Saved posts fixture to {fixture_path}")

    post_count = len(posts_resp.get("data", []))
    print(f"Fetched {post_count} posts from @{first_user['username']}")

    if post_count > 0:
        print("\nSample post:")
        post = posts_resp["data"][0]
        print(f"  [{post.get('created_at', 'no date')}] {post['text'][:120]}...")

    print("\nDone. Fixtures saved to tests/fixtures/")


if __name__ == "__main__":
    main()
