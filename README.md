# 📰 Authentic Daily Tech News → Telegram

A free, fully automated mini "news intelligence" pipeline. Every day it reads
trusted tech publishers, finds the 1–2 genuinely important stories, writes a
**fact-checked, LinkedIn-ready summary**, and sends it to you on Telegram with
source links so you can verify before posting.

**Core principle — authenticity first.** Every claim in a summary is traceable
to the original article. No fabricated, clickbait, or hallucinated news.

---

## How it works

```
Trusted RSS feeds
   → fetch FULL article text   (trafilatura)
   → cluster near-duplicates into "stories"
   → cross-verify: count independent trusted outlets
   → rank: source reliability + importance keywords + recency − clickbait
   → pick top 1–2
   → CONSENSUS summary (LLM uses only facts shared across outlets)
   → fact-grounding check (2nd LLM pass; regenerate once, else drop)
   → send to Telegram (summary + Why it matters + Confidence + Sources)
   → GitHub Actions runs it daily, free
```

Anti-fake-news layers:

1. **Full-text grounding** — the LLM reads the actual article, not the headline.
2. **Cross-verification** — a story needs a trusted outlet; 2+ = "verified".
   Discovery-feed-only stories are dropped.
3. **Consensus summary** — with multiple outlets, only overlapping facts are used.
4. **Strict editor prompt** — "if a fact is uncertain, omit it; prefer silence."
5. **Fact-check pass** — a separate LLM call verifies every claim; failures are
   regenerated once, then dropped.
6. **Honest fallback** — a quiet day sends "No high-impact story today" instead
   of forcing weak news.

---

## Project files

| File | Purpose |
|---|---|
| `config.py` | Feeds, reliability scores, keywords, weights, thresholds |
| `fetch.py` | RSS reading + full-text extraction (last 24h only) |
| `cluster.py` | Groups near-duplicate articles into stories |
| `rank.py` | Cross-verification, scoring, story selection |
| `summarize.py` | Consensus LLM summary + fact-grounding check |
| `telegram_sender.py` | Formats and delivers messages |
| `main.py` | Orchestrates the whole pipeline |
| `.github/workflows/daily.yml` | Daily scheduled run |

---

## Setup (free, ~15 minutes)

### 1. Create a Telegram bot
1. Open Telegram, message **@BotFather**.
2. Send `/newbot`, follow the prompts, choose a name.
3. Copy the **bot token** it gives you.
4. **Send your new bot any message** (e.g. "hi") — a bot cannot message you first.

### 2. Get your chat ID
1. Message **@userinfobot** on Telegram.
2. It replies with your numeric **Id** — that is your `TELEGRAM_CHAT_ID`.

### 3. Get a free LLM API key (Google Gemini)
1. Go to <https://aistudio.google.com> and sign in.
2. Click **Get API key** → create a key.
3. The free tier of **gemini-2.5-flash** is generous and works well here.
   (Check current free limits — they change over time.)

### 4. Put the project on GitHub
1. Create a **new GitHub repository**.
2. Upload all these files (keep the `.github/workflows/` folder intact).

### 5. Add the secrets
In your repo: **Settings → Secrets and variables → Actions → New repository
secret**. Add:

| Secret name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | from BotFather |
| `TELEGRAM_CHAT_ID` | from @userinfobot |
| `LLM_API_KEY` | your Gemini API key |
| `LLM_MODEL` | *(optional)* e.g. `gemini-2.5-flash` |

### 6. Enable and test
1. Open the **Actions** tab → enable workflows if prompted.
2. Select **Daily Tech News** → **Run workflow** to test immediately.
3. Check Telegram for the message. After that it runs automatically on the
   daily schedule.

---

## Changing the delivery time

GitHub Actions cron is in **UTC**. Bangladesh time is **UTC + 6**.

Edit the `cron` line in `.github/workflows/daily.yml`:

```yaml
- cron: "0 2 * * *"   # 02:00 UTC = 08:00 Bangladesh time
```

For 09:00 BST use `"0 3 * * *"`, for 07:00 BST use `"0 1 * * *"`, and so on.

---

## Local testing (optional)

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in your real values
python main.py
```

`main.py` auto-loads `.env` locally; `.env` is git-ignored so keys never leak.

---

## Tuning

All tuning lives in `config.py`:

- **`FEEDS`** — add/remove outlets; set each one's `score` and `trusted` flag.
- **`MIN_SCORE_TO_SEND`** — raise it to be stricter (more "quiet day" messages).
- **`SIMILARITY_THRESHOLD`** — raise if unrelated stories get merged; lower if
  duplicates slip through.
- **`MAX_CHARS_PER_ARTICLE` / `MAX_ARTICLES_PER_STORY`** — lower these to spend
  fewer tokens; raise for more thorough summaries.

---

## A note on Reuters

Reuters no longer offers a stable public RSS feed, so it is not in the trusted
list by default. If you find a working Reuters feed, add it to `FEEDS` with
`"trusted": True` and a high `score` (e.g. 10).
