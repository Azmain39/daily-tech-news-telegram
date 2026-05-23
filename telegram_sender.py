"""
telegram_sender.py — Format and deliver messages via the Telegram Bot API.

We use plain requests.post against the Bot API (no python-telegram-bot) so
GitHub Actions stays light and reliable.

Every story message includes:
- the premium summary,
- a Confidence / Verification line (the "human review mode"),
- a Sources section with outlet names + direct links,
- a visible warning for single-source stories.
"""

import html
import logging
import os

import requests

import config

log = logging.getLogger("telegram")

_API = "https://api.telegram.org/bot{token}/sendMessage"
_TELEGRAM_LIMIT = 4096  # max characters per Telegram message


def _send_raw(text):
    """Send one chunk of text. Returns True on success."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.")
        return False

    try:
        resp = requests.post(
            _API.format(token=token),
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=config.HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        log.error("Telegram send failed: %s", exc)
        return False


def _send_long(text):
    """Split text on line breaks if it exceeds the Telegram limit."""
    if len(text) <= _TELEGRAM_LIMIT:
        return _send_raw(text)

    ok = True
    chunk = ""
    for line in text.split("\n"):
        if len(chunk) + len(line) + 1 > _TELEGRAM_LIMIT:
            ok = _send_raw(chunk) and ok
            chunk = ""
        chunk += line + "\n"
    if chunk.strip():
        ok = _send_raw(chunk) and ok
    return ok


def _format_story(story):
    """Build the Telegram message for one fact-checked story.

    The message contains ONLY the copy-paste LinkedIn post (plus a tiny
    verify-first note). No review brief — the post is the deliverable.
    """
    draft = story.get("linkedin")

    # If the draft could not be built completely, do NOT send a broken
    # post. Send a short honest note instead.
    if not draft:
        return ("📋 A story was found, but a clean LinkedIn-ready post "
                "could not be generated today. Skipping it rather than "
                "posting something incomplete.")

    lines = ["<b>📋 LinkedIn post — ready to copy</b>", ""]
    # <code> renders as a tap-to-copy monospace block in Telegram.
    lines.append(f"<code>{html.escape(draft)}</code>")
    lines.append("")

    # A small, honest note for single-source stories — kept OUT of the
    # copy block so the post stays clean.
    if story.get("single_source"):
        lines.append("⚠️ <i>Single source — open the link and confirm the "
                      "story before you post.</i>")
    else:
        lines.append("<i>Tip: open a source link to confirm before posting.</i>")

    return "\n".join(lines)


def send_stories(stories):
    """Send every fact-checked story. Returns True if all sent OK."""
    ok = True
    for story in stories:
        ok = _send_long(_format_story(story)) and ok
    return ok


def send_no_news():
    """Send the honest 'nothing big today' fallback message."""
    msg = (
        "🟦 <b>No high-impact tech story today.</b>\n\n"
        "Nothing cleared the importance + authenticity bar in the last 24h. "
        "A quiet day is better than a fabricated headline — check back "
        "tomorrow."
    )
    return _send_raw(msg)