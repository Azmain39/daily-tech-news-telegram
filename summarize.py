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

# LinkedIn post writer. Runs AFTER the brief summary has passed fact-check,
# so it is grounded in an already-verified summary — it adds NO new facts.
# This version produces an OPINION-FREE, purely factual post that the user
# can copy and paste without editing.
LINKEDIN_PROMPT = """You are a technology professional writing a LinkedIn post.

Below is a SHORT, fact-checked summary of a tech news story. Rewrite it as a \
clean, FACTUAL LinkedIn post for the feed of a computer science student who \
follows tech closely.

ABSOLUTE RULES:
- Use ONLY the facts in the summary below. Add NO new numbers, names, or claims.
- This is a NEUTRAL, factual news post. Do NOT add personal opinion, \
prediction, or commentary. Report only what happened.
- The post must read like a clear, professional human wrote it.

WRITE THE POST WITH THIS STRUCTURE:

Line 1: A short, specific HEADLINE (under 12 words) stating the single most \
important concrete fact. No vague teasing, no hype.
(blank line)
3-5 short sentences explaining what happened: who, what, and the key verified \
details from the summary.
(blank line)
One factual closing sentence on context — ONLY if the summary supports it. \
If not, skip this line.
(blank line)
3-4 relevant hashtags.

STYLE:
- Short sentences. Short paragraphs (1-2 lines each). Generous white space.
- Neutral and informative, like a news wire. No "game-changer", no hype words.
- No emojis.
- Total length: 60-120 words.
- Every sentence must be complete. Never stop mid-sentence.
- The final non-hashtag sentence must end with a period, question mark, or \
exclamation mark.

Do NOT write a "Source" line — that is added automatically afterwards.
Output ONLY the post text. No preamble, no explanation.

=== FACT-CHECKED SUMMARY ===
{summary}
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
def _call_gemini(prompt, temperature=0.3, max_tokens=2048):
    """Call the Gemini REST API. Returns text, or None on any failure.

    max_tokens is the OUTPUT cap. It must be generous: too low a value
    makes Gemini stop mid-sentence, which was the cause of the cut-off
    summaries and LinkedIn drafts.
    """
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        log.error("LLM_API_KEY not set.")
        return None

    model = os.environ.get("LLM_MODEL", config.DEFAULT_LLM_MODEL)
    url = config.GEMINI_ENDPOINT.format(model=model)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
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
        candidate = data["candidates"][0]
        parts = candidate.get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        # If Gemini stopped because it hit the token cap, the text is
        # very likely cut off mid-sentence — warn so callers can react.
        if candidate.get("finishReason") == "MAX_TOKENS":
            log.warning("Gemini hit MAX_TOKENS — output may be truncated.")
        return text or None
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


def _clean_linkedin_draft(draft):
    """Strip code fences and any stray source lines from the LLM draft."""
    if not draft:
        return None
    draft = draft.strip()
    # Remove markdown code fences if Gemini adds them.
    draft = re.sub(r"^```(?:\w+)?\s*", "", draft)
    draft = re.sub(r"\s*```$", "", draft)
    # Drop any accidental source/read-more lines (we add our own).
    kept = []
    for line in draft.splitlines():
        low = line.strip().lower()
        if low.startswith("source:") or low.startswith("read more"):
            continue
        kept.append(line.rstrip())
    return "\n".join(kept).strip()


# Words that, if a sentence ends on them, signal a cut-off draft.
_DANGLING_WORDS = {
    "for", "to", "of", "in", "on", "with", "by", "from", "as", "and", "or",
    "the", "a", "an", "this", "that", "which", "including", "must", "will",
    "can", "could", "should", "is", "are", "was", "were", "be", "into",
    "at", "but", "their", "its",
}


def _looks_complete_linkedin_draft(draft):
    """True if the draft looks finished (not cut off mid-sentence)."""
    if not draft:
        return False
    lines = [ln.strip() for ln in draft.splitlines() if ln.strip()]
    content = [ln for ln in lines if not ln.startswith("#")]
    if not content:
        return False
    last = content[-1].strip()
    # A finished factual post ends with sentence punctuation.
    if last[-1] not in ".!?":
        return False
    # Reject an obvious dangling final word.
    last_word = re.sub(r"[^A-Za-z]", "", last.split()[-1]).lower()
    if last_word in _DANGLING_WORDS:
        return False
    return True


def _build_linkedin_draft(summary, cluster):
    """Turn a fact-checked summary into a ready-to-post LinkedIn draft.

    Appends a 'Source' line with real article links so the post is
    visibly authentic. If Gemini returns a cut-off draft, retries once;
    if it still looks incomplete, returns None so a broken post is never
    delivered. Adds NO new facts.
    """
    # Build the source block once (one or two distinct outlets).
    seen, links = set(), []
    for art in cluster:
        if art["url"] in seen:
            continue
        seen.add(art["url"])
        links.append(f"{art['source_name']}: {art['url']}")
        if len(links) == 2:
            break
    source_block = "\n".join(f"Read more — {ln}" for ln in links)

    for attempt in range(1, 3):
        temp = 0.4 if attempt == 1 else 0.15
        raw = _call_gemini(
            LINKEDIN_PROMPT.format(summary=summary),
            temperature=temp,
            max_tokens=1024,   # generous — a 120-word post fits easily
        )
        draft = _clean_linkedin_draft(raw)
        if _looks_complete_linkedin_draft(draft):
            return f"{draft}\n\nSource:\n{source_block}"
        log.warning("LinkedIn draft looked incomplete on attempt %d.", attempt)

    # Better to send no draft than a broken one.
    log.error("Could not build a complete LinkedIn draft.")
    return None


# ---------------------------------------------------------------------------
# PUBLIC ENTRY POINT
# ---------------------------------------------------------------------------
def summarize_story(story):
    """
    Generate a fact-checked consensus summary for one ranked story.

    `story` is a dict produced by rank.py. Returns the same dict with added
    "summary" and "linkedin" keys, or None if the summary cannot pass the
    fact check. "linkedin" may be None if only the draft step failed.
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
            # Build the LinkedIn draft from the VERIFIED summary only.
            draft = _build_linkedin_draft(summary, cluster)
            if draft is None:
                # No usable post -> drop the story rather than deliver
                # something incomplete.
                log.error("Dropping story — LinkedIn draft incomplete: %s",
                          cluster[0]["title"])
                return None
            story["linkedin"] = draft
            return story

        log.warning("Fact check failed (attempt %d): %s",
                    attempt, "; ".join(unsupported))

    log.error("Dropping story — could not produce a grounded summary: %s",
              cluster[0]["title"])
    return None