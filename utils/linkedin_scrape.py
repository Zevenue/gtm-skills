"""
LinkedIn Post Scraper via Apify
Pulls recent posts from a LinkedIn profile and stores them as structured markdown.

Usage:
    python utils/linkedin_scrape.py --profile-url https://www.linkedin.com/in/your-handle/ --count 10

Requires:
    - APIFY_API_KEY in .env
    - pip install requests python-dotenv
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = PROJECT_ROOT / "content" / "linkedin" / "posts"
IMAGES_DIR = PROJECT_ROOT / "content" / "linkedin" / "images"
INDEX_FILE = PROJECT_ROOT / "content" / "linkedin" / "index.md"

# Apify config - harvestapi/linkedin-profile-posts (no cookies needed)
ACTOR_ID = "harvestapi/linkedin-profile-posts"
APIFY_BASE = "https://api.apify.com/v2"

# Load env
load_dotenv(PROJECT_ROOT / ".env")
API_TOKEN = os.getenv("APIFY_API_KEY") or os.getenv("APIFY_API_TOKEN")


def slugify(text: str, max_len: int = 50) -> str:
    """Turn text into a filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len]


def start_actor_run(profile_url: str, count: int) -> str:
    """Start an Apify actor run and return the run ID."""
    actor_slug = ACTOR_ID.replace("/", "~")
    url = f"{APIFY_BASE}/acts/{actor_slug}/runs"
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "targetUrls": [profile_url],
        "maxPosts": count,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    run_id = data["data"]["id"]
    print(f"Started Apify run: {run_id}")
    return run_id


def wait_for_run(run_id: str, timeout_secs: int = 300) -> dict:
    """Poll until the actor run finishes."""
    url = f"{APIFY_BASE}/actor-runs/{run_id}"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    start = time.time()
    while time.time() - start < timeout_secs:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        run_data = resp.json()["data"]
        status = run_data.get("status")
        print(f"  Status: {status}")
        if status == "SUCCEEDED":
            return run_data
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            print(f"Run failed with status: {status}", file=sys.stderr)
            sys.exit(1)
        time.sleep(5)
    print("Timed out waiting for Apify run", file=sys.stderr)
    sys.exit(1)


