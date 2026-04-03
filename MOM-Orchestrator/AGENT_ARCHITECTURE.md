# Agent Architecture - Modular ReAct Pattern

## ✅ Completed Agents (Modular Structure)

### 1. Conversational Agent
**Location:** `agents/conversational/`
- `prompts.py` - All AI prompts (reasoning, acting)
- `schema.py` - Data structures (Context, Results)
- `agent.py` - ReAct implementation
- `__init__.py` - Module exports

**Features:**
- Fully AI-driven reasoning (no hardcoded if-else)
- Can handle ANY conversation (not just meetings)
- ReAct pattern: Reasoning → Acting → Observation
- Reusable for different purposes

### 2. Intent Refiner Agent
**Location:** `agents/intent_refiner/`
- `prompts.py` - Intent analysis prompts
- `schema.py` - Intent context and results
- `agent.py` - AI-driven intent detection
- `__init__.py` - Module exports

**Features:**
- AI determines user intent (no pattern matching)
- Dynamic intent classification
- Confidence scoring
- Suggests next agents

## 🔄 Agents To Be Modularized

### 3. Topic Extractor
- Extract discussion topics from transcripts
- AI-driven topic identification
- Thematic grouping

### 4. Decision Extractor
- Extract decisions made in meetings
- Identify decision owners
- Track decision status

### 5. Action Extractor
- Extract action items
- Identify owners and deadlines
- Priority detection

### 6. Language Detector
- Detect input language
- Confidence scoring
- Multi-language support

### 7. Translator
- Translate to English
- Preserve context
- Quality assurance

### 8. Speech to Text
- Convert audio to text
- AWS Transcribe integration
- Accuracy optimization

### 9. Formatter
- Format extracted data into MOM structure
- Support multiple formats
- Custom template handling

### 10. Response Generator
- Generate user-facing responses
- Include MOM summaries
- Provide download links

## Architecture Principles

### 1. Modular Structure
Each agent has:
```
agents/<agent_name>/
├── prompts.py      # All AI prompts
├── schema.py       # Data structures
├── agent.py        # ReAct implementation
└── __init__.py     # Exports
```

### 2. ReAct Pattern
Every agent follows:
1. **Reasoning** - AI analyzes situation and plans
2. **Acting** - AI executes based on reasoning
3. **Observation** - Verify results and decide next steps

### 3. Fully AI-Driven
- No hardcoded if-else logic
- AI makes all decisions
- Dynamic and adaptable

### 4. Reusable
- Change prompts for different purposes
- Swap schemas for different data
- Same boilerplate, different scenarios

### 5. Bidirectional Routing
- Agents can suggest next agents
- Orchestrator routes based on intent
- Dynamic flow control

## Orchestrator Integration

### Intent Routing
```python
INTENT_CAPABILITIES = {
    "generate_mom": ["extraction", "formatting", "response"],
    "extract_actions": ["action_extraction", "response"],
    "chat": ["conversational"],
    # ... dynamic routing
}
```

### Agent Registry
```python
AGENT_REGISTRY = {
    "conversational_agent": ConversationalAgent(),
    "intent_refiner": IntentRefinerAgent(),
    # ... all agents
}
```

## Testing

### Test Conversational Agent
```
User: "hi"
→ AI reasons: "User is greeting"
→ AI acts: Generates warm greeting
→ AI observes: Response is complete

User: "who is going to be the CM"
→ AI reasons: "General question, no meeting data needed"
→ AI acts: Responds naturally to the question
→ AI observes: Answer provided
```

### Test Intent Refiner
```
User: "Generate MOM from this transcript..."
→ AI reasons: "Long text, formal request"
→ AI acts: Classifies as "generate_mom"
→ AI observes: Intent confidence 0.95
```

## Next Steps

1. ✅ Conversational Agent - Complete
2. ✅ Intent Refiner - Complete
3. ⏳ Topic Extractor - In Progress
4. ⏳ Decision Extractor - Pending
5. ⏳ Action Extractor - Pending
6. ⏳ Other agents - Pending

## Benefits

- **Maintainable**: Each agent is self-contained
- **Testable**: Easy to test individual components
- **Scalable**: Add new agents easily
- **Flexible**: Change behavior via prompts
- **Intelligent**: AI-driven decisions, not rules
