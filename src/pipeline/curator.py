"""Curator Agent — assesses importance and generates story metadata from normalized posts."""

import json
from pathlib import Path

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """\
You are a curator for an AI engineering news feed. Given a social media post \
from an AI company or researcher, assess its importance and generate story metadata.

Respond with a JSON object containing exactly these fields:
- "title": A short, factual title (no hype, no clickbait)
- "summary": A concise 1-2 sentence summary of the post content
- "why_it_matters": A brief explanation of why this is relevant to AI engineers
- "importance": One of "high", "medium", or "low"

Respond with only the JSON object, no other text."""


def _build_user_message(post: dict) -> str:
    return (
        f"Source: @{post['handle']} ({post['author_name']})\n"
        f"Category: {post['category']}\n"
        f"Date: {post['date']}\n"
        f"Post text: {post['text']}"
    )


def curate(posts: list[dict], client) -> dict:
    """Curate normalized posts into candidate stories.

    Returns a dict with "stories" (list of candidate story dicts) and
    "usage" (total token counts).
    """
    stories = []
    total_input_tokens = 0
    total_output_tokens = 0

    for post in posts:
        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_message(post)}],
        )

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        curation = json.loads(response.content[0].text)

        stories.append({
            **post,
            "title": curation["title"],
            "summary": curation["summary"],
            "why_it_matters": curation["why_it_matters"],
            "importance": curation["importance"],
        })

    return {
        "stories": stories,
        "usage": {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
        },
    }


def curate_file(
    input_path: str | Path,
    output_path: str | Path,
    client,
) -> dict:
    """Read normalized_posts.json, curate, and write candidate_stories.json."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    posts = json.loads(input_path.read_text())
    result = curate(posts, client)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    return result


def run(run_dir: str | Path, client) -> Path:
    """Read normalized_posts.json from a run directory and write candidate_stories.json.

    Returns the path to the written candidate_stories.json file.
    """
    run_dir = Path(run_dir)
    input_path = run_dir / "normalized_posts.json"
    output_path = run_dir / "candidate_stories.json"

    result = curate_file(input_path, output_path, client)

    n = len(result["stories"])
    tokens = result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
    print(f"  [done] curated {n} candidate stories ({tokens} tokens) to {output_path}")
    return output_path
