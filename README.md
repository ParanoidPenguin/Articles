# Biweekly Reading List Curator

An automated, AI-curated biweekly reading list of in-depth articles, essays, and long reads — published to a free GitHub Pages site and optionally emailed via Buttondown.

**Total cost: $0** (using free tiers)

## How it works

```
Your RSS feeds (sources.yaml)
      ↓
GitHub Actions (runs every 2 weeks, free)
      ↓
Python script fetches recent articles
      ↓
AI ranks articles against your interest profile
      ↓
Top picks published to GitHub Pages
      ↓
Optional: Buttondown API sends email newsletter
```

## Quick start

1. **Fork or clone this repo**

2. **Edit `sources.yaml`** — add the RSS feeds of publications you love

3. **Edit `profile.yaml`** — describe your interests, preferred topics, and what makes a great read for you

4. **Get a free AI API key** (pick one):
   - **Gemini** (recommended): https://aistudio.google.com/apikey — free tier gives ~1,500 requests/day, more than enough
   - **OpenRouter**: https://openrouter.ai/keys — has free models, $0 cost

5. **Add your API key as a GitHub secret**:
   - Go to your repo → Settings → Secrets and variables → Actions
   - Add a new secret named `AI_API_KEY` with your key

6. **Enable GitHub Pages**:
   - Go to repo → Settings → Pages
   - Source: Deploy from branch
   - Branch: `main`, folder: `/docs`
   - Save

7. **Push your changes** — the workflow runs automatically every 2 weeks (or you can trigger it manually from the Actions tab)

## Output

Each issue includes:
- Article title and link
- Source publication
- Estimated reading time
- 1-2 sentence AI-generated reason for inclusion
- A short excerpt or quote

Past issues are archived at `/docs/archive/`.

## Email newsletter (optional)

To also send the reading list as an email:

1. Create a free [Buttondown](https://buttondown.com) account (free up to 100 subscribers, includes API access)
2. Get your API key from Buttondown settings → API
3. Add it as a GitHub secret: `BUTTONDOWN_API_KEY`
4. Set `send_email: true` in `profile.yaml`
5. The script will create a draft email automatically — review and send from Buttondown's dashboard

## Feedback loop

After each issue, you can edit `feedback.yaml` to mark articles as loved, okay, or not-for-me. The next run uses this feedback to improve recommendations.

## Customisation

- **Frequency**: Edit the cron schedule in `.github/workflows/biweekly.yml`
- **Number of articles**: Change `max_articles` in `profile.yaml`
- **Sources**: Add/remove feeds in `sources.yaml` anytime
- **Look**: Edit the Jinja2 templates in `templates/`

## Cost breakdown

| Component | Free tier | Your usage |
|-----------|-----------|------------|
| GitHub Actions | 2,000 min/month (private repo) or unlimited (public) | ~5 min per run |
| GitHub Pages | Free, unlimited project sites | 1 site |
| Gemini API | ~1,500 requests/day, ~250K tokens/min | ~1-2 requests per run |
| Buttondown | 100 subscribers, full API | 1 newsletter |

You will never hit any of these limits with a biweekly reading list.
