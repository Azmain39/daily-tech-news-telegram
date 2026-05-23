"""
summarize.py — Consensus summarization + fact-grounding check via Gemini.

Pipeline steps: LLM summarizes (grounded only in source text)
                -> fact-grounding check -> regenerate once if it fails.

Authenticity design:
- CONSENSUS SUMMARY: when several outlets cover a story, the model is told
  to prefer facts that appear in MORE THAN ONE source and to omit conflicting
  numbers. This is the single biggest hallucination-reduction step.
- A second LLM pass fact-checks the summary against the raw source text.
  If unsupported claims are found, we regenerate once; if it still fails,
  the story is dropped (return None) — never sent.
- Token cost is controlled: each article body is truncated, and at most
  MAX_ARTICLES_PER_STORY articles are sent.
"""

import json
import logging
import os
import re
from datetime import date

import requests

import config

log = logging.getLogger("summarize")


# ---------------------------------------------------------------------------
# PROMPTS
# ---------------------------------------------------------------------------
EDITOR_PROMPT = """You are a world-class technology news editor writing for a \
premium professional newsletter.

You will be given the FULL TEXT of one or more news articles, all covering the \
SAME story from different outlets. Write ONE LinkedIn-ready summary based \
STRICTLY and ONLY on those texts.

ABSOLUTE RULES:
- Use only facts, numbers, names, and quotes that appear in the provided \
articles. Never add, infer, assume, or embellish.
- When multiple articles are given, prefer facts that appear in MORE THAN ONE \
source. If outlets disagree on a number or detail, omit it or state it as a \
range.
- If a detail is not in the text, do not mention it. A shorter accurate \
summary always beats a fuller invented one.
- No clickbait, no hype, no opinion stated as fact.
- Never infer motivations, future impact, hidden meaning, or business strategy \
unless explicitly stated in the article.
- If a fact is uncertain, omit it. When unsure, prefer silence over speculation.
- If the articles are thin or low-substance, say so honestly and keep it brief.

OUTPUT EXACTLY THIS STRUCTURE (no extra text before or after):

🚀 Tech Insight — {today}

[2-4 sentence summary of what happened, in clear professional language.]

Why it matters:
• [point grounded in the article]
• [point grounded in the article]
• [point grounded in the article]

[One closing sentence on the bigger picture — ONLY if the articles support it.]

#hashtag #hashtag #hashtag

Tone: confident, professional, engaging — like a top-tier tech newsletter. \
No emojis except the header. Keep it tight enough to post on LinkedIn without \
editing.

=== SOURCE ARTICLES ===
{sources}
"""

FACTCHECK_PROMPT = """You are a strict, literal fact-checker.

Below is a SUMMARY and the SOURCE ARTICLE TEXT it was based on. Check whether \
EVERY factual claim, number, name, and quote in the summary is directly \
supported by the source text. Section headers, bullet markers, hashtags, and \
the date line are not claims — ignore them.

Respond in EXACTLY this format and nothing else:

VERDICT: PASS
(if every claim is supported)

or

VERDICT: FAIL
UNSUPPORTED:
- <the unsupported claim>
- <the unsupported claim>

=== SUMMARY ===
{summary}

=== SOURCE ARTICLE TEXT ===
{sources}
"""


# ---------------------------------------------------------------------------
# GEMINI CALL
# ---------------------------------------------------------------------------
def _call_gemini(prompt, temperature=0.3):
    """Call the Gemini REST API. Returns text, or None on any failure."""
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        log.error("LLM_API_KEY not set.")
        return None

    model = os.environ.get("LLM_MODEL", config.DEFAULT_LLM_MODEL)
    url = config.GEMINI_ENDPOINT.format(model=model)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 900},
    }
    try:
        resp = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=config.HTTP_TIMEOUT + 20,
        )
        resp.raise_for_status()
        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except Exception as exc:
        log.error("Gemini call failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def _build_sources_block(cluster):
    """Concatenate (truncated) article texts, labelled by outlet."""
    chosen = cluster[:config.MAX_ARTICLES_PER_STORY]
    blocks = []
    for i, art in enumerate(chosen, 1):
        body = art["text"][:config.MAX_CHARS_PER_ARTICLE]
        blocks.append(
            f"--- ARTICLE {i} | Outlet: {art['source_name']} ---\n"
            f"Title: {art['title']}\n\n{body}"
        )
    return "\n\n".join(blocks)


def _fact_check(summary, sources_block):
    """Return (passed: bool, unsupported: list[str])."""
    raw = _call_gemini(
        FACTCHECK_PROMPT.format(summary=summary, sources=sources_block),
        temperature=0.0,
    )
    if raw is None:
        # If the checker itself fails, be conservative and treat as a fail.
        return False, ["fact-check pass could not run"]

    if re.search(r"verdict:\s*pass", raw, re.IGNORECASE):
        return True, []

    unsupported = re.findall(r"^\s*[-•]\s*(.+)$", raw, re.MULTILINE)
    return False, unsupported or ["unspecified unsupported claim"]


# ---------------------------------------------------------------------------
# PUBLIC ENTRY POINT
# ---------------------------------------------------------------------------
def summarize_story(story):
    """
    Generate a fact-checked consensus summary for one ranked story.

    `story` is a dict produced by rank.py. Returns the same dict with an
    added "summary" key, or None if the summary cannot pass the fact check.
    """
    cluster = story["cluster"]
    sources_block = _build_sources_block(cluster)
    today = date.today().strftime("%d %b %Y")

    attempts = 1 + config.MAX_FACTCHECK_REGEN
    for attempt in range(1, attempts + 1):
        # Slightly higher temperature on a retry to escape a bad phrasing.
        temp = 0.3 if attempt == 1 else 0.15
        summary = _call_gemini(
            EDITOR_PROMPT.format(today=today, sources=sources_block),
            temperature=temp,
        )
        if not summary:
            log.warning("Empty summary (attempt %d).", attempt)
            continue

        passed, unsupported = _fact_check(summary, sources_block)
        if passed:
            log.info("Summary passed fact check (attempt %d).", attempt)
            story["summary"] = summary
            return story

        log.warning("Fact check failed (attempt %d): %s",
                    attempt, "; ".join(unsupported))

    log.error("Dropping story — could not produce a grounded summary: %s",
              cluster[0]["title"])
    return None
