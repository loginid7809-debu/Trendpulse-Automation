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

    def __init__(self):
        self.out = Config.TEMP_DIR

    def assemble(self, script_data, audio_files,
                 image_files, music_path):
        ctype    = script_data.get('content_type', 'long_video')
        portrait = ctype == 'short'
        max_dur  = 59 if portrait else None
        return self._build(script_data, audio_files, image_files,
                           music_path, portrait, max_dur)

    def _build(self, script_data, audio_files, image_files,
               music_path, portrait, max_dur):
        W, H  = (Config.VIDEO_RES_PORTRAIT if portrait
                 else Config.VIDEO_RES_LANDSCAPE)
        clips = []

        scene_audios = [a for a in audio_files
                        if not a.get('is_intro') and
                        not a.get('is_outro')]

        for i, ad in enumerate(scene_audios):
            if not os.path.exists(ad['path']):
                continue
            try:
                audio = AudioFileClip(ad['path'])
                dur   = audio.duration
                if dur < 0.1:
                    audio.close()
                    continue

                img_path = self._match(
                    image_files, ad.get('scene_index', i), i
                )
                vis  = self._img_clip(img_path, dur, W, H)
                vis  = self._subtitle(
                    vis, ad.get('text', ''), dur, W, H, portrait
                )
                vis  = vis.set_audio(audio)
                clips.append(vis)
            except Exception as e:
                log.warning(f"Scene {i} error: {e}")

        if not clips:
            log.error("No clips assembled")
            return None

        video = concatenate_videoclips(clips, method='compose')

        if max_dur and video.duration > max_dur:
            video = video.subclip(0, max_dur)

        if music_path and os.path.exists(music_path):
            video = self._music(video, music_path)

        video = self._watermark(video, W)

        suffix = 'short' if portrait else 'video'
        out    = os.path.join(self.out, f'final_{suffix}.mp4')

        log.info(f"Rendering {video.duration:.1f}s...")
        video.write_videofile(
            out, fps=Config.FPS,
            codec='libx264', audio_codec='aac',
            bitrate='2500k', audio_bitrate='192k',
            preset='ultrafast', threads=2, logger=None,
        )
        video.close()
        for c in clips:
            try:
                c.close()
            except Exception:
                pass

        log.info(f"Video saved: {out}")
        return out

    def _match(self, image_files, scene_idx, fallback_i):
        for im in image_files:
            if im.get('scene_index') == scene_idx:
                return im['path']
        if image_files:
            return image_files[fallback_i % len(image_files)]['path']
        return None

    def _img_clip(self, img_path, dur, W, H):
        if not img_path or not os.path.exists(img_path):
            return ColorClip((W, H), color=(20, 20, 20)).set_duration(dur)
        try:
            tmp = img_path + '_rs.jpg'
            Image.open(img_path).convert('RGB').resize(
                (W, H), Image.Resampling.LANCZOS
            ).save(tmp, 'JPEG', quality=88)
            clip = ImageClip(tmp).set_duration(dur)
            clip = clip.resize(lambda t: 1 + 0.03 * t / max(dur, 1))
            return clip.resize((W, H))
        except Exception as e:
            log.debug(f"ImageClip error: {e}")
            return ColorClip((W, H), color=(30, 30, 30)).set_duration(dur)

    def _subtitle(self, base, text, dur, W, H, is_short):
        if not text:
            return base
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
            bar   = (ColorClip((W, int(bar_h)), color=(0, 0, 0))
                     .set_opacity(0.55)
                     .set_duration(dur)
                     .set_position(('center', y_pos - 10)))

            return CompositeVideoClip([base, bar, txt])
        except Exception as e:
            log.debug(f"Subtitle error: {e}")
            return base

    def _music(self, video, music_path, vol=0.10):
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
            log.warning(f"Music error: {e}")
            return video

    def _watermark(self, video, W):
        try:
            wm = os.path.join(Config.ASSETS_DIR, 'watermark.png')
            if os.path.exists(wm):
                wm_clip = (ImageClip(wm)
                           .set_duration(video.duration)
                           .set_opacity(0.45)
                           .set_position((W - 300, 18)))
                return CompositeVideoClip([video, wm_clip])
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
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return '\n'.join(lines[:3])

    @staticmethod
    def _find_font():
        candidates = [
            os.path.join(Config.FONTS_DIR, 'Bold.ttf'),
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None
