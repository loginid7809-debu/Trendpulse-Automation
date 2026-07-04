#!/usr/bin/env python3
"""
TrendPulse Global — Main pipeline orchestrator.
Called by GitHub Actions every run.
"""

import os
import sys
import shutil
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.config          import Config
from src.utils.logger          import log
from src.utils.history_manager import HistoryManager
from src.trends.trend_aggregator     import TrendAggregator
from src.content.script_generator   import ScriptGenerator
from src.content.voice_generator    import VoiceGenerator
from src.content.image_fetcher      import ImageFetcher
from src.content.music_manager      import MusicManager
from src.content.thumbnail_generator import ThumbnailGenerator
from src.video.video_assembler      import VideoAssembler
from src.upload.youtube_uploader    import YouTubeUploader


def cleanup():
    for d in [Config.TEMP_DIR, Config.TEMP_ASSETS]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)


def main():
    t0 = time.time()
    log.info("=" * 55)
    log.info("  TrendPulse Global — Content Pipeline")
    log.info(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    log.info("=" * 55)

    Config.ensure_dirs()

    try:
        # ── 1. Trending topic ─────────────────────────────────
        log.info("\n[ 1 / 8 ]  Finding trending topic…")
        topic_data = TrendAggregator().get_best_topic()

        # ── 2. Script ─────────────────────────────────────────
        log.info("\n[ 2 / 8 ]  Generating script…")
        script = ScriptGenerator().generate(topic_data)

        # ── 3. Voice ──────────────────────────────────────────
        log.info("\n[ 3 / 8 ]  Generating voice narration…")
        audio_files = VoiceGenerator().generate(script)
        if not audio_files:
            raise RuntimeError("Voice generation produced no audio files")

        # ── 4. Images ─────────────────────────────────────────
        log.info("\n[ 4 / 8 ]  Fetching images…")
        image_files = ImageFetcher().fetch_for_script(script)
        if not image_files:
            raise RuntimeError("Image fetching produced no images")

        # ── 5. Music ──────────────────────────────────────────
        log.info("\n[ 5 / 8 ]  Downloading background music…")
        music_path = MusicManager().get_music()

        # ── 6. Thumbnail ──────────────────────────────────────
        log.info("\n[ 6 / 8 ]  Generating thumbnail…")
        bg = image_files[0]['path'] if image_files else None
        thumbnail = ThumbnailGenerator().generate(script, bg)

        # ── 7. Assemble video ─────────────────────────────────
        log.info("\n[ 7 / 8 ]  Assembling video…")
        video_path = VideoAssembler().assemble(
            script, audio_files, image_files, music_path
        )
        if not video_path or not os.path.exists(video_path):
            raise RuntimeError("Video assembly failed")

        mb = os.path.getsize(video_path) / 1_048_576
        log.info(f"  Video ready: {mb:.1f} MB")

        # ── 8. Upload ─────────────────────────────────────────
        log.info("\n[ 8 / 8 ]  Uploading to YouTube…")
        video_id = YouTubeUploader().upload(video_path, script, thumbnail)

        if video_id:
            HistoryManager().record(
                topic        = topic_data['topic'],
                video_id     = video_id,
                content_type = topic_data['content_type'],
                language     = topic_data['language'],
                title        = script.get('title', ''),
            )
            elapsed = time.time() - t0
            log.info("\n" + "=" * 55)
            log.info("  ✅  PIPELINE COMPLETE")
            log.info(f"  Video : https://youtu.be/{video_id}")
            log.info(f"  Topic : {topic_data['topic']}")
            log.info(f"  Type  : {topic_data['content_type']}")
            log.info(f"  Time  : {elapsed:.0f}s")
            log.info("=" * 55)
        else:
            log.error("Upload returned no video ID")

    except Exception as exc:
        log.error(f"Pipeline error: {exc}")
        import traceback
        log.error(traceback.format_exc())
    finally:
        cleanup()
        log.info("Temp files cleaned up.")


if __name__ == '__main__':
    main()
