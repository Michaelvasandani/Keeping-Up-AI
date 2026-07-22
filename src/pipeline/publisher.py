"""Publisher — renders verified stories as a self-contained static HTML feed."""

import json
from datetime import datetime, timezone
from html import escape
from itertools import groupby
from pathlib import Path


def _story_card(story: dict) -> str:
    """Render a single story as an HTML card."""
    return f"""\
    <article class="story-card" data-story-id="{escape(story['id'])}" data-category="{escape(story['category'])}">
      <div class="story-header">
        <img class="avatar" src="{escape(story['profile_image_url'])}" alt="{escape(story['author_name'])}" />
        <div class="source-info">
          <span class="handle">@{escape(story['handle'])}</span>
          <span class="category-badge">{escape(story['category'])}</span>
        </div>
      </div>
      <h3 class="story-title">{escape(story['title'])}</h3>
      <p class="story-summary"><strong>Summary:</strong> {escape(story['summary'])}</p>
      <p class="story-why"><strong>Why it matters:</strong> {escape(story['why_it_matters'])}</p>
      <a class="original-link" href="{escape(story['tweet_url'])}" target="_blank" rel="noopener">View original post</a>
    </article>"""


def _date_group(date: str, cards_html: str) -> str:
    """Wrap cards in a date-group section."""
    return f"""\
  <section class="date-group">
    <h2 class="date-heading">{escape(date)}</h2>
{cards_html}
  </section>"""


def publish(verified: dict) -> str:
    """Render verified stories dict into a self-contained HTML string."""
    stories = verified["stories"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Sort by date descending, then by created_at descending within date
    sorted_stories = sorted(
        stories,
        key=lambda s: (s["date"], s.get("created_at", "")),
        reverse=True,
    )

    # Group by date
    groups_html = []
    for date, group in groupby(sorted_stories, key=lambda s: s["date"]):
        cards = "\n".join(_story_card(s) for s in group)
        groups_html.append(_date_group(date, cards))
    stories_html = "\n".join(groups_html)

    # Collect unique categories for filter chips
    categories = sorted({s["category"] for s in stories})

    chips_html = '    <button class="chip active" data-category="all">All</button>\n'
    chips_html += "\n".join(
        f'    <button class="chip" data-category="{escape(cat)}">{escape(cat)}</button>'
        for cat in categories
    )

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>AI News Feed</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 0; background: #f5f5f5; color: #1a1a1a; }}
  .container {{ max-width: 720px; margin: 0 auto; padding: 1rem; }}
  header {{ text-align: center; margin-bottom: 1.5rem; }}
  header h1 {{ margin: 0 0 0.25rem; font-size: 1.5rem; }}
  .last-updated {{ font-size: 0.85rem; color: #666; }}
  #search-input {{ width: 100%; padding: 0.6rem 1rem; font-size: 1rem; border: 1px solid #ccc; border-radius: 6px; margin-bottom: 1rem; }}
  .filters {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1.5rem; }}
  .chip {{ padding: 0.35rem 0.75rem; border: 1px solid #ccc; border-radius: 999px; background: #fff; cursor: pointer; font-size: 0.85rem; }}
  .chip.active {{ background: #1a1a1a; color: #fff; border-color: #1a1a1a; }}
  .date-group {{ margin-bottom: 1.5rem; }}
  .date-heading {{ font-size: 1.1rem; color: #444; border-bottom: 1px solid #ddd; padding-bottom: 0.25rem; margin-bottom: 0.75rem; }}
  .story-card {{ background: #fff; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .story-header {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }}
  .avatar {{ width: 32px; height: 32px; border-radius: 50%; }}
  .handle {{ font-weight: 600; font-size: 0.9rem; }}
  .category-badge {{ font-size: 0.75rem; background: #e8e8e8; padding: 0.15rem 0.5rem; border-radius: 4px; }}
  .story-title {{ margin: 0 0 0.4rem; font-size: 1.05rem; }}
  .story-summary, .story-why {{ margin: 0.25rem 0; font-size: 0.9rem; line-height: 1.5; }}
  .original-link {{ display: inline-block; margin-top: 0.5rem; font-size: 0.85rem; color: #1d9bf0; text-decoration: none; }}
  .original-link:hover {{ text-decoration: underline; }}
  .no-results {{ text-align: center; color: #888; padding: 2rem 0; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>AI News Feed</h1>
    <p class="last-updated">Last updated: {now}</p>
  </header>
  <input type="text" id="search-input" placeholder="Search stories..." />
  <div class="filters">
{chips_html}
  </div>
  <main id="stories">
{stories_html}
  </main>
  <p class="no-results" id="no-results" style="display:none;">No matching stories.</p>
</div>
<script>
(function() {{
  var searchInput = document.getElementById('search-input');
  var chips = document.querySelectorAll('.chip');
  var stories = document.querySelectorAll('.story-card');
  var dateGroups = document.querySelectorAll('.date-group');
  var noResults = document.getElementById('no-results');
  var activeCategory = 'all';

  function applyFilters() {{
    var query = searchInput.value.toLowerCase();
    var visible = 0;
    stories.forEach(function(card) {{
      var matchesCat = activeCategory === 'all' || card.getAttribute('data-category') === activeCategory;
      var text = card.textContent.toLowerCase();
      var matchesSearch = !query || text.indexOf(query) !== -1;
      var show = matchesCat && matchesSearch;
      card.style.display = show ? '' : 'none';
      if (show) visible++;
    }});
    dateGroups.forEach(function(group) {{
      var hasVisible = group.querySelectorAll('.story-card:not([style*="display: none"])').length > 0;
      // Also check for cards with no display style set (visible by default)
      if (!hasVisible) {{
        var cards = group.querySelectorAll('.story-card');
        for (var i = 0; i < cards.length; i++) {{
          if (cards[i].style.display !== 'none') {{
            hasVisible = true;
            break;
          }}
        }}
      }}
      group.style.display = hasVisible ? '' : 'none';
    }});
    noResults.style.display = visible === 0 ? '' : 'none';
  }}

  searchInput.addEventListener('input', applyFilters);

  chips.forEach(function(chip) {{
    chip.addEventListener('click', function() {{
      chips.forEach(function(c) {{ c.classList.remove('active'); }});
      chip.classList.add('active');
      activeCategory = chip.getAttribute('data-category');
      applyFilters();
    }});
  }});
}})();
</script>
</body>
</html>"""


def publish_file(
    input_path: str | Path,
    output_path: str | Path,
) -> str:
    """Read verified_stories.json and write feed.html. Returns the HTML string."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    verified = json.loads(input_path.read_text())
    html = publish(verified)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)

    return html


def run(run_dir: str | Path) -> Path:
    """Read verified_stories.json from a run directory and write feed.html.

    Returns the path to the written feed.html file.
    """
    run_dir = Path(run_dir)
    input_path = run_dir / "verified_stories.json"
    output_path = run_dir / "feed.html"

    html = publish_file(input_path, output_path)

    story_count = html.count("data-story-id")
    print(f"  [done] published feed: {story_count} stories to {output_path}")
    return output_path
