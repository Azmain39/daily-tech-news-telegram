"""
diagnose.py — Find out WHY the bot keeps sending "No high-impact story".

Run this locally:   python diagnose.py
Or run it as a one-off GitHub Actions job (see instructions printed at the end).

It walks the real pipeline step by step and prints a clear verdict, so you
fix the ACTUAL cause instead of guessing.
"""

import logging
import sys

logging.basicConfig(level=logging.WARNING, format="%(message)s")

import config          # noqa: E402
import fetch as fetch_mod      # noqa: E402
import cluster as cluster_mod  # noqa: E402
import rank as rank_mod        # noqa: E402

BAR = "=" * 64


def main():
    print(BAR)
    print("TECH NEWS BOT — DIAGNOSTIC")
    print(BAR)

    # --- STEP 1: can each feed be read at all? -----------------------------
    print("\n[1] FEED CHECK — can each feed be reached and parsed?\n")
    import feedparser
    reachable = 0
    for feed in config.FEEDS:
        try:
            parsed = feedparser.parse(feed["url"])
            n = len(parsed.entries)
            if n > 0:
                reachable += 1
                print(f"   OK      {feed['name']:26} entries={n}")
            else:
                print(f"   EMPTY   {feed['name']:26} (0 entries — bad URL "
                      f"or blocked)")
        except Exception as exc:
            print(f"   ERROR   {feed['name']:26} {exc}")

    if reachable == 0:
        print("\n>>> VERDICT: No feed could be read at all.")
        print(">>> The problem is FEED ACCESS, not scoring.")
        print(">>> Fix the feed URLs in config.py — adding more won't help.")
        return

    # --- STEP 2: full fetch (last 24h + full-text extraction) --------------
    print(f"\n[2] FETCH — articles from the last {config.LOOKBACK_HOURS}h "
          f"with extractable full text\n")
    articles = fetch_mod.fetch_all_articles()
    print(f"   -> {len(articles)} usable articles fetched.")

    if not articles:
        print("\n>>> VERDICT: Feeds are reachable, but 0 articles survived.")
        print(">>> Likely causes:")
        print("    - LOOKBACK_HOURS too small, or")
        print("    - full-text extraction failing (sites blocking the fetch).")
        print(">>> Try raising LOOKBACK_HOURS to 48 in config.py.")
        return

    # --- STEP 3: cluster + rank --------------------------------------------
    clusters = cluster_mod.cluster_articles(articles)
    scored = rank_mod.rank_stories(clusters)
    print(f"\n[3] RANKING — {len(clusters)} stories, "
          f"{len(scored)} survived cross-verification\n")

    if not scored:
        print(">>> VERDICT: Articles fetched, but every story was dropped")
        print(">>> for having NO trusted source. Check the 'trusted' flags")
        print(">>> in config.py — at least a few feeds must be trusted=True.")
        return

    # Show the score of every story vs the cutoff.
    print(f"   Current MIN_SCORE_TO_SEND = {config.MIN_SCORE_TO_SEND}\n")
    top_score = scored[0]["score"]
    for s in scored[:8]:
        mark = "PASS" if s["score"] >= config.MIN_SCORE_TO_SEND else "below"
        print(f"   [{mark:5}] score={s['score']:6.2f}  "
              f"{s['cluster'][0]['title'][:46]}")

    # --- VERDICT -----------------------------------------------------------
    print("\n" + BAR)
    qualified = [s for s in scored if s["score"] >= config.MIN_SCORE_TO_SEND]
    if qualified:
        print(f">>> VERDICT: Healthy. {len(qualified)} story/stories would")
        print(">>> be sent today. If you still see 'no news', re-check that")
        print(">>> the summary/fact-check step is not dropping them.")
    else:
        print(">>> VERDICT: Feeds and articles are FINE. Stories are found,")
        print(f">>> but the best score ({top_score:.2f}) is below the cutoff")
        print(f">>> ({config.MIN_SCORE_TO_SEND}).")
        print(">>> FIX: lower MIN_SCORE_TO_SEND in config.py — try a value")
        print(f">>> slightly under {top_score:.1f} (but not below ~5.0).")
    print(BAR)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Diagnostic crashed")
        sys.exit(1)