def fetch_dataset(dataset_id: str) -> list:
    """Fetch results from the actor's default dataset."""
    url = f"{APIFY_BASE}/datasets/{dataset_id}/items"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    resp = requests.get(url, headers=headers, params={"format": "json"}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def download_image(image_url: str, filename: str) -> str | None:
    """Download an image and return the local relative path."""
    try:
        resp = requests.get(image_url, timeout=30, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "png" in content_type:
            ext = ".png"
        elif "gif" in content_type:
            ext = ".gif"
        elif "webp" in content_type:
            ext = ".webp"
        else:
            ext = ".jpg"
        filepath = IMAGES_DIR / f"{filename}{ext}"
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return str(filepath.relative_to(PROJECT_ROOT))
    except Exception as e:
        print(f"  Warning: failed to download image {image_url}: {e}", file=sys.stderr)
        return None


def parse_post_date(post: dict) -> str:
    """Extract date from harvestapi schema: postedAt.date or postedAt string."""
    posted_at = post.get("postedAt")
    if isinstance(posted_at, dict):
        # harvestapi returns {timestamp, date}
        date_str = posted_at.get("date", "")
        if date_str:
            for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
                try:
                    return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    continue
        ts = posted_at.get("timestamp")
        if ts:
            try:
                return datetime.fromtimestamp(int(ts) / 1000).strftime("%Y-%m-%d")
            except (ValueError, TypeError, OSError):
                pass
    elif isinstance(posted_at, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
            try:
                return datetime.strptime(posted_at, fmt).strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                continue
    return datetime.now().strftime("%Y-%m-%d")


def extract_text(post: dict) -> str:
    """Extract post text - harvestapi uses 'content' field."""
    for field in ("content", "text", "postText", "body", "commentary"):
        val = post.get(field)
        if val and isinstance(val, str) and len(val) > 5:
            return val.strip()
    return ""


def extract_images(post: dict) -> list:
    """Extract image URLs - harvestapi uses 'postImages' array."""
    urls = []
    # harvestapi schema: postImages[]
    post_images = post.get("postImages", [])
    if isinstance(post_images, list):
        for img in post_images:
            if isinstance(img, str) and img.startswith("http"):
                urls.append(img)
            elif isinstance(img, dict):
                for f in ("url", "originalUrl", "imageUrl"):
                    u = img.get(f)
                    if u and isinstance(u, str) and u.startswith("http"):
                        urls.append(u)
                        break
    # Fallback: check other common fields
    for field in ("imageUrl", "image", "imageUrls", "images", "mediaUrl"):
        val = post.get(field)
        if isinstance(val, str) and val.startswith("http") and val not in urls:
            urls.append(val)
        elif isinstance(val, list):
            for u in val:
                if isinstance(u, str) and u.startswith("http") and u not in urls:
                    urls.append(u)
    # Document cover pages
    doc = post.get("document", {})
    if isinstance(doc, dict):
        pages = doc.get("coverPages", [])
        if isinstance(pages, list):
            for p in pages:
                if isinstance(p, str) and p.startswith("http") and p not in urls:
                    urls.append(p)
    return urls


def detect_post_type(post: dict, images: list) -> str:
    """Detect post type from harvestapi 'type' field or infer from content."""
    ptype = post.get("type", "").lower()
    if ptype and ptype in ("video", "article", "document", "carousel", "poll", "repost"):
        return ptype
    if post.get("document"):
        return "document"
    if len(images) > 1:
        return "carousel"
    if images:
        return "image"
    return "text"


def extract_engagement(post: dict) -> dict:
    """Pull engagement - harvestapi nests under 'engagement' object."""
    result = {}
    eng = post.get("engagement", {})
    if isinstance(eng, dict):
        for key in ("likes", "comments", "shares"):
            val = eng.get(key)
            if val is not None and isinstance(val, (int, float)):
                result[key] = int(val)
        return result
    # Fallback: flat fields
    for key, fields in {
        "likes": ("numLikes", "likes", "likeCount", "reactionCount"),
        "comments": ("numComments", "comments", "commentCount"),
        "shares": ("numReposts", "reposts", "repostCount", "shareCount", "shares"),
    }.items():
        for f in fields:
            val = post.get(f)
            if val is not None and isinstance(val, (int, float)):
                result[key] = int(val)
                break
    return result


def save_post(post: dict, idx: int) -> Path | None:
    """Process a single post and save as markdown."""
    text = extract_text(post)
    if not text:
        print(f"  Skipping post {idx} - no text content")
        return None

    date = parse_post_date(post)
    first_line = text.split("\n")[0][:60]
    slug = slugify(first_line) or f"post-{idx}"
    filename = f"{date}-{slug}.md"
    filepath = POSTS_DIR / filename

    # Download images
    image_urls = extract_images(post)
    local_images = []
    for i, img_url in enumerate(image_urls):
        img_name = f"{date}-{slug}-{i}" if len(image_urls) > 1 else f"{date}-{slug}"
        local_path = download_image(img_url, img_name)
        if local_path:
            local_images.append(local_path)

    post_type = detect_post_type(post, image_urls)
    engagement = extract_engagement(post)
    post_url = post.get("linkedinUrl") or post.get("postUrl") or post.get("url") or ""

    # Build frontmatter
    fm = ["---", f"date: {date}", "platform: linkedin", f"type: {post_type}"]
    if post_url:
        fm.append(f"url: {post_url}")
    if engagement:
        eng_str = ", ".join(f"{k}: {v}" for k, v in engagement.items())
        fm.append(f"engagement: {{{eng_str}}}")
    if local_images:
        fm.append(f"images: {json.dumps(local_images)}")
    fm.append("repurposed: false")
    fm.append("---")

    # Build content
    parts = ["\n".join(fm), "", text]
    if local_images:
        parts.append("")
        parts.append("## Images")
        for img in local_images:
            parts.append(f"![post image](../../{img})")

    filepath.write_text("\n".join(parts), encoding="utf-8")
    print(f"  Saved: {filename}")
    return filepath


def build_index(posts_dir: Path) -> None:
    """Rebuild the index.md file listing all saved posts."""
    post_files = sorted(posts_dir.glob("*.md"), reverse=True)
    lines = [
        "# LinkedIn Posts Archive",
        "",
        f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        f"*Total posts: {len(post_files)}*",
        "",
        "| Date | Type | Preview | Repurposed |",
        "|------|------|---------|------------|",
    ]
    for pf in post_files:
        content = pf.read_text(encoding="utf-8")
        date = ptype = ""
        repurposed = "No"
        for line in content.split("\n"):
            if line.startswith("date:"):
                date = line.split(":", 1)[1].strip()
            elif line.startswith("type:"):
                ptype = line.split(":", 1)[1].strip()
            elif line.startswith("repurposed:") and "true" in line:
                repurposed = "Yes"
        # Get first line of actual content (after frontmatter)
        in_fm = False
        preview = ""
        for line in content.split("\n"):
            if line.strip() == "---":
                in_fm = not in_fm
                continue
            if not in_fm and line.strip() and not line.startswith("#"):
                preview = line.strip()[:80]
                break
        lines.append(f"| {date} | {ptype} | [{preview}]({pf.name}) | {repurposed} |")

    INDEX_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nIndex updated: {INDEX_FILE.relative_to(PROJECT_ROOT)}")


def main():
    parser = argparse.ArgumentParser(description="Scrape LinkedIn posts via Apify")
    parser.add_argument("--profile-url", required=True, help="LinkedIn profile URL")
    parser.add_argument("--count", type=int, default=10, help="Number of recent posts to fetch")
    parser.add_argument("--raw-output", help="Also save raw JSON to this path")
    args = parser.parse_args()

    if not API_TOKEN:
        print("Error: APIFY_API_KEY not found in .env", file=sys.stderr)
        print("Add it to your .env file: APIFY_API_KEY=your_token_here", file=sys.stderr)
        sys.exit(1)

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Scraping {args.count} posts from {args.profile_url}")

    run_id = start_actor_run(args.profile_url, args.count)
    run_data = wait_for_run(run_id)

    dataset_id = run_data["defaultDatasetId"]
    posts = fetch_dataset(dataset_id)
    print(f"\nFetched {len(posts)} posts")

    if args.raw_output:
        raw_path = Path(args.raw_output)
        raw_path.write_text(json.dumps(posts, indent=2, default=str), encoding="utf-8")
        print(f"Raw JSON saved to {args.raw_output}")

    saved = 0
    for i, post in enumerate(posts):
        result = save_post(post, i)
        if result:
            saved += 1

    build_index(POSTS_DIR)
    print(f"\nDone. {saved} posts saved to content/linkedin/posts/")


if __name__ == "__main__":
    main()
