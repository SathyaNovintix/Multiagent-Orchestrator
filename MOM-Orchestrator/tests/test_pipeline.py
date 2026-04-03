"""
End-to-end pipeline tests.
Tests the full LangGraph execution with stubbed LLM and in-memory Redis.
"""
import pytest
from unittest.mock import AsyncMock, patch
from tests.conftest import SAMPLE_TRANSCRIPT


@pytest.mark.asyncio
async def test_full_text_pipeline_english():
    """English text input → full pipeline → success with MOM."""
    from dotenv import load_dotenv
    load_dotenv()

    from orchestrator.registry import build_registry, AGENT_REGISTRY
    from orchestrator.core import init_orchestrator, new_session, run_pipeline

    build_registry()

    with patch("pdf.generator.generate_pdf", new_callable=AsyncMock) as mock_pdf:
        mock_pdf.return_value = "/tmp/test.pdf"
        init_orchestrator()

        session = await new_session(intent="auto_detect")

        result = await run_pipeline(
            session_id=session.session_id,
            input_type="text",
            content=SAMPLE_TRANSCRIPT,
            intent="generate_mom",
        )

    assert result["type"] == "success"
    assert result.get("structured_mom") is not None
    mom = result["structured_mom"]
    assert len(mom.get("topics", [])) >= 1
    assert len(mom.get("decisions", [])) >= 1
    assert len(mom.get("actions", [])) >= 1


@pytest.mark.asyncio
async def test_pipeline_skips_translator_for_english():
    """Translator node must be skipped when language is English."""
    from dotenv import load_dotenv
    load_dotenv()

    from orchestrator.registry import build_registry
    from orchestrator.core import init_orchestrator, new_session, run_pipeline
    from agents import translator as translator_module

    build_registry()

    translator_called = []

    original_execute = translator_module.TranslatorAgent._execute

    async def track_execute(self, request):
        translator_called.append(True)
        return await original_execute(self, request)

    translator_module.TranslatorAgent._execute = track_execute

    with patch("pdf.generator.generate_pdf", new_callable=AsyncMock):
        init_orchestrator()
        session = await new_session()
        await run_pipeline(
            session_id=session.session_id,
            input_type="text",
            content=SAMPLE_TRANSCRIPT,
            intent="generate_mom",
        )

    translator_module.TranslatorAgent._execute = original_execute
    assert len(translator_called) == 0, "Translator should be skipped for English input"


@pytest.mark.asyncio
async def test_pipeline_general_summary_skips_extraction():
    """general_summary intent must skip the extraction node."""
    from dotenv import load_dotenv
    load_dotenv()

    from orchestrator.registry import build_registry
    from orchestrator.core import init_orchestrator, new_session, run_pipeline
    import agents.topic_extractor as te_module

    build_registry()

    extractor_called = []
    original = te_module.TopicExtractorAgent._execute

    async def track(self, request):
        extractor_called.append(True)
        return await original(self, request)

    te_module.TopicExtractorAgent._execute = track

    with patch("pdf.generator.generate_pdf", new_callable=AsyncMock):
        init_orchestrator()
        session = await new_session()
        await run_pipeline(
            session_id=session.session_id,
            input_type="text",
            content="Please give me a brief summary of this text.",
            intent="general_summary",
        )

    te_module.TopicExtractorAgent._execute = original
    assert len(extractor_called) == 0, "TopicExtractor must be skipped for general_summary"


@pytest.mark.asyncio
async def test_new_session_creates_unique_ids():
    """Every call to new_session must return a unique session_id."""
    from dotenv import load_dotenv
    load_dotenv()

    from orchestrator.core import new_session

    ids = [await new_session() for _ in range(5)]
    assert len({s.session_id for s in ids}) == 5
