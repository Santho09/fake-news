"""
Fetch video title and description from YouTube using the Data API v3.
Used for YouTube video URL input in fake news detection.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional, Tuple

# Video ID is 11 alphanumeric, dash, underscore
_VIDEO_ID_PATTERN = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})"
)


def extract_video_id(url_or_id: str) -> Optional[str]:
    """Extract YouTube video ID from URL or return as-is if 11 chars."""
    s = (url_or_id or "").strip()
    if not s:
        return None
    m = _VIDEO_ID_PATTERN.search(s)
    if m:
        return m.group(1)
    if re.match(r"^[a-zA-Z0-9_-]{11}$", s):
        return s
    return None


def fetch_video_text(
    url_or_id: str,
    api_key: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """
    Fetch video title and description via YouTube Data API v3.
    Returns (text, error, meta). text = title + description combined.
    """
    video_id = extract_video_id(url_or_id)
    if not video_id:
        return None, "Invalid YouTube URL or video ID.", {}

    key = (
        (api_key or os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_FACT_CHECK_API_KEY") or "").strip()
    )
    if not key:
        return None, "YouTube API key not configured. Set YOUTUBE_API_KEY in backend/.env (or enable YouTube Data API v3 and use GOOGLE_FACT_CHECK_API_KEY if both APIs are on the same project).", {}

    try:
        import requests
    except ImportError:
        return None, "requests library required for YouTube fetch.", {}

    url = (
        "https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet&id={video_id}&key={key}"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        return None, f"YouTube API request failed: {str(e)[:100]}", {}

    data = r.json()
    if "error" in data:
        err = data["error"]
        code = err.get("code")
        msg = ""
        for item in err.get("errors", []):
            reason = item.get("reason", "")
            m = item.get("message", "")
            if "quotaExceeded" in reason:
                msg = "YouTube API quota exceeded. Try again later."
                break
            if "forbidden" in reason.lower() or "invalid" in reason.lower():
                msg = m or "Video not available or API key lacks permission."
                break
        if not msg:
            msg = err.get("message", "YouTube API error.")
        return None, msg[:120], {}

    items = data.get("items") or []
    if not items:
        return None, "Video not found or is private.", {}

    snippet = items[0].get("snippet") or {}
    title = (snippet.get("title") or "").strip()
    desc = (snippet.get("description") or "").strip()

    # Description can have newlines; normalize
    desc_clean = re.sub(r"\s+", " ", desc).strip()
    combined = f"{title}\n\n{desc_clean}".strip() if desc_clean else title

    if len(combined) < 20:
        return None, "Video has insufficient title/description text to analyze.", {}

    meta: Dict[str, Any] = {
        "video_id": video_id,
        "video_title": title,
        "channel_title": (snippet.get("channelTitle") or "").strip(),
        "published_at": snippet.get("publishedAt"),
    }

    return combined, None, meta
