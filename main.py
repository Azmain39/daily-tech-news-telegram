"""
main.py — Orchestrates the full daily pipeline.

  Trusted RSS feeds
        -> fetch full article text
        -> cluster into stories (deduplicate)
        -> cross-verify + rank
        -> select top 1-2
        -> consensus summarize + fact-check
        -> deliver to Telegram
        (-> automated daily by GitHub Actions)

The whole run is wrapped so that any unexpected error is logged and the
process still exits cleanly — a crash should never be silent.
"""

import logging
import os
import sys


def _load_dotenv():
    """Load a local .env file if present (no extra dependency needed).

    On GitHub Actions there is no .env file — secrets arrive as real
    environment variables, so this simply does nothing there.
    """
    if not os.path.exists(".env"):
        return
    with open(".env", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

import cluster as cluster_mod  # noqa: E402  (import after .env load)
import fetch as fetch_mod
import rank as rank_mod
import summarize as summarize_mod
import telegram_sender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-9s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")


def run():
    is_manual = os.environ.get("GITHUB_EVENT_NAME", "") == "workflow_dispatch"

    # 1. FETCH ---------------------------------------------------------------
    articles = fetch_mod.fetch_all_articles()
    if not articles:
        log.info("No articles fetched.")
        if is_manual:
            telegram_sender.send_test_result(0, 0, 0)
        else:
            telegram_sender.send_no_news()
        return

    # 2. CLUSTER (deduplicate) ----------------------------------------------
    clusters = cluster_mod.cluster_articles(articles)

    # 3. CROSS-VERIFY + RANK -------------------------------------------------
    scored = rank_mod.rank_stories(clusters)

    # 4. SELECT --------------------------------------------------------------
    top = rank_mod.select_top(scored)
    if not top:
        log.info("Nothing cleared the bar.")
        if is_manual:
            telegram_sender.send_test_result(len(articles), len(clusters), 0)
        else:
            telegram_sender.send_no_news()
        return

    # 5. SUMMARIZE + FACT-CHECK ---------------------------------------------
    final_stories = []
    for story in top:
        result = summarize_mod.summarize_story(story)
        if result is not None:
            final_stories.append(result)

    # 6. DELIVER -------------------------------------------------------------
    if not final_stories:
        log.info("All candidates failed fact check.")
        if is_manual:
            telegram_sender.send_test_result(len(articles), len(clusters), len(top))
        else:
            telegram_sender.send_no_news()
        return

    if telegram_sender.send_stories(final_stories):
        log.info("Delivered %d story/stories to Telegram.", len(final_stories))
    else:
        log.error("One or more Telegram deliveries failed.")


def main():
    try:
        run()
    except Exception:
        # Never crash silently — log the full traceback, exit non-zero so
        # the GitHub Actions run is visibly marked as failed.
        log.exception("Unhandled error in daily run.")
        sys.exit(1)


if __name__ == "__main__":
    main()
