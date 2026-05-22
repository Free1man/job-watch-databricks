"""Configuration for the public RSS/search job watcher."""

MIN_RATE = 125

# Authorized direct scraping is on by default per current project scope.
# Keep this polite: allowlisted URLs only, low rate, no auth bypass, no evasion.
DIRECT_SCRAPE_ENABLED = True

ROLE_KEYWORDS = [
    "software developer",
    "software engineer",
    "senior developer",
    "senior software engineer",
    "full stack",
    "full-stack",
    "technical lead",
    "tech lead",
    "solution architect",
    "payments architect",
    ".net",
    "aws",
    "backend",
    "back end",
]

SEARCH_SOURCES = [
    {
        "source": "bing_seek",
        "type": "bing_rss",
        "allowed_domains": ["seek.co.nz", "www.seek.co.nz", "nz.seek.com"],
        "queries": [
            'site:seek.co.nz/job Auckland contract "software developer"',
            'site:seek.co.nz/job Auckland contract "software engineer"',
            'site:seek.co.nz/job Auckland contract "senior developer"',
            'site:seek.co.nz/job Auckland contract "senior software engineer"',
            'site:seek.co.nz/job Auckland contract "full stack"',
            'site:seek.co.nz/job Auckland contract "technical lead"',
            'site:seek.co.nz/job Auckland contract "solution architect"',
            'site:seek.co.nz/job Auckland contract "payments architect"',
            'site:seek.co.nz/job Auckland contract ".NET"',
            'site:seek.co.nz/job Auckland contract "AWS"',
            'site:seek.co.nz/job Auckland "$125"',
            'site:seek.co.nz/job Auckland "$130"',
            'site:seek.co.nz/job Auckland "$140"',
        ],
    },
    {
        "source": "bing_trademe",
        "type": "bing_rss",
        "allowed_domains": ["trademe.co.nz", "www.trademe.co.nz"],
        "queries": [
            'site:trademe.co.nz/a/jobs Auckland contract "software developer"',
            'site:trademe.co.nz/a/jobs Auckland contract "software engineer"',
            'site:trademe.co.nz/a/jobs Auckland contract "senior developer"',
            'site:trademe.co.nz/a/jobs Auckland contract "technical lead"',
            'site:trademe.co.nz/a/jobs Auckland contract "solution architect"',
            'site:trademe.co.nz/a/jobs Auckland "$125"',
            'site:trademe.co.nz/a/jobs Auckland "$130"',
        ],
    },
    {
        "source": "bing_indeed",
        "type": "bing_rss",
        "allowed_domains": ["nz.indeed.com", "indeed.com"],
        "queries": [
            'site:nz.indeed.com Auckland contract "software developer"',
            'site:nz.indeed.com Auckland contract "software engineer"',
            'site:nz.indeed.com Auckland contract "senior developer"',
            'site:nz.indeed.com Auckland contract "technical lead"',
        ],
    },
]

DIRECT_SOURCES = [
    {
        "source": "direct_seek",
        "type": "direct_html",
        "allowed_domains": ["seek.co.nz", "www.seek.co.nz"],
        "respect_robots_txt": True,
        "delay_seconds": 2,
        "urls": [
            "https://www.seek.co.nz/software-developer-contract-jobs/in-All-Auckland",
            "https://www.seek.co.nz/software-engineer-contract-jobs/in-All-Auckland",
            "https://www.seek.co.nz/technical-lead-contract-jobs/in-All-Auckland",
        ],
    },
    {
        "source": "direct_trademe",
        "type": "direct_html",
        "allowed_domains": ["trademe.co.nz", "www.trademe.co.nz"],
        "respect_robots_txt": True,
        "delay_seconds": 2,
        "urls": [
            "https://www.trademe.co.nz/a/jobs/it/programming-development/auckland/search?search_string=software%20developer%20contract",
            "https://www.trademe.co.nz/a/jobs/it/programming-development/auckland/search?search_string=software%20engineer%20contract",
            "https://www.trademe.co.nz/a/jobs/it/programming-development/auckland/search?search_string=technical%20lead%20contract",
            "https://www.trademe.co.nz/a/jobs/it/programming-development/auckland",
        ],
    },
]

CUSTOM_RSS_FEEDS = []
