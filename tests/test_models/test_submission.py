import pytest
from bson.objectid import ObjectId
from unittest.mock import MagicMock
from models.submission import SubmissionModel
from datetime import datetime


class TestSubmissionModel:
    @pytest.fixture
    def mock_collection(self):
        return MagicMock()

    @pytest.fixture
    def submission_model(self, mock_collection):
        return SubmissionModel(mock_collection)

    def test_create_submission(self, submission_model, mock_collection):
        # Setup
        student_id = "60d21b4667d0d8992e610c85"
        assignment_id = "60d21b4667d0d8992e610c86"
        github_link = "https://github.com/student/repo"
        readme_content = "# Submission\nThis is my homework."
        mock_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId("60d21b4667d0d8992e610c87")
        )

        # Execute
        result = submission_model.create_submission(
            student_id, assignment_id, github_link, readme_content
        )

        # Verify
        assert isinstance(result, str)
        assert len(result) == 24  # ObjectId as string has 24 chars
        mock_collection.insert_one.assert_called_once()

        # Check the argument passed to insert_one
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["student_id"] == student_id
        assert call_args["assignment_id"] == assignment_id
        assert call_args["github_link"] == github_link
        assert call_args["readme_content"] == readme_content
        assert isinstance(call_args["submitted_at"], datetime)
        assert call_args["grade"] is None
        assert call_args["feedback"] is None
        assert call_args["status"] == "submitted"

    def test_get_submission(self, submission_model, mock_collection):
        # Setup
        submission_id = "60d21b4667d0d8992e610c87"
        expected_submission = {
            "_id": ObjectId(submission_id),
            "student_id": "60d21b4667d0d8992e610c85",
            "assignment_id": "60d21b4667d0d8992e610c86",
        }
        mock_collection.find_one.return_value = expected_submission

        # Execute
        result = submission_model.get_submission(submission_id)

        # Verify
        assert result == expected_submission
        mock_collection.find_one.assert_called_once_with(
            {"_id": ObjectId(submission_id)}
        )

    def test_get_student_submissions(self, submission_model, mock_collection):
        # Setup
        student_id = "60d21b4667d0d8992e610c85"
        mock_cursor = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_cursor.sort.return_value = [
            {"_id": ObjectId(), "assignment_id": "assignment1"},
            {"_id": ObjectId(), "assignment_id": "assignment2"},
        ]

        # Execute
        results = submission_model.get_student_submissions(student_id)

        # Verify
        assert len(results) == 2
        mock_collection.find.assert_called_once_with({"student_id": student_id})
        mock_cursor.sort.assert_called_once_with("submitted_at", -1)

    def test_get_assignment_submissions(self, submission_model, mock_collection):
        # Setup
        assignment_id = "60d21b4667d0d8992e610c86"
        mock_cursor = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_cursor.sort.return_value = [
            {"_id": ObjectId(), "student_id": "student1"},
            {"_id": ObjectId(), "student_id": "student2"},
            {"_id": ObjectId(), "student_id": "student3"},
        ]

        # Execute
        results = submission_model.get_assignment_submissions(assignment_id)

        # Verify
        assert len(results) == 3
        mock_collection.find.assert_called_once_with({"assignment_id": assignment_id})
        mock_cursor.sort.assert_called_once_with("submitted_at", -1)

    def test_get_student_assignment_submission(self, submission_model, mock_collection):
        # Setup
        student_id = "60d21b4667d0d8992e610c85"
        assignment_id = "60d21b4667d0d8992e610c86"
        expected_submission = {
            "_id": ObjectId(),
            "student_id": student_id,
            "assignment_id": assignment_id,
        }
        mock_collection.find_one.return_value = expected_submission

        # Execute
        result = submission_model.get_student_assignment_submission(
            student_id, assignment_id
        )

        # Verify
        assert result == expected_submission
        mock_collection.find_one.assert_called_once_with(
            {"student_id": student_id, "assignment_id": assignment_id}
        )

    def test_update_submission(self, submission_model, mock_collection):
        # Setup
        submission_id = "60d21b4667d0d8992e610c87"
        update_data = {"github_link": "https://github.com/student/repo/updated"}
        mock_collection.update_one.return_value = MagicMock(modified_count=1)

        # Execute
        result = submission_model.update_submission(submission_id, update_data)

        # Verify
        assert result is True
        mock_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(submission_id)}, {"$set": update_data}
        )

    def test_add_feedback(self, submission_model, mock_collection):
        # Setup
        submission_id = "60d21b4667d0d8992e610c87"
        grade = 95.5
        feedback = "Great work!"

        # Mock the update_submission method
        submission_model.update_submission = MagicMock(return_value=True)

        # Execute
        result = submission_model.add_feedback(submission_id, grade, feedback)

        # Verify
        assert result is True
        submission_model.update_submission.assert_called_once()

        # Check the arguments
        call_args = submission_model.update_submission.call_args[0]
        assert call_args[0] == submission_id
        update_data = call_args[1]
        assert update_data["grade"] == grade
        assert update_data["feedback"] == feedback
        assert update_data["status"] == "graded"
        assert isinstance(update_data["graded_at"], datetime)

    def test_delete_by_assignment(self, submission_model, mock_collection):
        # Setup
        assignment_id = "60d21b4667d0d8992e610c86"
        mock_collection.delete_many.return_value = MagicMock(deleted_count=5)

        # Execute
        result = submission_model.delete_by_assignment(assignment_id)

        # Verify
        assert result == 5
        mock_collection.delete_many.assert_called_once_with(
            {"assignment_id": assignment_id}
        )
