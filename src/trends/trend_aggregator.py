import random
from datetime import datetime
from src.trends.google_trends  import get_google_trends
from src.trends.youtube_trends import get_youtube_trends
from src.trends.news_trends    import get_news_trends
from src.utils.history_manager import HistoryManager
from src.utils.logger          import log


class TrendAggregator:
    """Collect, rank, deduplicate and select the best trending topic."""

    FALLBACKS = [
        "Amazing Science Discoveries That Shocked The World",
        "Top Technology Breakthroughs Happening Right Now",
        "Mind-Blowing Space Discoveries You Never Heard Of",
        "Incredible Historical Events That Changed Everything",
        "Future Technology That Will Blow Your Mind",
        "Psychology Facts About Human Behavior",
        "Mysterious Unsolved Mysteries Around The World",
        "Extreme Weather Events Breaking Records",
        "Artificial Intelligence Changing Our Daily Lives",
        "Wildlife Facts That Will Amaze You",
    ]

    def __init__(self):
        self.history = HistoryManager()

    def get_best_topic(self) -> dict:
        log.info("━" * 55)
        log.info("STEP 1 │ Aggregating trends from all sources")
        log.info("━" * 55)

        raw = []

        for name, fn in [
            ("Google Trends",    get_google_trends),
            ("YouTube Trending", get_youtube_trends),
            ("News / RSS",       get_news_trends),
        ]:
            try:
                items = fn()
                raw.extend(items)
                log.info(f"  ✓ {name:<20} {len(items)} topics")
            except Exception as e:
                log.warning(f"  ✗ {name}: {e}")

        if not raw:
            log.warning("All sources failed — using fallback list")
            raw = [{'topic': t, 'source': 'fallback', 'score': 55}
                   for t in self.FALLBACKS]

        # Deduplicate
        unique   = self._deduplicate(raw)
        # Filter already-covered topics
        fresh    = [t for t in unique if not self.history.is_duplicate(t['topic'])]

        if not fresh:
            log.warning("All topics were recently covered — reusing oldest")
            fresh = unique[:5]

        # Pick from top-5 scored topics (with randomness)
        top5     = sorted(fresh, key=lambda x: x.get('score', 50), reverse=True)[:5]
        selected = random.choice(top5)

        content_type = self._pick_content_type()
        language     = self._pick_language(selected)

        log.info(f"\n  ► Topic   : {selected['topic']}")
        log.info(f"  ► Type    : {content_type}")
        log.info(f"  ► Language: {language}")
        log.info(f"  ► Source  : {selected.get('source')}")

        return {
            'topic':        selected['topic'],
            'source':       selected.get('source', ''),
            'description':  selected.get('description', ''),
            'content_type': content_type,
            'language':     language,
            'score':        selected.get('score', 50),
        }

    # ── helpers ──────────────────────────────────────────────

    def _deduplicate(self, items: list) -> list:
        seen, out = set(), []
        for item in items:
            key = ' '.join(sorted(item['topic'].lower().split())[:6])
            if key not in seen and len(item['topic']) > 8:
                seen.add(key)
                out.append(item)
        return out

    def _pick_content_type(self) -> str:
        """Every 3rd video is a long-form; others are Shorts."""
        count = self.history.uploads_today()
        return 'long_video' if count % 3 == 0 else 'short'

    def _pick_language(self, item: dict) -> str:
        src = item.get('source', '')
        if any(x in src.lower() for x in ['india', '_IN', 'hindi', 'hi_']):
            return 'hi'
        return 'en'
