import os
import re
import random
import time
import urllib.parse
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from src.utils.config import Config
from src.utils.logger import log


class ImageFetcher:

    HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }

    def __init__(self):
        self.out = Config.TEMP_ASSETS

    def fetch_for_script(self, script_data):
        scenes       = script_data.get('scenes', [])
        content_type = script_data.get('content_type', 'long_video')
        topic        = script_data.get('topic', 'trending')
        results      = []

        for i, scene in enumerate(scenes):
            query = self._clean(scene.get('visual_query', topic))
            path  = self._fetch_best(query, i, content_type, topic)
            results.append({
                'path': path, 'scene_index': i, 'query': query
            })
            log.info(f"  Image {i+1}/{len(scenes)}: '{query}'")
            time.sleep(0.5)

        return results

    def _fetch_best(self, query, idx, ctype, topic):
        """Try sources in quality order."""
        sources = [
            # Best quality first
            lambda: self._pexels(query, idx, ctype),
            lambda: self._pexels(topic[:30], idx, ctype),
            lambda: self._unsplash(query, idx, ctype),
            lambda: self._pollinations_photo(query, idx, ctype),
            lambda: self._picsum_random(idx, ctype),
            lambda: self._pollinations_art(query, idx, ctype),
        ]

        for fn in sources:
            try:
                p = fn()
                if p and os.path.exists(p):
                    size = os.path.getsize(p)
                    if size > 15000:
                        # Enhance the image
                        enhanced = self._enhance(p, ctype)
                        return enhanced if enhanced else p
            except Exception as e:
                log.debug(f"Image source error: {e}")

        return self._generate_placeholder(query, idx, ctype)

    def _pexels(self, query, idx, ctype):
        """Pexels - highest quality photos."""
        if not Config.PEXELS_API_KEY:
            return None
        orient = 'portrait' if ctype == 'short' else 'landscape'
        try:
            resp = requests.get(
                'https://api.pexels.com/v1/search',
                headers={'Authorization': Config.PEXELS_API_KEY},
                params={
                    'query':       query,
                    'per_page':    15,
                    'orientation': orient,
                    'size':        'large',
                    'page':        random.randint(1, 5),
                },
                timeout=12,
            )
            if resp.status_code == 200:
                photos = resp.json().get('photos', [])
                if photos:
                    photo = random.choice(photos)
                    url   = photo['src'].get('original',
                                             photo['src']['large2x'])
                    return self._download(url, f'pexels_{idx}')
            elif resp.status_code == 429:
                log.debug("Pexels rate limit")
        except Exception as e:
            log.debug(f"Pexels error: {e}")
        return None

    def _unsplash(self, query, idx, ctype):
        """Unsplash Source - free, high quality."""
        try:
            w, h = (1080, 1920) if ctype == 'short' else (1920, 1080)
            q    = urllib.parse.quote(query.replace(' ', ','))
            seed = random.randint(1, 9999)
            url  = f"https://source.unsplash.com/{w}x{h}/?{q}&sig={seed}"
            return self._download(url, f'unsplash_{idx}', timeout=20)
        except Exception as e:
            log.debug(f"Unsplash error: {e}")
        return None

    def _pollinations_photo(self, query, idx, ctype):
        """
        Pollinations AI - generates realistic photos.
        Uses photorealistic style prompt.
        """
        try:
            w, h = (1080, 1920) if ctype == 'short' else (1920, 1080)
            enhanced_prompt = (
                f"{query}, "
                f"photorealistic, professional photography, "
                f"high resolution, sharp focus, dramatic lighting, "
                f"cinematic, 8k quality, vibrant colors"
            )
            encoded = urllib.parse.quote(enhanced_prompt)
            seed    = random.randint(1, 99999)
            url     = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width={w}&height={h}&seed={seed}"
                f"&model=flux&nologo=true&enhance=true"
            )
            return self._download(url, f'poll_photo_{idx}', timeout=60)
        except Exception as e:
            log.debug(f"Pollinations photo error: {e}")
        return None

    def _pollinations_art(self, query, idx, ctype):
        """Pollinations AI - artistic style as fallback."""
        try:
            w, h = (1080, 1920) if ctype == 'short' else (1920, 1080)
            enhanced_prompt = (
                f"{query}, "
                f"digital art, highly detailed, "
                f"vibrant, professional quality, 4k"
            )
            encoded = urllib.parse.quote(enhanced_prompt)
            seed    = random.randint(1, 99999)
            url     = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width={w}&height={h}&seed={seed}&nologo=true"
            )
            return self._download(url, f'poll_art_{idx}', timeout=60)
        except Exception as e:
            log.debug(f"Pollinations art error: {e}")
        return None

    def _picsum_random(self, idx, ctype):
        """Lorem Picsum - random beautiful photos."""
        try:
            w, h = (1080, 1920) if ctype == 'short' else (1920, 1080)
            seed = random.randint(1, 1000)
            url  = f"https://picsum.photos/seed/{seed}/{w}/{h}"
            return self._download(url, f'picsum_{idx}', timeout=15)
        except Exception as e:
            log.debug(f"Picsum error: {e}")
        return None

    def _enhance(self, img_path, ctype):
        """Enhance image quality - sharpen, contrast, brightness."""
        try:
            from PIL import ImageEnhance, ImageFilter
            img = Image.open(img_path).convert('RGB')

            # Target size
            W, H = (1080, 1920) if ctype == 'short' else (1920, 1080)

            # Smart cover crop
            ir = img.width / img.height
            fr = W / H
            if ir > fr:
                new_h = H
                new_w = int(H * ir)
            else:
                new_w = W
                new_h = int(W / ir)

            img  = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            left = (new_w - W) // 2
            top  = (new_h - H) // 2
            img  = img.crop((left, top, left + W, top + H))

            # Enhance quality
            img = ImageEnhance.Sharpness(img).enhance(1.4)
            img = ImageEnhance.Contrast(img).enhance(1.15)
            img = ImageEnhance.Color(img).enhance(1.2)

            enhanced_path = img_path.replace('.jpg', '_enhanced.jpg')
            img.save(enhanced_path, 'JPEG', quality=95)
            return enhanced_path

        except Exception as e:
            log.debug(f"Image enhance error: {e}")
        return None

    def _download(self, url, prefix, timeout=20):
        try:
            resp = requests.get(
                url, headers=self.HEADERS,
                timeout=timeout, stream=True,
                allow_redirects=True
            )
            if resp.status_code == 200:
                path = os.path.join(self.out, f'{prefix}.jpg')
                with open(path, 'wb') as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                if os.path.getsize(path) > 10000:
                    return path
        except Exception as e:
            log.debug(f"Download [{prefix}]: {e}")
        return None

    def _clean(self, query):
        q = re.sub(r'[^\w\s]', ' ', str(query))
        q = ' '.join(q.split()[:5]).strip()
        return q or 'nature landscape'

    def _generate_placeholder(self, query, idx, ctype):
        """
        Generate a high-quality AI-style placeholder
        using PIL with gradients and text.
        """
        W, H   = (1080, 1920) if ctype == 'short' else (1920, 1080)
        c1, c2 = Config.random_palette()

        # Create base gradient
        img  = Image.new('RGB', (W, H))
        draw = ImageDraw.Draw(img)

        for y in range(H):
            ratio = y / H
            r = int(c1[0] * (1-ratio) + c2[0] * ratio)
            g = int(c1[1] * (1-ratio) + c2[1] * ratio)
            b = int(c1[2] * (1-ratio) + c2[2] * ratio)
            draw.line([(0, y), (W, y)], fill=(r, g, b))

        # Add geometric patterns for visual interest
        for _ in range(8):
            x1 = random.randint(0, W)
            y1 = random.randint(0, H)
            x2 = random.randint(0, W)
            y2 = random.randint(0, H)
            alpha_color = (
                random.randint(200, 255),
                random.randint(200, 255),
                random.randint(200, 255),
            )
            draw.line([(x1, y1), (x2, y2)],
                      fill=alpha_color, width=2)

        # Add circles
        for _ in range(5):
            cx = random.randint(W//4, 3*W//4)
            cy = random.randint(H//4, 3*H//4)
            r  = random.randint(W//8, W//3)
            draw.ellipse(
                [cx-r, cy-r, cx+r, cy+r],
                outline=(255, 255, 255),
                width=3
            )

        # Add query text
        font_size = W // 20
        try:
            font_path = os.path.join(Config.FONTS_DIR, 'Bold.ttf')
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        text = query.upper()[:30]
        try:
            bb = draw.textbbox((0, 0), text, font=font)
            tw = bb[2] - bb[0]
            x  = (W - tw) // 2
            y  = (H - font_size) // 2
            # Shadow
            draw.text((x+3, y+3), text, font=font,
                      fill=(0, 0, 0))
            draw.text((x, y), text, font=font,
                      fill=(255, 255, 255))
        except Exception:
            pass

        # Apply subtle blur for smoothness
        img  = img.filter(ImageFilter.GaussianBlur(radius=1))
        path = os.path.join(self.out, f'placeholder_{idx}.jpg')
        img.save(path, 'JPEG', quality=92)
        return path
