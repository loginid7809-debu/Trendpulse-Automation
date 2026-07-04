import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from src.utils.config import Config
from src.utils.logger import log


class ThumbnailGenerator:

    def __init__(self):
        self.out   = Config.TEMP_DIR
        self.fonts = Config.FONTS_DIR

    def generate(self, script_data, bg_image_path=None):
        ctype = script_data.get('content_type', 'long_video')
        text  = script_data.get(
            'thumbnail_text', script_data.get('topic', 'TRENDING')
        )
        size  = (1080, 1920) if ctype == 'short' else (1280, 720)

        img = (self._from_image(bg_image_path, size)
               if bg_image_path and os.path.exists(bg_image_path)
               else self._gradient(size))

        img = self._overlay(img)
        img = self._text(img, text.upper(), size)
        img = self._brand(img, size)

        out = os.path.join(self.out, 'thumbnail.jpg')
        img.convert('RGB').save(out, 'JPEG', quality=95)
        log.info(f"Thumbnail: {size[0]}x{size[1]}")
        return out

    def _gradient(self, size):
        c1, c2 = Config.random_palette()
        img    = Image.new('RGB', size)
        draw   = ImageDraw.Draw(img)
        w, h   = size
        for y in range(h):
            r = int(c1[0] + (c2[0] - c1[0]) * y / h)
            g = int(c1[1] + (c2[1] - c1[1]) * y / h)
            b = int(c1[2] + (c2[2] - c1[2]) * y / h)
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        return img

    def _from_image(self, path, size):
        try:
            img = Image.open(path).convert('RGB')
            img = img.resize(size, Image.Resampling.LANCZOS)
            img = img.filter(ImageFilter.GaussianBlur(3))
            return ImageEnhance.Contrast(img).enhance(1.3)
        except Exception:
            return self._gradient(size)

    def _overlay(self, img):
        ov   = Image.new('RGBA', img.size, (0, 0, 0, 150))
        base = img.convert('RGBA')
        return Image.alpha_composite(base, ov)

    def _text(self, img, text, size):
        draw      = ImageDraw.Draw(img)
        w, h      = size
        font_size = w // 9
        font      = (self._font('ExtraBold.ttf', font_size)
                     or self._font('Bold.ttf', font_size)
                     or ImageFont.load_default())

        words, lines, line = text.split(), [], ''
        for word in words:
            test = (line + ' ' + word).strip()
            bb   = draw.textbbox((0, 0), test, font=font)
            if bb[2] - bb[0] < w * 0.88:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)

        lh      = font_size * 1.25
        total_h = len(lines) * lh
        y_start = (h - total_h) / 2

        for i, ln in enumerate(lines):
            bb    = draw.textbbox((0, 0), ln, font=font)
            x     = (w - (bb[2] - bb[0])) / 2
            y     = y_start + i * lh
            for dx in range(-4, 5):
                for dy in range(-4, 5):
                    draw.text((x + dx, y + dy), ln,
                              font=font, fill=(0, 0, 0))
            color = (255, 255, 0) if i == 0 else (255, 255, 255)
            draw.text((x, y), ln, font=font, fill=color)

        return img

    def _brand(self, img, size):
        draw  = ImageDraw.Draw(img)
        w, h  = size
        font  = self._font('Bold.ttf', w // 28) or ImageFont.load_default()
        brand = "TrendPulse Global"
        bb    = draw.textbbox((0, 0), brand, font=font)
        bw    = bb[2] - bb[0]
        bh    = bb[3] - bb[1]
        pad   = 12
        x     = w - bw - pad * 2 - 8
        y     = h - bh - pad * 2 - 8
        draw.rectangle([x - pad, y - pad, x + bw + pad, y + bh + pad],
                       fill=(220, 0, 0))
        draw.text((x, y), brand, font=font, fill=(255, 255, 255))
        return img

    def _font(self, name, size):
        candidates = [
            os.path.join(self.fonts, name),
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return None
