"""
Parse RSS/Atom feeds and extract article text from the latest entry.
Uses requests + feedparser; falls back to feed summary if page fetch fails.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

_FEED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*;q=0.8",
}


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    try:
        from bs4 import BeautifulSoup

        return BeautifulSoup(raw, "html.parser").get_text(separator=" ", strip=True)
    except Exception:
        pass
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)).strip()


def _entry_link(entry: Dict[str, Any]) -> str:
    link = (entry.get("link") or "").strip()
    if link:
        return link
    for item in entry.get("links") or []:
        href = (item.get("href") or "").strip()
        rel = (item.get("rel") or "alternate")
        if href and rel in ("alternate", "self"):
            return href
    if entry.get("links"):
        href = (entry["links"][0].get("href") or "").strip()
        if href:
            return href
    return ""


def text_from_rss_feed(feed_url: str, timeout: int = 20) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """
    Fetch the newest feed entry and return article text.
    Returns (text, error, meta). meta includes feed_title, item_title, item_link, text_source.
    """
    feed_url = (feed_url or "").strip()
    if not feed_url:
        return None, "RSS feed URL is empty.", {}

    if not re.match(r"^https?://", feed_url, re.IGNORECASE):
        feed_url = "https://" + feed_url

    try:
        import feedparser
        import requests
    except ImportError as e:
        return None, f"RSS support missing dependency: {e}", {}

    try:
        r = requests.get(feed_url, headers=_FEED_HEADERS, timeout=timeout)
        r.raise_for_status()
    except Exception as e:
        return None, f"Could not fetch feed: {str(e)[:100]}", {}

    parsed = feedparser.parse(r.content)
    if not parsed.entries:
        msg = "Feed has no entries or could not be parsed."
        if getattr(parsed, "bozo_exception", None):
            msg = f"Invalid feed: {parsed.bozo_exception}"
        return None, msg, {}

    entry = parsed.entries[0]
    title = (entry.get("title") or "").strip()
    link = _entry_link(entry)
    summary_raw = entry.get("summary") or entry.get("description") or ""
    summary_text = _strip_html(summary_raw)
    summary_text = re.sub(r"\s+", " ", summary_text).strip()

    feed_title = (parsed.feed.get("title") or "").strip()

    meta: Dict[str, Any] = {
        "feed_title": feed_title,
        "item_title": title,
        "item_link": link,
    }

    article_text: Optional[str] = None
    fetch_err: Optional[str] = None
    if link:
        from backend.src.article_fetcher import fetch_article_text

        article_text, fetch_err = fetch_article_text(link, timeout=timeout)

    if article_text and len(article_text.strip()) >= 50:
        meta["text_source"] = "article_page"
        return article_text.strip(), None, meta

    if summary_text and len(summary_text) >= 20:
        meta["text_source"] = "feed_summary"
        if fetch_err:
            meta["page_fetch_note"] = fetch_err[:120]
        return summary_text, None, meta

    err = fetch_err or "RSS entry has no usable summary and article page could not be read."
    return None, err, meta
