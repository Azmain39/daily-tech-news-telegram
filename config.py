"""
config.py — All tunable settings for the Tech News Bot.

Edit this file to change feeds, scoring weights, keywords, and behaviour.
Nothing here is secret — API keys/tokens come from environment variables.
"""

# ---------------------------------------------------------------------------
# 1. NEWS SOURCES
# ---------------------------------------------------------------------------
# Each feed has a reliability "score" (ChatGPT's suggestion #2).
#   trusted = True  -> can confirm a story on its own
#   trusted = False -> DISCOVERY ONLY. A story seen ONLY here is dropped.
#
# NOTE on Reuters: Reuters no longer publishes a stable public RSS feed.
# We instead use a Google-News query scoped to reuters.com as a *discovery*
# signal. If you have a working Reuters feed, add it here as trusted.
FEEDS = [
    # ---- Trusted tech media (each can confirm a story on its own) ----
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/",          "trusted": True,  "score": 9},
    {"name": "Ars Technica",          "url": "https://feeds.arstechnica.com/arstechnica/index", "trusted": True,  "score": 8},
    {"name": "Wired",                 "url": "https://www.wired.com/feed/rss",                  "trusted": True,  "score": 7},
    {"name": "The Verge",             "url": "https://www.theverge.com/rss/index.xml",          "trusted": True,  "score": 7},
    {"name": "TechCrunch",            "url": "https://techcrunch.com/feed/",                    "trusted": True,  "score": 6},
    {"name": "Engadget",              "url": "https://www.engadget.com/rss.xml",                "trusted": True,  "score": 6},
    {"name": "VentureBeat",           "url": "https://venturebeat.com/feed/",                   "trusted": True,  "score": 6},
    # ---- AI company blogs (trusted, but company-side — see note below) ----
    # These add volume on quiet days. They are first-party announcements,
    # so cross-checking against a media outlet is still wise before posting.
    {"name": "Google Blog (Tech)",    "url": "https://blog.google/technology/rss/",             "trusted": True,  "score": 6},
    {"name": "Microsoft AI Blog",     "url": "https://blogs.microsoft.com/ai/feed/",            "trusted": True,  "score": 6},
    # ---- Discovery only (never trusted on its own) ----
    {"name": "Google News (Discovery)",
     "url": "https://news.google.com/rss/search?q=technology+when:1d&hl=en-US&gl=US&ceid=US:en",
     "trusted": False, "score": 0},
]
# NOTE: If a feed ever shows 0 entries in diagnose.py, its URL has changed
# or is being blocked — fix or remove it. More feeds only help if they work.

# ---------------------------------------------------------------------------
# 2. TIME WINDOW
# ---------------------------------------------------------------------------
LOOKBACK_HOURS = 36          # consider articles from the last N hours.
                             # 36h (not 24h) prevents missing a story that
                             # broke just outside the window on a quiet day.

# ---------------------------------------------------------------------------
# 3. STORY CLUSTERING (deduplication)
# ---------------------------------------------------------------------------
SIMILARITY_THRESHOLD = 0.58  # 0-1. Higher = stricter "same story" grouping.

# ---------------------------------------------------------------------------
# 4. IMPORTANCE KEYWORDS  (boost score if found in title/text)
# ---------------------------------------------------------------------------
IMPORTANCE_KEYWORDS = [
    "ai", "artificial intelligence", "openai", "anthropic", "google",
    "deepmind", "apple", "microsoft", "nvidia", "meta", "amazon",
    "funding", "raises", "acquisition", "ipo", "cybersecurity", "breach",
    "hack", "robotics", "regulation", "lawsuit", "antitrust", "breakthrough",
    "chip", "semiconductor", "quantum", "launch", "model",
]
KEYWORD_BONUS = 1.5          # points per unique keyword (capped below)
KEYWORD_BONUS_CAP = 9.0      # max total keyword bonus

# ---------------------------------------------------------------------------
# 5. ANTI-CLICKBAIT PENALTY
# ---------------------------------------------------------------------------
CLICKBAIT_PATTERNS = [
    r"you won'?t believe", r"shocking", r"mind-?blowing", r"this is why",
    r"will blow your mind", r"\bgone wrong\b", r"insane", r"jaw-?dropping",
    r"number \d+ will", r"what happens next",
]
CLICKBAIT_PENALTY = 6.0      # subtracted if any pattern matches the title
ALLCAPS_PENALTY = 3.0        # subtracted if title is mostly UPPERCASE

# ---------------------------------------------------------------------------
# 6. RECENCY BONUS
# ---------------------------------------------------------------------------
RECENCY_BONUS = 2.0          # added if the freshest article is < 6h old

# ---------------------------------------------------------------------------
# 7. SELECTION
# ---------------------------------------------------------------------------
MAX_STORIES_PER_DAY = 2      # send at most this many stories
MIN_SCORE_TO_SEND = 5.5      # below this -> "no high-impact story today".
                             # Lowered from 7.0: a solid single-source story
                             # from a trusted outlet now clears the bar.
                             # Do NOT go below ~4.0 or weak news slips in.
                             # Use diagnose.py to see real scores and tune.

# ---------------------------------------------------------------------------
# 8. LLM SETTINGS  (Google Gemini — free tier)
# ---------------------------------------------------------------------------
# Model name is overridable via the LLM_MODEL environment variable.
DEFAULT_LLM_MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

# Token-cost control (ChatGPT suggestion #5): we do NOT send unlimited text.
MAX_CHARS_PER_ARTICLE = 6000     # truncate each article body before sending
MAX_ARTICLES_PER_STORY = 3       # use at most N articles for the consensus
MAX_FACTCHECK_REGEN = 1          # how many times to retry a failed summary

# ---------------------------------------------------------------------------
# 9. HTTP
# ---------------------------------------------------------------------------
HTTP_TIMEOUT = 20
FETCH_DELAY_SECONDS = 1.0    # polite pause before each article download.
                             # Prevents HTTP 429 ("Too Many Requests") from
                             # sites like VentureBeat. Raise to 1.5-2.0 if
                             # 429 errors still appear in the logs.
USER_AGENT = (
    "Mozilla/5.0 (compatible; TechNewsBot/1.0; "
    "+personal-automation; respectful-fetch)"
)