"""
fetch.py — Pull RSS entries from the last 24h and extract clean full text.

Pipeline step: Trusted RSS feeds -> fetch FULL article text.

Design notes:
- We use ONLY trafilatura for extraction (newspaper3k is outdated/fragile).
- Any article whose full body cannot be extracted is SKIPPED, not guessed.
- Every network call is wrapped: a failure logs and continues, never crashes.
"""

import logging
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests
import trafilatura

import config

log = logging.getLogger("fetch")

# trafilatura and its dependencies emit very chatty messages like
# "discarding data: None" for every page they can't fully parse. These
# are harmless but flood the log and hide real problems. Raise their
# log level so only genuine errors get through.
for _noisy in ("trafilatura", "trafilatura.core", "trafilatura.utils",
               "trafilatura.htmlprocessing", "urllib3", "charset_normalizer"):
    logging.getLogger(_noisy).setLevel(logging.ERROR)


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


def _extract_full_text(url):
    """Download a page and extract clean article body text. None on failure.

    Handles HTTP 429 (Too Many Requests): if a site rate-limits us, we
    wait briefly and retry once before giving up. A small delay before
    every request keeps us a polite, low-rate visitor.
    """
    html_text = None
    for attempt in range(1, 3):  # at most 2 tries
        try:
            # Be a polite crawler — small pause before each request.
            time.sleep(config.FETCH_DELAY_SECONDS)
            resp = requests.get(
                url,
                timeout=config.HTTP_TIMEOUT,
                headers={"User-Agent": config.USER_AGENT},
            )
            if resp.status_code == 429:
                # Rate-limited. Honour Retry-After if the server sent one.
                wait = int(resp.headers.get("Retry-After", 5))
                wait = min(wait, 15)  # never stall the whole run too long
                log.warning("Rate-limited (429) on %s — waiting %ds.",
                            url, wait)
                time.sleep(wait)
                continue  # retry once
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
        # Too thin to summarize honestly -> skip.
        log.info("Skipping thin/empty extraction: %s", url)
        return None
    return text.strip()


def fetch_all_articles():
    """
    Read every configured feed and return a flat list of Article dicts:

        {
          "source_name": str, "trusted": bool, "source_score": int,
          "title": str, "url": str, "published": datetime, "text": str,
        }

    Only articles from the last LOOKBACK_HOURS with extractable full text
    are returned.
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

        for entry in parsed.entries:
            published = _entry_datetime(entry)
            # If no date, keep it but treat as 'now' so it isn't wrongly dropped.
            if published is None:
                published = datetime.now(timezone.utc)
            if published < cutoff:
                continue

            url = entry.get("link")
            title = (entry.get("title") or "").strip()
            if not url or not title:
                continue

            text = _extract_full_text(url)
            if text is None:
                continue  # cannot verify -> skip

            articles.append({
                "source_name": feed["name"],
                "trusted": feed["trusted"],
                "source_score": feed["score"],
                "title": title,
                "url": url,
                "published": published,
                "text": text,
            })

    log.info("Fetched %d usable articles total.", len(articles))
    return articles