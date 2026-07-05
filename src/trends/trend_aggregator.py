import random
from datetime import datetime
from src.trends.google_trends  import get_google_trends
from src.trends.youtube_trends import get_youtube_trends
from src.trends.news_trends    import get_news_trends
from src.utils.history_manager import HistoryManager
from src.utils.logger          import log


class TrendAggregator:

    FALLBACKS = [
        "Amazing Science Discoveries Changing The World",
        "Top Technology Innovations Right Now",
        "Mind Blowing Space Discoveries Explained",
        "Incredible Historical Events You Never Knew",
        "Future Technology Coming In Next 5 Years",
        "Psychology Facts About Human Behavior",
        "Unsolved Mysteries That Baffle Scientists",
        "Artificial Intelligence Revolution 2024",
        "Wildlife Facts That Will Amaze You",
        "Climate Change Solutions Being Tested Now",
        "Hidden Secrets Of Ancient Civilizations",
        "Extreme Sports That Push Human Limits",
        "Medical Breakthroughs Saving Lives Today",
        "Ocean Mysteries Scientists Just Discovered",
        "How Billionaires Think Differently",
    ]

    def __init__(self):
        self.history = HistoryManager()

    def get_best_topic(self):
        log.info("Aggregating trends from all sources...")
        raw = []

        for name, fn in [
            ("Google Trends",    get_google_trends),
            ("YouTube Trending", get_youtube_trends),
            ("News/RSS",         get_news_trends),
        ]:
            try:
                items = fn()
                raw.extend(items)
                log.info(f"  {name}: {len(items)} topics")
            except Exception as e:
                log.warning(f"  {name} failed: {e}")

        if not raw:
            log.warning("All sources failed, using fallbacks")
            raw = [
                {'topic': t, 'source': 'fallback', 'score': 55}
                for t in self.FALLBACKS
            ]

        unique = self._dedup(raw)
        fresh  = [
            t for t in unique
            if not self.history.is_duplicate(t['topic'])
        ]

        if not fresh:
            log.warning("All topics covered recently, reusing")
            fresh = unique[:5]

        top5     = sorted(
            fresh, key=lambda x: x.get('score', 50), reverse=True
        )[:5]
        selected = random.choice(top5)

        # Alternate: every 3rd upload is a Short
        uploads  = self.history.uploads_today()
        ctype    = 'short' if (uploads % 3 == 2) else 'long_video'
        language = self._language(selected)

        log.info(f"Selected: '{selected['topic']}'")
        log.info(f"Type: {ctype} | Language: {language}")

        return {
            'topic':        selected['topic'],
            'source':       selected.get('source', ''),
            'description':  selected.get('description', ''),
            'content_type': ctype,
            'language':     language,
            'score':        selected.get('score', 50),
        }

    def _dedup(self, items):
        seen, out = set(), []
        for item in items:
            key = ' '.join(
                sorted(item['topic'].lower().split())[:6]
            )
            if key not in seen and len(item['topic']) > 8:
                seen.add(key)
                out.append(item)
        return out

    def _language(self, item):
        src = item.get('source', '')
        if any(x in src.lower() for x in ['india', '_in', 'hindi']):
            return 'hi'
        return 'en'
