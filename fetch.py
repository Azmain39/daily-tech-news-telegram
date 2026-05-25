"""
fetch.py — Pull RSS entries from the last 24h and extract clean full text.

Pipeline step: Trusted RSS feeds -> fetch FULL article text.

Design notes:
- Primary: trafilatura full-text extraction from the article URL.
- Fallback: if the site is paywalled, blocks scrapers, or returns thin text,
  we use the RSS entry's own summary/description field. Major outlets (Reuters,
  NYT, Guardian, BBC …) include substantive summaries in their feed XML that
  do not require any additional HTTP request. This is the single biggest
  reliability improvement: we no longer discard an article simply because we
  cannot scrape its page.
- Discovery feeds (trusted=False) skip HTTP fetch entirely and use their RSS
  summary directly — they only matter for clustering, not for LLM input.
- Every network call is wrapped: a failure logs and continues, never crashes.
"""

import logging
import re
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests
import trafilatura

import config

log = logging.getLogger("fetch")

for _noisy in ("trafilatura", "trafilatura.core", "trafilatura.utils",
               "trafilatura.htmlprocessing", "urllib3", "charset_normalizer"):
    logging.getLogger(_noisy).setLevel(logging.ERROR)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _entry_datetime(entry):
    """Return a timezone-aware datetime for an RSS entry, or None."""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
            except Exception:
                continue
    return None


def _strip_html(raw):
    """Remove HTML tags and collapse whitespace."""
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(raw))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _get_rss_summary(entry):
    """
    Extract usable text from the RSS entry itself (no HTTP request needed).

    feedparser normalises content into several possible fields. We try them
    all and return the longest clean text that meets the minimum length.
    Returns None if nothing long enough is found.
    """
    candidates = []

    # 'content' is a list of dicts (can hold full article body in some feeds)
    for block in entry.get("content", []):
        candidates.append(_strip_html(block.get("value", "")))

    candidates.append(_strip_html(entry.get("summary", "")))
    candidates.append(_strip_html(entry.get("description", "")))

    best = max(candidates, key=len, default="")
    return best if len(best) >= config.MIN_RSS_TEXT_CHARS else None


def _extract_full_text(url):
    """
    Download a page and extract clean article body text. Returns None on failure.

    Handles HTTP 429: waits and retries once. A small delay before every
    request keeps us a polite, low-rate visitor.
    """
    html_text = None
    for attempt in range(1, 3):
        try:
            time.sleep(config.FETCH_DELAY_SECONDS)
            resp = requests.get(
                url,
                timeout=config.HTTP_TIMEOUT,
                headers={"User-Agent": config.USER_AGENT},
            )
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 5))
                wait = min(wait, 15)
                log.warning("Rate-limited (429) on %s — waiting %ds.", url, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            html_text = resp.text
            break
        except Exception as exc:
            log.warning("Could not download %s (%s)", url, exc)
            return None

    if html_text is None:
        log.warning("Giving up on %s after rate-limit retries.", url)
        return None

    try:
        text = trafilatura.extract(
            html_text,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
    except Exception as exc:
        log.warning("trafilatura failed on %s (%s)", url, exc)
        return None

    if not text or len(text.strip()) < 250:
        log.info("Thin/empty full-text extraction: %s", url)
        return None
    return text.strip()


# ---------------------------------------------------------------------------
# PUBLIC ENTRY POINT
# ---------------------------------------------------------------------------

def fetch_all_articles():
    """
    Read every configured feed and return a flat list of Article dicts:

        {
          "source_name": str, "trusted": bool, "source_score": int,
          "title": str, "url": str, "published": datetime,
          "text": str, "rss_fallback": bool,
        }

    Only articles from the last LOOKBACK_HOURS are returned.
    Articles where neither full-text extraction nor RSS summary produces
    enough text are skipped.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.LOOKBACK_HOURS)
    articles = []

    for feed in config.FEEDS:
        log.info("Reading feed: %s", feed["name"])
        try:
            parsed = feedparser.parse(feed["url"])
        except Exception as exc:
            log.warning("Feed parse failed for %s (%s)", feed["name"], exc)
            continue

        if parsed.bozo and not parsed.entries:
            log.warning("Feed unreadable or empty: %s", feed["name"])
            continue

        # Collect entries within the lookback window, sorted newest first.
        window_entries = []
        for entry in parsed.entries:
            published = _entry_datetime(entry)
            if published is None:
                published = datetime.now(timezone.utc)
            if published >= cutoff:
                window_entries.append((published, entry))

        # Cap per-feed volume to keep the total run time within budget.
        window_entries.sort(key=lambda t: t[0], reverse=True)
        window_entries = window_entries[:config.MAX_ARTICLES_PER_FEED]

        for published, entry in window_entries:
            url = entry.get("link")
            title = (entry.get("title") or "").strip()
            if not url or not title:
                continue

            rss_fallback = False

            if not feed["trusted"]:
                # Discovery-only feeds: skip the HTTP round-trip entirely.
                # Their text is only used for clustering, not for LLM input.
                text = _get_rss_summary(entry)
                if text is None:
                    continue
                rss_fallback = True
            else:
                # Trusted feeds: try full extraction first, then RSS fallback.
                text = _extract_full_text(url)
                if text is None:
                    rss_text = _get_rss_summary(entry)
                    if rss_text:
                        text = rss_text
                        rss_fallback = True
                        log.info("RSS-summary fallback used: %s", title[:60])
                    else:
                        log.info("No usable text for: %s", title[:60])
                        continue

            articles.append({
                "source_name":  feed["name"],
                "trusted":      feed["trusted"],
                "source_score": feed["score"],
                "title":        title,
                "url":          url,
                "published":    published,
                "text":         text,
                "rss_fallback": rss_fallback,
            })

    log.info("Fetched %d usable articles total.", len(articles))
    return articles
