import os, json, asyncio, logging
from typing import List, Optional, Dict, Any
from google import genai
from google.genai.types import HttpOptions
import vertexai

logger = logging.getLogger(__name__)

class StyleAnalyzer:
    """LLM-backed style/scene resolver using Google GenAI SDK (Gemini)."""

    def __init__(self):
        # Reads GEMINI_API_KEY from env by default
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        
        try:
            vertexai.init(project=self.project_id, location=self.location)
            client = genai.Client(vertexai=True, project=self.project_id, location=self.location)
            self.client = client
            logger.info("✅ Initialized Google GenAI client for style analysis")
        except Exception as e:
            self.client = None
            logger.error(f"❌ Failed to init GenAI client: {e}")

    async def analyze_styles_and_scene(
        self,
        labels: List[str],
        colors: List[str],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return {scene_type, styles[], tags[], confidence} without hardcoded rules."""
        if not self.client:
            logger.warning("GenAI client not available; using fallback.")
            return self._fallback_analysis(labels, colors)

        # Build a compact JSON payload for the model
        payload = {
            "labels": labels[:20],
            "colors": colors[:5],
            "context": context or "",
            "allowed_styles": ["modern","minimalist","scandinavian","boho","industrial","vintage"],
            "allowed_scenes": ["indoor","outdoor","portrait","product","general"]
        }

        # Ask Gemini for structured JSON
        def _call():
            # Combine system and user messages into a single prompt
            prompt = (
                "You map noisy vision signals to a fixed style taxonomy. "
                "Return strict JSON with keys: scene_type, styles, tags, confidence (0..1). "
                "Only use values from allowed lists when applicable.\n\n"
                f"Data: {json.dumps(payload)}"
            )
            return self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, _call)
            print("=========== resp ===========", resp)
            # New SDK returns Pydantic objects; .text will be JSON string here
            text = getattr(resp, "text", None) or getattr(resp, "candidates", [{}])[0].content.parts[0].text
            print("=========== text ===========", text)
            # Clean the response - remove markdown code blocks
            cleaned_text = text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]  # Remove ```json
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]   # Remove ```
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]  # Remove closing ```
            cleaned_text = cleaned_text.strip()

            data = json.loads(cleaned_text)
            logger.info("STYLE ANALYSIS DATA FROM GEMINI: ", data)
            # Basic validation / defaults
            return {
                "scene_type": data.get("scene_type", "general"),
                "styles": data.get("styles", [])[:5],
                "tags": data.get("tags", [])[:8],
                "confidence": float(data.get("confidence", 0.7))
            }
        except Exception as e:
            logger.error(f"Gemini style analysis failed: {e}")
            return self._fallback_analysis(labels, colors)

    # --- simple fallback if LLM unavailable ---
    def _fallback_analysis(self, labels: List[str], colors: List[str]) -> Dict[str, Any]:
        """Fallback analysis when Gemini is not available."""
        logger.info("Using fallback style analysis")
        
        # Basic scene type detection
        scene_type = self._detect_scene_type_basic(labels)
        
        # Basic style detection
        styles = self._detect_styles_basic(labels)
        
        # Basic mood from colors
        mood = self._detect_mood_from_colors(colors)
        
        return {
            "scene_type": scene_type,
            "styles": styles,
            "mood": mood,
            "tags": labels[:10],  # Use original labels
            "confidence": 0.6  # Lower confidence for basic analysis
        }
    
    def _detect_scene_type_basic(self, labels: List[str]) -> str:
        """Basic scene type detection using keyword matching."""
        scene_keywords = {
            "indoor": ["room", "furniture", "kitchen", "bedroom", "office", "restaurant", "interior"],
            "outdoor": ["sky", "tree", "building", "street", "park", "nature", "landscape", "outdoor"],
            "portrait": ["person", "face", "human", "people", "portrait"],
            "product": ["product", "item", "object", "merchandise", "bottle", "package"],
            "food": ["food", "meal", "dish", "restaurant", "kitchen", "eating"],
            "vehicle": ["car", "truck", "vehicle", "transportation", "road"],
            "animal": ["animal", "pet", "dog", "cat", "wildlife", "bird"]
        }
        
        label_text = " ".join(labels).lower()
        for scene_type, keywords in scene_keywords.items():
            if any(keyword in label_text for keyword in keywords):
                return scene_type
        
        return "general"
    
    def _detect_styles_basic(self, labels: List[str]) -> List[str]:
        """Basic style detection using keyword matching."""
        style_keywords = {
            "modern": ["modern", "contemporary", "sleek", "clean"],
            "vintage": ["vintage", "retro", "classic", "antique", "old"],
            "artistic": ["art", "painting", "drawing", "artistic", "creative"],
            "professional": ["professional", "business", "corporate", "formal"],
            "casual": ["casual", "informal", "relaxed", "everyday"],
            "natural": ["natural", "organic", "nature", "wood", "stone"]
        }
        
        styles = []
        label_text = " ".join(labels).lower()
        for style, keywords in style_keywords.items():
            if any(keyword in label_text for keyword in keywords):
                styles.append(style)
        
        return styles[:3]  # Limit to top 3 styles
    
    def _detect_mood_from_colors(self, colors: List[str]) -> str:
        """Detect mood based on dominant colors."""
        if not colors:
            return "neutral"
        
        # Convert hex colors to RGB for analysis
        color_moods = {
            "bright": ["#ffff", "#ff0", "#00ff", "#0ff"],  # Bright colors
            "warm": ["#ff", "#f0", "#ff8", "#ffa"],       # Warm tones
            "cool": ["#00f", "#0ff", "#008", "#88f"],     # Cool tones
            "dark": ["#000", "#333", "#666", "#444"],     # Dark colors
            "peaceful": ["#8f8", "#88f", "#f8f", "#ccc"]  # Soft colors
        }
        
        # Simple heuristic based on first dominant color
        primary_color = colors[0].lower() if colors else "#ffffff"
        
        for mood, color_patterns in color_moods.items():
            if any(pattern in primary_color for pattern in color_patterns):
                return mood
        
        return "neutral" 