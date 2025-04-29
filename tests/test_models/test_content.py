# tests/test_models/test_content.py
import pytest
from bson.objectid import ObjectId
from unittest.mock import MagicMock
from models.content import ContentModel
from datetime import datetime


class TestContentModel:
    @pytest.fixture
    def mock_collection(self):
        return MagicMock()

    @pytest.fixture
    def content_model(self, mock_collection):
        return ContentModel(mock_collection)

    def test_create_content(self, content_model, mock_collection):
        # Setup
        teacher_id = "60d21b4667d0d8992e610c85"
        title = "Introduction to Python"
        description = "Learn the basics of Python programming"
        github_repo_url = "https://github.com/teacher/repo"
        github_repo_path = "lectures/python-intro"
        mock_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId("60d21b4667d0d8992e610c88")
        )

        # Execute
        result = content_model.create_content(
            teacher_id, title, description, github_repo_url, github_repo_path
        )

        # Verify
        assert isinstance(result, str)
        assert len(result) == 24  # ObjectId as string has 24 chars
        mock_collection.insert_one.assert_called_once()

        # Check the argument passed to insert_one
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["teacher_id"] == teacher_id
        assert call_args["title"] == title
        assert call_args["description"] == description
        assert call_args["github_repo_url"] == github_repo_url
        assert call_args["github_repo_path"] == github_repo_path
        assert isinstance(call_args["created_at"], datetime)

    def test_get_content(self, content_model, mock_collection):
        # Setup
        content_id = "60d21b4667d0d8992e610c88"
        expected_content = {
            "_id": ObjectId(content_id),
            "title": "Introduction to Python",
        }
        mock_collection.find_one.return_value = expected_content

        # Execute
        result = content_model.get_content(content_id)

        # Verify
        assert result == expected_content
        mock_collection.find_one.assert_called_once_with({"_id": ObjectId(content_id)})

    def test_get_teacher_content(self, content_model, mock_collection):
        # Setup
        teacher_id = "60d21b4667d0d8992e610c85"
        mock_cursor = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_cursor.sort.return_value = [
            {"_id": ObjectId(), "title": "Lecture 1"},
            {"_id": ObjectId(), "title": "Lecture 2"},
        ]

        # Execute
        results = content_model.get_teacher_content(teacher_id)

        # Verify
        assert len(results) == 2
        mock_collection.find.assert_called_once_with({"teacher_id": teacher_id})
        mock_cursor.sort.assert_called_once_with("created_at", -1)

    def test_get_all_content(self, content_model, mock_collection):
        # Setup
        mock_cursor = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_cursor.sort.return_value = [
            {"_id": ObjectId(), "title": "Lecture 1"},
            {"_id": ObjectId(), "title": "Lecture 2"},
            {"_id": ObjectId(), "title": "Lecture 3"},
        ]

        # Execute
        results = content_model.get_all_content()

        # Verify
        assert len(results) == 3
        mock_collection.find.assert_called_once_with()
        mock_cursor.sort.assert_called_once_with("created_at", -1)

    def test_update_content(self, content_model, mock_collection):
        # Setup
        content_id = "60d21b4667d0d8992e610c88"
        update_data = {"title": "Updated Title", "description": "Updated description"}
        mock_collection.update_one.return_value = MagicMock(modified_count=1)

        # Execute
        result = content_model.update_content(content_id, update_data)

        # Verify
        assert result is True
        mock_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(content_id)}, {"$set": update_data}
        )

    def test_update_content_no_changes(self, content_model, mock_collection):
        # Setup
        content_id = "60d21b4667d0d8992e610c88"
        update_data = {"title": "Same Title"}
        mock_collection.update_one.return_value = MagicMock(modified_count=0)

        # Execute
        result = content_model.update_content(content_id, update_data)

        # Verify
        assert result is False
        mock_collection.update_one.assert_called_once()

    def test_delete_content(self, content_model, mock_collection):
        # Setup
        content_id = "60d21b4667d0d8992e610c88"
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

        # Execute
        result = content_model.delete_content(content_id)

        # Verify
        assert result is True
        mock_collection.delete_one.assert_called_once_with(
            {"_id": ObjectId(content_id)}
        )

    def test_delete_content_not_found(self, content_model, mock_collection):
        # Setup
        content_id = "60d21b4667d0d8992e610c88"
        mock_collection.delete_one.return_value = MagicMock(deleted_count=0)

        # Execute
        result = content_model.delete_content(content_id)

        # Verify
        assert result is False
        mock_collection.delete_one.assert_called_once_with(
            {"_id": ObjectId(content_id)}
        )
