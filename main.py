#!/usr/bin/env python3
import os
import sys
import shutil
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def cleanup(*dirs):
    for d in dirs:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)


def main():
    t0 = time.time()
    print("=" * 55)
    print("  TrendPulse Global - Content Pipeline")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 55)

    from src.utils.config            import Config
    from src.utils.logger            import log
    from src.utils.history_manager   import HistoryManager
    from src.trends.trend_aggregator       import TrendAggregator
    from src.content.script_generator     import ScriptGenerator
    from src.content.voice_generator      import VoiceGenerator
    from src.content.image_fetcher        import ImageFetcher
    from src.content.music_manager        import MusicManager
    from src.content.thumbnail_generator  import ThumbnailGenerator
    from src.video.video_assembler        import VideoAssembler
    from src.upload.youtube_uploader      import YouTubeUploader

    Config.ensure_dirs()

    try:
        # 1. Topic
        log.info("\n[ 1/8 ] Finding trending topic...")
        topic_data = TrendAggregator().get_best_topic()
        log.info(f"  Topic : {topic_data['topic']}")
        log.info(f"  Type  : {topic_data['content_type']}")
        log.info(f"  Lang  : {topic_data['language']}")

        # 2. Script
        log.info("\n[ 2/8 ] Generating script...")
        script = ScriptGenerator().generate(topic_data)
        log.info(f"  Title : {script.get('title', 'N/A')[:70]}")
        log.info(f"  Scenes: {len(script.get('scenes', []))}")

        # 3. Voice
        log.info("\n[ 3/8 ] Generating voice narration...")
        audio_files = VoiceGenerator().generate(script)
        if not audio_files:
            raise RuntimeError("No audio files generated")
        log.info(f"  Audio files: {len(audio_files)}")

        # 4. Images
        log.info("\n[ 4/8 ] Fetching images...")
        image_files = ImageFetcher().fetch_for_script(script)
        if not image_files:
            raise RuntimeError("No images fetched")
        log.info(f"  Images: {len(image_files)}")

        # 5. Music
        log.info("\n[ 5/8 ] Downloading background music...")
        music_path = MusicManager().get_music()
        log.info(f"  Music : {'OK' if music_path else 'Skipped'}")

        # 6. Thumbnail
        log.info("\n[ 6/8 ] Generating thumbnail...")
        bg        = image_files[0]['path'] if image_files else None
        thumbnail = ThumbnailGenerator().generate(script, bg)
        log.info("  Thumbnail: OK")

        # 7. Video
        log.info("\n[ 7/8 ] Assembling video...")
        video_path = VideoAssembler().assemble(
            script, audio_files, image_files, music_path
        )
        if not video_path or not os.path.exists(video_path):
            raise RuntimeError("Video assembly failed")
        mb = os.path.getsize(video_path) / 1_048_576
        log.info(f"  Video : {mb:.1f} MB")
        log.info(f"  Type  : {topic_data['content_type']}")

        # 8. Upload
        log.info("\n[ 8/8 ] Uploading to YouTube...")
        video_id = YouTubeUploader().upload(
            video_path, script, thumbnail
        )

        if video_id:
            HistoryManager().record(
                topic        = topic_data['topic'],
                video_id     = video_id,
                content_type = topic_data['content_type'],
                language     = topic_data['language'],
                title        = script.get('title', ''),
            )
            elapsed = time.time() - t0
            print("\n" + "=" * 55)
            print("  SUCCESS!")
            print(f"  URL  : https://youtu.be/{video_id}")
            print(f"  Topic: {topic_data['topic']}")
            print(f"  Type : {topic_data['content_type']}")
            print(f"  Time : {elapsed:.0f}s")
            print("=" * 55)
        else:
            # Don't crash on upload limit - exit gracefully
            log.warning(
                "Upload failed. Pipeline will retry next run."
            )
            sys.exit(0)

    except Exception as exc:
        print(f"\nPIPELINE ERROR: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        from src.utils.config import Config
        cleanup(Config.TEMP_DIR, Config.TEMP_ASSETS)
        print("Cleanup done.")


if __name__ == '__main__':
    main()
