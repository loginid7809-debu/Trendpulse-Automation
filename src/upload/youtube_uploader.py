import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from src.utils.config import Config
from src.utils.logger import log


class YouTubeUploader:
    """Upload videos to YouTube via Data API v3."""

    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube.force-ssl',
        'https://www.googleapis.com/auth/youtube',
    ]

    def __init__(self):
        self.yt = self._auth()

    def upload(self, video_path: str, script_data: dict,
               thumbnail_path: str | None = None) -> str | None:

        if not os.path.exists(video_path):
            log.error(f"Video file missing: {video_path}")
            return None

        title       = self._safe_title(script_data)
        description = self._build_description(script_data)
        tags        = script_data.get('tags', ['trending', 'viral'])[:30]
        category    = Config.yt_category(script_data.get('category', 'entertainment'))

        body = {
            'snippet': {
                'title':                title,
                'description':          description,
                'tags':                 tags,
                'categoryId':           category,
                'defaultLanguage':      script_data.get('language', 'en'),
                'defaultAudioLanguage': script_data.get('language', 'en'),
            },
            'status': {
                'privacyStatus':            'public',
                'selfDeclaredMadeForKids':  False,
                'embeddable':               True,
                'publicStatsViewable':      True,
            },
        }

        size_mb = os.path.getsize(video_path) / 1_048_576
        log.info(f"Uploading '{title}' ({size_mb:.1f} MB)…")

        try:
            media   = MediaFileUpload(video_path, mimetype='video/mp4',
                                      resumable=True,
                                      chunksize=5 * 1024 * 1024)
            request = self.yt.videos().insert(
                part='snippet,status', body=body, media_body=media)

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    log.info(f"  Upload: {pct}%")

            video_id = response['id']
            log.info(f"✅ Uploaded → https://youtu.be/{video_id}")

            if thumbnail_path and os.path.exists(thumbnail_path):
                self._set_thumb(video_id, thumbnail_path)

            return video_id

        except Exception as e:
            log.error(f"Upload failed: {e}")
            return None

    # ── helpers ───────────────────────────────────────────────

    def _auth(self):
        creds = Credentials(
            token=None,
            refresh_token=Config.YOUTUBE_REFRESH_TOKEN,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=Config.YOUTUBE_CLIENT_ID,
            client_secret=Config.YOUTUBE_CLIENT_SECRET,
            scopes=self.SCOPES,
        )
        creds.refresh(Request())
        log.info("YouTube API authenticated ✓")
        return build('youtube', 'v3', credentials=creds)

    def _set_thumb(self, video_id: str, path: str):
        try:
            self.yt.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(path, mimetype='image/jpeg'),
            ).execute()
            log.info("Thumbnail set ✓")
        except Exception as e:
            log.warning(f"Thumbnail upload failed: {e}")

    @staticmethod
    def _safe_title(script_data: dict) -> str:
        title = script_data.get('title', 'Trending Now | TrendPulse Global')
        if len(title) > 100:
            title = title[:97] + '…'
        return title

    @staticmethod
    def _build_description(script_data: dict) -> str:
        topic  = script_data.get('topic', '')
        desc   = script_data.get('description', '')
        scenes = script_data.get('scenes', [])

        lines = [
            desc, '',
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
            '⚡ TrendPulse Global — Trending content every few hours!',
            '🔔 Subscribe & hit the bell so you never miss a trend.',
            '',
            '📌 TIMESTAMPS:',
        ]
        t = 0
        for i, sc in enumerate(scenes):
            dur = int(sc.get('duration_hint', 15))
            lines.append(f"{t//60:02d}:{t%60:02d} — Scene {i+1}")
            t += dur

        lines += [
            '',
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
            '👍 Like  |  💬 Comment  |  🔔 Subscribe',
            '',
            f'#trending #viral #{topic.replace(" ","")} '
            f'#TrendPulseGlobal #facts #news #2024',
            '',
            '⚠️ Disclaimer: Content is for educational & entertainment '
            'purposes. Visuals are royalty-free stock & AI-generated images.',
            '',
            '© TrendPulse Global',
        ]
        full = '\n'.join(lines)
        return full[:4990]  # YouTube 5000-char limit
