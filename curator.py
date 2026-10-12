#!/usr/bin/env python3
"""
Biweekly Reading List Curator
Fetches articles from RSS feeds, ranks them with AI, and publishes to GitHub Pages.
Optionally sends via Buttondown API.
"""

import os
import sys
import json
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- Dependencies (installed by the GitHub Action) ---
# feedparser, trafilatura, jinja2, pyyaml

import feedparser
import trafilatura
import yaml
from jinja2 import Template

# --- Configuration ---
HERE = Path(__file__).parent.resolve()
SOURCES_FILE = HERE / "sources.yaml"
PROFILE_FILE = HERE / "profile.yaml"
FEEDBACK_FILE = HERE / "feedback.yaml"
DOCS_DIR = HERE / "docs"
ARCHIVE_DIR = DOCS_DIR / "archive"

# AI API: Gemini (free tier) or OpenRouter (free models)
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini")  # "gemini" or "openrouter"
BUTTONDOWN_API_KEY = os.environ.get("BUTTONDOWN_API_KEY", "")

DAYS_WINDOW = 14  # How far back to look for articles


def load_yaml(path):
    """Load a YAML file, returning empty dict/list if missing."""
    if not path.exists():
        return {} if path.suffix == ".yaml" else []
    with open(path) as f:
        return yaml.safe_load(f) or {}


def fetch_feeds(sources):
    """Fetch all RSS feeds and return candidate articles from the last DAYS_WINDOW days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_WINDOW)
    candidates = []
    seen_urls = set()

    for source in sources:
        name = source.get("name", "Unknown")
        feed_url = source.get("feed", "")
        topics = source.get("topics", [])
        weight = source.get("weight", 1.0)

        if not feed_url:
            continue

        print(f"  Fetching: {name} ({feed_url})")
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"    Warning: Could not parse feed for {name}: {e}")
            continue

        for entry in feed.entries:
            # Parse publication date
            pub_date = None
            for date_field in ["published_parsed", "updated_parsed", "created_parsed"]:
                if hasattr(entry, date_field) and getattr(entry, date_field):
                    try:
                        pub_date = datetime(*getattr(entry, date_field)[:6], tzinfo=timezone.utc)
                    except Exception:
                        pass
                    break

            if pub_date and pub_date < cutoff:
                continue

            # Get URL
            url = entry.get("link", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            # Get title and summary
            title = entry.get("title", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()

            # Try to extract full text (may fail on some sites — that's fine)
            excerpt = ""
            try:
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
                    if text:
                        # Take first ~500 chars as excerpt
                        excerpt = text[:500].strip()
            except Exception:
                pass

            # Estimate reading time (avg 200 words per minute)
            word_count = len((summary + " " + excerpt).split())
            reading_time = max(1, round(word_count / 200))

            candidates.append({
                "title": title,
                "url": url,
                "source": name,
                "topics": topics,
                "weight": weight,
                "summary": summary,
                "excerpt": excerpt,
                "reading_time": reading_time,
                "pub_date": pub_date.isoformat() if pub_date else "",
            })

    print(f"  Found {len(candidates)} candidate articles from last {DAYS_WINDOW} days")
    return candidates


def rank_with_ai(candidates, profile, feedback):
    """Use AI to rank candidates and select the top picks."""
    if not AI_API_KEY:
        print("  No AI_API_KEY set — falling back to basic heuristic ranking")
        return rank_heuristic(candidates, profile)

    # Prepare a compact summary of candidates for the AI
    candidate_summaries = []
    for i, c in enumerate(candidates):
        candidate_summaries.append({
            "id": i,
            "title": c["title"],
            "source": c["source"],
            "topics": c["topics"],
            "reading_time": c["reading_time"],
            "summary": c["summary"][:300] if c["summary"] else c["excerpt"][:300],
        })

    # Build the prompt
    profile_text = json.dumps({
        "description": profile.get("description", ""),
        "topics_liked": profile.get("topics_liked", []),
        "topics_avoided": profile.get("topics_avoided", []),
        "preferences": profile.get("preferences", {}),
        "loved_examples": profile.get("loved_examples", []),
        "feedback": feedback,
    }, indent=2)

    max_articles = profile.get("max_articles", 5)

    prompt = f"""You are a personal reading curator. Below is a list of candidate articles published in the last 2 weeks, along with the reader's interest profile and feedback.

Your task: select the {max_articles} best articles for this reader. Choose for depth, quality, and relevance to their interests. Avoid clickbait, listicles, and anything in their "topics_avoided" list. Prefer in-depth, thought-provoking pieces.

For each selected article, provide:
- id: the article ID from the list
- reason: 1-2 sentences explaining why this article is a great pick for this reader

Return ONLY a JSON array of objects with "id" and "reason" fields. No markdown, no explanation.

READER PROFILE AND FEEDBACK:
{profile_text}

