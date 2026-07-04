import asyncio
import os
import edge_tts
from src.utils.config import Config
from src.utils.logger import log


class VoiceGenerator:

    def __init__(self):
        self.out = Config.TEMP_DIR

    def generate(self, script_data):
        language = script_data.get('language', 'en')
        voice    = Config.random_voice(language)
        scenes   = script_data.get('scenes', [])
        log.info(f"Voice: {voice} | Scenes: {len(scenes)}")

        audio_files = []

        hook = script_data.get('intro_hook', '')
        if hook:
            p = self._tts(hook, voice, 'intro_hook.mp3')
            if p:
                audio_files.append({
                    'path': p, 'scene_index': -1,
                    'text': hook, 'is_intro': True
                })

        for i, scene in enumerate(scenes):
            text = scene.get('narration', '').strip()
            if not text:
                continue
            p = self._tts(text, voice, f'narration_{i:03d}.mp3')
            if p:
                audio_files.append({
                    'path': p, 'scene_index': i, 'text': text
                })
                log.info(f"  Audio {i+1}/{len(scenes)} OK")
            else:
                log.warning(f"  Audio {i+1}/{len(scenes)} FAILED")

        outro = script_data.get('outro', '')
        if outro:
            p = self._tts(outro, voice, 'outro.mp3')
            if p:
                audio_files.append({
                    'path': p, 'scene_index': 999,
                    'text': outro, 'is_outro': True
                })

        log.info(f"Total audio files: {len(audio_files)}")
        return audio_files

    def _tts(self, text, voice, filename):
        out_path = os.path.join(self.out, filename)
        try:
            asyncio.run(self._run(text, voice, out_path))
            if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
                return out_path
        except Exception as e:
            log.debug(f"TTS error [{filename}]: {e}")
        return None

    @staticmethod
    async def _run(text, voice, path):
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(path)
