"""
Tests for CourseSearchTool.execute() in search_tools.py.

Verifies that the tool correctly formats results, propagates filters to the
vector store, and populates last_sources for the UI.
"""
import pytest
from unittest.mock import MagicMock
from search_tools import CourseSearchTool
from vector_store import SearchResults


def make_store(documents=None, metadata=None, error=None):
    """Build a mock VectorStore with preset search results."""
    store = MagicMock()
    if error:
        store.search.return_value = SearchResults.empty(error)
    else:
        docs = documents or []
        meta = metadata or []
        store.search.return_value = SearchResults(
            documents=docs,
            metadata=meta,
            distances=[0.5] * len(docs),
        )
    store.get_lesson_link.return_value = None
    return store


class TestExecuteReturnsContent:
    def test_returns_formatted_text_when_results_found(self):
        store = make_store(
            documents=["Tool use lets the model call external functions."],
            metadata=[{"course_title": "Agentic AI", "lesson_number": 2}],
        )
        store.get_lesson_link.return_value = "https://example.com/lesson/2"

        tool = CourseSearchTool(store)
        result = tool.execute(query="tool use")

        assert "Agentic AI" in result
        assert "Lesson 2" in result
        assert "Tool use lets the model call external functions." in result

    def test_multiple_results_all_appear_in_output(self):
        store = make_store(
            documents=["Content A.", "Content B."],
            metadata=[
                {"course_title": "Course X", "lesson_number": 1},
                {"course_title": "Course X", "lesson_number": 2},
            ],
        )

        tool = CourseSearchTool(store)
        result = tool.execute(query="topic")

        assert "Content A." in result
        assert "Content B." in result


class TestExecuteEmptyAndErrors:
    def test_returns_no_content_message_when_empty(self):
        store = make_store()

        tool = CourseSearchTool(store)
        result = tool.execute(query="quantum entanglement")

        assert "No relevant content found" in result

    def test_empty_message_includes_course_filter(self):
        store = make_store()

        tool = CourseSearchTool(store)
        result = tool.execute(query="topic", course_name="Machine Learning")

        assert "Machine Learning" in result

    def test_empty_message_includes_lesson_filter(self):
        store = make_store()

        tool = CourseSearchTool(store)
        result = tool.execute(query="topic", lesson_number=7)

        assert "7" in result

    def test_returns_error_string_on_vector_store_error(self):
        store = make_store(error="ChromaDB connection refused")

        tool = CourseSearchTool(store)
        result = tool.execute(query="anything")

        assert "ChromaDB connection refused" in result


class TestExecuteFiltersPassedThrough:
    def test_passes_course_name_to_vector_store(self):
        store = make_store()

        tool = CourseSearchTool(store)
        tool.execute(query="loops", course_name="Python Basics")

        store.search.assert_called_once_with(
            query="loops", course_name="Python Basics", lesson_number=None
        )

    def test_passes_lesson_number_to_vector_store(self):
        store = make_store()

        tool = CourseSearchTool(store)
        tool.execute(query="recursion", lesson_number=3)

        store.search.assert_called_once_with(
            query="recursion", course_name=None, lesson_number=3
        )

    def test_passes_both_filters_to_vector_store(self):
        store = make_store()

        tool = CourseSearchTool(store)
        tool.execute(query="generators", course_name="Advanced Python", lesson_number=5)

        store.search.assert_called_once_with(
            query="generators", course_name="Advanced Python", lesson_number=5
        )


class TestExecuteSourcesTracking:
    def test_populates_last_sources_after_successful_search(self):
        store = make_store(
            documents=["Content."],
            metadata=[{"course_title": "Test Course", "lesson_number": 4}],
        )
        store.get_lesson_link.return_value = "https://example.com/lesson/4"

        tool = CourseSearchTool(store)
        tool.execute(query="something")

        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["label"] == "Test Course - Lesson 4"
        assert tool.last_sources[0]["url"] == "https://example.com/lesson/4"

    def test_last_sources_empty_when_no_results(self):
        store = make_store()

        tool = CourseSearchTool(store)
        tool.execute(query="nothing")

        assert tool.last_sources == []

    def test_last_sources_count_matches_result_count(self):
        store = make_store(
            documents=["Doc 1", "Doc 2", "Doc 3"],
            metadata=[
                {"course_title": "C", "lesson_number": 1},
                {"course_title": "C", "lesson_number": 2},
                {"course_title": "C", "lesson_number": 3},
            ],
        )

        tool = CourseSearchTool(store)
        tool.execute(query="content")

        assert len(tool.last_sources) == 3
