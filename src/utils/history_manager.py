import json
import os
from datetime import datetime, timedelta


class HistoryManager:

    def __init__(self):
        base = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.path = os.path.join(base, 'data', 'upload_history.json')
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {'uploads': [], 'topics': []}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.data['uploads'] = self.data.get('uploads', [])[-500:]
        self.data['topics']  = self.data.get('topics',  [])[-1000:]
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def is_duplicate(self, topic):
        cutoff = (datetime.utcnow() - timedelta(hours=48)).isoformat()
        for entry in self.data.get('topics', []):
            if entry.get('ts', '') < cutoff:
                continue
            if self._sim(topic.lower(), entry.get('topic', '').lower()) > 0.6:
                return True
        return False

    def record(self, topic, video_id, content_type, language, title):
        now = datetime.utcnow().isoformat()
        self.data.setdefault('uploads', []).append({
            'video_id': video_id, 'title': title,
            'topic': topic, 'type': content_type,
            'language': language, 'ts': now,
        })
        self.data.setdefault('topics', []).append(
            {'topic': topic, 'ts': now}
        )
        self._save()

    def uploads_today(self):
        today = datetime.utcnow().date().isoformat()
        return sum(
            1 for e in self.data.get('uploads', [])
            if e.get('ts', '').startswith(today)
        )

    @staticmethod
    def _sim(a, b):
        wa, wb = set(a.split()), set(b.split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)
