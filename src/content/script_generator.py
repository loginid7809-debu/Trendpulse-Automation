import json
import time
import google.generativeai as genai
from src.utils.config import Config
from src.utils.logger import log


class ScriptGenerator:

    def __init__(self):
        self.groq_client  = self._init_groq()
        self.groq_model   = None
        self.gemini_model = self._init_gemini()

        if self.groq_client:
            self.groq_model = self._get_working_groq_model()

    def _init_groq(self):
        if not Config.GROQ_API_KEY:
            log.warning("GROQ_API_KEY not set")
            return None
        try:
            from groq import Groq
            client = Groq(api_key=Config.GROQ_API_KEY)
            log.info("Groq client initialized")
            return client
        except Exception as e:
            log.warning(f"Groq init failed: {e}")
            return None

    def _get_working_groq_model(self):
        for model in Config.GROQ_MODELS:
            try:
                resp = self.groq_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Say OK"}],
                    max_tokens=5,
                    temperature=0.1,
                )
                result = resp.choices[0].message.content.strip()
                log.info(f"Groq model working: {model} -> {result}")
                return model
            except Exception as e:
                log.warning(f"Groq model {model} failed: {e}")
                continue
        log.error("No Groq model available")
        return None

    def _init_gemini(self):
        if not Config.GEMINI_API_KEY:
            return None
        try:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            for model_name in Config.GEMINI_MODELS:
                try:
                    m = genai.GenerativeModel(model_name)
                    m.generate_content(
                        "Say OK",
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=5,
                            temperature=0.1,
                        )
                    )
                    log.info(f"Gemini model working: {model_name}")
                    return m
                except Exception as e:
                    log.warning(f"Gemini {model_name}: {e}")
                    time.sleep(1)
                    continue
        except Exception as e:
            log.warning(f"Gemini init failed: {e}")
        return None

    def generate(self, topic_data):
        topic        = topic_data['topic']
        content_type = topic_data['content_type']
        language     = topic_data['language']

        log.info(f"Generating [{content_type}|{language}]: '{topic[:60]}'")

        script = None

        # Try Groq first (primary - free, fast, no quota issues)
        if self.groq_client and self.groq_model:
            try:
                log.info("Trying Groq AI...")
                script = self._groq_generate(topic, content_type, language)
                if script:
                    log.info("Script from Groq AI")
            except Exception as e:
                log.warning(f"Groq generation failed: {e}")

        # Try Gemini second (fallback)
        if not script and self.gemini_model:
            try:
                log.info("Trying Gemini AI...")
                if content_type == 'short':
                    script = self._gemini_short(topic, language)
                else:
                    script = self._gemini_long(topic, language)
                if script:
                    log.info("Script from Gemini AI")
            except Exception as e:
                log.warning(f"Gemini generation failed: {e}")

        # Use fallback script if all AI fails
        if not script:
            log.warning("All AI failed - using fallback script")
            script = self._fallback(topic, language, content_type)

        script.update({
            'topic':        topic,
            'language':     language,
            'content_type': content_type,
        })

        log.info(f"Title : {script.get('title', 'N/A')[:70]}")
        log.info(f"Scenes: {len(script.get('scenes', []))}")
        return script

    def _groq_generate(self, topic, content_type, language):
        lang     = 'Hindi' if language == 'hi' else 'English'
        is_short = content_type == 'short'

        if is_short:
            scene_count = 5
            duration    = "45 seconds"
            scene_dur   = 9
        else:
            scene_count = 8
            duration    = "4-5 minutes"
            scene_dur   = 20

        prompt = f"""You are a professional YouTube content creator for "TrendPulse Global".

Create a {duration} YouTube {"Short" if is_short else "video"} script about:
"{topic}"

Language: {lang}

CRITICAL: Respond with ONLY a valid JSON object. Nothing else before or after it.

{{
  "title": "{"Engaging title with emoji #Shorts" if is_short else "Engaging SEO title with emoji"} (max 90 chars)",
  "description": "YouTube description with relevant hashtags (100 words)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "category": "entertainment",
  "thumbnail_text": "3 powerful words",
  "scenes": [
    {{
      "narration": "{"1-2 sentences" if is_short else "2-3 sentences"} of engaging narration",
      "visual_query": "specific image search query",
      "duration_hint": {scene_dur}
    }}
  ],
  "intro_hook": "One attention-grabbing opening sentence",
  "outro": "Call to action for subscribers"
}}

Include exactly {scene_count} scenes. Make content original, engaging, informative."""

        try:
            resp = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a YouTube script writer. "
                            "Always respond with valid JSON only. "
                            "No markdown, no explanation, just JSON."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000 if not is_short else 1500,
                temperature=0.7,
            )
            text = resp.choices[0].message.content
            return self._parse(text)
        except Exception as e:
            log.error(f"Groq API call failed: {e}")
            return None

    def _gemini_long(self, topic, language):
        lang   = 'Hindi' if language == 'hi' else 'English'
        prompt = f"""Create a YouTube video script about: "{topic}"
Language: {lang}

Return ONLY valid JSON (no markdown):
{{
  "title": "title with emoji max 90 chars",
  "description": "description with hashtags",
  "tags": ["tag1","tag2","tag3","tag4","tag5"],
  "category": "entertainment",
  "thumbnail_text": "3 words",
  "scenes": [
    {{"narration": "2-3 sentences", "visual_query": "keyword", "duration_hint": 20}}
  ],
  "intro_hook": "opening sentence",
  "outro": "subscribe CTA"
}}
Include exactly 8 scenes."""
        return self._gemini_call(prompt, 3000)

    def _gemini_short(self, topic, language):
        lang   = 'Hindi' if language == 'hi' else 'English'
        prompt = f"""Create a 45 second YouTube Short about: "{topic}"
Language: {lang}

Return ONLY valid JSON (no markdown):
{{
  "title": "title emoji #Shorts max 90 chars",
  "description": "description hashtags",
  "tags": ["tag1","tag2","tag3","#shorts"],
  "category": "entertainment",
  "thumbnail_text": "2 words",
  "scenes": [
    {{"narration": "1-2 sentences", "visual_query": "keyword", "duration_hint": 9}}
  ],
  "intro_hook": "hook",
  "outro": "CTA"
}}
Include exactly 5 scenes."""
        return self._gemini_call(prompt, 1500)

    def _gemini_call(self, prompt, max_tokens):
        try:
            response = self.gemini_model.generate_content(
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

        log.warning("Could not parse AI JSON response")
        return None

    def _fallback(self, topic, language, content_type):
        is_short = content_type == 'short'
        clean    = (topic
                    .replace(' - CNN', '')
                    .replace(' - BBC', '')
                    .replace(' - Reuters', '')
                    .replace(' - Yahoo', '')
                    .replace(' - Fox News', '')
                    .replace(' - NBC', '')
                    .strip()[:80])

        if is_short:
            scenes = [
                {
                    "narration": (
                        f"You will not believe what is happening "
                        f"with {clean} right now!"
                    ),
                    "visual_query": clean[:40],
                    "duration_hint": 9,
                },
                {
                    "narration": (
                        "This is trending worldwide and millions "
                        "of people are reacting to it right now."
                    ),
                    "visual_query": f"{clean[:30]} trending",
                    "duration_hint": 9,
                },
                {
                    "narration": (
                        "Experts are calling this one of the most "
                        "significant stories we have seen recently."
                    ),
                    "visual_query": "experts analysis news",
                    "duration_hint": 9,
                },
                {
                    "narration": (
                        "The full story behind the headlines is "
                        "even more fascinating than you think."
                    ),
                    "visual_query": "breaking news world global",
                    "duration_hint": 9,
                },
                {
                    "narration": (
                        "Subscribe to TrendPulse Global for the "
                        "latest trending updates every hour!"
                    ),
                    "visual_query": "subscribe youtube notification",
                    "duration_hint": 9,
                },
            ]
            title = f"🔥 {clean[:55]} #Shorts"
        else:
            scenes = [
                {
                    "narration": (
                        f"Welcome to TrendPulse Global. Today we are "
                        f"covering {clean}, which is one of the biggest "
                        f"stories trending around the world right now."
                    ),
                    "visual_query": clean[:40],
                    "duration_hint": 18,
                },
                {
                    "narration": (
                        f"Here is everything you need to know about "
                        f"{clean} and why millions of people worldwide "
                        f"are paying close attention to this story."
                    ),
                    "visual_query": f"{clean[:30]} explained",
                    "duration_hint": 22,
                },
                {
                    "narration": (
                        "Let us start with some important background. "
                        "Understanding the full context here is "
                        "essential to grasping the complete picture."
                    ),
                    "visual_query": "background context history world",
                    "duration_hint": 20,
                },
                {
                    "narration": (
                        "The key facts that everyone needs to know "
                        "are being discussed by leading experts and "
                        "analysts from around the globe."
                    ),
                    "visual_query": "facts analysis global experts meeting",
                    "duration_hint": 22,
                },
                {
                    "narration": (
                        "What makes this story particularly compelling "
                        "is how it connects to much larger global "
                        "trends that have been building for months."
                    ),
                    "visual_query": "global trends technology society",
                    "duration_hint": 22,
                },
                {
                    "narration": (
                        "There are three key takeaways from all of "
                        "this that will affect how the situation "
                        "develops over the coming weeks and months."
                    ),
                    "visual_query": "key points summary infographic",
                    "duration_hint": 22,
                },
                {
                    "narration": (
                        "Looking ahead, analysts and observers "
                        "expect significant developments. The "
                        "situation continues to evolve rapidly."
                    ),
                    "visual_query": "future outlook prediction horizon",
                    "duration_hint": 20,
                },
                {
                    "narration": (
                        "Thank you for watching TrendPulse Global. "
                        "Subscribe and turn on notifications to "
                        "stay ahead with trending content every hour."
                    ),
                    "visual_query": "subscribe youtube channel notification",
                    "duration_hint": 18,
                },
            ]
            title = f"🔥 {clean[:65]} — Full Story"

        return {
            "title": title,
            "description": (
                f"Full coverage of {clean}.\n\n"
                f"TrendPulse Global delivers the biggest trending "
                f"topics analyzed and explained every single hour.\n\n"
                f"#trending #TrendPulseGlobal #viral #news #facts"
            ),
            "tags": [
                clean[:40], "trending", "viral",
                "TrendPulse", "news", "facts", "2024"
            ],
            "category":       "entertainment",
            "thumbnail_text": clean[:20],
            "scenes":         scenes,
            "intro_hook": (
                f"Here is everything you need to know about "
                f"{clean} right now!"
            ),
            "outro": (
                "Subscribe to TrendPulse Global for hourly "
                "trending content delivered around the clock!"
            ),
        }
