import os
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy.editor import (
    ImageClip, AudioFileClip, ColorClip,
    CompositeVideoClip, CompositeAudioClip,
    concatenate_videoclips, concatenate_audioclips,
)
from src.utils.config import Config
from src.utils.logger import log


class VideoAssembler:

    def __init__(self):
        self.out = Config.TEMP_DIR

    def assemble(self, script_data, audio_files,
                 image_files, music_path):
        ctype    = script_data.get('content_type', 'long_video')
        portrait = ctype == 'short'
        max_dur  = 59 if portrait else None

        return self._build(
            script_data, audio_files, image_files,
            music_path, portrait, max_dur
        )

    def _build(self, script_data, audio_files, image_files,
               music_path, portrait, max_dur):

        W, H = (Config.VIDEO_RES_PORTRAIT if portrait
                else Config.VIDEO_RES_LANDSCAPE)

        scene_audios = [
            a for a in audio_files
            if not a.get('is_intro') and not a.get('is_outro')
        ]

        clips = []

        for i, ad in enumerate(scene_audios):
            if not os.path.exists(ad['path']):
                log.warning(f"Audio missing: {ad['path']}")
                continue

            try:
                audio    = AudioFileClip(ad['path'])
                dur      = audio.duration
                if dur < 0.5:
                    audio.close()
                    continue

                # Find the matching image
                img_path = self._match_image(
                    image_files, ad.get('scene_index', i), i
                )

                # Build the visual frame using PIL (reliable)
                frame    = self._build_frame(
                    img_path, ad.get('text', ''),
                    script_data.get('title', ''),
                    i, len(scene_audios), W, H, portrait
                )

                # Create clip from PIL frame
                vis = ImageClip(frame).set_duration(dur)

                # Set audio
                vis = vis.set_audio(audio)
                clips.append(vis)

                log.info(
                    f"  Scene {i+1}/{len(scene_audios)} "
                    f"assembled ({dur:.1f}s)"
                )

            except Exception as e:
                log.warning(f"Scene {i+1} assembly error: {e}")
                import traceback
                log.debug(traceback.format_exc())

        if not clips:
            log.error("No clips assembled!")
            return None

        log.info(f"Concatenating {len(clips)} clips...")
        video = concatenate_videoclips(clips, method='compose')

        if max_dur and video.duration > max_dur:
            video = video.subclip(0, max_dur)

        # Add background music
        if music_path and os.path.exists(music_path):
            video = self._mix_music(video, music_path)

        # Export
        suffix = 'short' if portrait else 'video'
        out    = os.path.join(self.out, f'final_{suffix}.mp4')

        log.info(f"Rendering {video.duration:.1f}s → {out}")

        video.write_videofile(
            out,
            fps=Config.FPS,
            codec='libx264',
            audio_codec='aac',
            bitrate='3000k',
            audio_bitrate='192k',
            preset='ultrafast',
            threads=2,
            logger=None,
        )

        video.close()
        for c in clips:
            try:
                c.close()
            except Exception:
                pass

        log.info(f"Video saved: {out}")
        return out

    def _build_frame(self, img_path, narration_text,
                     video_title, scene_num, total_scenes,
                     W, H, is_short):
        """
        Build a complete video frame using PIL.
        Combines: background image + gradient overlay +
                  title bar + subtitle text + scene counter + branding
        """
        # Step 1: Load and resize background image
        frame = self._load_background(img_path, W, H)

        # Step 2: Add cinematic dark gradient overlay
        frame = self._add_gradient_overlay(frame, W, H, is_short)

        # Step 3: Add top title bar
        frame = self._add_title_bar(frame, video_title, W, H, is_short)

        # Step 4: Add subtitle / narration text at bottom
        frame = self._add_subtitle(frame, narration_text, W, H, is_short)

        # Step 5: Add bottom branding bar
        frame = self._add_branding_bar(frame, W, H)

        # Step 6: Add scene progress indicator
        frame = self._add_progress(frame, scene_num, total_scenes, W, H)

        # Convert to numpy array for MoviePy
        import numpy as np
        return np.array(frame.convert('RGB'))

    def _load_background(self, img_path, W, H):
        """Load image, resize to fill frame, enhance it."""
        try:
            if img_path and os.path.exists(img_path):
                img = Image.open(img_path).convert('RGB')

                # Smart crop to fill frame (cover mode)
                img_ratio   = img.width / img.height
                frame_ratio = W / H

                if img_ratio > frame_ratio:
                    # Image is wider - fit by height
                    new_h = H
                    new_w = int(H * img_ratio)
                else:
                    # Image is taller - fit by width
                    new_w = W
                    new_h = int(W / img_ratio)

                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # Center crop
                left = (new_w - W) // 2
                top  = (new_h - H) // 2
                img  = img.crop((left, top, left + W, top + H))

                # Enhance: slight brightness boost and contrast
                img = ImageEnhance.Brightness(img).enhance(0.85)
                img = ImageEnhance.Contrast(img).enhance(1.2)
                img = ImageEnhance.Sharpness(img).enhance(1.3)

                return img

        except Exception as e:
            log.debug(f"Background load error: {e}")

        # Fallback: gradient background
        return self._gradient_bg(W, H)

    def _gradient_bg(self, W, H):
        """Create a nice gradient background."""
        c1, c2 = Config.random_palette()
        img    = Image.new('RGB', (W, H))
        draw   = ImageDraw.Draw(img)
        for y in range(H):
            ratio = y / H
            r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
            g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
            b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
            draw.line([(0, y), (W, y)], fill=(r, g, b))
        return img

    def _add_gradient_overlay(self, img, W, H, is_short):
        """Add cinematic dark gradient overlay for text readability."""
        overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)

        # Top gradient (dark → transparent)
        top_h = int(H * 0.25)
        for y in range(top_h):
            alpha = int(180 * (1 - y / top_h))
            draw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))

        # Bottom gradient (transparent → very dark)
        bot_h   = int(H * 0.45)
        bot_start = H - bot_h
        for y in range(bot_h):
            alpha = int(220 * (y / bot_h))
            draw.line(
                [(0, bot_start + y), (W, bot_start + y)],
                fill=(0, 0, 0, alpha)
            )

        base = img.convert('RGBA')
        base = Image.alpha_composite(base, overlay)
        return base.convert('RGB')

    def _add_title_bar(self, img, title, W, H, is_short):
        """Add channel name and video title at the top."""
        draw      = ImageDraw.Draw(img)
        font_size = max(20, W // 55)
        font      = self._get_font('Bold.ttf', font_size)

        # Channel name with red accent
        channel   = "⚡ TrendPulse Global"
        ch_bbox   = draw.textbbox((0, 0), channel, font=font)
        ch_w      = ch_bbox[2] - ch_bbox[0]
        ch_h      = ch_bbox[3] - ch_bbox[1]

        # Red pill background for channel name
        pad    = 10
        margin = 20
        draw.rounded_rectangle(
            [margin, margin,
             margin + ch_w + pad * 2, margin + ch_h + pad * 2],
            radius=8,
            fill=(220, 30, 30, 220)
        )
        draw.text(
            (margin + pad, margin + pad),
            channel, font=font, fill=(255, 255, 255)
        )

        # Video title below channel name (truncated)
        title_font = self._get_font('Bold.ttf', max(18, W // 65))
        clean_title = self._clean_title(title)
        title_y     = margin + ch_h + pad * 2 + 10

        # Draw title with shadow
        self._draw_text_with_shadow(
            draw, clean_title, (margin, title_y),
            title_font, (255, 255, 255), max_width=int(W * 0.75)
        )

        return img

    def _add_subtitle(self, img, text, W, H, is_short):
        """Add narration subtitle at the bottom of the frame."""
        if not text or not text.strip():
            return img

        draw      = ImageDraw.Draw(img)
        font_size = max(24, W // 45) if is_short else max(20, W // 58)
        font      = self._get_font('Bold.ttf', font_size)

        # Word wrap
        wrapped = self._wrap_text(text, font, draw, int(W * 0.88))
        lines   = wrapped.split('\n')[:3]  # Max 3 lines

        # Calculate subtitle area
        line_h    = font_size + 10
        total_h   = len(lines) * line_h + 20
        sub_y     = H - total_h - 80  # Above branding bar

        # Draw semi-transparent background
        sub_bg = Image.new('RGBA', (W, total_h + 20), (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(sub_bg)
        bg_draw.rectangle(
            [0, 0, W, total_h + 20],
            fill=(0, 0, 0, 180)
        )

        img_rgba = img.convert('RGBA')
        img_rgba.paste(sub_bg, (0, sub_y - 10), sub_bg)
        img = img_rgba.convert('RGB')
        draw = ImageDraw.Draw(img)

        # Draw each line centered
        for j, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                tw   = bbox[2] - bbox[0]
            except Exception:
                tw = len(line) * (font_size // 2)

            x = (W - tw) // 2
            y = sub_y + j * line_h

            # Shadow
            for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
                try:
                    draw.text((x + dx, y + dy), line,
                              font=font, fill=(0, 0, 0, 255))
                except Exception:
                    pass

            # Main text (white with yellow for first word)
            try:
                draw.text((x, y), line, font=font,
                          fill=(255, 255, 255))
            except Exception:
                pass

        return img

    def _add_branding_bar(self, img, W, H):
        """Add bottom branding bar."""
        draw     = ImageDraw.Draw(img)
        bar_h    = max(45, H // 22)
        font_sz  = max(16, bar_h // 2)
        font     = self._get_font('Bold.ttf', font_sz)

        # Draw dark bar at bottom
        draw.rectangle(
            [0, H - bar_h, W, H],
            fill=(15, 15, 15)
        )

        # Left: channel name
        left_text = "TrendPulse Global"
        draw.text(
            (20, H - bar_h + (bar_h - font_sz) // 2),
            left_text, font=font, fill=(255, 60, 60)
        )

        # Right: subscribe prompt
        right_text = "🔔 Subscribe for Hourly Trends"
        try:
            rb = draw.textbbox((0, 0), right_text, font=font)
            rw = rb[2] - rb[0]
        except Exception:
            rw = len(right_text) * (font_sz // 2)

        draw.text(
            (W - rw - 20, H - bar_h + (bar_h - font_sz) // 2),
            right_text, font=font, fill=(255, 255, 255)
        )

        return img

    def _add_progress(self, img, scene_num, total_scenes, W, H):
        """Add a thin progress bar at the very top."""
        if total_scenes <= 0:
            return img

        draw     = ImageDraw.Draw(img)
        bar_h    = 5
        progress = (scene_num + 1) / total_scenes
        filled_w = int(W * progress)

        # Background track
        draw.rectangle([0, 0, W, bar_h], fill=(60, 60, 60))
        # Filled portion
        draw.rectangle([0, 0, filled_w, bar_h], fill=(255, 60, 60))

        return img

    def _mix_music(self, video, music_path, vol=0.10):
        """Mix background music at low volume under narration."""
        try:
            music = AudioFileClip(music_path)
            if music.duration < video.duration:
                loops = int(video.duration / music.duration) + 2
                music = concatenate_audioclips([music] * loops)
            music = music.subclip(0, video.duration).volumex(vol)
            if video.audio:
                from moviepy.audio.AudioClip import CompositeAudioClip
                mixed = CompositeAudioClip([video.audio, music])
            else:
                mixed = music
            return video.set_audio(mixed)
        except Exception as e:
            log.warning(f"Music mix error: {e}")
            return video

    # ── Helper methods ────────────────────────────────────────

    def _match_image(self, image_files, scene_idx, fallback_i):
        for im in image_files:
            if im.get('scene_index') == scene_idx:
                if im['path'] and os.path.exists(im['path']):
                    return im['path']
        if image_files:
            idx = fallback_i % len(image_files)
            return image_files[idx]['path']
        return None

    def _wrap_text(self, text, font, draw, max_width):
        words  = text.split()
        lines  = []
        cur    = ''
        for word in words:
            test = (cur + ' ' + word).strip()
            try:
                bbox = draw.textbbox((0, 0), test, font=font)
                tw   = bbox[2] - bbox[0]
            except Exception:
                tw = len(test) * 10
            if tw <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return '\n'.join(lines[:3])

    def _draw_text_with_shadow(self, draw, text, pos,
                                font, color, max_width=None):
        x, y = pos
        if max_width:
            # Truncate if too long
            try:
                bb = draw.textbbox((0, 0), text, font=font)
                while (bb[2] - bb[0]) > max_width and len(text) > 10:
                    text = text[:-4] + '...'
                    bb   = draw.textbbox((0, 0), text, font=font)
            except Exception:
                pass

        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            try:
                draw.text((x + dx, y + dy), text,
                          font=font, fill=(0, 0, 0))
            except Exception:
                pass
        try:
            draw.text((x, y), text, font=font, fill=color)
        except Exception:
            pass

    def _clean_title(self, title):
        """Remove source tags from title."""
        for tag in [' - CNN', ' - BBC', ' - Reuters',
                    ' - Yahoo', ' - Fox News', ' - NBC',
                    ' | TrendPulse Global']:
            title = title.replace(tag, '')
        return title.strip()[:80]

    def _get_font(self, name, size):
        """Load best available font."""
        size = max(12, int(size))
        candidates = [
            os.path.join(Config.FONTS_DIR, name),
            os.path.join(Config.FONTS_DIR, 'Bold.ttf'),
            os.path.join(Config.FONTS_DIR, 'Regular.ttf'),
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf',
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return ImageFont.load_default()
