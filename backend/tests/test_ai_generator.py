"""
Tests for AIGenerator in ai_generator.py.

Key regression being tested: _run_tool_loop() must include the 'tools'
parameter in every follow-up Anthropic API call. The Anthropic API rejects
requests where the message history contains tool_use blocks but tools are not
defined — this causes a 400/exception that propagates as HTTP 500 and the
frontend shows 'query failed'.
"""
import pytest
from unittest.mock import MagicMock, patch
from ai_generator import AIGenerator


DUMMY_TOOLS = [
    {
        "name": "search_course_content",
        "description": "Search course content",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    }
]


def make_generator():
    """Create an AIGenerator with a mocked Anthropic client (no real API calls)."""
    with patch("ai_generator.anthropic.Anthropic"):
        gen = AIGenerator(api_key="test-key", model="claude-haiku-4-5")
    gen.client = MagicMock()
    return gen


def text_response(text="Direct answer"):
    """Simulate a Claude response that doesn't use a tool."""
    response = MagicMock()
    response.stop_reason = "end_turn"
    content = MagicMock()
    content.text = text
    response.content = [content]
    return response


def tool_use_response(tool_name="search_course_content", tool_id="toolu_01", input_data=None):
    """Simulate a Claude response requesting a tool call."""
    response = MagicMock()
    response.stop_reason = "tool_use"
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.id = tool_id
    block.input = input_data or {"query": "test topic"}
    response.content = [block]
    return response


class TestDirectResponse:
    def test_returns_text_directly_when_no_tool_use(self):
        gen = make_generator()
        gen.client.messages.create.return_value = text_response("Python is a programming language.")

        result = gen.generate_response(query="What is Python?")

        assert result == "Python is a programming language."

    def test_only_one_api_call_when_no_tool_use(self):
        gen = make_generator()
        gen.client.messages.create.return_value = text_response()

        gen.generate_response(query="General question", tools=DUMMY_TOOLS)

        assert gen.client.messages.create.call_count == 1

    def test_tool_manager_not_invoked_when_no_tool_use(self):
        gen = make_generator()
        gen.client.messages.create.return_value = text_response("42")
        mock_tm = MagicMock()

        gen.generate_response(query="What is 2+2?", tools=DUMMY_TOOLS, tool_manager=mock_tm)

        mock_tm.execute_tool.assert_not_called()


