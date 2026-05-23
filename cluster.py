"""
cluster.py — Group near-duplicate articles into "stories".

The same event is reported by many outlets. We group them so that each
cluster = one real-world story. This enables cross-verification and the
consensus summary later.

We deliberately avoid heavy ML dependencies (scikit-learn, embeddings) to
keep GitHub Actions fast and free. Title similarity + a light body-text
check is more than enough for news headlines.
"""

import logging
import re
from difflib import SequenceMatcher

import config

log = logging.getLogger("cluster")

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "as", "at", "by", "from", "new", "its", "it", "this",
    "that", "will", "has", "have", "after", "amid", "over", "into",
}


def _normalize(text):
    """Lowercase, strip punctuation, drop stopwords -> token set."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _similarity(a, b):
    """Combined similarity (0-1) between two articles using title + lede."""
    # 1. Sequence similarity on raw titles.
    seq = SequenceMatcher(None, a["title"].lower(), b["title"].lower()).ratio()

    # 2. Jaccard overlap on meaningful title tokens.
    ta, tb = _normalize(a["title"]), _normalize(b["title"])
    jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0

    # 3. Light body check on the first ~400 chars (the lede).
    lede = SequenceMatcher(
        None, a["text"][:400].lower(), b["text"][:400].lower()
    ).ratio()

    # Weighted blend — titles dominate, lede breaks ties.
    return 0.45 * seq + 0.40 * jac + 0.15 * lede


def cluster_articles(articles):
    """
    Group articles into stories.

    Returns a list of clusters; each cluster is a list of Article dicts.
    Greedy single-pass union — adequate for the small daily volume.
    """
    clusters = []  # list[list[article]]

    for art in articles:
        placed = False
        for cluster in clusters:
            # Compare against the first (representative) article of the cluster.
            if _similarity(art, cluster[0]) >= config.SIMILARITY_THRESHOLD:
                cluster.append(art)
                placed = True
                break
        if not placed:
            clusters.append([art])

    log.info("Grouped %d articles into %d stories.",
             len(articles), len(clusters))
    return clusters
