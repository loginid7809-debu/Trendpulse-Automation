import requests
import json
import random
from src.utils.logger import log


def get_youtube_trends(limit=10):
    results = []
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept-Language': 'en-US,en;q=0.9',
    }
    for region in ['US', 'IN', 'GB']:
        try:
            url  = f'https://www.youtube.com/feed/trending?gl={region}'
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            titles = _extract(resp.text)
            for title in titles[:4]:
                results.append({
                    'topic':  title,
                    'source': f'youtube_{region}',
                    'score':  random.randint(80, 100),
                })
        except Exception as e:
            log.debug(f"YouTube Trending [{region}]: {e}")
    log.info(f"YouTube Trending: {len(results)} topics")
    return results[:limit]


def _extract(html):
    titles = []
    try:
        marker = 'var ytInitialData = '
        idx = html.find(marker)
        if idx == -1:
            return titles
        json_str = html[idx + len(marker):]
        depth = end = 0
        for i, ch in enumerate(json_str):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        data = json.loads(json_str[:end])
        _walk(data, titles)
    except Exception as e:
        log.debug(f"YT extract error: {e}")
    seen, unique = set(), []
    for t in titles:
        if t not in seen and len(t) > 8:
            seen.add(t)
            unique.append(t)
    return unique


def _walk(obj, titles):
    if isinstance(obj, dict):
        if 'title' in obj:
            t = obj['title']
            if isinstance(t, dict):
                text = t.get('simpleText', '')
                if not text and 'runs' in t:
                    text = ''.join(r.get('text', '') for r in t['runs'])
                if text and len(text) > 8:
                    titles.append(text)
        for v in obj.values():
            _walk(v, titles)
    elif isinstance(obj, list):
        for item in obj:
            _walk(item, titles)
