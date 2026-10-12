# The Complete Guide: Building Your Biweekly AI-Curated Reading List

A step-by-step guide to creating a free, automated reading list of in-depth articles, essays, and long reads — curated by AI to match your interests, published to a website, and optionally sent as an email newsletter.

---

## What You'll Get

A biweekly reading list that:
- Pulls articles from publications you choose (via RSS feeds)
- Uses AI to rank and select the best 3-7 articles based on your personal interest profile
- Publishes automatically to a free website (GitHub Pages)
- Optionally sends as an email newsletter (via Buttondown)
- Learns from your feedback over time

**Total cost: $0** using free tiers.

---

## Architecture Overview

```
Your chosen RSS feeds (sources.yaml)
         ↓
GitHub Actions (free, runs every 2 weeks automatically)
         ↓
Python script fetches recent articles from feeds
         ↓
AI (Gemini free tier) ranks articles against your profile
         ↓
Top picks published to GitHub Pages (free website)
         ↓
Optional: Buttondown API creates email draft for you to review and send
```

---

## Step-by-Step Setup

### Step 1: Create a GitHub Account (Free)

If you don't have one, sign up at [github.com](https://github.com). A free account gives you:
- Private repositories with 2,000 GitHub Actions minutes per month ([GitHub Docs](https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions))
- Public repositories with unlimited Actions minutes
- Free GitHub Pages hosting for unlimited project sites ([GitHub Pages Docs](https://pages.github.com/))

A biweekly run uses about 3-5 minutes. You'll never approach the limit.

### Step 2: Create a New Repository

1. Go to [github.com/new](https://github.com/new)
2. Name it something like `reading-list`
3. Set it to Public (this gives you unlimited free Actions minutes and free Pages hosting)
4. Check "Add a README file"
5. Click "Create repository"

### Step 3: Upload the Project Files

Take the files from this project template and add them to your repository. You can either:

**Option A — Upload via the GitHub web interface:**
- Click "Add file" → "Upload files" in your repo
- Drag all the project files into the upload area
- Commit changes

**Option B — Clone and push (if you have Git installed):**
```bash
git clone https://github.com/YOUR-USERNAME/reading-list.git
# Copy the project files into the cloned folder
cd reading-list
git add .
git commit -m "Initial reading list setup"
git push
```

The key files to include:
- `curator.py` — the main script that does everything
- `sources.yaml` — your RSS feed list
- `profile.yaml` — your interest profile
- `feedback.yaml` — for improving recommendations over time
- `.github/workflows/biweekly.yml` — the automated schedule
- `docs/index.html` — placeholder for your published page

### Step 4: Add Your RSS Feeds (sources.yaml)

Edit `sources.yaml` to list the publications you want articles from. Most publications have RSS feeds — search "[publication name] RSS feed" to find them.

The file is pre-populated with quality sources (Aeon, The Atlantic, The New Yorker, Longreads, Ars Technica, Stratechery, Paul Graham). Add or remove as you like.

Each entry has:
- `name`: publication name
- `feed`: the RSS feed URL
- `topics`: tags that help the AI understand what the source covers
- `weight`: a multiplier (1.0 = normal, 1.3 = boost this source slightly)

### Step 5: Define Your Interests (profile.yaml)

Edit `profile.yaml` to tell the AI what you love. This is the heart of the "recommendation system." Be specific:

- **description**: A paragraph about what kind of reader you are
- **topics_liked**: Topics you want to see
- **topics_avoided**: Topics to filter out
- **preferences**: Preferred length, depth, tone
- **loved_examples**: Describe articles you've genuinely enjoyed — the AI uses these as reference points
- **max_articles**: How many articles per issue (3-7 is ideal)

The more specific and honest you are, the better the curation.

### Step 6: Get a Free AI API Key

The script uses AI to rank articles. You have two free options:

**Option A — Google Gemini (Recommended):**
1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with a Google account
3. Click "Create API key"
4. Copy the key

Gemini's free tier gives you approximately 1,500 requests per day and 250,000 tokens per minute on the Flash models — far more than you need for a biweekly run ([UsageBox](https://usagebox.com/articles/gemini-api-billing-free-tier-confusion)).

Important: Do NOT enable billing on your Google Cloud project — if you do, the free tier disappears and every call becomes billable.

**Option B — OpenRouter (Free models):**
1. Go to [openrouter.ai/keys](https://openrouter.ai/keys)
2. Sign up and create a key
3. Copy the key
4. In your GitHub repository, add a secret named `AI_PROVIDER` with value `openrouter`

OpenRouter offers several free models, including Google Gemini Flash Lite, with $0 cost per million tokens ([OpenRouter](https://openrouter.ai/models)).

### Step 7: Add Your API Key to GitHub

1. Go to your repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `AI_API_KEY`
4. Value: paste your API key
5. Click "Add secret"

If using OpenRouter, also add:
- Name: `AI_PROVIDER`, Value: `openrouter`

Your key is encrypted and never visible to anyone but you.

### Step 8: Enable GitHub Pages

1. Go to your repository → Settings → Pages
2. Under "Source", select "Deploy from branch"
3. Branch: `main`, folder: `/docs`
4. Click Save

Your site will be available at `https://YOUR-USERNAME.github.io/reading-list/` within a few minutes.

### Step 9: Test the Workflow

1. Go to your repository → Actions tab
2. Click on "Biweekly Reading List" workflow
3. Click "Run workflow" → "Run workflow"
4. Wait 1-2 minutes for it to complete
5. Check your Pages URL — the reading list should be live

The workflow runs automatically on the 1st and 15th of each month at 09:00 UTC (10:00 AM London time during BST, 09:00 AM during GMT). You can edit the schedule in `.github/workflows/biweekly.yml`.

### Step 10: Set Up Email Newsletter (Optional)

If you want the reading list emailed to you (or others), use Buttondown:

1. Create a free account at [buttondown.com](https://buttondown.com)
   - Free for up to 100 subscribers
   - Includes full REST API access on the free plan ([Buttondown](https://buttondown.com/features/api), [Buttondown Pricing](https://buttondown.com/pricing))
   - No credit card required

2. Get your API key:
   - Go to Buttondown settings → API section
   - Create an API key

3. Add to GitHub secrets:
   - Name: `BUTTONDOWN_API_KEY`, Value: your Buttondown key

4. Edit `profile.yaml`:
   - Change `send_email: false` to `send_email: true`

5. The script will create a draft email in your Buttondown account each run. Review it and click send.

Buttondown handles unsubscribe links, subscriber management, and deliverability automatically — you don't need to worry about email compliance.

### Step 11: Improve Over Time (feedback.yaml)

After each issue, edit `feedback.yaml` to note which articles you loved, which were just okay, and which weren't for you. The AI reads this on the next run and adjusts its selections.

```yaml
loved:
  - https://example.com/article-you-loved

okay:
  - https://example.com/article-that-was-fine

not_for_me:
  - https://example.com/article-you-didnt-enjoy
```

Over time, the AI learns your taste and the recommendations get sharper.

---

## Customisation

### Change the schedule

Edit `.github/workflows/biweekly.yml` and modify the cron line:
```yaml
# Current: 1st and 15th at 09:00 UTC
- cron: "0 9 1,15 * *"

# Weekly (every Sunday at 09:00 UTC)
- cron: "0 9 * * 0"

# Monthly (1st of each month at 09:00 UTC)
- cron: "0 9 1 * *"
```

Cron uses UTC. London is UTC+1 (BST) in summer and UTC+0 (GMT) in winter.

### Change the number of articles

Edit `profile.yaml`:
```yaml
max_articles: 7  # default is 5
```

### Add or remove sources anytime

Just edit `sources.yaml` and push to GitHub. The next run picks up the changes automatically.

### Change the AI model

In `curator.py`, the `call_gemini()` function uses `gemini-2.5-flash`. You can change the model name to any Gemini model that has a free tier. For OpenRouter, edit `call_openrouter()` and change the model string.

### Restyle the page

The HTML template is embedded in `curator.py` in the `generate_html()` function. Edit the CSS or HTML structure to match your taste.

---

## Cost Summary

| Component | Free tier | Your biweekly usage | Cost |
|-----------|-----------|---------------------|------|
| GitHub Actions | 2,000 min/month (private) / unlimited (public) | ~5 min per run | $0 |
| GitHub Pages | Free, unlimited project sites | 1 site | $0 |
| Gemini API | ~1,500 requests/day, ~250K tokens/min | ~1-2 requests per run | $0 |
| Buttondown | 100 subscribers, full API | 1 newsletter | $0 |

Even if you scale up to weekly runs with 20+ sources, you will stay well within all free tiers.

---

## Alternative: No-Code Quick Start

If setting up the full system feels like too much, here's the simplest possible version:

1. **Use an RSS reader** (Feedly free tier or Inoreader free tier) to follow your favourite publications
2. **Every two weeks**, skim through and pick 3-5 articles
3. **Paste them** into a free [Substack](https://substack.com) or [Buttondown](https://buttondown.com) newsletter

This gives you the same result (curated reading list emailed to you) with zero setup, but without the AI curation or automation. You can always upgrade to the automated system later.

---

## Troubleshooting

**No articles showing up?**
- Check that your RSS feed URLs are correct (open them in a browser — you should see XML)
- Some sites may block automated fetching. Try alternative feed URLs.
- Increase `DAYS_WINDOW` in `curator.py` if publications post less frequently.

**AI ranking not working?**
- Check that `AI_API_KEY` secret is set correctly in GitHub
- Check Actions logs for API errors
- The script falls back to heuristic ranking if the AI fails, so you'll still get results

**GitHub Pages not updating?**
- Make sure Pages is configured to deploy from `main` branch, `/docs` folder
- Check the Actions tab for any deployment errors
- It can take 1-2 minutes for changes to propagate

**Email not sending?**
- Verify `BUTTONDOWN_API_KEY` is set
- Set `send_email: true` in `profile.yaml`
- Check Buttondown's dashboard for the draft email
