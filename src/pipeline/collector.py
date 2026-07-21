"""Collector module — fetches posts from X API v2."""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

X_API_BASE = "https://api.x.com/2"

USER_FIELDS = "id,name,username,profile_image_url,verified"
TWEET_FIELDS = "created_at,text,author_id,public_metrics,entities,referenced_tweets"
EXPANSIONS = "author_id,referenced_tweets.id"
MAX_RESULTS = 20


def _get(bearer_token: str, url: str, params: dict) -> dict:
    """Make an authenticated GET request to the X API and return JSON."""
    headers = {"Authorization": f"Bearer {bearer_token}"}
    resp = httpx.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()


def resolve_users(
    handles: list[str], bearer_token: str
) -> dict:
    """Look up X users by username. Returns the raw API response dict."""
    usernames = ",".join(handles)
    return _get(bearer_token, f"{X_API_BASE}/users/by", {
        "usernames": usernames,
        "user.fields": USER_FIELDS,
    })


def fetch_user_posts(
    user_id: str,
    bearer_token: str,
    since: datetime | None = None,
) -> dict:
    """Fetch recent posts for a user. Returns the raw API response dict."""
    params: dict[str, str | int] = {
        "tweet.fields": TWEET_FIELDS,
        "expansions": EXPANSIONS,
        "max_results": MAX_RESULTS,
        "exclude": "retweets,replies",
    }
    if since is not None:
        params["start_time"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    return _get(bearer_token, f"{X_API_BASE}/users/{user_id}/tweets", params)


def collect_all(
    sources_path: str,
    bearer_token: str,
    since: datetime | None = None,
) -> list[dict]:
    """Orchestrate collection: load sources, resolve users, fetch posts.

    Returns a list of dicts, one per source account, each containing
    the user info and their raw posts response.
    """
    sources = json.loads(Path(sources_path).read_text())
    handles = [s["handle"] for s in sources]

    users_resp = resolve_users(handles, bearer_token)
    users = {u["username"].lower(): u for u in users_resp.get("data", [])}

    results = []
    for source in sources:
        handle = source["handle"]
        user = users.get(handle.lower())
        if user is None:
            print(f"  [skip] could not resolve @{handle}")
            continue

        print(f"  [fetch] @{handle} (id={user['id']})")
        try:
            posts_resp = fetch_user_posts(user["id"], bearer_token, since=since)
        except httpx.HTTPStatusError as exc:
            print(f"  [error] @{handle}: {exc.response.status_code}")
            continue

        results.append({
            "source": source,
            "user": user,
            "posts": posts_resp,
        })

    return results
