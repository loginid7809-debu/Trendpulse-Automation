import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
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

        title    = self._title(script_data)
        desc     = self._desc(script_data)
        tags     = script_data.get('tags', ['trending'])[:30]
        category = Config.yt_category(
            script_data.get('category', 'entertainment')
        )

        body = {
            'snippet': {
                'title':                title,
                'description':          desc,
                'tags':                 tags,
                'categoryId':           category,
                'defaultLanguage':      script_data.get('language', 'en'),
                'defaultAudioLanguage': script_data.get('language', 'en'),
            },
            'status': {
                'privacyStatus':           'public',
                'selfDeclaredMadeForKids': False,
                'embeddable':              True,
            },
        }

        mb = os.path.getsize(video_path) / 1_048_576
        log.info(f"Uploading '{title}' ({mb:.1f} MB)...")

        try:
            media   = MediaFileUpload(
                video_path, mimetype='video/mp4',
                resumable=True, chunksize=5 * 1024 * 1024
            )
            request = self.yt.videos().insert(
                part='snippet,status', body=body, media_body=media
            )
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    log.info(f"  Upload: {int(status.progress()*100)}%")

            video_id = response['id']
            log.info(f"Uploaded: https://youtu.be/{video_id}")

            if thumbnail_path and os.path.exists(thumbnail_path):
                self._thumb(video_id, thumbnail_path)

            return video_id

        except Exception as e:
            log.error(f"Upload failed: {e}")
            return None

    def _thumb(self, video_id, path):
        try:
            self.yt.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(path, mimetype='image/jpeg'),
            ).execute()
            log.info("Thumbnail set OK")
        except Exception as e:
            log.warning(f"Thumbnail failed: {e}")

    @staticmethod
    def _title(script_data):
        title = script_data.get('title', 'Trending Now | TrendPulse Global')
        return title[:100] if len(title) > 100 else title

    @staticmethod
    def _desc(script_data):
        topic  = script_data.get('topic', '')
        desc   = script_data.get('description', '')
        scenes = script_data.get('scenes', [])
        lines  = [
            desc, '',
            'TrendPulse Global — Trending content every hour!',
            'Subscribe and turn on notifications.',
            '', 'TIMESTAMPS:',
        ]
        t = 0
        for i, sc in enumerate(scenes):
            dur = int(sc.get('duration_hint', 15))
            lines.append(f"{t//60:02d}:{t%60:02d} — Scene {i+1}")
            t += dur
        lines += [
            '',
            f'#trending #viral #{topic.replace(" ","")} '
            f'#TrendPulseGlobal #facts #news',
            '',
            'Disclaimer: Content is for educational and entertainment '
            'purposes. Visuals are royalty-free stock and AI-generated.',
            '', 'TrendPulse Global',
        ]
        return '\n'.join(lines)[:4990]
