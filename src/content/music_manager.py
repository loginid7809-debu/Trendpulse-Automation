import os
import random
import requests
from src.utils.config import Config
from src.utils.logger import log


class MusicManager:
    """Download royalty-free background music (Pixabay CDN — no account needed)."""

    def __init__(self):
        self.out = Config.TEMP_ASSETS

    def get_music(self) -> str | None:
        urls = Config.MUSIC_URLS.copy()
        random.shuffle(urls)

        for url in urls:
            try:
                resp = requests.get(url, timeout=20, stream=True)
                if resp.status_code == 200:
                    path = os.path.join(self.out, 'bg_music.mp3')
                    with open(path, 'wb') as f:
                        for chunk in resp.iter_content(8192):
                            f.write(chunk)
                    if os.path.getsize(path) > 20_000:
                        log.info("Background music downloaded ✓")
                        return path
            except Exception as e:
                log.debug(f"Music download failed [{url}]: {e}")

        log.warning("All music sources failed — video will have no background music")
        return None
