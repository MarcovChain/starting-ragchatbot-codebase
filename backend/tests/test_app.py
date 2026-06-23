"""
Tests for FastAPI endpoints in app.py.

app.py is imported via conftest.py (which applies module-level patches so that
RAGSystem construction and the StaticFiles mount don't require real infrastructure).
The `mock_rag` fixture exposes the module-level rag_system MagicMock so tests can
control return values and assert on calls.
"""
import pytest


class TestQueryEndpoint:
    def test_returns_200_with_valid_query(self, client, mock_rag):
        response = client.post("/api/query", json={"query": "What is lesson 1?"})

        assert response.status_code == 200

    def test_response_has_required_fields(self, client, mock_rag):
        mock_rag.query.return_value = ("Some answer", [{"label": "Course A", "url": "http://x.com"}])

        body = client.post("/api/query", json={"query": "What is lesson 1?"}).json()

        assert "answer" in body
        assert "sources" in body
        assert "session_id" in body

    def test_creates_session_when_none_provided(self, client, mock_rag):
        mock_rag.session_manager.create_session.return_value = "new-sess"

        body = client.post("/api/query", json={"query": "Hello"}).json()

        mock_rag.session_manager.create_session.assert_called_once()
        assert body["session_id"] == "new-sess"

    def test_uses_provided_session_id(self, client, mock_rag):
        body = client.post(
            "/api/query", json={"query": "Hello", "session_id": "existing-sess"}
        ).json()

        mock_rag.session_manager.create_session.assert_not_called()
        assert body["session_id"] == "existing-sess"

    def test_passes_query_and_session_to_rag(self, client, mock_rag):
        mock_rag.session_manager.create_session.return_value = "s1"

        client.post("/api/query", json={"query": "What is Python?"})

        mock_rag.query.assert_called_once_with("What is Python?", "s1")

    def test_returns_sources_from_rag(self, client, mock_rag):
        sources = [{"label": "Course X - Lesson 1", "url": "http://example.com/1"}]
        mock_rag.query.return_value = ("Answer", sources)

        body = client.post("/api/query", json={"query": "question"}).json()

        assert body["sources"] == sources

    def test_returns_500_when_rag_raises(self, client, mock_rag):
        mock_rag.query.side_effect = RuntimeError("upstream failure")

        response = client.post("/api/query", json={"query": "question"})

        assert response.status_code == 500

    def test_returns_422_when_query_field_missing(self, client):
        response = client.post("/api/query", json={})

        assert response.status_code == 422


class TestCoursesEndpoint:
    def test_returns_200(self, client, mock_rag):
        response = client.get("/api/courses")

        assert response.status_code == 200

    def test_response_has_required_fields(self, client, mock_rag):
        body = client.get("/api/courses").json()

        assert "total_courses" in body
        assert "course_titles" in body

    def test_total_courses_count(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["A", "B", "C"],
        }

        body = client.get("/api/courses").json()

        assert body["total_courses"] == 3

    def test_course_titles_list(self, client, mock_rag):
        titles = ["Python Basics", "Advanced ML"]
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": titles,
        }

        body = client.get("/api/courses").json()

        assert body["course_titles"] == titles

    def test_returns_500_when_analytics_raises(self, client, mock_rag):
        mock_rag.get_course_analytics.side_effect = RuntimeError("collection error")

        response = client.get("/api/courses")

        assert response.status_code == 500
