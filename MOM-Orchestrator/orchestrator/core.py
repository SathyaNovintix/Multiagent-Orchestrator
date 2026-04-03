"""
Orchestrator Core — AgentMesh AI (LangGraph)

The full pipeline is a LangGraph StateGraph.
Each of the 9 agents is a graph node.
Conditional edges implement dynamic skipping.
Parallel extraction runs topic + decision + action concurrently via asyncio.gather.

Session lifecycle:
  - new_session()  → creates session_id in Redis, returns it to the caller
  - run_pipeline() → builds initial state, invokes the compiled graph, persists result
"""
from __future__ import annotations
import asyncio
import time
import uuid
import os
from typing import Any

from langgraph.graph import StateGraph, END
import agentops
from agentops.sdk.decorators import agent as agentops_agent, operation as agentops_operation

from orchestrator.state import AgentMeshState
from schemas.contracts import (
    AgentRequest,
    Context,
    Meta,
    Payload,
    Session,
)
from storage.mongo_client import create_session, get_session, update_session, save_mom
from schemas.contracts import MOMDocument


# ---------------------------------------------------------------------------
# Helpers — build an AgentRequest from current graph state
# ---------------------------------------------------------------------------

def _make_request(state: AgentMeshState) -> AgentRequest:
    return AgentRequest(
        session_id=state["session_id"],
        intent=state.get("intent", "auto_detect"),
        payload=Payload(
            input_type=state["input_type"],
            content=state.get("english_transcript") or state.get("transcript") or state["content"],
            language=state.get("detected_language"),
        ),
        context=Context(
            conversation_history=state.get("conversation_history", []),
            intermediate_data={
                "transcript": state.get("transcript"),
                "detected_language": state.get("detected_language"),
                "language_confidence": state.get("language_confidence", 0.0),
                "english_transcript": state.get("english_transcript"),
                "intent_confidence": state.get("intent_confidence", 0.0),
                "topics": state.get("topics", []),
                "decisions": state.get("decisions", []),
                "actions": state.get("actions", []),
                "structured_mom": state.get("structured_mom"),
                "input_type": state.get("input_type"),
                "format_id": state.get("format_id", "standard"),
            },
            memory=state.get("memory", {}),
        ),
        meta=Meta(source="orchestrator"),
    )


# ---------------------------------------------------------------------------
# Node functions — one per agent
# ---------------------------------------------------------------------------

