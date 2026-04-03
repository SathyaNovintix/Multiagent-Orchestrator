"""Language Detector Agent - Uses Python Library (langdetect)"""
from __future__ import annotations
from typing import Dict, Any
from schemas.contracts import AgentRequest, AgentResponse
from agents.base_agent import BaseAgent


class LanguageDetectorAgent(BaseAgent):
    name = "language_detector"
    
    async def _execute(self, request: AgentRequest) -> AgentResponse:
        """Detect language using langdetect library"""
        data = request.context.intermediate_data
        text = data.get("transcript") or request.payload.content
        
        if not text:
            return self.fail(session_id=request.session_id, reasoning="No text available")
        
        try:
            from langdetect import detect, detect_langs
            
            # Detect language
            detected = detect(text)
            langs = detect_langs(text)
            
            # Map to our language codes
            lang_map = {
                'en': ('en', 'English'),
                'ta': ('ta', 'Tamil'),
                'hi': ('hi', 'Hindi'),
            }
            
            lang_code, lang_name = lang_map.get(detected, (detected, detected.upper()))
            confidence = max([l.prob for l in langs if l.lang == detected], default=0.8)
            
            return self.success(
                session_id=request.session_id,
                output={
                    "detected_language": lang_code,
                    "language_confidence": confidence,
                },
                confidence=confidence,
                reasoning=f"Detected {lang_name} using langdetect library with {confidence:.2f} confidence",
            )
            
        except ImportError:
            # Fallback to English if library not available
            return self.success(
                session_id=request.session_id,
                output={
                    "detected_language": "en",
                    "language_confidence": 0.7,
                },
                confidence=0.7,
                reasoning="langdetect library not available, defaulting to English",
            )
        except Exception as exc:
            return self.fail(
                session_id=request.session_id,
                reasoning=f"Language detection failed: {exc}",
            )
