import requests
import feedparser
import random
from src.utils.config import Config
from src.utils.logger import log

# Free RSS feeds — zero API key needed
RSS_FEEDS = [
    'https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en',
    'https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en',
    'http://feeds.bbci.co.uk/news/rss.xml',
    'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',
    'https://feeds.reuters.com/reuters/topNews',
    'https://rss.cnn.com/rss/edition.rss',
    'https://www.theguardian.com/world/rss',
    'https://feeds.feedburner.com/TechCrunch',
    'https://www.nasa.gov/rss/dyn/breaking_news.rss',
    'https://www.sciencedaily.com/rss/top.xml',
]


def get_news_trends(limit: int = 15) -> list:
    """Fetch trending headlines from RSS feeds + NewsAPI."""
    results = []

    # 1. NewsAPI (free tier — 100 req/day)
    results.extend(_fetch_newsapi())

    # 2. RSS Feeds (unlimited, no key)
    results.extend(_fetch_rss())

    log.info(f"News trends → {len(results)} topics")
    return results[:limit]


def _fetch_newsapi() -> list:
    results = []
    if not Config.NEWS_API_KEY:
        return results
    try:
        resp = requests.get(
            'https://newsapi.org/v2/top-headlines',
            params={'language': 'en', 'pageSize': 10,
                    'apiKey': Config.NEWS_API_KEY},
            timeout=10,
        )
        if resp.status_code == 200:
            for art in resp.json().get('articles', []):
                title = art.get('title', '')
                if title and '[Removed]' not in title:
                    results.append({
                        'topic':       title,
                        'source':      'newsapi',
                        'description': art.get('description', ''),
                        'score':       random.randint(70, 90),
                    })
    except Exception as e:
        log.debug(f"NewsAPI: {e}")
    return results


def _fetch_rss() -> list:
    results = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                title = entry.get('title', '').strip()
                if title and len(title) > 10:
                    results.append({
                        'topic':       title,
                        'source':      f"rss_{feed_url.split('/')[2]}",
                        'description': entry.get('summary', ''),
                        'score':       random.randint(60, 80),
                    })
        except Exception as e:
            log.debug(f"RSS [{feed_url}]: {e}")
    return results
