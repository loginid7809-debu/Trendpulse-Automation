import json
import random
import google.generativeai as genai
from src.utils.config import Config
from src.utils.logger import log


class ScriptGenerator:
    """Generate video scripts with Google Gemini 1.5 Flash (free tier)."""

    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    # ── Public ────────────────────────────────────────────────

    def generate(self, topic_data: dict) -> dict:
        topic        = topic_data['topic']
        content_type = topic_data['content_type']
        language     = topic_data['language']

        log.info(f"Generating script: '{topic}' [{content_type}|{language}]")

        if content_type == 'short':
            script = self._gen_short(topic, language)
        else:
            script = self._gen_long(topic, language)

        if not script:
            script = self._fallback(topic, language, content_type)

        script.update({
            'topic':        topic,
            'language':     language,
            'content_type': content_type,
        })
        log.info(f"  Title  : {script.get('title','N/A')}")
        log.info(f"  Scenes : {len(script.get('scenes',[]))}")
        return script

    # ── Private ───────────────────────────────────────────────

    def _gen_long(self, topic: str, language: str) -> dict | None:
        lang_name = 'Hindi' if language == 'hi' else 'English'
        prompt = f"""
You are a professional YouTube content creator for "TrendPulse Global".

Write an ORIGINAL, engaging video script about: "{topic}"
Language : {lang_name}
Duration : 4-6 minutes (~700-900 words of narration)

Rules:
- 100% original analysis and perspective
- Educational + entertaining
- No copyrighted material
- Engaging storytelling

Return ONLY raw JSON (no markdown):
{{
  "title": "Engaging SEO title with emoji ≤100 chars",
  "description": "YouTube description 200-300 words with hashtags",
  "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"],
  "category": "one of: entertainment|science|technology|sports|news|education|gaming|people",
  "thumbnail_text": "2-5 impactful words",
  "scenes": [
    {{
      "narration": "2-4 sentence narration for this scene",
      "visual_query": "image search query for stock photo",
      "duration_hint": 20
    }}
  ],
  "intro_hook": "One powerful opening sentence",
  "outro": "Subscribe CTA sentence"
}}
Include 8-14 scenes total.
"""
        return self._call_gemini(prompt, 4096)

    def _gen_short(self, topic: str, language: str) -> dict | None:
        lang_name = 'Hindi' if language == 'hi' else 'English'
        prompt = f"""
You are a viral YouTube Shorts creator for "TrendPulse Global".

Create a 40-55 second Short script about: "{topic}"
Language: {lang_name}

Rules:
- Hook in FIRST 2 seconds
- Fast-paced, surprising
- Max 120 words total
- 100% original

Return ONLY raw JSON (no markdown):
{{
  "title": "Catchy title with emoji + #Shorts ≤100 chars",
  "description": "Short description with hashtags",
  "tags": ["tag1","tag2","tag3","tag4","tag5","#shorts"],
  "category": "one of: entertainment|science|technology|news|education",
  "thumbnail_text": "2-3 word hook",
  "scenes": [
    {{
      "narration": "1-2 sentence narration",
      "visual_query": "image search query",
      "duration_hint": 10
    }}
  ],
  "intro_hook": "Attention-grabbing opening",
  "outro": "Quick subscribe CTA"
}}
Include 4-6 scenes total.
"""
        return self._call_gemini(prompt, 2048)

    def _call_gemini(self, prompt: str, max_tokens: int) -> dict | None:
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,
                    max_output_tokens=max_tokens,
                ),
            )
            return self._parse(response.text)
        except Exception as e:
            log.error(f"Gemini API error: {e}")
            return None

    def _parse(self, text: str) -> dict | None:
        text = text.strip()
        # Strip markdown fences if present
        for fence in ['```json', '```']:
            if text.startswith(fence):
                text = text[len(fence):]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to salvage JSON between first { and last }
            s = text.find('{')
            e = text.rfind('}')
            if s != -1 and e > s:
                try:
                    return json.loads(text[s:e+1])
                except Exception:
                    pass
        log.warning("Could not parse Gemini JSON response")
        return None

    # ── Fallback script ───────────────────────────────────────

    def _fallback(self, topic: str, language: str,
                  content_type: str) -> dict:
        log.warning("Using fallback script")
        is_short = content_type == 'short'
        scenes = (
            [
                {"narration": f"Did you know this incredible fact about {topic}?",
                 "visual_query": topic, "duration_hint": 8},
                {"narration": f"{topic} is making headlines worldwide — here is why.",
                 "visual_query": f"{topic} news", "duration_hint": 12},
                {"narration": "The implications are massive. Stay informed!",
                 "visual_query": f"{topic} impact", "duration_hint": 10},
                {"narration": "Subscribe to TrendPulse Global for hourly updates!",
                 "visual_query": "subscribe youtube", "duration_hint": 6},
            ] if is_short else [
                {"narration": f"Welcome to TrendPulse Global. Today we explore {topic}.",
                 "visual_query": topic, "duration_hint": 15},
                {"narration": f"{topic} has become one of the most discussed topics globally.",
                 "visual_query": f"{topic} world", "duration_hint": 20},
                {"narration": "Let us break down why this matters and what experts say.",
                 "visual_query": f"{topic} experts", "duration_hint": 20},
                {"narration": "Here are key facts most people do not know.",
                 "visual_query": f"{topic} facts", "duration_hint": 25},
                {"narration": "The long-term impact could reshape everything.",
                 "visual_query": f"{topic} future", "duration_hint": 20},
                {"narration": "Our analysis shows three major takeaways.",
                 "visual_query": "infographic analysis", "duration_hint": 20},
                {"narration": "Subscribe for more trending content every hour!",
                 "visual_query": "subscribe youtube", "duration_hint": 15},
            ]
        )
        title_suffix = " #Shorts" if is_short else ""
        return {
            "title":          f"🔥 {topic} — What You Need To Know!{title_suffix}",
            "description":    (f"Everything about {topic}.\n\n"
                               f"#trending #{topic.replace(' ','')} "
                               f"#TrendPulseGlobal #viral #2024"),
            "tags":           [topic, "trending", "viral", "TrendPulse",
                               "facts", "news", "2024"],
            "category":       "entertainment",
            "thumbnail_text": topic[:30],
            "scenes":         scenes,
            "intro_hook":     f"You won't believe what is happening with {topic}!",
            "outro":          "Subscribe to TrendPulse Global — new content every hour!",
        }
