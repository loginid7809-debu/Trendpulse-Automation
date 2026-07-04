# TrendPulse Global - Automated YouTube Channel

Fully automated YouTube channel that posts trending content every hour.
Zero manual intervention after setup.

## Tech Stack
- Python 3.11
- GitHub Actions (automation)
- Google Gemini AI (script generation)
- edge-tts (voice narration)
- MoviePy + FFmpeg (video assembly)
- Pexels + Unsplash + Pollinations (images)
- YouTube Data API v3 (upload)
- Google Apps Script (hourly trigger)

## Setup

### 1. Get API Keys
| Service | URL | Purpose |
|---------|-----|---------|
| Google Gemini | https://aistudio.google.com | Script generation |
| Pexels | https://www.pexels.com/api | Stock images |
| NewsAPI | https://newsapi.org/register | News trends |
| YouTube API | https://console.cloud.google.com | Video upload |

### 2. Generate YouTube Token
```bash
pip install google-auth-oauthlib google-api-python-client
python generate_token.py