CANDIDATE ARTICLES:
{json.dumps(candidate_summaries, indent=2)}
"""

    # Call the AI API
    try:
        result = call_ai_api(prompt)
        # Parse the JSON response
        # Try to extract JSON from the response
        result = result.strip()
        if result.startswith("```"):
            # Remove markdown code fences
            result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        selections = json.loads(result)
    except Exception as e:
        print(f"  AI ranking failed ({e}) — falling back to heuristic")
        return rank_heuristic(candidates, profile)

    # Build the final list
    selected = []
    for sel in selections:
        idx = sel.get("id")
        if idx is not None and 0 <= idx < len(candidates):
            article = candidates[idx].copy()
            article["reason"] = sel.get("reason", "")
            selected.append(article)

    return selected


def call_ai_api(prompt):
    """Call the AI API (Gemini or OpenRouter) and return the response text."""
    if AI_PROVIDER == "openrouter":
        return call_openrouter(prompt)
    else:
        return call_gemini(prompt)


def call_gemini(prompt):
    """Call Google Gemini API (free tier)."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={AI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4096,
        }
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
    return result["candidates"][0]["content"]["parts"][0]["text"]


def call_openrouter(prompt):
    """Call OpenRouter API (free models available)."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": "google/gemini-2.5-flash-lite-preview:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}",
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
    return result["choices"][0]["message"]["content"]


def rank_heuristic(candidates, profile):
    """Basic fallback ranking when no AI API key is available."""
    liked_topics = set(profile.get("topics_liked", []))
    avoided_topics = set(profile.get("topics_avoided", []))
    max_articles = profile.get("max_articles", 5)

    scored = []
    for c in candidates:
        score = c["weight"]
        # Topic overlap
        article_topics = set(c["topics"])
        liked_overlap = len(article_topics & liked_topics)
        avoided_overlap = len(article_topics & avoided_topics)
        score += liked_overlap * 2 - avoided_overlap * 3
        # Prefer longer articles
        if c["reading_time"] >= 10:
            score += 1.5
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = []
    for score, c in scored[:max_articles]:
        c = c.copy()
        c["reason"] = "Selected based on topic relevance and source quality."
        selected.append(c)
    return selected


def generate_html(articles, issue_date):
    """Generate the HTML for the reading list page."""
    template_str = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Biweekly Reading List</title>
    <style>
        :root {
            --bg: #faf8f5;
            --text: #1a1a1a;
            --muted: #666;
            --accent: #8b5cf6;
            --border: #e5e5e5;
            --card-bg: #fff;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Georgia, 'Times New Roman', serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.7;
            max-width: 680px;
            margin: 0 auto;
            padding: 2rem 1.5rem 4rem;
        }
        header { text-align: center; margin-bottom: 3rem; }
        h1 { font-size: 2rem; font-weight: normal; margin-bottom: 0.5rem; }
        .subtitle { color: var(--muted); font-size: 0.95rem; }
        .issue-date {
            color: var(--accent);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-top: 0.5rem;
        }
        article {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            transition: box-shadow 0.2s;
        }
        article:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
        .article-header { display: flex; justify-content: space-between; align-items: baseline; }
        h2 { font-size: 1.3rem; font-weight: normal; margin-bottom: 0.25rem; }
        h2 a { color: var(--text); text-decoration: none; }
        h2 a:hover { color: var(--accent); }
        .source { color: var(--muted); font-size: 0.85rem; font-style: italic; }
        .reading-time {
            color: var(--muted);
            font-size: 0.8rem;
            white-space: nowrap;
        }
        .reason {
            margin: 0.75rem 0;
            color: #333;
            font-size: 0.95rem;
        }
        .excerpt {
            margin-top: 0.5rem;
            color: var(--muted);
            font-size: 0.9rem;
            border-left: 3px solid var(--accent);
            padding-left: 1rem;
        }
        .archive-link {
            text-align: center;
            margin-top: 2rem;
            font-size: 0.85rem;
        }
        .archive-link a { color: var(--accent); text-decoration: none; }
        footer { text-align: center; margin-top: 3rem; color: var(--muted); font-size: 0.8rem; }
    </style>
</head>
<body>
    <header>
        <h1>Biweekly Reading List</h1>
        <p class="subtitle">Curated long reads, essays, and in-depth articles</p>
        <p class="issue-date">{{ issue_date }}</p>
    </header>

    {% for article in articles %}
    <article>
        <div class="article-header">
            <h2><a href="{{ article.url }}">{{ article.title }}</a></h2>
            <span class="reading-time">{{ article.reading_time }} min</span>
        </div>
        <p class="source">{{ article.source }}</p>
        <p class="reason">{{ article.reason }}</p>
        {% if article.excerpt %}
        <p class="excerpt">{{ article.excerpt }}...</p>
        {% endif %}
    </article>
    {% endfor %}

    <div class="archive-link">
        <a href="archive/">Past issues</a>
    </div>

    <footer>
        <p>Curated by AI, tailored to your interests. Updated every two weeks.</p>
    </footer>
</body>
</html>"""

    template = Template(template_str)
    html = template.render(articles=articles, issue_date=issue_date)
    return html


