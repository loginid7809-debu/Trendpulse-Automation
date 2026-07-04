import random
from datetime import datetime
from src.trends.google_trends  import get_google_trends
from src.trends.youtube_trends import get_youtube_trends
from src.trends.news_trends    import get_news_trends
from src.utils.history_manager import HistoryManager
from src.utils.logger          import log


class TrendAggregator:

    FALLBACKS = [
        "Amazing Science Discoveries That Shocked The World",
        "Top Technology Breakthroughs Happening Right Now",
        "Mind-Blowing Space Discoveries You Never Heard Of",
        "Incredible Historical Events That Changed Everything",
        "Future Technology That Will Blow Your Mind",
        "Psychology Facts About Human Behavior",
        "Mysterious Unsolved Mysteries Around The World",
        "Artificial Intelligence Changing Our Daily Lives",
        "Wildlife Facts That Will Amaze You",
        "Extreme Weather Events Breaking Records",
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
            raw = [{'topic': t, 'source': 'fallback', 'score': 55}
                   for t in self.FALLBACKS]

        unique = self._dedup(raw)
        fresh  = [t for t in unique
                  if not self.history.is_duplicate(t['topic'])]

        if not fresh:
            log.warning("All topics covered recently, reusing")
            fresh = unique[:5]

        top5     = sorted(fresh,
                          key=lambda x: x.get('score', 50),
                          reverse=True)[:5]
        selected = random.choice(top5)

        ctype    = self._content_type()
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
            key = ' '.join(sorted(item['topic'].lower().split())[:6])
            if key not in seen and len(item['topic']) > 8:
                seen.add(key)
                out.append(item)
        return out

    def _content_type(self):
        count = self.history.uploads_today()
        return 'long_video' if count % 3 == 0 else 'short'

    def _language(self, item):
        src = item.get('source', '')
        if any(x in src.lower() for x in ['india', '_in', 'hindi']):
            return 'hi'
        return 'en'
