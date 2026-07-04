import json
import random
import google.generativeai as genai
from src.utils.config import Config
from src.utils.logger import log


class ScriptGenerator:

    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate(self, topic_data):
        topic        = topic_data['topic']
        content_type = topic_data['content_type']
        language     = topic_data['language']
        log.info(f"Generating script: '{topic}' [{content_type}|{language}]")

        if content_type == 'short':
            script = self._short(topic, language)
        else:
            script = self._long(topic, language)

        if not script:
            script = self._fallback(topic, language, content_type)

        script.update({
            'topic':        topic,
            'language':     language,
            'content_type': content_type,
        })
        log.info(f"Script title: {script.get('title','N/A')}")
        log.info(f"Scenes: {len(script.get('scenes',[]))}")
        return script

    def _long(self, topic, language):
        lang = 'Hindi' if language == 'hi' else 'English'
        prompt = f"""You are a YouTube content creator for "TrendPulse Global".
Write an ORIGINAL engaging video script about: "{topic}"
Language: {lang}
Duration: 4-6 minutes

Return ONLY raw JSON, no markdown fences:
{{
  "title": "Engaging SEO title with emoji under 100 chars",
  "description": "YouTube description 200 words with hashtags",
  "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8"],
  "category": "entertainment",
  "thumbnail_text": "2-4 impactful words",
  "scenes": [
    {{
      "narration": "2-3 sentence narration",
      "visual_query": "image search query",
      "duration_hint": 20
    }}
  ],
  "intro_hook": "One powerful opening sentence",
  "outro": "Subscribe CTA sentence"
}}
Include 8-12 scenes."""
        return self._call(prompt, 4096)

    def _short(self, topic, language):
        lang = 'Hindi' if language == 'hi' else 'English'
        prompt = f"""You are a YouTube Shorts creator for "TrendPulse Global".
Create a 40-55 second Short about: "{topic}"
Language: {lang}

Return ONLY raw JSON, no markdown fences:
{{
  "title": "Catchy title with emoji #Shorts under 100 chars",
  "description": "Short description with hashtags",
  "tags": ["tag1","tag2","tag3","tag4","tag5","#shorts"],
  "category": "entertainment",
  "thumbnail_text": "2-3 word hook",
  "scenes": [
    {{
      "narration": "1-2 sentence narration",
      "visual_query": "image search query",
      "duration_hint": 10
    }}
  ],
  "intro_hook": "Attention grabbing opening",
  "outro": "Quick subscribe CTA"
}}
Include 4-6 scenes."""
        return self._call(prompt, 2048)

    def _call(self, prompt, max_tokens):
        try:
            resp = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,
                    max_output_tokens=max_tokens,
                ),
            )
            return self._parse(resp.text)
        except Exception as e:
            log.error(f"Gemini error: {e}")
            return None

    def _parse(self, text):
        text = text.strip()
        for fence in ['```json', '```']:
            if text.startswith(fence):
                text = text[len(fence):]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            s = text.find('{')
            e = text.rfind('}')
            if s != -1 and e > s:
                try:
                    return json.loads(text[s:e+1])
                except Exception:
                    pass
        log.warning("Could not parse Gemini response")
        return None

    def _fallback(self, topic, language, content_type):
        log.warning("Using fallback script")
        is_short = content_type == 'short'
        if is_short:
            scenes = [
                {"narration": f"Did you know this incredible fact about {topic}?",
                 "visual_query": topic, "duration_hint": 10},
                {"narration": f"{topic} is making headlines worldwide right now.",
                 "visual_query": f"{topic} news", "duration_hint": 12},
                {"narration": "The implications are massive and affect all of us!",
                 "visual_query": f"{topic} impact", "duration_hint": 10},
                {"narration": "Subscribe to TrendPulse Global for hourly updates!",
                 "visual_query": "subscribe youtube", "duration_hint": 8},
            ]
        else:
            scenes = [
                {"narration": f"Welcome to TrendPulse Global. Today we explore {topic}.",
                 "visual_query": topic, "duration_hint": 15},
                {"narration": f"{topic} has become one of the most discussed topics globally.",
                 "visual_query": f"{topic} world", "duration_hint": 20},
                {"narration": "Let us break down why this matters and what experts say.",
                 "visual_query": f"{topic} experts", "duration_hint": 20},
                {"narration": "Here are key facts most people do not know about this.",
                 "visual_query": f"{topic} facts", "duration_hint": 25},
                {"narration": "The long term impact could reshape everything we know.",
                 "visual_query": f"{topic} future", "duration_hint": 20},
                {"narration": "Our analysis shows three major takeaways from this.",
                 "visual_query": "infographic analysis", "duration_hint": 20},
                {"narration": "Subscribe to TrendPulse Global for more every hour!",
                 "visual_query": "subscribe youtube", "duration_hint": 15},
            ]
        suffix = " #Shorts" if is_short else ""
        return {
            "title":          f"🔥 {topic} — What You Need To Know!{suffix}",
            "description":    (f"Everything about {topic}.\n\n"
                               f"#trending #{topic.replace(' ','')} "
                               f"#TrendPulseGlobal #viral #2024"),
            "tags":           [topic, "trending", "viral",
                               "TrendPulse", "facts", "news", "2024"],
            "category":       "entertainment",
            "thumbnail_text": topic[:30],
            "scenes":         scenes,
            "intro_hook":     f"You will not believe what is happening with {topic}!",
            "outro":          "Subscribe to TrendPulse Global — new content every hour!",
        }
