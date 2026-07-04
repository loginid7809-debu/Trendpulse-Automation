import asyncio
import os
import edge_tts
from src.utils.config import Config
from src.utils.logger import log


class VoiceGenerator:
    """Convert script narrations to MP3 using edge-tts (free, unlimited)."""

    def __init__(self):
        self.out = Config.TEMP_DIR

    def generate(self, script_data: dict) -> list:
        """
        Returns a list of dicts:
        [{'path': str, 'scene_index': int, 'text': str, 'duration': float}]
        """
        language = script_data.get('language', 'en')
        voice    = Config.random_voice(language)
        scenes   = script_data.get('scenes', [])
        log.info(f"Voice: {voice}  |  Scenes: {len(scenes)}")

        audio_files = []

        # ── intro hook ────────────────────────────────────────
        hook = script_data.get('intro_hook', '')
        if hook:
            p = self._tts(hook, voice, 'intro_hook.mp3')
            if p:
                audio_files.append({'path': p, 'scene_index': -1,
                                    'text': hook, 'is_intro': True})

        # ── scene narrations ──────────────────────────────────
        for i, scene in enumerate(scenes):
            text = scene.get('narration', '').strip()
            if not text:
                continue
            p = self._tts(text, voice, f'narration_{i:03d}.mp3')
            if p:
                audio_files.append({'path': p, 'scene_index': i, 'text': text})
                log.info(f"  ✓ Scene {i+1}/{len(scenes)}")
            else:
                log.warning(f"  ✗ Scene {i+1} TTS failed")

        # ── outro ─────────────────────────────────────────────
        outro = script_data.get('outro', '')
        if outro:
            p = self._tts(outro, voice, 'outro.mp3')
            if p:
                audio_files.append({'path': p, 'scene_index': 999,
                                    'text': outro, 'is_outro': True})

        log.info(f"Audio files generated: {len(audio_files)}")
        return audio_files

    # ── helpers ───────────────────────────────────────────────

    def _tts(self, text: str, voice: str, filename: str) -> str | None:
        out_path = os.path.join(self.out, filename)
        try:
            asyncio.run(self._run_tts(text, voice, out_path))
            if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
                return out_path
        except Exception as e:
            log.debug(f"TTS error [{filename}]: {e}")
        return None

    @staticmethod
    async def _run_tts(text: str, voice: str, path: str):
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(path)
