import os
import random


class Config:

    CHANNEL_NAME    = "TrendPulse Global"
    CHANNEL_TAGLINE = "Your hourly pulse on what's trending worldwide!"

    YOUTUBE_CLIENT_ID     = os.environ.get('YOUTUBE_CLIENT_ID',     '')
    YOUTUBE_CLIENT_SECRET = os.environ.get('YOUTUBE_CLIENT_SECRET', '')
    YOUTUBE_REFRESH_TOKEN = os.environ.get('YOUTUBE_REFRESH_TOKEN', '')
    GEMINI_API_KEY        = os.environ.get('GEMINI_API_KEY',        '')
    PEXELS_API_KEY        = os.environ.get('PEXELS_API_KEY',        '')
    NEWS_API_KEY          = os.environ.get('NEWS_API_KEY',          '')

    BASE_DIR     = os.path.dirname(
                       os.path.dirname(
                           os.path.dirname(os.path.abspath(__file__))
                       )
                   )
    TEMP_DIR     = os.path.join(BASE_DIR, 'temp_output')
    TEMP_ASSETS  = os.path.join(BASE_DIR, 'temp_assets')
    DATA_DIR     = os.path.join(BASE_DIR, 'data')
    ASSETS_DIR   = os.path.join(BASE_DIR, 'assets')
    FONTS_DIR    = os.path.join(BASE_DIR, 'assets', 'fonts')
    HISTORY_FILE = os.path.join(BASE_DIR, 'data', 'upload_history.json')

    VIDEO_RES_LANDSCAPE = (1920, 1080)
    VIDEO_RES_PORTRAIT  = (1080, 1920)
    FPS = 24

    VOICES_EN = [
        'en-US-GuyNeural',
        'en-US-JennyNeural',
        'en-US-TonyNeural',
        'en-US-AriaNeural',
        'en-GB-RyanNeural',
        'en-AU-NatashaNeural',
        'en-IN-NeerjaNeural',
    ]
    VOICES_HI = [
        'hi-IN-MadhurNeural',
        'hi-IN-SwaraNeural',
    ]

    THUMB_PALETTES = [
        [(180, 0,   0),   (255, 120, 0)],
        [(0,   40,  180), (0,   180, 255)],
        [(100, 0,   180), (255, 0,   120)],
        [(0,   120, 0),   (0,   220, 100)],
        [(255, 180, 0),   (255, 80,  0)],
        [(20,  20,  20),  (60,  60,  60)],
    ]

    YT_CATEGORIES = {
        'entertainment': '24',
        'science':       '28',
        'technology':    '28',
        'sports':        '17',
        'news':          '25',
        'education':     '27',
        'gaming':        '20',
        'people':        '22',
        'comedy':        '23',
        'howto':         '26',
    }

    MUSIC_URLS = [
        "https://cdn.pixabay.com/download/audio/2022/03/15/audio_115fe888fc.mp3",
        "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3",
        "https://cdn.pixabay.com/download/audio/2021/11/25/audio_cb4b9e6e07.mp3",
        "https://cdn.pixabay.com/download/audio/2022/10/25/audio_946bc5ce6e.mp3",
        "https://cdn.pixabay.com/download/audio/2023/05/16/audio_166b39e84a.mp3",
        "https://cdn.pixabay.com/download/audio/2022/08/02/audio_884fe92c21.mp3",
        "https://cdn.pixabay.com/download/audio/2021/08/09/audio_88447e769a.mp3",
    ]

    @classmethod
    def random_voice(cls, language='en'):
        pool = cls.VOICES_HI if language == 'hi' else cls.VOICES_EN
        return random.choice(pool)

    @classmethod
    def random_palette(cls):
        return random.choice(cls.THUMB_PALETTES)

    @classmethod
    def ensure_dirs(cls):
        for p in [cls.TEMP_DIR, cls.TEMP_ASSETS,
                  cls.DATA_DIR, cls.FONTS_DIR]:
            os.makedirs(p, exist_ok=True)

    @classmethod
    def yt_category(cls, name='entertainment'):
        return cls.YT_CATEGORIES.get(name.lower(), '22')
