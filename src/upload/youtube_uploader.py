import os
import time
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from src.utils.config import Config
from src.utils.logger import log


class YouTubeUploader:

    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube.force-ssl',
        'https://www.googleapis.com/auth/youtube',
    ]

    def __init__(self):
        self.yt = self._auth()

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
        log.info("YouTube API authenticated OK")
        return build('youtube', 'v3', credentials=creds)

    def upload(self, video_path, script_data, thumbnail_path=None):
        if not os.path.exists(video_path):
            log.error(f"Video missing: {video_path}")
            return None

        title    = self._safe_title(script_data)
        desc     = self._build_desc(script_data)
        tags     = script_data.get('tags', ['trending'])[:30]
        category = Config.yt_category(
            script_data.get('category', 'entertainment')
        )
        ctype    = script_data.get('content_type', 'long_video')
        language = script_data.get('language', 'en')

        body = {
            'snippet': {
                'title':                title,
                'description':          desc,
                'tags':                 tags,
                'categoryId':           category,
                'defaultLanguage':      language,
                'defaultAudioLanguage': language,
            },
            'status': {
                'privacyStatus':           'public',
                'selfDeclaredMadeForKids': False,
                'embeddable':              True,
                'publicStatsViewable':     True,
            },
        }

        mb = os.path.getsize(video_path) / 1_048_576
        log.info(f"Uploading '{title}' ({mb:.1f} MB)...")
        log.info(f"Format: {ctype}")

        try:
            media   = MediaFileUpload(
                video_path,
                mimetype='video/mp4',
                resumable=True,
                chunksize=5 * 1024 * 1024,
            )
            request = self.yt.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media,
            )

            response = None
            retry    = 0
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        pct = int(status.progress() * 100)
                        log.info(f"  Upload: {pct}%")
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        retry += 1
                        if retry > 3:
                            raise
                        wait = 2 ** retry
                        log.warning(f"Server error, retry {retry} in {wait}s")
                        time.sleep(wait)
                    else:
                        raise

            video_id = response['id']
            log.info(f"Uploaded: https://youtu.be/{video_id}")

            # Set thumbnail
            if thumbnail_path and os.path.exists(thumbnail_path):
                self._set_thumbnail(video_id, thumbnail_path)

            # Add to playlist based on type
            self._add_to_playlist(video_id, ctype)

            return video_id

        except HttpError as e:
            error_reason = str(e)
            if 'uploadLimitExceeded' in error_reason:
                log.error(
                    "UPLOAD LIMIT EXCEEDED!\n"
                    "Your YouTube channel has hit the daily upload limit.\n"
                    "SOLUTIONS:\n"
                    "1. Wait 24 hours for limit reset\n"
                    "2. Verify channel at https://www.youtube.com/verify\n"
                    "3. Delete old test videos in YouTube Studio\n"
                    "The pipeline will resume automatically tomorrow."
                )
            elif 'forbidden' in error_reason.lower():
                log.error(f"Permission error: {e}")
            else:
                log.error(f"Upload HTTP error: {e}")
            return None
        except Exception as e:
            log.error(f"Upload failed: {e}")
            return None

    def _set_thumbnail(self, video_id, path):
        try:
            self.yt.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(
                    path, mimetype='image/jpeg'
                ),
            ).execute()
            log.info("Thumbnail set OK")
        except HttpError as e:
            if '403' in str(e):
                log.warning(
                    "Thumbnail upload needs channel verification.\n"
                    "Go to: https://www.youtube.com/verify"
                )
            else:
                log.warning(f"Thumbnail error: {e}")

    def _add_to_playlist(self, video_id, content_type):
        """
        Adds Shorts tag to title if it's a short video.
        YouTube auto-detects Shorts by aspect ratio (9:16)
        and duration (<60 seconds).
        """
        pass  # YouTube auto-detects Shorts from video metadata

    def _safe_title(self, script_data):
        title = script_data.get(
            'title', 'Trending Now | TrendPulse Global'
        )
        ctype = script_data.get('content_type', 'long_video')

        # Ensure #Shorts tag for shorts
        if ctype == 'short':
            if '#shorts' not in title.lower():
                title = title.rstrip() + ' #Shorts'

        return title[:100] if len(title) > 100 else title

    def _build_desc(self, script_data):
        topic  = script_data.get('topic', '')
        desc   = script_data.get('description', '')
        scenes = script_data.get('scenes', [])
        ctype  = script_data.get('content_type', 'long_video')

        lines = [
            desc, '',
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
            '⚡ TrendPulse Global',
            'Trending content posted every few hours!',
            '🔔 Subscribe & turn on notifications',
            '',
        ]

        if ctype == 'long_video':
            lines.append('📌 TIMESTAMPS:')
            t = 0
            for i, sc in enumerate(scenes):
                dur = int(sc.get('duration_hint', 15))
                lines.append(f"{t//60:02d}:{t%60:02d} — Part {i+1}")
                t += dur
            lines.append('')

        tag = topic.replace(' ', '').replace('-', '')[:25]
        lines += [
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
            '👍 Like  |  💬 Comment  |  🔔 Subscribe',
            '',
            f'#trending #viral #{tag} #TrendPulseGlobal '
            f'#news #facts #today',
            '',
            'All visuals are royalty-free stock footage '
            'and AI-generated images.',
            '© TrendPulse Global',
        ]

        if ctype == 'short':
            lines.append('#shorts #short #ytshorts')

        return '\n'.join(lines)[:4990]
