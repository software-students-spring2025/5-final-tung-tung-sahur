import pytest
from unittest.mock import patch, MagicMock
from models.submission import SubmissionModel
from bson.objectid import ObjectId
from datetime import datetime


class TestSubmissionModelExtended:
    @pytest.fixture
    def mock_collection(self):
        return MagicMock()
    
    @pytest.fixture
    def submission_model(self, mock_collection):
        return SubmissionModel(mock_collection)
    
    def test_get_student_assignment_submission_not_found(self, submission_model, mock_collection):
        # Setup
        student_id = "60d21b4667d0d8992e610c85"
        assignment_id = "60d21b4667d0d8992e610c86"
        mock_collection.find_one.return_value = None
        
        # Execute
        result = submission_model.get_student_assignment_submission(student_id, assignment_id)
        
        # Assert
        assert result is None
        mock_collection.find_one.assert_called_once_with(
            {"student_id": student_id, "assignment_id": assignment_id}
        )
    
    def test_update_submission_not_found(self, submission_model, mock_collection):
        # Setup
        submission_id = "60d21b4667d0d8992e610c87"
        update_data = {"github_link": "new_link"}
        mock_collection.update_one.return_value = MagicMock(modified_count=0)
        
        # Execute
        result = submission_model.update_submission(submission_id, update_data)
        
        # Assert
        assert result is False
        mock_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(submission_id)}, {"$set": update_data}
        )
    
    def test_add_feedback_failure(self, submission_model):
        # Setup
        submission_id = "60d21b4667d0d8992e610c87"
        grade = 90.5
        feedback = "Good job"
        
        # Mock update_submission to fail
        submission_model.update_submission = MagicMock(return_value=False)
        
        # Execute
        result = submission_model.add_feedback(submission_id, grade, feedback)
        
        # Assert
        assert result is False
        submission_model.update_submission.assert_called_once()
    
    def test_delete_by_assignment_none(self, submission_model, mock_collection):
        # Setup
        assignment_id = "60d21b4667d0d8992e610c86"
        mock_collection.delete_many.return_value = MagicMock(deleted_count=0)
        
        # Execute
        result = submission_model.delete_by_assignment(assignment_id)
        
        # Assert
        assert result == 0
        mock_collection.delete_many.assert_called_once_with(
            {"assignment_id": assignment_id}
        )