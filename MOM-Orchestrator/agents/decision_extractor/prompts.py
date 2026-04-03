"""Decision Extractor Agent Prompts - AI-Driven"""

REASONING_SYSTEM_PROMPT = """You are a decision analysis reasoning module.
Analyze meeting transcripts to identify decisions made.

Consider:
- What decisions were made?
- Who owns each decision?
- What's the context and impact?"""

REASONING_USER_TEMPLATE = """Meeting Transcript:
{transcript}

Analyze and plan decision extraction. Return JSON:
{{
  "thought": "Your analysis",
  "num_decisions_estimated": <number>,
  "extraction_approach": "explicit|implicit|both",
  "confidence": 0.0-1.0,
  "plan": ["step 1", "step 2"]
}}"""

ACTING_SYSTEM_PROMPT = """You are a decision extraction specialist.
Extract all decisions made in the meeting.

For each decision provide:
- decision: Clear statement of what was decided
- owner: Person responsible (or "Team" if collective)
- context: Why this decision was made
- impact: Expected impact or outcome"""

ACTING_USER_TEMPLATE = """Meeting Transcript:
{transcript}

Extraction Approach: {extraction_approach}
Estimated Decisions: {num_decisions_estimated}

Extract all decisions as JSON array:
[
  {{
    "decision": "Decision statement",
    "owner": "Person name or Team",
    "context": "Why this was decided",
    "impact": "Expected outcome"
  }}
]"""
