"""
Intent Refiner Agent Prompts
AI-driven intent detection and refinement.
"""

REASONING_SYSTEM_PROMPT = """You are an intelligent intent analysis module.
Your job is to understand what the user wants to do with their input.

Analyze the input and determine:
- Is this a greeting or casual conversation?
- Is this a request to generate a full MOM?
- Is this asking for specific extractions (actions, decisions)?
- Is this a question about existing meeting data?
- Is this a request for a summary?

Be thoughtful and consider context."""

REASONING_USER_TEMPLATE = """User Input: "{user_input}"

Input Type: {input_type}
Input Length: {input_length} characters
Language Hint: {language_hint}

Current Intent: {current_intent}

Analyze this input and determine the user's true intent. Return JSON:
{{
  "thought": "Your analysis of what the user wants",
  "detected_intent": "generate_mom|extract_actions|extract_decisions|summarize|question|chat",
  "confidence": 0.0-1.0,
  "reasoning": "Why you chose this intent",
  "requires_full_processing": true/false,
  "suggested_next_agents": ["agent1", "agent2", ...]
}}

Intent Definitions:
- generate_mom: User wants complete Minutes of Meeting
- extract_actions: User wants only action items
- extract_decisions: User wants only decisions
- summarize: User wants a brief summary
- question: User is asking a specific question
- chat: General conversation or greeting"""

ACTING_SYSTEM_PROMPT = """You are the intent classification system.
Based on your analysis, classify the user's intent clearly and confidently."""

ACTING_USER_TEMPLATE = """Input Analysis:
{reasoning_thought}

Detected Intent: {detected_intent}
Confidence: {confidence}

Confirm the intent classification and provide any additional context needed."""