def _agent_node(agent_name: str):
    """Factory: returns an async node function that runs the named agent."""
    async def node(state: AgentMeshState) -> AgentMeshState:
        from orchestrator.registry import AGENT_REGISTRY
        
        start_time = time.time()
        print(f"\n{'='*60}")
        print(f"🔹 AGENT: {agent_name}")
        print(f"{'='*60}")
        
        # Start AgentOps operation span for this agent
        operation_span = None
        if _agentops_initialized:
            try:
                # Create a span context for this agent operation
                from opentelemetry import trace
                tracer = trace.get_tracer(__name__)
                operation_span = tracer.start_span(
                    name=f"agent.{agent_name}",
                    attributes={
                        "agentops.span.kind": "AGENT",
                        "agent.name": agent_name,
                        "session.id": state.get("session_id"),
                        "intent": state.get("intent")
                    }
                )
            except Exception as e:
                print(f"⚠️  Failed to start AgentOps span: {e}")
        
        agent = AGENT_REGISTRY[agent_name]
        request = _make_request(state)
        response = await agent.run(request)
        
        elapsed = time.time() - start_time
        print(f"⏱️  Duration: {elapsed*1000:.0f}ms")
        print(f"📊 Status: {response.status}")
        print(f"💭 Reasoning: {response.reasoning[:100]}..." if len(response.reasoning) > 100 else f"💭 Reasoning: {response.reasoning}")

        updates: AgentMeshState = {}

        if response.status == "fail":
            updates["status"] = "error"
            updates["error_message"] = response.reasoning
            print(f"❌ Error: {response.reasoning}")
            
            # Mark span as error
            if operation_span:
                try:
                    operation_span.set_attribute("error", True)
                    operation_span.set_attribute("error.message", response.reasoning)
                except Exception:
                    pass
                    
        elif response.status == "need_more_input":
            updates["status"] = "needs_clarification"
            updates["clarification_prompt"] = response.data.output.get("clarification_prompt", "")
            print(f"❓ Needs clarification: {updates['clarification_prompt']}")
        else:
            # Merge agent output into state
            out = response.data.output
            updates.update({k: v for k, v in out.items() if v is not None})

            # Agent may refine intent
            if response.intent:
                updates["intent"] = response.intent
                print(f"🎯 Intent: {response.intent}")
            
            # Log key outputs
            for key, value in out.items():
                if key in ["detected_language", "language_confidence", "intent_confidence"]:
                    print(f"📌 {key}: {value}")
                    if operation_span:
                        try:
                            operation_span.set_attribute(f"output.{key}", value)
                        except Exception:
                            pass
                elif key in ["topics", "decisions", "actions"] and value:
                    print(f"📌 {key}: {len(value)} items")
                    if operation_span:
                        try:
                            operation_span.set_attribute(f"output.{key}.count", len(value))
                        except Exception:
                            pass
                elif key == "structured_mom" and value:
                    print(f"📌 structured_mom: Generated")
                elif key == "user_message" and value:
                    print(f"📌 user_message: {value[:80]}..." if len(str(value)) > 80 else f"📌 user_message: {value}")
        
        # End AgentOps span
        if operation_span:
            try:
                operation_span.set_attribute("duration_ms", round(elapsed * 1000, 2))
                operation_span.set_attribute("status", response.status)
                operation_span.end()
            except Exception as e:
                print(f"⚠️  Failed to end AgentOps span: {e}")
        
        # Add to trace with FULL details for API response
        if "trace" not in state:
            state["trace"] = []
        
        trace_entry = {
            "agent": agent_name,
            "duration_ms": round(elapsed * 1000, 2),
            "status": response.status,
            "reasoning": response.reasoning,
            "intent": response.intent if response.intent else None,
            "outputs": {}
        }
        
        # Capture ALL outputs from the agent
        if response.status == "success":
            out = response.data.output
            for key, value in out.items():
                if key in ["detected_language", "language_confidence", "intent_confidence", "refined_intent", "transcript", "english_transcript"]:
                    trace_entry["outputs"][key] = value
                elif key in ["topics", "decisions", "actions"] and isinstance(value, list):
                    trace_entry["outputs"][key] = {
                        "count": len(value),
                        "items": value  # Include full data
                    }
                elif key == "structured_mom":
                    trace_entry["outputs"]["structured_mom"] = "generated (see final response)"
                elif key == "user_message":
                    trace_entry["outputs"]["user_message"] = value
                else:
                    # Include any other outputs
                    if not isinstance(value, (dict, list)) or (isinstance(value, list) and len(value) < 10):
                        trace_entry["outputs"][key] = value
        
        state["trace"].append(trace_entry)
        updates["trace"] = state["trace"]
        
        print(f"{'='*60}\n")
        return updates

    node.__name__ = agent_name
    return node


async def _parallel_extraction_node(state: AgentMeshState) -> AgentMeshState:
    """
    Runs topic_extractor, decision_extractor, action_extractor in parallel.
    Waits for all three before returning merged results.
    """
    from orchestrator.registry import AGENT_REGISTRY
    
    start_time = time.time()
    print(f"\n{'='*60}")
    print(f"🔹 PARALLEL EXTRACTION (3 agents running concurrently)")
    print(f"{'='*60}")
    
    request = _make_request(state)

    topic_agent = AGENT_REGISTRY["topic_extractor"]
    decision_agent = AGENT_REGISTRY["decision_extractor"]
    action_agent = AGENT_REGISTRY["action_extractor"]

    topic_resp, decision_resp, action_resp = await asyncio.gather(
        topic_agent.run(request),
        decision_agent.run(request),
        action_agent.run(request),
    )
    
    elapsed = time.time() - start_time
    print(f"⏱️  Total Duration: {elapsed*1000:.0f}ms (parallel)")

    updates: AgentMeshState = {}
    parallel_details = []

    for resp, name in [(topic_resp, "topic_extractor"), (decision_resp, "decision_extractor"), (action_resp, "action_extractor")]:
        print(f"\n  ├─ {name}:")
        print(f"  │  Status: {resp.status}")
        
        agent_detail = {
            "agent": name,
            "status": resp.status,
            "reasoning": resp.reasoning,
            "outputs": {}
        }
        
        if resp.status == "fail":
            updates["status"] = "error"
            updates["error_message"] = resp.reasoning
            print(f"  │  ❌ Error: {resp.reasoning}")
            agent_detail["error"] = resp.reasoning
        else:
            out = resp.data.output
            updates.update({k: v for k, v in out.items() if v is not None})
            
            # Capture outputs
            for key, value in out.items():
                if isinstance(value, list):
                    print(f"  │  {key}: {len(value)} items")
                    agent_detail["outputs"][key] = {
                        "count": len(value),
                        "items": value
                    }
        
        parallel_details.append(agent_detail)
        
        if resp.status == "fail":
            return updates
    
    # Add to trace with parallel details
    if "trace" not in state:
        state["trace"] = []
    
    trace_entry = {
        "agent": "extraction_parallel",
        "duration_ms": round(elapsed * 1000, 2),
        "status": "success",
        "reasoning": "Parallel execution of topic, decision, and action extractors",
        "parallel_agents": parallel_details,
        "outputs": {
            "topics": {"count": len(updates.get('topics', [])), "items": updates.get('topics', [])},
            "decisions": {"count": len(updates.get('decisions', [])), "items": updates.get('decisions', [])},
            "actions": {"count": len(updates.get('actions', [])), "items": updates.get('actions', [])}
        }
    }
    
    state["trace"].append(trace_entry)
    updates["trace"] = state["trace"]
    
    print(f"{'='*60}\n")
    return updates


