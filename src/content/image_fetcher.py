import os
import random
import time
import urllib.parse
import requests
from PIL import Image, ImageDraw
from src.utils.config import Config
from src.utils.logger import log


class ImageFetcher:
    """
    Fetch royalty-free images.
    Priority: Pexels → Unsplash Source → Picsum → Pollinations AI → Placeholder
    """

    HEADERS = {'User-Agent': 'TrendPulse/1.0 (open-source automation)'}

    def __init__(self):
        self.out = Config.TEMP_ASSETS

    def fetch_for_script(self, script_data: dict) -> list:
        scenes       = script_data.get('scenes', [])
        content_type = script_data.get('content_type', 'long_video')
        topic        = script_data.get('topic', 'trending')
        results      = []

        for i, scene in enumerate(scenes):
            query = self._clean(scene.get('visual_query', topic))
            path  = self._best(query, i, content_type)
            results.append({'path': path, 'scene_index': i, 'query': query})
            log.info(f"  ✓ Image {i+1}/{len(scenes)}  query='{query}'")
            time.sleep(0.4)   # gentle throttle

        return results

    # ── source waterfall ─────────────────────────────────────

    def _best(self, query: str, idx: int, ctype: str) -> str:
        for fn in [
            lambda: self._pexels(query, idx, ctype),
            lambda: self._unsplash(query, idx, ctype),
            lambda: self._picsum(idx, ctype),
            lambda: self._pollinations(query, idx, ctype),
        ]:
            try:
                p = fn()
                if p and os.path.exists(p) and os.path.getsize(p) > 8000:
                    return p
            except Exception as e:
                log.debug(f"Image source error: {e}")
        return self._placeholder(idx, ctype)

    def _pexels(self, query: str, idx: int, ctype: str) -> str | None:
        if not Config.PEXELS_API_KEY:
            return None
        orient = 'portrait' if ctype == 'short' else 'landscape'
        resp = requests.get(
            'https://api.pexels.com/v1/search',
            headers={'Authorization': Config.PEXELS_API_KEY},
            params={'query': query, 'per_page': 10,
                    'orientation': orient, 'size': 'large',
                    'page': random.randint(1, 3)},
            timeout=10,
        )
        if resp.status_code == 429:
            log.debug("Pexels rate limit — skipping")
            return None
        if resp.status_code == 200:
            photos = resp.json().get('photos', [])
            if photos:
                url = random.choice(photos)['src']['large2x']
                return self._download(url, f'pexels_{idx}')
        return None

    def _unsplash(self, query: str, idx: int, ctype: str) -> str | None:
        w, h = (1080, 1920) if ctype == 'short' else (1920, 1080)
        q    = urllib.parse.quote(query.replace(' ', ','))
        seed = random.randint(1, 9999)
        url  = f"https://source.unsplash.com/{w}x{h}/?{q}&sig={seed}"
        return self._download(url, f'unsplash_{idx}', stream=True)

    def _picsum(self, idx: int, ctype: str) -> str | None:
        w, h = (1080, 1920) if ctype == 'short' else (1920, 1080)
        seed = random.randint(1, 1000)
        url  = f"https://picsum.photos/seed/{seed}/{w}/{h}"
        return self._download(url, f'picsum_{idx}', stream=True)

    def _pollinations(self, query: str, idx: int, ctype: str) -> str | None:
        w, h    = (1080, 1920) if ctype == 'short' else (1920, 1080)
        prompt  = urllib.parse.quote(
            f"{query}, high quality, cinematic, 4k, detailed"
        )
        seed    = random.randint(1, 99999)
        url     = (f"https://image.pollinations.ai/prompt/{prompt}"
                   f"?width={w}&height={h}&seed={seed}&nologo=true")
        return self._download(url, f'pollinations_{idx}', stream=True,
                              timeout=45)

    # ── utilities ─────────────────────────────────────────────

    def _download(self, url: str, prefix: str,
                  stream: bool = True,
                  timeout: int = 15) -> str | None:
        try:
            resp = requests.get(url, headers=self.HEADERS,
                                timeout=timeout, stream=stream,
                                allow_redirects=True)
            if resp.status_code == 200:
                path = os.path.join(self.out, f'{prefix}.jpg')
                with open(path, 'wb') as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                if os.path.getsize(path) > 8000:
                    return path
        except Exception as e:
            log.debug(f"Download error [{prefix}]: {e}")
        return None

    @staticmethod
    def _clean(query: str) -> str:
        import re
        q = re.sub(r'[^\w\s]', ' ', query)
        return ' '.join(q.split()[:5]).strip() or 'nature landscape'

    def _placeholder(self, idx: int, ctype: str) -> str:
        """Gradient image — never fails."""
        w, h   = (1080, 1920) if ctype == 'short' else (1920, 1080)
        c1, c2 = Config.random_palette()
        img    = Image.new('RGB', (w, h))
        draw   = ImageDraw.Draw(img)
        for y in range(h):
            r = int(c1[0] + (c2[0]-c1[0]) * y / h)
            g = int(c1[1] + (c2[1]-c1[1]) * y / h)
            b = int(c1[2] + (c2[2]-c1[2]) * y / h)
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        path = os.path.join(self.out, f'placeholder_{idx}.jpg')
        img.save(path, 'JPEG', quality=90)
        return path
