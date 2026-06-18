"""
Tests for RAGSystem.query() in rag_system.py.

Verifies that the orchestrator correctly wires tools to the AI generator,
forwards conversation history, and exposes exceptions rather than swallowing them.
"""
import pytest
from unittest.mock import MagicMock, patch
from rag_system import RAGSystem


def make_rag_system():
    """
    Create a RAGSystem with all I/O-bound dependencies mocked.

    - VectorStore, DocumentProcessor: replaced by mocks (no ChromaDB/disk I/O)
    - AIGenerator: replaced by mock (no Anthropic API calls)
    - SessionManager: replaced by mock
    - tool_manager: replaced with a mock after construction so we can control
      get_tool_definitions() / get_last_sources() / reset_sources()
    """
    with (
        patch("rag_system.VectorStore"),
        patch("rag_system.DocumentProcessor"),
        patch("rag_system.AIGenerator"),
        patch("rag_system.SessionManager"),
    ):
        config = MagicMock()
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "/tmp/test_chroma"
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        config.MAX_RESULTS = 5
        config.MAX_HISTORY = 2
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "claude-haiku-4-5"

        system = RAGSystem(config)

    # Replace tool_manager with a mock so we can set return values on it.
    system.tool_manager = MagicMock()
    system.tool_manager.get_tool_definitions.return_value = [
        {
            "name": "search_course_content",
            "description": "Search course content",
            "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        }
    ]

    return system


class TestQueryReturns:
    def test_returns_string_answer(self):
        system = make_rag_system()
        system.ai_generator.generate_response.return_value = "Lesson 1 covers tool use."
        system.tool_manager.get_last_sources.return_value = []

        answer, _ = system.query("What does lesson 1 cover?")

        assert isinstance(answer, str)
        assert len(answer) > 0

    def test_returns_sources_list(self):
        system = make_rag_system()
        system.ai_generator.generate_response.return_value = "Answer"
        system.tool_manager.get_last_sources.return_value = [
            {"label": "Course A - Lesson 1", "url": "https://example.com"}
        ]

        _, sources = system.query("What is covered?")

        assert isinstance(sources, list)

    def test_sources_come_from_tool_manager(self):
        system = make_rag_system()
        system.ai_generator.generate_response.return_value = "Answer"
        expected = [{"label": "Course X - Lesson 2", "url": "https://example.com/2"}]
        system.tool_manager.get_last_sources.return_value = expected

        _, sources = system.query("Detail question")

        assert sources == expected


class TestQueryWiresToolsCorrectly:
    def test_passes_tools_to_ai_generator(self):
        """Without tools, Claude cannot call search_course_content."""
        system = make_rag_system()
        system.ai_generator.generate_response.return_value = "Answer"
        system.tool_manager.get_last_sources.return_value = []

        system.query("What does this course cover?")

        call_kwargs = system.ai_generator.generate_response.call_args.kwargs
        tools = call_kwargs.get("tools")
        assert tools is not None and len(tools) > 0, (
            "tools were not passed to generate_response — "
            "the AI cannot call search_course_content"
        )

    def test_passes_tool_manager_to_ai_generator(self):
        """Without tool_manager, tool calls cannot be executed."""
        system = make_rag_system()
        system.ai_generator.generate_response.return_value = "Answer"
        system.tool_manager.get_last_sources.return_value = []

        system.query("What does lesson 2 cover?")

        call_kwargs = system.ai_generator.generate_response.call_args.kwargs
        assert call_kwargs.get("tool_manager") is not None, (
            "tool_manager was not passed to generate_response"
        )

    def test_resets_sources_after_each_query(self):
        """Sources must be cleared after retrieval to prevent leaking between requests."""
        system = make_rag_system()
        system.ai_generator.generate_response.return_value = "Answer"
        system.tool_manager.get_last_sources.return_value = []

        system.query("Any question")

        system.tool_manager.reset_sources.assert_called_once()


class TestQuerySessionHistory:
    def test_passes_conversation_history_when_session_exists(self):
        system = make_rag_system()
        system.ai_generator.generate_response.return_value = "Answer"
        system.tool_manager.get_last_sources.return_value = []
        system.session_manager.get_conversation_history.return_value = (
            "User: hi\nAssistant: hello"
        )

        system.query("Follow-up", session_id="sess_1")

        system.session_manager.get_conversation_history.assert_called_once_with("sess_1")
        call_kwargs = system.ai_generator.generate_response.call_args.kwargs
        assert call_kwargs.get("conversation_history") == "User: hi\nAssistant: hello"

    def test_no_history_passed_without_session_id(self):
        system = make_rag_system()
        system.ai_generator.generate_response.return_value = "Answer"
        system.tool_manager.get_last_sources.return_value = []

        system.query("First question")

        call_kwargs = system.ai_generator.generate_response.call_args.kwargs
        assert call_kwargs.get("conversation_history") is None

    def test_adds_exchange_to_session_after_query(self):
        system = make_rag_system()
        system.ai_generator.generate_response.return_value = "The answer."
        system.tool_manager.get_last_sources.return_value = []
        system.session_manager.get_conversation_history.return_value = None

        system.query("A question", session_id="sess_42")

        system.session_manager.add_exchange.assert_called_once_with(
            "sess_42", "A question", "The answer."
        )


class TestQueryErrorHandling:
    def test_exception_from_ai_generator_propagates(self):
        """Exceptions must propagate so FastAPI can return HTTP 500."""
        system = make_rag_system()
        system.ai_generator.generate_response.side_effect = Exception("Anthropic API error")

        with pytest.raises(Exception, match="Anthropic API error"):
            system.query("What is covered?")