# ---------------------------------------------------------------------------
# Conditional routing functions (dynamic skipping)
# ---------------------------------------------------------------------------

def route_after_input(state: AgentMeshState) -> str:
    """Skip speech_to_text if input is text."""
    if state.get("input_type") == "text":
        return "language_detector"
    return "speech_to_text"


def route_after_language_detection(state: AgentMeshState) -> str:
    """Skip translator if already English or language is unknown/None."""
    lang = state.get("detected_language") or "en"
    if lang in ("en", "english", "en-US", "en-GB", "en-us", "en-gb"):
        return "intent_refiner"
    return "translator"


def route_after_intent_refiner(state: AgentMeshState) -> str:
    """Route based on refined intent to appropriate processing path."""
    intent = state.get("intent", "auto_detect")
    
    # Full MOM generation - go through extraction
    if intent == "generate_mom":
        return "extraction"
    
    # Extract only actions - skip topics and decisions
    elif intent == "extract_actions":
        return "action_extractor"
    
    # Extract only decisions - skip topics and actions
    elif intent == "extract_decisions":
        return "decision_extractor"
    
    # Simple summary - skip extraction, go to formatter
    elif intent in ["summarize", "general_summary"]:
        return "formatter"
    
    # Question or chat - go to conversational agent
    elif intent in ["question", "chat"]:
        return "conversational_agent"
    
    # Default: full extraction
    else:
        return "extraction"


def route_after_extraction(state: AgentMeshState) -> str:
    """Check for errors before formatting."""
    if state.get("status") == "error":
        return END
    return "formatter"


def route_on_error(state: AgentMeshState) -> str:
    """Terminate graph on error or clarification needed."""
    if state.get("status") in ("error", "needs_clarification"):
        return END
    return "continue"


# ---------------------------------------------------------------------------
# Build the LangGraph StateGraph
# ---------------------------------------------------------------------------