class TestToolExecution:
    def test_two_api_calls_made_when_tool_used(self):
        gen = make_generator()
        gen.client.messages.create.side_effect = [
            tool_use_response(),
            text_response("Synthesized answer"),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "search result text"

        gen.generate_response(query="What does lesson 1 cover?", tools=DUMMY_TOOLS, tool_manager=mock_tm)

        assert gen.client.messages.create.call_count == 2

    def test_tool_manager_called_with_correct_tool_name_and_args(self):
        gen = make_generator()
        gen.client.messages.create.side_effect = [
            tool_use_response(
                tool_name="search_course_content",
                input_data={"query": "MCP tool patterns"},
            ),
            text_response("Answer"),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "results"

        gen.generate_response(query="question", tools=DUMMY_TOOLS, tool_manager=mock_tm)

        mock_tm.execute_tool.assert_called_once_with(
            "search_course_content", query="MCP tool patterns"
        )

    def test_final_api_call_includes_tools(self):
        """
        REGRESSION: _handle_tool_execution must pass 'tools' to the final API call.

        When the message history contains an assistant tool_use block, the Anthropic
        API requires 'tools' to be present in every follow-up request.  Omitting it
        causes a 400 that surfaces as HTTP 500 and 'query failed' in the frontend.
        """
        gen = make_generator()
        gen.client.messages.create.side_effect = [
            tool_use_response(),
            text_response("Final answer"),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "results"

        gen.generate_response(
            query="What does lesson 1 cover?", tools=DUMMY_TOOLS, tool_manager=mock_tm
        )

        second_call_kwargs = gen.client.messages.create.call_args_list[1].kwargs
        assert "tools" in second_call_kwargs, (
            "'tools' is missing from the final API call inside _handle_tool_execution. "
            "The Anthropic API rejects requests where message history has tool_use blocks "
            "but tools are not defined — this is what causes 'query failed'."
        )

    def test_final_api_call_tools_match_original_tools(self):
        """The tools forwarded to the final call must be the same as the first call."""
        gen = make_generator()
        gen.client.messages.create.side_effect = [
            tool_use_response(),
            text_response("Answer"),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "results"

        gen.generate_response(query="question", tools=DUMMY_TOOLS, tool_manager=mock_tm)

        second_call_kwargs = gen.client.messages.create.call_args_list[1].kwargs
        assert second_call_kwargs.get("tools") == DUMMY_TOOLS

    def test_tool_result_present_in_final_messages(self):
        """The tool execution result must appear in the messages sent on the second call."""
        gen = make_generator()
        gen.client.messages.create.side_effect = [
            tool_use_response(tool_id="toolu_abc"),
            text_response("Synthesized"),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "Lesson 1 covers Python basics."

        gen.generate_response(query="question", tools=DUMMY_TOOLS, tool_manager=mock_tm)

        second_call_kwargs = gen.client.messages.create.call_args_list[1].kwargs
        messages = second_call_kwargs["messages"]

        tool_result_found = False
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if (
                            isinstance(block, dict)
                            and block.get("type") == "tool_result"
                            and block.get("tool_use_id") == "toolu_abc"
                        ):
                            assert "Lesson 1 covers Python basics." in block.get("content", "")
                            tool_result_found = True

        assert tool_result_found, "tool_result block not found in final API call messages"

    def test_returns_final_response_text(self):
        gen = make_generator()
        gen.client.messages.create.side_effect = [
            tool_use_response(),
            text_response("The model result."),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "results"

        result = gen.generate_response(query="question", tools=DUMMY_TOOLS, tool_manager=mock_tm)

        assert result == "The model result."


class TestSequentialToolExecution:
    def test_two_sequential_tool_rounds_makes_three_api_calls(self):
        gen = make_generator()
        gen.client.messages.create.side_effect = [
            tool_use_response(tool_id="toolu_r1"),
            tool_use_response(tool_id="toolu_r2"),
            text_response("Final synthesized answer"),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "search result"

        result = gen.generate_response(query="compare courses", tools=DUMMY_TOOLS, tool_manager=mock_tm)

        assert gen.client.messages.create.call_count == 3
        assert mock_tm.execute_tool.call_count == 2
        assert result == "Final synthesized answer"

    def test_early_exit_after_first_tool_round(self):
        gen = make_generator()
        gen.client.messages.create.side_effect = [
            tool_use_response(),
            text_response("Early exit answer"),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "results"

        result = gen.generate_response(query="question", tools=DUMMY_TOOLS, tool_manager=mock_tm)

        assert gen.client.messages.create.call_count == 2
        assert result == "Early exit answer"

    def test_tool_error_returns_gracefully_without_extra_api_calls(self):
        gen = make_generator()
        gen.client.messages.create.return_value = tool_use_response()
        mock_tm = MagicMock()
        mock_tm.execute_tool.side_effect = RuntimeError("DB timeout")

        result = gen.generate_response(query="question", tools=DUMMY_TOOLS, tool_manager=mock_tm)

        assert gen.client.messages.create.call_count == 1
        assert mock_tm.execute_tool.call_count == 1
        assert isinstance(result, str) and len(result) > 0

    def test_round_cap_stops_at_three_total_api_calls(self):
        gen = make_generator()
        gen.client.messages.create.side_effect = [
            tool_use_response(tool_id="toolu_r1"),
            tool_use_response(tool_id="toolu_r2"),
            tool_use_response(tool_id="toolu_r3"),
        ]
        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "results"

        result = gen.generate_response(query="question", tools=DUMMY_TOOLS, tool_manager=mock_tm)

        assert gen.client.messages.create.call_count == 3
        assert isinstance(result, str) and len(result) > 0
