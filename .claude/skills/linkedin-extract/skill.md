# LinkedIn Post Extractor

You extract recent LinkedIn posts (text + images) from a given LinkedIn profile using Apify and store them locally for later repurposing into blogs and other content. Designed primarily for archiving your own posts.

## How to invoke

The user says something like:
- "pull my latest linkedin posts"
- "scrape my last 10 linkedin posts"
- "extract linkedin posts"

Parameters:
1. **Profile URL** (required on first use; save as `LINKEDIN_DEFAULT_PROFILE_URL` in `.env` to make it the default afterward)
2. **Count** (optional) - number of posts to pull. Default: 10

## Prerequisites

- `APIFY_API_TOKEN` must be set in `.env`
- Python packages: `requests`, `python-dotenv` (install if missing)

## Process

### Step 1: Check prerequisites

1. Read `.env` and confirm `APIFY_API_TOKEN` is present. If not, tell the user to add it:
   ```
   Add to .env: APIFY_API_TOKEN=your_token_here
   Get your token at https://console.apify.com/account/integrations
   ```
2. Check that `requests` and `python-dotenv` are installed. If not, run:
   ```
   pip install requests python-dotenv
   ```

### Step 2: Run the scraper

Run the scrape script:
```bash
python utils/linkedin_scrape.py \
  --profile-url "{profile_url}" \
  --count {count} \
  --raw-output content/linkedin/raw-latest.json
```

If the user provides a different profile URL or count, substitute accordingly.

The script will:
- Start an Apify actor run using the LinkedIn Profile Posts Scraper
- Wait for completion (up to 5 minutes)
- Download post text + images
- Save each post as a markdown file in `content/linkedin/posts/`
- Save images to `content/linkedin/images/`
- Update `content/linkedin/index.md` with a table of all archived posts

### Step 3: Verify and report

After the script completes:

1. Read `content/linkedin/index.md` to confirm what was saved
2. Spot-check 1-2 post files to verify content quality
3. Report to the user:
   - How many posts were saved
   - Date range covered
   - Any posts that were skipped (no text content)
   - Any images that failed to download

### Step 4: Handle actor mismatch (if needed)

Apify actors vary in their output schema. If the script saves posts but they have missing text or images, check `content/linkedin/raw-latest.json` to see the actual field names returned by the actor. Then update the field mappings in `utils/linkedin_scrape.py`:
- `extract_text()` - fields that contain post text
- `extract_images()` - fields that contain image URLs
- `parse_post_date()` - fields that contain the post date
- `extract_engagement()` - fields with likes/comments/reposts

Re-run after fixing.

## Output structure

```
content/linkedin/
  index.md              # Table of all archived posts
  raw-latest.json       # Raw Apify JSON (for debugging)
  posts/
    2026-03-20-the-best-outbound.md
    2026-03-15-clay-workflow-trick.md
    ...
  images/
    2026-03-20-the-best-outbound.jpg
    2026-03-15-clay-workflow-trick-0.jpg
    2026-03-15-clay-workflow-trick-1.jpg
    ...
```

Each post markdown file has this format:
```markdown
---
date: 2026-03-20
platform: linkedin
type: image
url: https://linkedin.com/feed/update/...
engagement: {likes: 142, comments: 23, reposts: 8}
images: ["content/linkedin/images/2026-03-20-the-best-outbound.jpg"]
repurposed: false
---

Post text content here...

## Images
![post image](../../content/linkedin/images/2026-03-20-the-best-outbound.jpg)
```

The `repurposed: false` flag lets the blog repurposing skill know which posts haven't been turned into blogs yet.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `APIFY_API_TOKEN not found` | Add token to `.env` file |
| Actor run fails or times out | Check Apify console for the run details. May need to increase timeout or check actor availability |
| Posts saved but no text | Check `raw-latest.json` for actual field names, update `extract_text()` in the script |
| Images not downloading | LinkedIn CDN URLs may expire. Re-run sooner after scraping. Check `raw-latest.json` for image URLs |
| Wrong actor / schema changed | The script uses `apimaestro/linkedin-profile-posts-scraper`. If deprecated, find a replacement on Apify Store and update `ACTOR_ID` in the script |

## What this skill does NOT do

- **Does not repurpose posts into blogs.** That's a separate skill. This one archives the raw LinkedIn content.
- **Does not post to LinkedIn.** Read-only extraction.
- **Does not scrape other people's profiles** without explicit instruction. Best used for archiving your own content; for competitive/prospect research, use the `prospect-posts` skill instead.
- **Does not handle LinkedIn authentication.** Apify handles session/cookie management on their infra.
