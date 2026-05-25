"""
config.py — All tunable settings for the Tech News Bot.

Edit this file to change feeds, scoring weights, keywords, and behaviour.
Nothing here is secret — API keys/tokens come from environment variables.
"""

# ---------------------------------------------------------------------------
# 1. NEWS SOURCES
# ---------------------------------------------------------------------------
# Each feed has a reliability "score":
#   trusted = True  -> can confirm a story on its own
#   trusted = False -> DISCOVERY ONLY. A story seen ONLY here is dropped.
#
# Feed URLs are verified against publicly documented RSS endpoints.
# If a feed returns 0 entries in diagnose.py, its URL may have changed —
# update or remove it. Dead feeds only cost a warning log, not a crash.
FEEDS = [
    # =========================================================================
    # TIER 1 — PREMIER GLOBAL TECH & SCIENCE JOURNALISM  (score 8-9)
    # Most authoritative sources. A single story from here carries max weight.
    # =========================================================================
    {"name": "MIT Technology Review",    "url": "https://www.technologyreview.com/feed/",                               "trusted": True, "score": 9},
    {"name": "IEEE Spectrum",            "url": "https://spectrum.ieee.org/feeds/feed.rss",                             "trusted": True, "score": 9},
    {"name": "BBC Technology",           "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",                     "trusted": True, "score": 9},
    {"name": "Reuters Technology",       "url": "https://feeds.reuters.com/reuters/technologyNews",                     "trusted": True, "score": 9},
    {"name": "The Guardian Technology",  "url": "https://www.theguardian.com/technology/rss",                           "trusted": True, "score": 8},
    {"name": "NYT Technology",           "url": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",          "trusted": True, "score": 8},
    {"name": "Nature (all)",             "url": "https://www.nature.com/nature.rss",                                    "trusted": True, "score": 9},
    {"name": "Science Magazine",         "url": "https://www.science.org/rss/news_current.xml",                         "trusted": True, "score": 9},
    {"name": "Phys.org Technology",      "url": "https://phys.org/rss-feed/technology-news/",                           "trusted": True, "score": 8},
    {"name": "New Scientist Technology", "url": "https://www.newscientist.com/subject/technology/feed/",                "trusted": True, "score": 8},
    {"name": "ScienceDaily (CS)",        "url": "https://www.sciencedaily.com/rss/computers_math/computer_science.xml", "trusted": True, "score": 8},
    {"name": "TechXplore",               "url": "https://techxplore.com/rss-feed/",                                     "trusted": True, "score": 7},
    {"name": "MIT News (Computing)",     "url": "https://news.mit.edu/rss/topic/computers-internet-and-technology",     "trusted": True, "score": 8},

    # =========================================================================
    # TIER 2 — ESTABLISHED TECH MEDIA  (score 7-8)
    # Long-track-record outlets respected by industry professionals.
    # =========================================================================
    {"name": "Ars Technica",             "url": "https://feeds.arstechnica.com/arstechnica/index",                      "trusted": True, "score": 8},
    {"name": "Ars Technica Tech Policy", "url": "https://feeds.arstechnica.com/arstechnica/tech-policy",                "trusted": True, "score": 8},
    {"name": "Ars Technica Science",     "url": "https://feeds.arstechnica.com/arstechnica/science",                    "trusted": True, "score": 8},
    {"name": "Ars Technica Gadgets",     "url": "https://feeds.arstechnica.com/arstechnica/gadgets",                    "trusted": True, "score": 7},
    {"name": "Wired",                    "url": "https://www.wired.com/feed/rss",                                        "trusted": True, "score": 7},
    {"name": "Wired UK",                 "url": "https://www.wired.co.uk/rss",                                          "trusted": True, "score": 7},
    {"name": "The Verge",                "url": "https://www.theverge.com/rss/index.xml",                               "trusted": True, "score": 7},
    {"name": "The Register",             "url": "https://www.theregister.com/headlines.atom",                           "trusted": True, "score": 7},
    {"name": "Tom's Hardware",           "url": "https://www.tomshardware.com/feeds/all",                               "trusted": True, "score": 7},
    {"name": "ExtremeTech",              "url": "https://www.extremetech.com/feed",                                     "trusted": True, "score": 6},
    {"name": "LWN.net",                  "url": "https://lwn.net/headlines/rss",                                        "trusted": True, "score": 7},

    # =========================================================================
    # TIER 3 — MAINSTREAM TECH NEWS  (score 5-7)
    # High-volume, broad-audience tech coverage.
    # =========================================================================
    {"name": "TechCrunch",              "url": "https://techcrunch.com/feed/",                                          "trusted": True, "score": 6},
    {"name": "TechCrunch AI",           "url": "https://techcrunch.com/category/artificial-intelligence/feed/",         "trusted": True, "score": 6},
    {"name": "TechCrunch Security",     "url": "https://techcrunch.com/category/security/feed/",                        "trusted": True, "score": 6},
    {"name": "TechCrunch Startups",     "url": "https://techcrunch.com/category/startups/feed/",                        "trusted": True, "score": 6},
    {"name": "Engadget",                "url": "https://www.engadget.com/rss.xml",                                      "trusted": True, "score": 6},
    {"name": "VentureBeat",             "url": "https://venturebeat.com/feed/",                                         "trusted": True, "score": 6},
    {"name": "VentureBeat AI",          "url": "https://venturebeat.com/category/ai/feed/",                             "trusted": True, "score": 6},
    {"name": "VentureBeat Security",    "url": "https://venturebeat.com/category/security/feed/",                       "trusted": True, "score": 6},
    {"name": "ZDNet",                   "url": "https://www.zdnet.com/news/rss.xml",                                    "trusted": True, "score": 6},
    {"name": "CNET",                    "url": "https://www.cnet.com/rss/news/",                                        "trusted": True, "score": 6},
    {"name": "CNET AI",                 "url": "https://www.cnet.com/rss/ai/",                                          "trusted": True, "score": 6},
    {"name": "PCMag",                   "url": "https://www.pcmag.com/feeds/latest",                                    "trusted": True, "score": 6},
    {"name": "Gizmodo",                 "url": "https://gizmodo.com/rss",                                               "trusted": True, "score": 6},
    {"name": "The Next Web",            "url": "https://thenextweb.com/feed/",                                          "trusted": True, "score": 6},
    {"name": "TechRadar",               "url": "https://www.techradar.com/rss",                                         "trusted": True, "score": 6},
    {"name": "Digital Trends",          "url": "https://www.digitaltrends.com/feed/",                                   "trusted": True, "score": 6},
    {"name": "Mashable Tech",           "url": "https://mashable.com/feeds/rss/tech",                                   "trusted": True, "score": 5},
    {"name": "ReadWrite",               "url": "https://readwrite.com/feed/",                                           "trusted": True, "score": 5},
    {"name": "Silicon Republic",        "url": "https://www.siliconrepublic.com/feed/",                                  "trusted": True, "score": 5},

    # =========================================================================
    # TIER 4 — AI / ML SPECIALIST SOURCES  (score 7-9)
    # First-party announcements from the leading AI labs and deep AI journalism.
    # =========================================================================
    {"name": "OpenAI Blog",             "url": "https://openai.com/blog/rss.xml",                                       "trusted": True, "score": 9},
    {"name": "Anthropic News",          "url": "https://www.anthropic.com/rss.xml",                                     "trusted": True, "score": 9},
    {"name": "Google Research Blog",    "url": "https://blog.research.google/feeds/posts/default",                      "trusted": True, "score": 8},
    {"name": "Google Blog (Tech)",      "url": "https://blog.google/technology/rss/",                                   "trusted": True, "score": 7},
    {"name": "DeepMind Blog",           "url": "https://deepmind.google/blog/rss.xml",                                  "trusted": True, "score": 8},
    {"name": "Meta AI Blog",            "url": "https://ai.meta.com/blog/rss/",                                         "trusted": True, "score": 7},
    {"name": "Microsoft AI Blog",       "url": "https://blogs.microsoft.com/ai/feed/",                                  "trusted": True, "score": 7},
    {"name": "NVIDIA Blog",             "url": "https://blogs.nvidia.com/feed/",                                        "trusted": True, "score": 7},
    {"name": "HuggingFace Blog",        "url": "https://huggingface.co/blog/feed.xml",                                  "trusted": True, "score": 7},
    {"name": "The Gradient",            "url": "https://thegradient.pub/rss/",                                          "trusted": True, "score": 7},

    # =========================================================================
    # TIER 5 — CYBERSECURITY  (score 7-8)
    # Specialized security journalism and threat intelligence.
    # =========================================================================
    {"name": "Krebs on Security",       "url": "https://krebsonsecurity.com/feed/",                                     "trusted": True, "score": 8},
    {"name": "BleepingComputer",        "url": "https://www.bleepingcomputer.com/feed/",                                "trusted": True, "score": 7},
    {"name": "The Hacker News (Sec)",   "url": "https://feeds.feedburner.com/TheHackersNews",                           "trusted": True, "score": 7},
    {"name": "Dark Reading",            "url": "https://www.darkreading.com/rss/all.xml",                               "trusted": True, "score": 7},
    {"name": "SecurityWeek",            "url": "https://www.securityweek.com/feed/",                                    "trusted": True, "score": 7},
    {"name": "Naked Security (Sophos)", "url": "https://nakedsecurity.sophos.com/feed/",                                "trusted": True, "score": 7},
    {"name": "Schneier on Security",    "url": "https://www.schneier.com/blog/atom.xml",                                "trusted": True, "score": 8},
    {"name": "SANS Internet Storm",     "url": "https://isc.sans.edu/rssfeed_full.xml",                                 "trusted": True, "score": 7},

    # =========================================================================
    # TIER 6 — ENTERPRISE / BUSINESS TECH  (score 5-6)
    # Business-focused coverage for professional audiences.
    # =========================================================================
    {"name": "Forbes Technology",       "url": "https://www.forbes.com/technology/feed2/",                              "trusted": True, "score": 6},
    {"name": "Fast Company Technology", "url": "https://www.fastcompany.com/technology/rss",                            "trusted": True, "score": 6},
    {"name": "TechRepublic",            "url": "https://www.techrepublic.com/rssfeeds/articles/",                       "trusted": True, "score": 5},
    {"name": "InfoWorld",               "url": "https://www.infoworld.com/index.rss",                                   "trusted": True, "score": 5},
    {"name": "Computerworld",           "url": "https://www.computerworld.com/news/rss",                                "trusted": True, "score": 5},
    {"name": "CIO Magazine",            "url": "https://www.cio.com/news/rss",                                          "trusted": True, "score": 5},
    {"name": "Rest of World",           "url": "https://restofworld.org/feed/",                                         "trusted": True, "score": 6},
    {"name": "Tech in Asia",            "url": "https://www.techinasia.com/feed",                                       "trusted": True, "score": 6},
    {"name": "Crunchbase News",         "url": "https://news.crunchbase.com/feed/",                                     "trusted": True, "score": 6},

    # =========================================================================
    # TIER 7 — DEVELOPER / OPEN SOURCE / CLOUD  (score 5-7)
    # =========================================================================
    {"name": "GitHub Blog",             "url": "https://github.blog/feed/",                                             "trusted": True, "score": 7},
    {"name": "Stack Overflow Blog",     "url": "https://stackoverflow.blog/feed/",                                      "trusted": True, "score": 6},
    {"name": "Cloudflare Blog",         "url": "https://blog.cloudflare.com/rss/",                                      "trusted": True, "score": 7},
    {"name": "AWS Blog",                "url": "https://aws.amazon.com/blogs/aws/feed/",                                "trusted": True, "score": 6},
    {"name": "Azure Blog",              "url": "https://azure.microsoft.com/en-us/blog/feed/",                          "trusted": True, "score": 6},
    {"name": "Google Cloud Blog",       "url": "https://cloudblog.withgoogle.com/rss/",                                 "trusted": True, "score": 6},
    {"name": "InfoQ",                   "url": "https://feed.infoq.com/",                                               "trusted": True, "score": 6},
    {"name": "Phoronix",                "url": "https://www.phoronix.com/rss.php",                                      "trusted": True, "score": 5},
    {"name": "Netflix Tech Blog",       "url": "https://netflixtechblog.com/feed",                                      "trusted": True, "score": 6},

    # =========================================================================
    # TIER 8 — COMPANY NEWSROOMS & SPECIALIST VERTICALS  (score 5-7)
    # =========================================================================
    {"name": "Apple Newsroom",          "url": "https://www.apple.com/newsroom/rss-feed.xml",                           "trusted": True, "score": 7},
    {"name": "Samsung Newsroom",        "url": "https://news.samsung.com/global/feed",                                  "trusted": True, "score": 6},
    {"name": "Meta Newsroom",           "url": "https://about.fb.com/feed/",                                            "trusted": True, "score": 6},
    {"name": "Tesla Blog",              "url": "https://www.tesla.com/blog/rss.xml",                                    "trusted": True, "score": 6},
    {"name": "SpaceNews",               "url": "https://spacenews.com/feed/",                                           "trusted": True, "score": 7},
    {"name": "The Robot Report",        "url": "https://www.therobotreport.com/feed/",                                  "trusted": True, "score": 7},

    # =========================================================================
    # TIER 9 — DISCOVERY ONLY  (trusted: False, score 0)
    # Never the sole confirmation of a story. Used only to surface stories
    # that are then verified via trusted outlets in the same cluster.
    # =========================================================================
    {"name": "Google News — Tech",
     "url": "https://news.google.com/rss/search?q=technology+when:1d&hl=en-US&gl=US&ceid=US:en",
     "trusted": False, "score": 0},
    {"name": "Google News — AI",
     "url": "https://news.google.com/rss/search?q=artificial+intelligence+when:1d&hl=en-US&gl=US&ceid=US:en",
     "trusted": False, "score": 0},
    {"name": "Google News — Cybersecurity",
     "url": "https://news.google.com/rss/search?q=cybersecurity+breach+when:1d&hl=en-US&gl=US&ceid=US:en",
     "trusted": False, "score": 0},
    {"name": "Google News — Semiconductors",
     "url": "https://news.google.com/rss/search?q=chip+semiconductor+nvidia+when:1d&hl=en-US&gl=US&ceid=US:en",
     "trusted": False, "score": 0},
    {"name": "Hacker News Frontpage",
     "url": "https://hnrss.org/frontpage",
     "trusted": False, "score": 0},
    {"name": "Reddit r/technology",
     "url": "https://www.reddit.com/r/technology/.rss",
     "trusted": False, "score": 0},
    {"name": "Reddit r/MachineLearning",
     "url": "https://www.reddit.com/r/MachineLearning/.rss",
     "trusted": False, "score": 0},
]

# ---------------------------------------------------------------------------
# 2. TIME WINDOW
# ---------------------------------------------------------------------------
LOOKBACK_HOURS = 36   # consider articles from the last N hours (36h prevents
                      # missing a story that broke just outside 24h on a quiet day)

# ---------------------------------------------------------------------------
# 3. PER-FEED ARTICLE LIMIT
# ---------------------------------------------------------------------------
MAX_ARTICLES_PER_FEED = 6   # fetch at most this many recent articles per feed.
                             # Prevents timeout when a single feed has 50+ entries.

# ---------------------------------------------------------------------------
# 4. STORY CLUSTERING (deduplication)
# ---------------------------------------------------------------------------
SIMILARITY_THRESHOLD = 0.58  # 0-1. Higher = stricter "same story" grouping.

# ---------------------------------------------------------------------------
# 5. IMPORTANCE KEYWORDS  (boost score if found in title/text)
# ---------------------------------------------------------------------------
IMPORTANCE_KEYWORDS = [
    # AI companies & models
    "ai", "artificial intelligence", "openai", "anthropic", "google", "deepmind",
    "gpt", "gemini", "claude", "llm", "copilot", "chatbot", "large language model",
    # Hardware & chips
    "nvidia", "apple", "microsoft", "meta", "amazon", "chip", "semiconductor",
    "quantum", "gpu", "processor", "intel", "amd", "qualcomm", "tsmc",
    # Business events
    "funding", "raises", "acquisition", "ipo", "merger", "layoffs", "bankrupt",
    "antitrust", "lawsuit", "regulation", "fine",
    # Security
    "cybersecurity", "breach", "hack", "ransomware", "vulnerability",
    "zero-day", "exploit", "phishing", "malware",
    # Robotics & physical tech
    "robotics", "robot", "autonomous", "self-driving", "ev", "battery",
    # Breakthroughs & launches
    "breakthrough", "launch", "model", "release", "open source",
    # Infrastructure & connectivity
    "5g", "6g", "satellite", "spacex", "nasa",
    # Privacy & policy
    "privacy", "gdpr", "surveillance", "biometric",
]
KEYWORD_BONUS = 1.5          # points per unique keyword hit (capped below)
KEYWORD_BONUS_CAP = 12.0     # raised from 9 — more keywords available now

# ---------------------------------------------------------------------------
# 6. ANTI-CLICKBAIT PENALTY
# ---------------------------------------------------------------------------
CLICKBAIT_PATTERNS = [
    r"you won'?t believe", r"shocking", r"mind-?blowing", r"this is why",
    r"will blow your mind", r"\bgone wrong\b", r"insane", r"jaw-?dropping",
    r"number \d+ will", r"what happens next",
]
CLICKBAIT_PENALTY = 6.0
ALLCAPS_PENALTY = 3.0

# ---------------------------------------------------------------------------
# 7. RECENCY BONUS
# ---------------------------------------------------------------------------
RECENCY_BONUS = 2.0          # added if the freshest article is < 6h old

# ---------------------------------------------------------------------------
# 8. SELECTION
# ---------------------------------------------------------------------------
MAX_STORIES_PER_DAY = 2      # send at most this many stories per run
MIN_SCORE_TO_SEND = 5.0      # lowered from 5.5 to 5.0. With 90+ feeds there will
                             # nearly always be a qualifying story.
                             # Do NOT go below 4.0 or weak news slips in.
                             # Use diagnose.py to see real scores and tune.

# ---------------------------------------------------------------------------
# 9. LLM SETTINGS  (Google Gemini — free tier)
# ---------------------------------------------------------------------------
DEFAULT_LLM_MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

MAX_CHARS_PER_ARTICLE = 6000
MAX_ARTICLES_PER_STORY = 3
MAX_FACTCHECK_REGEN = 1

# ---------------------------------------------------------------------------
# 10. HTTP
# ---------------------------------------------------------------------------
HTTP_TIMEOUT = 15            # reduced from 20 — faster failure for blocked sites
FETCH_DELAY_SECONDS = 0.5    # reduced from 1.0 — still polite, but 90+ feeds
                             # need to finish within the GitHub Actions window.
                             # Raise to 1.0 if you see persistent 429 errors.
MIN_RSS_TEXT_CHARS = 50      # minimum chars required for an RSS summary fallback.
                             # BBC, Reuters, NYT summaries are often 50-100 chars
                             # after HTML stripping — 150 was silently dropping them.
USER_AGENT = (
    "Mozilla/5.0 (compatible; TechNewsBot/1.0; "
    "+personal-automation; respectful-fetch)"
)
