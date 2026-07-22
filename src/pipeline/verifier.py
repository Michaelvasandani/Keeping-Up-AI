"""Verifier Agent — checks generated claims against original source text."""

import json
import re
from pathlib import Path

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """\
You are a fact-checking verifier for an AI engineering news feed. Given a \
candidate story (with a generated title, summary, and "why it matters" \
explanation) alongside the original source post, verify that every claim in \
the generated content is faithful to the source.

Respond with a JSON object containing exactly these fields:
- "verdict": Either "approved" (all claims are faithful) or "rejected" (any claim is fabricated or misleading)
- "reason": If rejected, explain which specific claim is unfaithful and why. If approved, this can be an empty string.

Respond with only the JSON object, no other text."""


def _build_user_message(story: dict) -> str:
    return (
        f"ORIGINAL POST:\n"
        f"Source: @{story['handle']} ({story['author_name']})\n"
        f"Date: {story['date']}\n"
        f"Text: {story['text']}\n\n"
        f"GENERATED CONTENT:\n"
        f"Title: {story['title']}\n"
        f"Summary: {story['summary']}\n"
        f"Why it matters: {story['why_it_matters']}"
    )


def verify(candidates: dict, client) -> dict:
    """Verify candidate stories against their source text.

    Returns a dict with "stories" (approved only), "rejections" (logged),
    and "usage" (total token counts).
    """
    stories = []
    rejections = []
    total_input_tokens = 0
    total_output_tokens = 0

    for story in candidates["stories"]:
        response = client.messages.create(
            model=MODEL,
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_message(story)}],
        )

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        text = response.content[0].text
        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
        text = re.sub(r"\n?```\s*$", "", text)
        result = json.loads(text)

        if result["verdict"] == "approved":
            stories.append(story)
        else:
            rejections.append({
                "id": story["id"],
                "title": story["title"],
                "reason": result["reason"],
            })

    return {
        "stories": stories,
        "rejections": rejections,
        "usage": {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
        },
    }


def verify_file(
    input_path: str | Path,
    output_path: str | Path,
    client,
) -> dict:
    """Read candidate_stories.json, verify, and write verified_stories.json."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    candidates = json.loads(input_path.read_text())
    result = verify(candidates, client)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    return result


def run(run_dir: str | Path, client) -> Path:
    """Read candidate_stories.json from a run directory and write verified_stories.json.

    Returns the path to the written verified_stories.json file.
    """
    run_dir = Path(run_dir)
    input_path = run_dir / "candidate_stories.json"
    output_path = run_dir / "verified_stories.json"

    result = verify_file(input_path, output_path, client)

    approved = len(result["stories"])
    rejected = len(result["rejections"])
    tokens = result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
    print(
        f"  [done] verified stories: {approved} approved, {rejected} rejected "
        f"({tokens} tokens) to {output_path}"
    )
    return output_path
