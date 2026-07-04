import json
import random
import google.generativeai as genai
from src.utils.config import Config
from src.utils.logger import log


class ScriptGenerator:

    # Try these models in order until one works
    MODELS = [
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash',
        'gemini-1.5-pro-latest',
        'gemini-pro',
        'gemini-1.0-pro',
    ]

    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = self._get_working_model()

    def _get_working_model(self):
        """Try each model name until one works."""
        for model_name in self.MODELS:
            try:
                m = genai.GenerativeModel(model_name)
                # Quick test call
                test = m.generate_content(
                    "Say OK",
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=5,
                        temperature=0.1,
                    )
                )
                log.info(f"Gemini model working: {model_name}")
                return m
            except Exception as e:
                log.warning(f"Model {model_name} failed: {e}")
                continue

        log.warning("No Gemini model available - will use fallback scripts")
        return None

    def generate(self, topic_data):
        topic        = topic_data['topic']
        content_type = topic_data['content_type']
        language     = topic_data['language']

        log.info(f"Generating [{content_type}|{language}]: '{topic[:60]}'")

        script = None

        if self.model:
            try:
                if content_type == 'short':
                    script = self._short(topic, language)
                else:
                    script = self._long(topic, language)
            except Exception as e:
                log.error(f"Script generation failed: {e}")

        if not script:
            log.warning("Using fallback script")
            script = self._fallback(topic, language, content_type)

        script.update({
            'topic':        topic,
            'language':     language,
            'content_type': content_type,
        })

        log.info(f"Title : {script.get('title', 'N/A')[:70]}")
        log.info(f"Scenes: {len(script.get('scenes', []))}")
        return script

    def _long(self, topic, language):
        lang = 'Hindi' if language == 'hi' else 'English'
        prompt = f"""You are a YouTube content creator for "TrendPulse Global".
Write an ORIGINAL engaging video script about: "{topic}"
Language: {lang}

Return ONLY valid JSON starting with {{ and ending with }}.
No markdown. No backticks. No explanation outside JSON.

{{
  "title": "Engaging title with emoji max 90 chars",
  "description": "YouTube description 150 words with hashtags",
  "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8"],
  "category": "entertainment",
  "thumbnail_text": "3 word hook",
  "scenes": [
    {{
      "narration": "2-3 sentence narration text",
      "visual_query": "image search keyword",
      "duration_hint": 20
    }}
  ],
  "intro_hook": "One powerful opening sentence",
  "outro": "Subscribe CTA"
}}

Include exactly 8 scenes. Natural conversational tone."""
        return self._call(prompt, 3000)

    def _short(self, topic, language):
        lang = 'Hindi' if language == 'hi' else 'English'
        prompt = f"""You are a YouTube Shorts creator for "TrendPulse Global".
Create a 45 second Short script about: "{topic}"
Language: {lang}

Return ONLY valid JSON starting with {{ and ending with }}.
No markdown. No backticks.

{{
  "title": "Catchy title with emoji #Shorts max 90 chars",
  "description": "Short description with hashtags",
  "tags": ["tag1","tag2","tag3","tag4","#shorts"],
  "category": "entertainment",
  "thumbnail_text": "2 word hook",
  "scenes": [
    {{
      "narration": "1-2 sentence narration",
      "visual_query": "image keyword",
      "duration_hint": 10
    }}
  ],
  "intro_hook": "Attention grabbing first line",
  "outro": "Subscribe CTA"
}}

Include exactly 5 scenes."""
        return self._call(prompt, 1500)

    def _call(self, prompt, max_tokens):
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=max_tokens,
                ),
            )
            return self._parse(response.text)
        except Exception as e:
            log.error(f"Gemini call failed: {e}")
            return None

    def _parse(self, text):
        if not text:
            return None
        text = text.strip()
        for fence in ['```json', '```JSON', '```']:
            if text.startswith(fence):
                text = text[len(fence):]
                break
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
            if isinstance(data, dict) and 'scenes' in data:
                return data
        except Exception:
            pass

        s = text.find('{')
        e = text.rfind('}')
        if s != -1 and e > s:
            try:
                data = json.loads(text[s:e + 1])
                if isinstance(data, dict) and 'scenes' in data:
                    return data
            except Exception:
                pass

        log.warning("Could not parse Gemini JSON")
        return None

    def _fallback(self, topic, language, content_type):
        is_short = content_type == 'short'
        # Clean topic for use in narration
        clean_topic = topic.replace(' - CNN', '').replace(
            ' - BBC', '').replace(' - Reuters', '').strip()
        clean_topic = clean_topic[:80]

        if is_short:
            scenes = [
                {
                    "narration": (
                        f"You will not believe what is happening "
                        f"with {clean_topic} right now!"
                    ),
                    "visual_query": clean_topic[:40],
                    "duration_hint": 10,
                },
                {
                    "narration": (
                        f"This is trending worldwide and millions "
                        f"of people are talking about it today."
                    ),
                    "visual_query": f"{clean_topic[:30]} news",
                    "duration_hint": 12,
                },
                {
                    "narration": (
                        "Experts are calling this one of the most "
                        "significant stories of the year."
                    ),
                    "visual_query": "experts analysis news",
                    "duration_hint": 10,
                },
                {
                    "narration": (
                        "The full story is even more interesting "
                        "than what the headlines are showing."
                    ),
                    "visual_query": "breaking news world",
                    "duration_hint": 10,
                },
                {
                    "narration": (
                        "Subscribe to TrendPulse Global for trending "
                        "updates every single hour!"
                    ),
                    "visual_query": "subscribe youtube",
                    "duration_hint": 8,
                },
            ]
            title = f"🔥 {clean_topic[:55]} #Shorts"
        else:
            scenes = [
                {
                    "narration": (
                        f"Welcome to TrendPulse Global. Today we are "
                        f"covering {clean_topic}, which is one of the "
                        f"biggest stories trending right now."
                    ),
                    "visual_query": clean_topic[:40],
                    "duration_hint": 18,
                },
                {
                    "narration": (
                        f"Here is everything you need to know about "
                        f"{clean_topic} and why it matters to you "
                        f"and millions of people worldwide."
                    ),
                    "visual_query": f"{clean_topic[:30]} explained",
                    "duration_hint": 22,
                },
                {
                    "narration": (
                        "Let us start with the background. "
                        "Understanding the context here is essential "
                        "to grasping the full picture."
                    ),
                    "visual_query": "background context history",
                    "duration_hint": 20,
                },
                {
                    "narration": (
                        "The key facts that everyone needs to know "
                        "are being discussed by experts and analysts "
                        "from around the globe."
                    ),
                    "visual_query": "facts analysis global",
                    "duration_hint": 22,
                },
                {
                    "narration": (
                        "What makes this story particularly compelling "
                        "is the way it connects to larger trends we "
                        "have been tracking for months."
                    ),
                    "visual_query": "global trends connection",
                    "duration_hint": 22,
                },
                {
                    "narration": (
                        "There are three key takeaways from this "
                        "story that will affect how things unfold "
                        "over the coming weeks and months."
                    ),
                    "visual_query": "key points takeaways",
                    "duration_hint": 22,
                },
                {
                    "narration": (
                        "Looking ahead, the situation is expected "
                        "to develop significantly. Stay informed "
                        "and stay ahead of the curve."
                    ),
                    "visual_query": "future outlook prediction",
                    "duration_hint": 20,
                },
                {
                    "narration": (
                        "Thank you for watching TrendPulse Global. "
                        "Subscribe and turn on notifications to get "
                        "trending content delivered every hour."
                    ),
                    "visual_query": "subscribe youtube trending",
                    "duration_hint": 18,
                },
            ]
            title = f"🔥 {clean_topic[:65]} — Full Story"

        return {
            "title": title,
            "description": (
                f"Full coverage of {clean_topic}.\n\n"
                f"TrendPulse Global covers the biggest trending "
                f"topics every hour.\n\n"
                f"#trending #TrendPulseGlobal #viral #news #facts"
            ),
            "tags": [
                clean_topic[:40], "trending", "viral",
                "TrendPulse", "news", "facts", "2024"
            ],
            "category": "entertainment",
            "thumbnail_text": clean_topic[:20],
            "scenes": scenes,
            "intro_hook": (
                f"Here is everything you need to know about "
                f"{clean_topic} right now!"
            ),
            "outro": (
                "Subscribe to TrendPulse Global for hourly "
                "trending content around the clock!"
            ),
        }