def generate_archive_html(articles, issue_date):
    """Generate HTML for an archived issue."""
    base = generate_html(articles, issue_date)
    # Update the archive link to point back
    base = base.replace('href="archive/"', 'href="../index.html"')
    return base


def generate_archive_index():
    """Generate an index of past issues."""
    issues = []
    if ARCHIVE_DIR.exists():
        for f in sorted(ARCHIVE_DIR.glob("*.html"), reverse=True):
            date_str = f.stem
            issues.append({"date": date_str, "filename": f.name})

    template_str = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Past Issues — Biweekly Reading List</title>
    <style>
        body {
            font-family: Georgia, serif;
            background: #faf8f5;
            color: #1a1a1a;
            max-width: 680px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
            line-height: 1.7;
        }
        h1 { font-weight: normal; margin-bottom: 2rem; }
        a { color: #8b5cf6; text-decoration: none; }
        a:hover { text-decoration: underline; }
        ul { list-style: none; padding: 0; }
        li { padding: 0.5rem 0; border-bottom: 1px solid #e5e5e5; }
        .back { margin-top: 2rem; font-size: 0.9rem; }
    </style>
</head>
<body>
    <h1>Past Issues</h1>
    <ul>
    {% for issue in issues %}
        <li><a href="{{ issue.filename }}">{{ issue.date }}</a></li>
    {% endfor %}
    </ul>
    {% if not issues %}
    <p>No past issues yet. Check back after the next run.</p>
    {% endif %}
    <p class="back"><a href="../index.html">← Back to latest</a></p>
</body>
</html>"""
    template = Template(template_str)
    return template.render(issues=issues)


def send_buttondown_email(articles, issue_date, profile):
    """Send the reading list as an email via Buttondown API."""
    if not BUTTONDOWN_API_KEY:
        print("  No BUTTONDOWN_API_KEY set — skipping email")
        return

    subject = profile.get("email_subject_template", "Reading List — {date}").format(date=issue_date)

    # Build email body as markdown
    body = f"# {subject}\n\n"
    for article in articles:
        body += f"## [{article['title']}]({article['url']})\n"
        body += f"*{article['source']} · {article['reading_time']} min read*\n\n"
        body += f"{article['reason']}\n\n"
        if article.get("excerpt"):
            body += f"> {article['excerpt']}...\n\n"
        body += "---\n\n"

    body += "\n*Curated by AI, tailored to your interests. See you in two weeks.*\n"

    # Send via Buttondown API (creates a draft)
    url = "https://api.buttondown.com/v1/emails"
    payload = {
        "subject": subject,
        "body": body,
        "status": "draft",  # Draft so you can review before sending
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
    })

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            print(f"  Email draft created in Buttondown: {result.get('id', 'unknown')}")
            print(f"  Review and send at https://buttondown.com")
    except urllib.error.HTTPError as e:
        print(f"  Buttondown API error: {e.code} {e.read().decode()}")
    except Exception as e:
        print(f"  Could not send email: {e}")


def main():
    print("=" * 60)
    print("  Biweekly Reading List Curator")
    print("=" * 60)

    # Load configuration
    sources = load_yaml(SOURCES_FILE)
    profile = load_yaml(PROFILE_FILE)
    feedback = load_yaml(FEEDBACK_FILE)

    if not sources:
        print("Error: No sources found in sources.yaml")
        sys.exit(1)

    print(f"\n1. Fetching articles from {len(sources)} sources...")
    candidates = fetch_feeds(sources)

    if not candidates:
        print("No articles found. Try adding more sources or increasing DAYS_WINDOW.")
        sys.exit(0)

    print(f"\n2. Ranking with AI...")
    selected = rank_with_ai(candidates, profile, feedback)

    if not selected:
        print("No articles selected. Check your profile and sources.")
        sys.exit(0)

    print(f"   Selected {len(selected)} articles:")
    for a in selected:
        print(f"   - {a['title']} ({a['source']})")

    # Generate issue date
    issue_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
    date_slug = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"\n3. Generating pages...")
    # Ensure directories exist
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    # Generate main page
    html = generate_html(selected, issue_date)
    with open(DOCS_DIR / "index.html", "w") as f:
        f.write(html)

    # Archive this issue
    archive_html = generate_archive_html(selected, issue_date)
    with open(ARCHIVE_DIR / f"{date_slug}.html", "w") as f:
        f.write(archive_html)

    # Update archive index
    archive_index = generate_archive_index()
    with open(ARCHIVE_DIR / "index.html", "w") as f:
        f.write(archive_index)

    print(f"   Published to docs/index.html")
    print(f"   Archived at docs/archive/{date_slug}.html")

    # Optional: send email
    if profile.get("send_email", False):
        print(f"\n4. Sending email via Buttondown...")
        send_buttondown_email(selected, issue_date, profile)

    print(f"\nDone. Your reading list for {issue_date} is ready.")
    print(f"View at: https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/")


if __name__ == "__main__":
    main()