def build_graph() -> Any:
    """
    Constructs and compiles the AgentMesh pipeline graph.
    Called once at app startup.

    Graph flow:
      START
        ↓ (conditional: text → skip STT)
      [speech_to_text]
        ↓
      language_detector
        ↓ (conditional: english → skip translator)
      [translator]
        ↓
      intent_refiner
        ↓ (conditional: general_summary → skip extraction)
      extraction  ← parallel: topic + decision + action
        ↓
      formatter
        ↓
      response_generator
        ↓
      END
    """
    graph = StateGraph(AgentMeshState)

    # Add nodes
    graph.add_node("speech_to_text", _agent_node("speech_to_text"))
    graph.add_node("language_detector", _agent_node("language_detector"))
    graph.add_node("translator", _agent_node("translator"))
    graph.add_node("intent_refiner", _agent_node("intent_refiner"))
    graph.add_node("extraction", _parallel_extraction_node)
    graph.add_node("action_extractor", _agent_node("action_extractor"))
    graph.add_node("decision_extractor", _agent_node("decision_extractor"))
    graph.add_node("formatter", _agent_node("formatter"))
    graph.add_node("response_generator", _agent_node("response_generator"))
    graph.add_node("conversational_agent", _agent_node("conversational_agent"))

    # Entry: conditional on input type
    graph.set_conditional_entry_point(
        route_after_input,
        {
            "speech_to_text": "speech_to_text",
            "language_detector": "language_detector",
        },
    )

    # speech_to_text → language_detector (always, if it ran)
    graph.add_edge("speech_to_text", "language_detector")

    # language_detector → translator OR intent_refiner (skip if english)
    graph.add_conditional_edges(
        "language_detector",
        route_after_language_detection,
        {
            "translator": "translator",
            "intent_refiner": "intent_refiner",
        },
    )

    # translator → intent_refiner
    graph.add_edge("translator", "intent_refiner")

    # intent_refiner → extraction OR formatter OR conversational OR single extractors
    graph.add_conditional_edges(
        "intent_refiner",
        route_after_intent_refiner,
        {
            "extraction": "extraction",
            "formatter": "formatter",
            "conversational_agent": "conversational_agent",
            "action_extractor": "action_extractor",
            "decision_extractor": "decision_extractor",
        },
    )

    # extraction → formatter (or END on error)
    graph.add_conditional_edges(
        "extraction",
        route_after_extraction,
        {
            "formatter": "formatter",
            END: END,
        },
    )
    
    # Single extractors → response_generator
    graph.add_edge("action_extractor", "response_generator")
    graph.add_edge("decision_extractor", "response_generator")
    
    # Conversational agent → END (direct response)
    graph.add_edge("conversational_agent", END)

    # formatter → response_generator
    graph.add_edge("formatter", "response_generator")

    # response_generator → END
    graph.add_edge("response_generator", END)

    return graph.compile()


# Compiled graph — populated at startup via init_orchestrator()
_compiled_graph = None
_agentops_initialized = False


def init_orchestrator() -> None:
    """Called once at app startup after build_registry()."""
    global _compiled_graph, _agentops_initialized
    _compiled_graph = build_graph()
    
    # Initialize AgentOps for monitoring
    if not _agentops_initialized:
        agentops_api_key = os.getenv("AGENTOPS_API_KEY")
        if agentops_api_key and agentops_api_key != "your_agentops_api_key_here":
            try:
                agentops.init(
                    api_key=agentops_api_key,
                    auto_start_session=False,  # We'll manage sessions manually
                    default_tags=["mom-orchestrator", "production"]
                )
                _agentops_initialized = True
                print("✅ AgentOps initialized successfully")
            except Exception as e:
                print(f"⚠️  AgentOps initialization failed: {e}")
        else:
            print("⚠️  AgentOps API key not configured")


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

async def new_session(intent: str = "auto_detect", label: str = "New Session") -> Session:
    """Creates a new session in MongoDB."""
    session = Session(
        session_id=str(uuid.uuid4()),
        intent=intent,
        label=label,
    )
    await create_session(session)
    return session


async def load_session(session_id: str) -> Session:
    session = await get_session(session_id)
    if session is None:
        raise ValueError(f"Session '{session_id}' not found.")
    return session


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

