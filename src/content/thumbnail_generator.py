import os
import random
from PIL import (
    Image, ImageDraw, ImageFont,
    ImageFilter, ImageEnhance, ImageOps
)
from src.utils.config import Config
from src.utils.logger import log


class ThumbnailGenerator:

    def __init__(self):
        self.out   = Config.TEMP_DIR
        self.fonts = Config.FONTS_DIR

    def generate(self, script_data, bg_image_path=None):
        ctype = script_data.get('content_type', 'long_video')
        text  = script_data.get(
            'thumbnail_text',
            script_data.get('topic', 'TRENDING')
        )
        title = script_data.get('title', '')
        size  = (1080, 1920) if ctype == 'short' else (1280, 720)

        # Build thumbnail layers
        img = self._background(bg_image_path, size)
        img = self._cinematic_overlay(img, size)
        img = self._add_accent_shapes(img, size)
        img = self._add_main_text(img, text.upper(), size)
        img = self._add_subtitle_text(img, title, size)
        img = self._add_channel_badge(img, size)
        img = self._add_border(img, size)

        out = os.path.join(self.out, 'thumbnail.jpg')
        img.convert('RGB').save(out, 'JPEG', quality=97)
        log.info(f"Thumbnail: {size[0]}x{size[1]} saved")
        return out

    def _background(self, path, size):
        """Create background from image or gradient."""
        W, H = size
        if path and os.path.exists(path):
            try:
                img = Image.open(path).convert('RGB')

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

                # Boost colors for thumbnail impact
                img = ImageEnhance.Brightness(img).enhance(0.7)
                img = ImageEnhance.Contrast(img).enhance(1.4)
                img = ImageEnhance.Saturation(img).enhance(1.3)
                img = img.filter(ImageFilter.GaussianBlur(radius=1))
                return img

            except Exception as e:
                log.debug(f"Thumbnail bg image error: {e}")

        return self._gradient_bg(size)

    def _gradient_bg(self, size):
        W, H   = size
        c1, c2 = Config.random_palette()
        img    = Image.new('RGB', (W, H))
        draw   = ImageDraw.Draw(img)

        # Diagonal gradient
        for y in range(H):
            for x in range(0, W, 2):
                ratio = (x / W + y / H) / 2
                r     = int(c1[0] * (1 - ratio) + c2[0] * ratio)
                g     = int(c1[1] * (1 - ratio) + c2[1] * ratio)
                b     = int(c1[2] * (1 - ratio) + c2[2] * ratio)
                draw.line([(x, y), (x + 1, y)], fill=(r, g, b))

        return img

    def _cinematic_overlay(self, img, size):
        """Heavy dark overlay for text contrast."""
        W, H    = size
        overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)

        # Strong bottom-up gradient
        bot_h = int(H * 0.7)
        for y in range(bot_h):
            alpha = int(200 * (y / bot_h) ** 1.5)
            ypos  = H - bot_h + y
            draw.line([(0, ypos), (W, ypos)], fill=(0, 0, 0, alpha))

        # Top gradient
        top_h = int(H * 0.3)
        for y in range(top_h):
            alpha = int(140 * (1 - y / top_h))
            draw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))

        base = img.convert('RGBA')
        return Image.alpha_composite(base, overlay).convert('RGB')

    def _add_accent_shapes(self, img, size):
        """Add decorative accent shapes for visual interest."""
        W, H   = size
        draw   = ImageDraw.Draw(img)
        colors = Config.random_palette()
        accent = colors[0]

        # Left accent bar
        bar_w = max(8, W // 80)
        draw.rectangle(
            [0, int(H * 0.15), bar_w, int(H * 0.85)],
            fill=accent
        )

        # Bottom accent line
        draw.rectangle(
            [0, H - max(6, W // 100), W, H],
            fill=accent
        )

        # Corner accent dots
        dot_r = max(15, W // 60)
        draw.ellipse(
            [W - dot_r * 3, H // 2 - dot_r,
             W - dot_r, H // 2 + dot_r],
            fill=(*accent, 180)
        )

        return img

    def _add_main_text(self, img, text, size):
        """Add large impactful main text."""
        W, H  = size
        draw  = ImageDraw.Draw(img)

        # Dynamic font size
        font_size = W // 7
        font      = self._font('ExtraBold.ttf', font_size)
        if not font:
            font = self._font('Bold.ttf', font_size)
        if not font:
            font = ImageFont.load_default()

        # Word wrap
        words, lines, cur = text.split(), [], ''
        for word in words:
            test = (cur + ' ' + word).strip()
            try:
                bb = draw.textbbox((0, 0), test, font=font)
                tw = bb[2] - bb[0]
            except Exception:
                tw = len(test) * (font_size // 2)
            if tw < W * 0.85:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)

        lines    = lines[:3]
        lh       = int(font_size * 1.15)
        total_h  = len(lines) * lh
        y_start  = int(H * 0.38) - total_h // 2

        for i, line in enumerate(lines):
            try:
                bb = draw.textbbox((0, 0), line, font=font)
                tw = bb[2] - bb[0]
            except Exception:
                tw = len(line) * (font_size // 2)

            x = (W - tw) // 2
            y = y_start + i * lh

            # Thick black outline
            for ox in range(-4, 5):
                for oy in range(-4, 5):
                    if ox != 0 or oy != 0:
                        try:
                            draw.text(
                                (x + ox, y + oy), line,
                                font=font, fill=(0, 0, 0)
                            )
                        except Exception:
                            pass

            # Main text color
            color = (255, 230, 0) if i == 0 else (255, 255, 255)
            try:
                draw.text((x, y), line, font=font, fill=color)
            except Exception:
                pass

        return img

    def _add_subtitle_text(self, img, title, size):
        """Add smaller subtitle below main text."""
        if not title:
            return img

        W, H  = size
        draw  = ImageDraw.Draw(img)

        # Clean title
        clean = title
        for tag in [' - CNN', ' - BBC', ' - Reuters',
                    ' - Yahoo', ' - NBC', ' #Shorts', ' #shorts']:
            clean = clean.replace(tag, '')
        clean = clean.strip()

        if not clean:
            return img

        font_size = max(20, W // 42)
        font      = self._font('Bold.ttf', font_size)
        if not font:
            font = ImageFont.load_default()

        # Truncate
        try:
            bb = draw.textbbox((0, 0), clean, font=font)
            tw = bb[2] - bb[0]
            while tw > W * 0.80 and len(clean) > 15:
                clean = clean[:-4] + '...'
                bb    = draw.textbbox((0, 0), clean, font=font)
                tw    = bb[2] - bb[0]
        except Exception:
            tw = len(clean) * (font_size // 2)

        x = (W - tw) // 2
        y = int(H * 0.38) + int(H * 0.22)

        # Draw with shadow
        for ox, oy in [(-2, -2), (2, 2), (-2, 2), (2, -2)]:
            try:
                draw.text((x + ox, y + oy), clean,
                          font=font, fill=(0, 0, 0))
            except Exception:
                pass
        try:
            draw.text((x, y), clean, font=font,
                      fill=(220, 220, 220))
        except Exception:
            pass

        return img

    def _add_channel_badge(self, img, size):
        """Add TrendPulse Global badge."""
        W, H  = size
        draw  = ImageDraw.Draw(img)

        font_size = max(18, W // 50)
        font      = self._font('Bold.ttf', font_size)
        if not font:
            font = ImageFont.load_default()

        # Badge text
        badge = "⚡ TrendPulse Global"
        try:
            bb = draw.textbbox((0, 0), badge, font=font)
            bw = bb[2] - bb[0]
            bh = bb[3] - bb[1]
        except Exception:
            bw = len(badge) * (font_size // 2)
            bh = font_size

        pad = 12
        x   = W - bw - pad * 2 - 15
        y   = H - bh - pad * 2 - 15

        # Red pill badge
        draw.rounded_rectangle(
            [x - pad, y - pad,
             x + bw + pad, y + bh + pad],
            radius=10,
            fill=(220, 30, 30)
        )

        # White outline
        draw.rounded_rectangle(
            [x - pad - 2, y - pad - 2,
             x + bw + pad + 2, y + bh + pad + 2],
            radius=12,
            outline=(255, 255, 255),
            width=2
        )

        try:
            draw.text((x, y), badge, font=font, fill=(255, 255, 255))
        except Exception:
            pass

        return img

    def _add_border(self, img, size):
        """Add a colored border frame."""
        W, H    = size
        border  = max(4, W // 160)
        c1, c2  = Config.random_palette()
        draw    = ImageDraw.Draw(img)

        # Top and bottom borders
        draw.rectangle([0, 0, W, border], fill=c1)
        draw.rectangle([0, H - border, W, H], fill=c1)
        # Left and right borders
        draw.rectangle([0, 0, border, H], fill=c1)
        draw.rectangle([W - border, 0, W, H], fill=c1)

        return img

    def _font(self, name, size):
        size = max(12, int(size))
        candidates = [
            os.path.join(self.fonts, name),
            os.path.join(self.fonts, 'Bold.ttf'),
            os.path.join(self.fonts, 'Regular.ttf'),
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf',
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return None
