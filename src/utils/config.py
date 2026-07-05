import os
import random


class Config:

    CHANNEL_NAME    = "TrendPulse Global"
    CHANNEL_TAGLINE = "Your hourly pulse on what's trending worldwide!"

    YOUTUBE_CLIENT_ID     = os.environ.get('YOUTUBE_CLIENT_ID',     '')
    YOUTUBE_CLIENT_SECRET = os.environ.get('YOUTUBE_CLIENT_SECRET', '')
    YOUTUBE_REFRESH_TOKEN = os.environ.get('YOUTUBE_REFRESH_TOKEN', '')
    GEMINI_API_KEY        = os.environ.get('GEMINI_API_KEY',        '')
    GROQ_API_KEY          = os.environ.get('GROQ_API_KEY',          '')
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

    # 100% Copyright-free music - YouTube Audio Library
    # These are confirmed public domain / CC0 tracks
    MUSIC_URLS = [
        # FreePD.com - 100% Public Domain
        "https://freepd.com/music/Wakingup.mp3",
        "https://freepd.com/music/Mysterious%20Ambiance.mp3",
        "https://freepd.com/music/Surf%20Shimmy.mp3",
        # Mixkit free music (royalty free)
        "https://assets.mixkit.co/music/preview/mixkit-tech-house-vibes-130.mp3",
        "https://assets.mixkit.co/music/preview/mixkit-hip-hop-02-738.mp3",
        "https://assets.mixkit.co/music/preview/mixkit-dreaming-big-31.mp3",
        "https://assets.mixkit.co/music/preview/mixkit-a-very-happy-christmas-897.mp3",
        "https://assets.mixkit.co/music/preview/mixkit-deep-urban-623.mp3",
        "https://assets.mixkit.co/music/preview/mixkit-serene-view-443.mp3",
        "https://assets.mixkit.co/music/preview/mixkit-games-worldbeat-466.mp3",
    ]

    GEMINI_MODELS = [
        'gemini-2.0-flash',
        'gemini-2.0-flash-lite',
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash',
        'gemini-1.5-pro',
    ]

    GROQ_MODELS = [
        'llama-3.3-70b-versatile',
        'llama-3.1-8b-instant',
        'mixtral-8x7b-32768',
        'gemma2-9b-it',
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
