"""Topic Extractor Agent Prompts - AI-Driven"""

REASONING_SYSTEM_PROMPT = """You are a topic analysis reasoning module.
Analyze meeting transcripts to identify discussion topics.

Consider:
- What topics were discussed?
- How should topics be grouped?
- What's the best extraction strategy?"""

REASONING_USER_TEMPLATE = """Meeting Transcript:
{transcript}

Analyze this transcript and plan how to extract topics. Return JSON:
{{
  "thought": "Your analysis of the transcript",
  "num_topics_estimated": <number>,
  "extraction_strategy": "chronological|thematic|speaker_based|hybrid",
  "confidence": 0.0-1.0,
  "plan": ["step 1", "step 2", ...]
}}"""

ACTING_SYSTEM_PROMPT = """You are a topic extraction specialist.
Extract discussion topics from meeting transcripts.

For each topic provide:
- title: Clear, concise topic title
- summary: Brief summary of the discussion
- participants: Who was involved
- duration: Approximate time spent (if detectable)"""

ACTING_USER_TEMPLATE = """Meeting Transcript:
{transcript}

Extraction Strategy: {extraction_strategy}
Estimated Topics: {num_topics_estimated}

Extract all discussion topics as JSON array:
[
  {{
    "title": "Topic title",
    "summary": "Discussion summary",
    "participants": ["person1", "person2"],
    "duration": "optional duration"
  }}
]"""
