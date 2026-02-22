#!/usr/bin/env python3
"""
Fetch the latest posts from @pilarvahey on Instagram and update the
Instagram grid section in www.pilarvahey.com/index.html.

Usage:
    pip install instaloader
    python scripts/update_instagram.py

For authenticated access (avoids rate limiting), set env vars:
    INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD
"""

import instaloader
import os
import re
import shutil
import html
from pathlib import Path

PROFILE_NAME = "pilarvahey"
POSTS_TO_SHOW = 9
IMAGES_DIR = Path("www.pilarvahey.com/ig-images")
HTML_FILE = Path("www.pilarvahey.com/index.html")
GRID_START = "<!-- INSTAGRAM_GRID_START -->"
GRID_END = "<!-- INSTAGRAM_GRID_END -->"


def make_slide(shortcode, img_src, caption, width=1440, height=1800):
    safe_caption = html.escape(caption[:300] if caption else "")
    return f"""        <div class="slide" data-type="image" data-animation-role="image">
          <div class="margin-wrapper">
            <a href="https://www.instagram.com/p/{shortcode}/" target="_blank"
               aria-label="{safe_caption}"
               class="image-slide-anchor content-fill">
              <noscript><img src="{img_src}" alt="{safe_caption}" /></noscript>
              <img class="thumb-image" elementtiming="system-gallery-block-grid"
                   src="{img_src}"
                   data-image="{img_src}"
                   data-image-dimensions="{width}x{height}"
                   data-image-focal-point="0.5,0.5"
                   alt="{safe_caption}"
                   data-load="true"
                   data-type="image" />
            </a>
          </div>
        </div>"""


def build_grid_html(slides_html):
    return f"""{GRID_START}
<div class="sqs-gallery-container sqs-gallery-block-grid sqs-gallery-aspect-ratio-square sqs-gallery-thumbnails-per-row-3 sqs-gallery-block-show-meta block-animation-none clear"
     data-async-rendering-enabled="true">
  <div class="sqs-gallery">
{slides_html}
  </div>
</div>
<style type="text/css" id="design-grid-css">
.sqs-gallery-block-grid .sqs-gallery-design-grid {{ margin-right: -17px; }}
.sqs-gallery-block-grid .sqs-gallery-design-grid-slide .margin-wrapper {{ margin-right: 17px; margin-bottom: 17px; }}
</style>
{GRID_END}"""


def download_post_image(loader, post, images_dir):
    """Download the post display image into images_dir, return relative path."""
    images_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{post.shortcode}_image-asset.jpeg"
    dest = images_dir / filename

    if dest.exists():
        print(f"  Already have {filename}, skipping download.")
        return f"ig-images/{filename}"

    # Download into a temp directory then move the jpg/png
    tmp_dir = images_dir / f"_tmp_{post.shortcode}"
    try:
        loader.download_post(post, target=tmp_dir)
        # Find the downloaded image (jpg or png)
        for ext in ("jpg", "jpeg", "png", "webp"):
            candidates = list(tmp_dir.glob(f"*.{ext}"))
            if candidates:
                shutil.move(str(candidates[0]), str(dest))
                break
        else:
            print(f"  Warning: no image found for {post.shortcode}")
            return None
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"  Downloaded {filename}")
    return f"ig-images/{filename}"


def main():
    loader = instaloader.Instaloader(
        download_pictures=True,
        download_videos=False,
        download_video_thumbnails=True,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
        quiet=True,
    )

    # Optional: log in to avoid rate limits
    username = os.environ.get("INSTAGRAM_USERNAME")
    password = os.environ.get("INSTAGRAM_PASSWORD")
    if username and password:
        try:
            loader.login(username, password)
            print(f"Logged in as {username}")
        except Exception as e:
            print(f"Login failed ({e}), continuing anonymously")

    print(f"Fetching latest {POSTS_TO_SHOW} posts from @{PROFILE_NAME}...")
    profile = instaloader.Profile.from_username(loader.context, PROFILE_NAME)

    slides = []
    for post in profile.get_posts():
        if len(slides) >= POSTS_TO_SHOW:
            break
        print(f"  Post {post.shortcode}: {(post.caption or '')[:60]!r}")
        img_src = download_post_image(loader, post, IMAGES_DIR)
        if img_src is None:
            continue
        slides.append(make_slide(post.shortcode, img_src, post.caption or ""))

    if not slides:
        print("No posts fetched — aborting HTML update.")
        return

    slides_html = "\n\n".join(slides)
    grid_html = build_grid_html(slides_html)

    content = HTML_FILE.read_text(encoding="utf-8")
    if GRID_START not in content or GRID_END not in content:
        print(f"ERROR: Markers '{GRID_START}' / '{GRID_END}' not found in {HTML_FILE}.")
        print("Add them manually around the Instagram grid section first.")
        return

    updated = re.sub(
        re.escape(GRID_START) + r".*?" + re.escape(GRID_END),
        grid_html,
        content,
        flags=re.DOTALL,
    )

    HTML_FILE.write_text(updated, encoding="utf-8")
    print(f"Updated {HTML_FILE} with {len(slides)} posts.")


if __name__ == "__main__":
    main()
