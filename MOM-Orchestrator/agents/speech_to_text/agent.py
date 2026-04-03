"""Speech to Text Agent - Hybrid Approach
- Live recording: Chrome Web Speech API in frontend (free)
- Audio file upload: Google Gemini API (free tier available)
"""
from __future__ import annotations
import os
import asyncio
from typing import Dict, Any
import httpx
import google.generativeai as genai
from llm.bedrock_client import invoke_llm_json
from schemas.contracts import AgentRequest, AgentResponse
from agents.base_agent import BaseAgent
from .prompts import REASONING_SYSTEM_PROMPT, REASONING_USER_TEMPLATE

# Language mapping
_LANGUAGE_HINTS = {"ta": "Tamil", "hi": "Hindi", "en": "English"}


class SpeechToTextAgent(BaseAgent):
    name = "speech_to_text"
    
    def __init__(self):
        super().__init__()
        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        else:
            self.model = None
    
    async def _reason(self, request: AgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """AI analyzes audio file and plans transcription"""
        audio_url = request.payload.content
        
        if not audio_url:
            return {'thought': 'No audio URL provided', 'should_act': False}
        
        file_format = self._detect_format(audio_url)
        
        user_prompt = REASONING_USER_TEMPLATE.format(
            file_size="unknown",
            file_format=file_format,
            language_hint=request.payload.language or "not specified",
        )
        
        try:
            result = await invoke_llm_json(REASONING_SYSTEM_PROMPT, user_prompt)
            return {
                'thought': result.get('thought', 'Planning transcription'),
                'transcription_strategy': result.get('transcription_strategy', 'standard'),
                'expected_quality': result.get('expected_quality', 'medium'),
                'confidence': result.get('confidence', 0.85),
                'plan': result.get('plan', ['Transcribe audio']),
                'should_act': True,
            }
        except Exception as exc:
            return {
                'thought': f'AI reasoning failed: {exc}',
                'transcription_strategy': 'standard',
                'expected_quality': 'medium',
                'confidence': 0.8,
                'plan': ['Transcribe with fallback'],
                'should_act': True,
            }
    
    async def _act(self, request: AgentRequest, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """Transcribe audio using Google Gemini"""
        audio_identifier = request.payload.content
        language_hint = request.payload.language or request.context.intermediate_data.get("detected_language")
        
        try:
            # Check if it's a URL, GridFS file_id, or local file path
            if audio_identifier.startswith('http://') or audio_identifier.startswith('https://'):
                transcript = await self._transcribe_audio_gemini_url(audio_identifier, language_hint)
            elif len(audio_identifier) == 24 and all(c in '0123456789abcdef' for c in audio_identifier):
                # Looks like MongoDB ObjectId (24 hex chars) - retrieve from GridFS
                transcript = await self._transcribe_audio_gemini_gridfs(audio_identifier, language_hint)
            else:
                # Local file path from upload
                transcript = await self._transcribe_audio_gemini_file(audio_identifier, language_hint)
            return {
                'transcript': transcript,
                'transcription_method': 'Google Gemini (Free)',
            }
        except Exception as exc:
            return {
                'transcript': '',
                'transcription_method': f'error: {exc}',
            }
    
    async def _observe(self, request: AgentRequest, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify transcription quality"""
        transcript = action_result.get('transcript', '')
        return {
            'observation': f"Transcribed {len(transcript)} characters using {action_result.get('transcription_method')}",
            'is_complete': len(transcript) > 0,
            'next_step': None,
        }
    
    async def _execute(self, request: AgentRequest) -> AgentResponse:
        """Execute ReAct pattern for speech-to-text"""
        reasoning = await self._reason(request, request.context.intermediate_data)
        
        if not reasoning['should_act']:
            return self.fail(session_id=request.session_id, reasoning="No audio URL provided")
        
        action_result = await self._act(request, reasoning)
        
        if not action_result['transcript']:
            return self.fail(
                session_id=request.session_id,
                reasoning=f"Transcription failed: {action_result['transcription_method']}"
            )
        
        observation = await self._observe(request, action_result)
        
        full_reasoning = (
            f"[Reasoning] {reasoning['thought']}\n"
            f"[Plan] {', '.join(reasoning['plan'])}\n"
            f"[Action] {action_result.get('transcription_method')}\n"
            f"[Observation] {observation['observation']}"
        )
        
        return self.success(
            session_id=request.session_id,
            output={"transcript": action_result['transcript']},
            confidence=reasoning['confidence'],
            reasoning=full_reasoning,
        )
    
    def _detect_format(self, url: str) -> str:
        """Detect audio format from URL"""
        url_lower = url.lower()
        for fmt in ("mp3", "mp4", "wav", "flac", "ogg", "amr", "webm", "m4a"):
            if url_lower.endswith(f".{fmt}"):
                return fmt
        return "mp3"
    
    async def _transcribe_audio_gemini_gridfs(self, file_id: str, language_hint: str | None) -> str:
        """Transcribe audio from MongoDB GridFS using Google Gemini API"""
        if not self.model:
            raise RuntimeError("Gemini API key not configured. Set GEMINI_API_KEY in .env. Get free key at: https://aistudio.google.com/apikey")
        
        # Import here to avoid circular dependency
        from storage.mongo_client import get_audio_file, delete_audio_file
        
        # Retrieve audio from GridFS
        audio_data = await get_audio_file(file_id)
        if not audio_data:
            raise RuntimeError(f"Audio file not found in GridFS: {file_id}")
        
        # Save to temp file for Gemini processing
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(audio_data)
            tmp_path = tmp_file.name
        
        try:
            transcript = await self._transcribe_audio_gemini_file(tmp_path, language_hint)
            # Delete from GridFS after successful transcription
            await delete_audio_file(file_id)
            return transcript
        finally:
            # Cleanup temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    async def _transcribe_audio_gemini_file(self, file_path: str, language_hint: str | None) -> str:
        """Transcribe audio file using Google Gemini API (Free)"""
        if not self.model:
            raise RuntimeError("Gemini API key not configured. Set GEMINI_API_KEY in .env. Get free key at: https://aistudio.google.com/apikey")
        
        try:
            # Upload audio to Gemini
            loop = asyncio.get_event_loop()
            
            def _upload_and_transcribe():
                audio_file = genai.upload_file(file_path)
                
                # Create prompt
                language = _LANGUAGE_HINTS.get(language_hint or "", "English")
                prompt = f"Transcribe this audio file to text. The language is {language}. Provide ONLY the transcription text, no additional commentary or formatting."
                
                # Generate transcription
                response = self.model.generate_content([prompt, audio_file])
                return response.text
            
            transcript = await loop.run_in_executor(None, _upload_and_transcribe)
            return transcript.strip()
            
        finally:
            # Cleanup temp file
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    async def _transcribe_audio_gemini_url(self, audio_url: str, language_hint: str | None) -> str:
        """Transcribe audio from URL using Google Gemini API (Free)"""
        if not self.model:
            raise RuntimeError("Gemini API key not configured. Set GEMINI_API_KEY in .env. Get free key at: https://aistudio.google.com/apikey")
        
        # Download audio file
        audio_data = await self._download_audio(audio_url)
        
        # Save temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{self._detect_format(audio_url)}") as tmp_file:
            tmp_file.write(audio_data)
            tmp_path = tmp_file.name
        
        return await self._transcribe_audio_gemini_file(tmp_path, language_hint)
    
    async def _download_audio(self, audio_url: str) -> bytes:
        """Download audio file from URL"""
        async with httpx.AsyncClient() as client:
            response = await client.get(audio_url, timeout=60.0)
            response.raise_for_status()
            return response.content
