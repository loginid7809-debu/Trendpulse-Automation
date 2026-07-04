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
            p = self._tts(hook, voice, language, 'intro_hook.mp3')
            if p:
                audio_files.append({
                    'path': p, 'scene_index': -1,
                    'text': hook, 'is_intro': True,
                })

        for i, scene in enumerate(scenes):
            text = scene.get('narration', '').strip()
            if not text:
                continue
            p = self._tts(text, voice, language, f'narration_{i:03d}.mp3')
            if p:
                audio_files.append({
                    'path': p, 'scene_index': i, 'text': text,
                })
                log.info(f"  Audio {i+1}/{len(scenes)} OK")
            else:
                log.warning(f"  Audio {i+1}/{len(scenes)} FAILED")

        outro = script_data.get('outro', '')
        if outro:
            p = self._tts(outro, voice, language, 'outro.mp3')
            if p:
                audio_files.append({
                    'path': p, 'scene_index': 999,
                    'text': outro, 'is_outro': True,
                })

        log.info(f"Total audio files: {len(audio_files)}")
        return audio_files

    def _tts(self, text, voice, language, filename):
        """Try multiple TTS methods in order."""
        out_path = os.path.join(self.out, filename)

        # Method 1: gTTS (Google TTS - most reliable in CI)
        if self._gtts(text, language, out_path):
            log.debug(f"gTTS success: {filename}")
            return out_path

        # Method 2: edge-tts subprocess
        if self._edge_subprocess(text, voice, out_path):
            log.debug(f"edge-tts subprocess success: {filename}")
            return out_path

        # Method 3: edge-tts new event loop
        if self._edge_new_loop(text, voice, out_path):
            log.debug(f"edge-tts new loop success: {filename}")
            return out_path

        # Method 4: edge-tts asyncio.run
        if self._edge_asyncio_run(text, voice, out_path):
            log.debug(f"edge-tts asyncio success: {filename}")
            return out_path

        log.debug(f"All TTS methods failed: {filename}")
        return None

    def _gtts(self, text, language, out_path):
        """
        Google Text-to-Speech via gTTS library.
        No API key needed. Works perfectly in GitHub Actions.
        """
        try:
            from gtts import gTTS

            # Map language codes
            lang_map = {
                'en': 'en',
                'hi': 'hi',
            }
            lang = lang_map.get(language, 'en')

            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(out_path)

            if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
                return True

        except Exception as e:
            log.debug(f"gTTS error: {e}")

        return False

    def _edge_subprocess(self, text, voice, out_path):
        """edge-tts via subprocess - works in most CI environments."""
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

        except subprocess.TimeoutExpired:
            log.debug("edge-tts subprocess timeout")
        except Exception as e:
            log.debug(f"edge-tts subprocess error: {e}")

        return False

    def _edge_new_loop(self, text, voice, out_path):
        """edge-tts with a fresh event loop."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self._run_edge_tts(text, voice, out_path)
                )
            finally:
                loop.close()
                asyncio.set_event_loop(None)

            if (os.path.exists(out_path)
                    and os.path.getsize(out_path) > 500):
                return True

        except Exception as e:
            log.debug(f"edge-tts new loop error: {e}")

        return False

    def _edge_asyncio_run(self, text, voice, out_path):
        """edge-tts with standard asyncio.run."""
        try:
            asyncio.run(self._run_edge_tts(text, voice, out_path))
            if (os.path.exists(out_path)
                    and os.path.getsize(out_path) > 500):
                return True
        except Exception as e:
            log.debug(f"edge-tts asyncio run error: {e}")

        return False

    @staticmethod
    async def _run_edge_tts(text, voice, path):
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(path)
