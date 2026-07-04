import os
import subprocess
import sys
import tempfile
import asyncio
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

        # Intro hook
        hook = script_data.get('intro_hook', '')
        if hook:
            p = self._tts(hook, voice, 'intro_hook.mp3')
            if p:
                audio_files.append({
                    'path': p, 'scene_index': -1,
                    'text': hook, 'is_intro': True,
                })

        # Scene narrations
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

        # Outro
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
        """Generate TTS audio using multiple methods."""
        out_path = os.path.join(self.out, filename)

        # Method 1: Subprocess (most reliable in CI)
        if self._tts_subprocess(text, voice, out_path):
            return out_path

        # Method 2: New event loop
        if self._tts_new_loop(text, voice, out_path):
            return out_path

        # Method 3: asyncio.run with nest_asyncio workaround
        if self._tts_run(text, voice, out_path):
            return out_path

        log.debug(f"All TTS methods failed for: {filename}")
        return None

    def _tts_subprocess(self, text, voice, out_path):
        """
        Use edge-tts as a subprocess command.
        Most reliable method in GitHub Actions.
        """
        try:
            # Write text to temp file to avoid shell escaping issues
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
                    '--file', tmp_text,
                    '--write-media', out_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            os.unlink(tmp_text)

            if (result.returncode == 0 and
                    os.path.exists(out_path) and
                    os.path.getsize(out_path) > 500):
                return True

            log.debug(f"Subprocess TTS stderr: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            log.debug("TTS subprocess timeout")
        except Exception as e:
            log.debug(f"Subprocess TTS error: {e}")

        return False

    def _tts_new_loop(self, text, voice, out_path):
        """Create a brand new event loop."""
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

            if (os.path.exists(out_path) and
                    os.path.getsize(out_path) > 500):
                return True

        except Exception as e:
            log.debug(f"New loop TTS error: {e}")

        return False

    def _tts_run(self, text, voice, out_path):
        """Standard asyncio.run method."""
        try:
            asyncio.run(self._run_tts(text, voice, out_path))
            if (os.path.exists(out_path) and
                    os.path.getsize(out_path) > 500):
                return True
        except RuntimeError as e:
            log.debug(f"asyncio.run TTS error: {e}")
        except Exception as e:
            log.debug(f"TTS run error: {e}")

        return False

    @staticmethod
    async def _run_tts(text, voice, path):
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(path)
