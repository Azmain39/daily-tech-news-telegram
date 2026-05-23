"""
rank.py — Cross-verification, scoring, and selection of top stories.

Pipeline steps: authenticity / cross-verification -> ranking -> pick top 1-2.

Authenticity rules (the heart of "no fake news"):
- A story covered by 2+ INDEPENDENT trusted outlets is "verified".
- A single-trusted-source story is allowed but flagged for manual review.
- A story seen ONLY in the discovery feed (no trusted outlet) is DROPPED.
"""

import logging
import re
from datetime import datetime, timezone

import config

log = logging.getLogger("rank")


def _trusted_sources(cluster):
    """Set of distinct trusted outlet names covering this story."""
    return {a["source_name"] for a in cluster if a["trusted"]}


def _is_clickbait(title):
    """True if the title matches a known clickbait pattern."""
    low = title.lower()
    for pat in config.CLICKBAIT_PATTERNS:
        if re.search(pat, low):
            return True
    return False


def _is_allcaps(title):
    letters = [c for c in title if c.isalpha()]
    if len(letters) < 8:
        return False
    caps = sum(1 for c in letters if c.isupper())
    return caps / len(letters) > 0.7


def _keyword_bonus(cluster):
    """Reward stories that mention important tech topics."""
    blob = " ".join(
        (a["title"] + " " + a["text"][:600]).lower() for a in cluster
    )
    hits = {kw for kw in config.IMPORTANCE_KEYWORDS if kw in blob}
    bonus = len(hits) * config.KEYWORD_BONUS
    return min(bonus, config.KEYWORD_BONUS_CAP), sorted(hits)


def _recency_bonus(cluster):
    freshest = max(a["published"] for a in cluster)
    age_h = (datetime.now(timezone.utc) - freshest).total_seconds() / 3600
    return config.RECENCY_BONUS if age_h < 6 else 0.0


def score_cluster(cluster):
    """
    Compute a score + metadata for one story cluster.

    Returns a dict, or None if the story must be dropped (discovery-only).
    """
    trusted = _trusted_sources(cluster)

    # --- AUTHENTICITY GATE: no trusted outlet -> drop entirely. ---
    if not trusted:
        log.info("Dropped discovery-only story: %s", cluster[0]["title"])
        return None

    # Source-reliability score = sum of distinct trusted outlet scores.
    by_name = {}
    for a in cluster:
        if a["trusted"]:
            by_name[a["source_name"]] = a["source_score"]
    source_points = sum(by_name.values())

    kw_bonus, kw_hits = _keyword_bonus(cluster)
    rec_bonus = _recency_bonus(cluster)

    # Clickbait penalty — applied if ANY article title looks sensational.
    penalty = 0.0
    if any(_is_clickbait(a["title"]) for a in cluster):
        penalty += config.CLICKBAIT_PENALTY
    if any(_is_allcaps(a["title"]) for a in cluster):
        penalty += config.ALLCAPS_PENALTY

    total = source_points + kw_bonus + rec_bonus - penalty

    n_trusted = len(trusted)
    if n_trusted >= 3:
        confidence = "High"
        verification = f"{n_trusted} trusted sources"
    elif n_trusted == 2:
        confidence = "Medium-High"
        verification = "2 trusted sources"
    else:
        confidence = "Medium"
        verification = "Single trusted source — verify before posting"

    return {
        "cluster": cluster,
        "score": round(total, 2),
        "trusted_sources": sorted(trusted),
        "n_trusted": n_trusted,
        "confidence": confidence,
        "verification": verification,
        "single_source": n_trusted < 2,
        "keywords": kw_hits,
    }


def rank_stories(clusters):
    """Score every cluster, drop the invalid ones, return sorted best-first."""
    scored = []
    for cluster in clusters:
        result = score_cluster(cluster)
        if result is not None:
            scored.append(result)

    scored.sort(key=lambda s: s["score"], reverse=True)
    for s in scored:
        log.info("Story score %.2f | %s | %s",
                 s["score"], s["confidence"], s["cluster"][0]["title"])
    return scored


def select_top(scored):
    """Return the stories worth sending today (may be empty)."""
    qualified = [s for s in scored if s["score"] >= config.MIN_SCORE_TO_SEND]
    return qualified[:config.MAX_STORIES_PER_DAY]
