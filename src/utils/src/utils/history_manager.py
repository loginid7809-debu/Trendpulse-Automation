import json
import os
from datetime import datetime, timedelta
from src.utils.config import Config
from src.utils.logger import log


class HistoryManager:
    """Track uploaded videos to avoid repeating topics."""

    def __init__(self):
        self.path    = Config.HISTORY_FILE
        self.history = self._load()

    # ── Public API ────────────────────────────────────────────

    def is_duplicate(self, topic: str) -> bool:
        """Return True if this topic was covered in the last 72 hours."""
        cutoff = (datetime.utcnow() - timedelta(hours=72)).isoformat()
        for entry in self.history.get('topics', []):
            if entry['ts'] < cutoff:
                continue
            if self._jaccard(topic.lower(), entry['topic'].lower()) > 0.65:
                return True
        return False

    def record(self, topic: str, video_id: str,
               content_type: str, language: str, title: str):
        now = datetime.utcnow().isoformat()
        self.history.setdefault('uploads', []).append({
            'video_id':    video_id,
            'title':       title,
            'topic':       topic,
            'type':        content_type,
            'language':    language,
            'ts':          now,
        })
        self.history.setdefault('topics', []).append({
            'topic': topic,
            'ts':    now,
        })
        self._trim()
        self._save()
        log.info(f"History updated → {len(self.history['uploads'])} total uploads")

    def uploads_today(self) -> int:
        today = datetime.utcnow().date().isoformat()
        return sum(
            1 for e in self.history.get('uploads', [])
            if e.get('ts', '').startswith(today)
        )

    # ── Private helpers ───────────────────────────────────────

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {'uploads': [], 'topics': []}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w') as f:
            json.dump(self.history, f, indent=2)

    def _trim(self):
        """Keep history files from growing unbounded."""
        self.history['uploads'] = self.history.get('uploads', [])[-500:]
        self.history['topics']  = self.history.get('topics',  [])[-1000:]

    @staticmethod
    def _jaccard(a: str, b: str) -> float:
        wa, wb = set(a.split()), set(b.split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)
