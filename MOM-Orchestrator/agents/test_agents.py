"""
Agent Testing Framework
Test each agent individually with sample inputs.
"""
import asyncio
from schemas.contracts import AgentRequest, Payload, Context, Meta


async def test_conversational_agent():
    """Test conversational agent with various inputs"""
    from agents.conversational import ConversationalAgent
    
    agent = ConversationalAgent()
    
    test_cases = [
        "hi",
        "who are you?",
        "what is your purpose?",
        "who is going to be the CM",
        "okay i will give the input data",
    ]
    
    print("\n=== Testing Conversational Agent ===")
    for test_input in test_cases:
        request = AgentRequest(
            session_id="test-session",
            intent="chat",
            payload=Payload(input_type="text", content=test_input),
            context=Context(conversation_history=[], intermediate_data={}, memory={}),
            meta=Meta(source="test"),
        )
        
        print(f"\nInput: {test_input}")
        response = await agent.run(request)
        print(f"Status: {response.status}")
        print(f"Output: {response.data.output.get('user_message', 'N/A')[:200]}")
        print(f"Reasoning: {response.reasoning[:200]}")


async def test_intent_refiner():
    """Test intent refiner with various inputs"""
    from agents.intent_refiner import IntentRefinerAgent
    
    agent = IntentRefinerAgent()
    
    test_cases = [
        ("Generate MOM from this meeting", "generate_mom"),
        ("What are the action items?", "extract_actions"),
        ("Summarize this meeting", "summarize"),
        ("hi", "chat"),
    ]
    
    print("\n=== Testing Intent Refiner Agent ===")
    for test_input, expected_intent in test_cases:
        request = AgentRequest(
            session_id="test-session",
            intent="auto_detect",
            payload=Payload(input_type="text", content=test_input),
            context=Context(conversation_history=[], intermediate_data={}, memory={}),
            meta=Meta(source="test"),
        )
        
        print(f"\nInput: {test_input}")
        response = await agent.run(request)
        print(f"Detected Intent: {response.intent}")
        print(f"Expected: {expected_intent}")
        print(f"Match: {'✓' if response.intent == expected_intent else '✗'}")


if __name__ == "__main__":
    asyncio.run(test_conversational_agent())
    asyncio.run(test_intent_refiner())
