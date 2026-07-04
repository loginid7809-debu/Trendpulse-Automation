import os
import sys
import asyncio
import tempfile
import subprocess
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
                    'text': hook, 'is_intro': True,
                })

        for i, scene in enumerate(scenes):
            text = scene.get('narration', '').strip()
            if not text:
                continue
            p = self._tts(text, voice, f'narration_{i:03d}.mp3')
            if p:
                audio_files.append({
                    'path': p, 'scene_index': i, 'text': text,
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
                    'text': outro, 'is_outro': True,
                })

        log.info(f"Total audio files: {len(audio_files)}")
        return audio_files

    def _tts(self, text, voice, filename):
        out_path = os.path.join(self.out, filename)

        if self._tts_subprocess(text, voice, out_path):
            return out_path

        if self._tts_new_loop(text, voice, out_path):
            return out_path

        if self._tts_asyncio_run(text, voice, out_path):
            return out_path

        log.debug(f"All TTS methods failed: {filename}")
        return None

    def _tts_subprocess(self, text, voice, out_path):
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.txt',
                delete=False, encoding='utf-8'
            ) as f:
                f.write(text)
                tmp_text = f.name

            result = subprocess.run(
                [
                    sys.executable, '-m', 'edge_tts',
                    '--voice', voice,
                    '--file',  tmp_text,
                    '--write-media', out_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            try:
                os.unlink(tmp_text)
            except Exception:
                pass

            if (result.returncode == 0
                    and os.path.exists(out_path)
                    and os.path.getsize(out_path) > 500):
                return True

            log.debug(f"subprocess TTS stderr: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            log.debug("TTS subprocess timeout")
        except Exception as e:
            log.debug(f"Subprocess TTS error: {e}")

        return False

    def _tts_new_loop(self, text, voice, out_path):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self._run_tts(text, voice, out_path)
                )
            finally:
                loop.close()
                asyncio.set_event_loop(None)

            if (os.path.exists(out_path)
                    and os.path.getsize(out_path) > 500):
                return True

        except Exception as e:
            log.debug(f"New loop TTS error: {e}")

        return False

    def _tts_asyncio_run(self, text, voice, out_path):
        try:
            asyncio.run(self._run_tts(text, voice, out_path))
            if (os.path.exists(out_path)
                    and os.path.getsize(out_path) > 500):
                return True
        except Exception as e:
            log.debug(f"asyncio.run TTS error: {e}")

        return False

    @staticmethod
    async def _run_tts(text, voice, path):
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(path)
