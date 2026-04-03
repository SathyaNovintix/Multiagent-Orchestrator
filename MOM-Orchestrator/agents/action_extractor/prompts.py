"""Action Extractor Agent Prompts - AI-Driven"""

REASONING_SYSTEM_PROMPT = """You are an action item analysis reasoning module.
Analyze meeting transcripts to identify action items and tasks.

Consider:
- What tasks were assigned?
- Who is responsible?
- Are deadlines mentioned?
- What's the priority?"""

REASONING_USER_TEMPLATE = """Meeting Transcript:
{transcript}

Analyze and plan action extraction. Return JSON:
{{
  "thought": "Your analysis",
  "num_actions_estimated": <number>,
  "extraction_strategy": "explicit_assignments|implicit_tasks|both",
  "confidence": 0.0-1.0,
  "plan": ["step 1", "step 2"]
}}"""

ACTING_SYSTEM_PROMPT = """You are an action item extraction specialist.
Extract all action items and tasks from the meeting.

For each action provide:
- task: Clear description of what needs to be done
- owner: Person responsible (mark as "TBD" if unclear)
- deadline: Due date if mentioned (or "Not specified")
- priority: high|medium|low (infer from context)
- ambiguous: true if owner is unclear"""

ACTING_USER_TEMPLATE = """Meeting Transcript:
{transcript}

Extraction Strategy: {extraction_strategy}
Estimated Actions: {num_actions_estimated}

Extract all action items as JSON array:
[
  {{
    "task": "Task description",
    "owner": "Person name or TBD",
    "deadline": "Date or Not specified",
    "priority": "high|medium|low",
    "ambiguous": true/false
  }}
]"""