async def run_pipeline(
    session_id: str,
    input_type: str,
    content: str,
    language_hint: Optional[str] = None,
    intent: str = "auto_detect",
    format_id: str = "standard",
) -> dict[str, Any]:
    """
    Runs the full LangGraph pipeline for a user request.
    Returns the final result dict for the API layer.
    """
    if _compiled_graph is None:
        raise RuntimeError("Orchestrator not initialized. Call init_orchestrator() at startup.")

    session = await load_session(session_id)
    
    # Start AgentOps trace for this pipeline execution
    agentops_trace = None
    if _agentops_initialized:
        try:
            agentops_trace = agentops.start_trace(
                trace_name=f"MOM_Pipeline_{intent}",
                tags=[
                    "mom-generation",
                    f"intent:{intent}",
                    f"format:{format_id}",
                    f"input:{input_type}"
                ]
            )
        except Exception as e:
            print(f"⚠️  Failed to start AgentOps trace: {e}")

    print(f"\n{'#'*60}")
    print(f"🚀 ORCHESTRATOR PIPELINE STARTED")
    print(f"{'#'*60}")
    print(f"📝 Session ID: {session_id}")
    print(f"📥 Input Type: {input_type}")
    print(f"🎯 Intent: {intent}")
    print(f"📄 Format: {format_id}")
    print(f"💬 Content: {content[:100]}..." if len(content) > 100 else f"💬 Content: {content}")
    if agentops_trace:
        print(f"📊 AgentOps Trace: Active")
    print(f"{'#'*60}\n")

    initial_state: AgentMeshState = {
        "session_id": session_id,
        "intent": intent,
        "input_type": input_type,
        "content": content,
        "language_hint": language_hint,
        "format_id": format_id,
        "status": "running",
        "conversation_history": session.conversation_history if session else [],
        "memory": session.memory if session else {},
        "topics": [],
        "decisions": [],
        "actions": [],
        "trace": [],
    }

    try:
        final_state: AgentMeshState = await _compiled_graph.ainvoke(initial_state)
        
        print(f"\n{'#'*60}")
        print(f"✅ ORCHESTRATOR PIPELINE COMPLETED")
        print(f"{'#'*60}")
        print(f"� Final Status: {final_state.get('status')}")
        
        # Print execution trace
        if final_state.get("trace"):
            print(f"\n📈 EXECUTION TRACE:")
            total_time = 0
            for step in final_state["trace"]:
                duration = step.get("duration_ms", 0)
                total_time += duration
                print(f"  ├─ {step['agent']}: {duration:.0f}ms ({step.get('status', 'unknown')})")
            print(f"  └─ TOTAL: {total_time:.0f}ms")
        
        # Print results summary
        if final_state.get("topics"):
            print(f"\n📌 Topics: {len(final_state['topics'])}")
        if final_state.get("decisions"):
            print(f"📌 Decisions: {len(final_state['decisions'])}")
        if final_state.get("actions"):
            print(f"📌 Actions: {len(final_state['actions'])}")
        
        print(f"{'#'*60}\n")

        # End AgentOps trace with success
        if agentops_trace:
            try:
                agentops.end_trace(agentops_trace, end_state=agentops.TraceState.SUCCESS)
            except Exception as e:
                print(f"⚠️  Failed to end AgentOps trace: {e}")

    except Exception as e:
        print(f"\n❌ PIPELINE ERROR: {e}")
        
        # End AgentOps trace with error
        if agentops_trace:
            try:
                agentops.end_trace(agentops_trace, end_state=agentops.TraceState.ERROR)
            except Exception as e:
                print(f"⚠️  Failed to end AgentOps trace: {e}")
        
        raise

    # Persist final state back to MongoDB
    session.intent = final_state.get("intent", intent)
    session.intermediate_data = {
        k: final_state.get(k)
        for k in (
            "transcript", "detected_language", "english_transcript",
            "intent_confidence", "topics", "decisions", "actions",
            "structured_mom", "user_message", "file_url",
        )
    }
    session.status = (
        "completed" if final_state.get("status") != "error" else "error"
    )
    await update_session(session)

    # Save MOM document to MongoDB if generated
    if final_state.get("structured_mom"):
        structured_mom_data = final_state.get("structured_mom", {})
        mom = MOMDocument(
            session_id=session_id,
            topics=final_state.get("topics", []),
            decisions=final_state.get("decisions", []),
            actions=final_state.get("actions", []),
            source_language="en",
            original_language=final_state.get("detected_language", "en"),
            file_url=final_state.get("file_url"),
            format_id=structured_mom_data.get("format_id", "standard"),
            # Persist custom template data for PDF/Excel exports
            sections=structured_mom_data.get("sections"),
            template_structure=structured_mom_data.get("template_structure"),
        )
        await save_mom(mom)
        
        # Add mom_id and file_url to structured_mom for frontend
        structured_mom_data["mom_id"] = mom.mom_id
        structured_mom_data["file_url"] = mom.file_url
        structured_mom_data["original_language"] = mom.original_language
        if "participants" not in structured_mom_data:
            structured_mom_data["participants"] = []
        final_state["structured_mom"] = structured_mom_data


    if final_state.get("status") == "error":
        return {"type": "error", "message": final_state.get("error_message", "Unknown error")}

    if final_state.get("status") == "needs_clarification":
        return {"type": "clarification", "prompt": final_state.get("clarification_prompt", "")}

    result = {
        "type": "success",
        "user_message": final_state.get("user_message"),
        "file_url": final_state.get("file_url"),
        "structured_mom": final_state.get("structured_mom"),
        "trace": final_state.get("trace", []),  # Include trace in response
    }
    
    return result
