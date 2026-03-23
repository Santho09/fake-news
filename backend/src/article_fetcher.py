"""
Fetch article text from a URL using requests and BeautifulSoup.
Used for URL input in fake news detection.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple


def fetch_article_text(url: str, timeout: int = 15) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch and extract main article text from a URL.
    Returns (text, error_message). If successful, error_message is None.
    """
    url = (url or "").strip()
    if not url:
        return None, "URL is empty."

    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url

    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as e:
        return None, f"Missing dependency for URL fetch: {e}"

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        return None, f"Could not fetch URL: {str(e)[:120]}"

    try:
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        article = soup.find("article") or soup.find("main") or soup.find(class_=re.compile(r"article|post|content|entry", re.I))
        root = article if article else soup.body or soup

        if root is None:
            return None, "No readable content found."

        text = root.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        text = text[:150000]

        if len(text) < 50:
            return None, "Extracted text is too short. The page may not be a standard article."

        return text, None
    except Exception as e:
        return None, f"Error parsing page: {str(e)[:80]}"
