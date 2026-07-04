import os
from moviepy.editor import (
    ImageClip, AudioFileClip, ColorClip, TextClip,
    CompositeVideoClip, CompositeAudioClip,
    concatenate_videoclips, concatenate_audioclips,
)
from PIL import Image
from src.utils.config import Config
from src.utils.logger import log


class VideoAssembler:
    """Assemble final MP4 from images + audio + music."""

    def __init__(self):
        self.out = Config.TEMP_DIR

    def assemble(self, script_data: dict, audio_files: list,
                 image_files: list, music_path: str | None) -> str | None:
        ctype = script_data.get('content_type', 'long_video')
        if ctype == 'short':
            return self._build(script_data, audio_files, image_files,
                               music_path, portrait=True, max_dur=59)
        else:
            return self._build(script_data, audio_files, image_files,
                               music_path, portrait=False, max_dur=None)

    # ── core builder ─────────────────────────────────────────

    def _build(self, script_data, audio_files, image_files,
               music_path, portrait, max_dur):
        W, H   = (Config.VIDEO_RES_PORTRAIT if portrait
                  else Config.VIDEO_RES_LANDSCAPE)
        fps    = Config.FPS
        clips  = []

        # Only scene narrations (not intro/outro markers)
        scene_audios = [a for a in audio_files
                        if not a.get('is_intro') and not a.get('is_outro')]

        for i, ad in enumerate(scene_audios):
            if not os.path.exists(ad['path']):
                continue
            try:
                audio = AudioFileClip(ad['path'])
                dur   = audio.duration
                if dur <= 0.1:
                    audio.close()
                    continue

                # Match image
                img_path = self._match_image(image_files, ad.get('scene_index', i), i)
                vis      = self._image_clip(img_path, dur, W, H)

                # Subtitle
                vis = self._subtitle(vis, ad.get('text', ''), dur, W, H, portrait)

                vis  = vis.set_audio(audio)
                clips.append(vis)
            except Exception as e:
                log.warning(f"Scene {i} assembly error: {e}")

        if not clips:
            log.error("No clips assembled — aborting")
            return None

        video = concatenate_videoclips(clips, method='compose')

        if max_dur and video.duration > max_dur:
            video = video.subclip(0, max_dur)

        if music_path and os.path.exists(music_path):
            video = self._mix_music(video, music_path)

        video = self._watermark(video, W)

        suffix = 'short' if portrait else 'video'
        out    = os.path.join(self.out, f'final_{suffix}.mp4')
        log.info(f"Rendering {video.duration:.1f}s → {out}")

        video.write_videofile(
            out, fps=fps,
            codec='libx264', audio_codec='aac',
            bitrate='2500k', audio_bitrate='192k',
            preset='ultrafast', threads=2,
            logger=None,
        )
        video.close()
        for c in clips:
            try: c.close()
            except Exception: pass

        log.info("Video render complete ✓")
        return out

    # ── helpers ───────────────────────────────────────────────

    def _match_image(self, image_files, scene_idx, fallback_i):
        for im in image_files:
            if im.get('scene_index') == scene_idx:
                return im['path']
        if image_files:
            return image_files[fallback_i % len(image_files)]['path']
        return None

    def _image_clip(self, img_path, dur, W, H):
        if not img_path or not os.path.exists(img_path):
            return ColorClip((W, H), color=(20, 20, 20)).set_duration(dur)
        try:
            # Resize to target resolution
            tmp = img_path + '_rs.jpg'
            im  = Image.open(img_path).convert('RGB').resize(
                    (W, H), Image.Resampling.LANCZOS)
            im.save(tmp, 'JPEG', quality=88)
            clip = ImageClip(tmp).set_duration(dur)
            # Subtle Ken-Burns zoom
            clip = clip.resize(lambda t: 1 + 0.03 * t / dur)
            return clip.resize((W, H))
        except Exception as e:
            log.debug(f"ImageClip error: {e}")
            return ColorClip((W, H), color=(30, 30, 30)).set_duration(dur)

    def _subtitle(self, base_clip, text, dur, W, H, is_short):
        if not text:
            return base_clip
        try:
            font_size = 38 if is_short else 30
            font_path = self._find_font()
            wrapped   = self._wrap(text, 38 if is_short else 52)

            txt = TextClip(
                wrapped, fontsize=font_size,
                font=font_path or 'Liberation-Sans-Bold',
                color='white', stroke_color='black', stroke_width=2,
                size=(int(W * 0.92), None),
                method='caption', align='center',
            ).set_duration(dur)

            y_pos = H * 0.80 if is_short else H * 0.83
            txt   = txt.set_position(('center', y_pos))

            bar_h = (txt.size[1] or 60) + 20
            bar   = (ColorClip((W, int(bar_h)), color=(0,0,0))
                     .set_opacity(0.55)
                     .set_duration(dur)
                     .set_position(('center', y_pos - 10)))

            return CompositeVideoClip([base_clip, bar, txt])
        except Exception as e:
            log.debug(f"Subtitle error: {e}")
            return base_clip

    def _mix_music(self, video, music_path, vol=0.10):
        try:
            music = AudioFileClip(music_path)
            if music.duration < video.duration:
                n     = int(video.duration / music.duration) + 1
                music = concatenate_audioclips([music] * n)
            music = music.subclip(0, video.duration).volumex(vol)
            mixed = (CompositeAudioClip([video.audio, music])
                     if video.audio else music)
            return video.set_audio(mixed)
        except Exception as e:
            log.warning(f"Music mixing error: {e}")
            return video

    def _watermark(self, video, W):
        try:
            wm_path = os.path.join(Config.ASSETS_DIR, 'watermark.png')
            if os.path.exists(wm_path):
                from moviepy.editor import ImageClip as IC
                wm = (IC(wm_path)
                      .set_duration(video.duration)
                      .set_opacity(0.45)
                      .set_position((W - 230, 18)))
                return CompositeVideoClip([video, wm])
        except Exception:
            pass
        return video

    @staticmethod
    def _wrap(text, max_chars):
        words, lines, cur = text.split(), [], ''
        for w in words:
            test = (cur + ' ' + w).strip()
            if len(test) <= max_chars:
                cur = test
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        return '\n'.join(lines[:3])

    @staticmethod
    def _find_font():
        import os
        candidates = [
            os.path.join(Config.FONTS_DIR, 'Bold.ttf'),
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None
