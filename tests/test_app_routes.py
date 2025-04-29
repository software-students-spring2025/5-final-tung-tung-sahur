# tests/test_app_routes.py (improved)
import pytest
from unittest.mock import MagicMock, patch
from bson.objectid import ObjectId
import app


class TestAppRoutes:
    @patch("app.users")
    def test_all_students_route(self, mock_users, client):
        # Setup
        mock_users.find.return_value = [
            {"username": "student1", "identity": "student"},
            {"username": "teacher1", "identity": "teacher"},
            {"username": "student2", "identity": "student"},
        ]

        # Execute with teacher login
        with client.session_transaction() as sess:
            sess["username"] = "teacher"
            sess["identity"] = "teacher"

        with patch("app.render_template") as mock_render_template:
            mock_render_template.return_value = "Rendered Template"
            response = client.get("/allStudents")

            # Verify render_template was called
            mock_render_template.assert_called_once()

    @patch("app.users")
    def test_delete_student_route(self, mock_users, client):
        # Setup
        mock_users.find_one.return_value = {
            "username": "student1",
            "identity": "student",
        }

        # Execute with teacher login
        with client.session_transaction() as sess:
            sess["username"] = "teacher"
            sess["identity"] = "teacher"

        with patch("app.github_accounts"):
            response = client.post("/deleteStudent/student1")

            # Verify
            assert response.status_code == 302
            assert response.location == "/allStudents"
            mock_users.delete_one.assert_called_once_with({"username": "student1"})

    # Add tests for template filters
    def test_markdown_filter(self):
        # Test basic markdown
        result = app.markdown_filter("# Heading\n- Item 1\n- Item 2")
        assert "<h1>" in result
        assert "<li>" in result

        # Test with None
        result = app.markdown_filter(None)
        assert result == ""

    def test_datetime_format(self):
        # Test with ISO string
        result = app.datetime_format("2023-01-01T12:00:00Z")
        assert "2023-01-01" in result

        # Test with non-ISO string
        result = app.datetime_format("not a date")
        assert result == "not a date"

    def test_chat_time_format(self):
        # Test with ISO string
        result = app.chat_time_format("2023-01-01T12:00:00Z")
        assert "2023-01-01" in result

        # Test with non-ISO string
        result = app.chat_time_format("not a date")
        assert result == "not a date"
