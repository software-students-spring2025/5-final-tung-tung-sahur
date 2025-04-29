import pytest
from bson.objectid import ObjectId
from unittest.mock import MagicMock
from models.assignment import AssignmentModel
from datetime import datetime


class TestAssignmentModel:
    @pytest.fixture
    def mock_collection(self):
        return MagicMock()

    @pytest.fixture
    def assignment_model(self, mock_collection):
        return AssignmentModel(mock_collection)

    def test_create_assignment(self, assignment_model, mock_collection):
        # Setup
        teacher_id = "60d21b4667d0d8992e610c85"
        title = "Test Assignment"
        description = "This is a test assignment"
        due_date = "2025-05-01T23:59:00"
        github_repo_url = "https://github.com/teacher/repo"
        github_repo_path = "assignments/hw1"
        mock_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId("60d21b4667d0d8992e610c86")
        )

        # Execute
        result = assignment_model.create_assignment(
            teacher_id, title, description, due_date, github_repo_url, github_repo_path
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
        assert call_args["due_date"] == due_date
        assert call_args["github_repo_url"] == github_repo_url
        assert call_args["github_repo_path"] == github_repo_path
        assert isinstance(call_args["created_at"], datetime)
        assert call_args["reminder_sent"] is False

    def test_get_assignment(self, assignment_model, mock_collection):
        # Setup
        assignment_id = "60d21b4667d0d8992e610c86"
        expected_assignment = {
            "_id": ObjectId(assignment_id),
            "title": "Test Assignment",
        }
        mock_collection.find_one.return_value = expected_assignment

        # Execute
        result = assignment_model.get_assignment(assignment_id)

        # Verify
        assert result == expected_assignment
        mock_collection.find_one.assert_called_once_with(
            {"_id": ObjectId(assignment_id)}
        )

    def test_get_assignment_not_found(self, assignment_model, mock_collection):
        # Setup
        assignment_id = "60d21b4667d0d8992e610c86"
        mock_collection.find_one.return_value = None

        # Execute
        result = assignment_model.get_assignment(assignment_id)

        # Verify
        assert result is None
        mock_collection.find_one.assert_called_once_with(
            {"_id": ObjectId(assignment_id)}
        )

    def test_get_teacher_assignments(self, assignment_model, mock_collection):
        # Setup
        teacher_id = "60d21b4667d0d8992e610c85"
        mock_cursor = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_cursor.sort.return_value = [
            {"_id": ObjectId(), "title": "Assignment 1"},
            {"_id": ObjectId(), "title": "Assignment 2"},
        ]

        # Execute
        results = assignment_model.get_teacher_assignments(teacher_id)

        # Verify
        assert len(results) == 2
        mock_collection.find.assert_called_once_with({"teacher_id": teacher_id})
        mock_cursor.sort.assert_called_once_with("created_at", -1)

    def test_get_all_assignments(self, assignment_model, mock_collection):
        # Setup
        mock_cursor = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_cursor.sort.return_value = [
            {"_id": ObjectId(), "title": "Assignment 1"},
            {"_id": ObjectId(), "title": "Assignment 2"},
            {"_id": ObjectId(), "title": "Assignment 3"},
        ]

        # Execute
        results = assignment_model.get_all_assignments()

        # Verify
        assert len(results) == 3
        mock_collection.find.assert_called_once_with()
        mock_cursor.sort.assert_called_once_with("created_at", -1)

    def test_update_assignment(self, assignment_model, mock_collection):
        # Setup
        assignment_id = "60d21b4667d0d8992e610c86"
        update_data = {
            "title": "Updated Assignment",
            "description": "Updated description",
        }
        mock_collection.update_one.return_value = MagicMock(modified_count=1)

        # Execute
        result = assignment_model.update_assignment(assignment_id, update_data)

        # Verify
        assert result is True
        mock_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(assignment_id)}, {"$set": update_data}
        )

    def test_update_assignment_no_changes(self, assignment_model, mock_collection):
        # Setup
        assignment_id = "60d21b4667d0d8992e610c86"
        update_data = {"title": "Same Title"}
        mock_collection.update_one.return_value = MagicMock(modified_count=0)

        # Execute
        result = assignment_model.update_assignment(assignment_id, update_data)

        # Verify
        assert result is False
        mock_collection.update_one.assert_called_once()

    def test_delete_assignment(self, assignment_model, mock_collection):
        # Setup
        assignment_id = "60d21b4667d0d8992e610c86"
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

        # Execute
        result = assignment_model.delete_assignment(assignment_id)

        # Verify
        assert result is True
        mock_collection.delete_one.assert_called_once_with(
            {"_id": ObjectId(assignment_id)}
        )

    def test_delete_assignment_not_found(self, assignment_model, mock_collection):
        # Setup
        assignment_id = "60d21b4667d0d8992e610c86"
        mock_collection.delete_one.return_value = MagicMock(deleted_count=0)

        # Execute
        result = assignment_model.delete_assignment(assignment_id)

        # Verify
        assert result is False
        mock_collection.delete_one.assert_called_once_with(
            {"_id": ObjectId(assignment_id)}
        )
