import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from bson.objectid import ObjectId
import app


class TestDueSoonJob:
    @patch("app.assignments_collection")
    @patch("app.users")
    @patch("app.send_mail")
    def test_due_soon_job(self, mock_send_mail, mock_users, mock_assignments):
        # Setup
        now = datetime.now(timezone.utc)
        due_time = now + timedelta(hours=12)
        
        # Mock assignments
        mock_cursor = MagicMock()
        mock_assignments.find.return_value = mock_cursor
        mock_cursor.__iter__.return_value = [
            {
                "_id": ObjectId("6071a2a80a8a7b9240b39422"),
                "title": "Test Assignment",
                "due_date": due_time.isoformat()
            }
        ]
        
        # Mock students
        mock_students_cursor = MagicMock()
        mock_users.find.return_value = mock_students_cursor
        mock_students_cursor.__iter__.return_value = [
            {
                "identity": "student",
                "email": "student1@example.com"
            },
            {
                "identity": "student",
                "email": "student2@example.com"
            }
        ]
        
        # Execute
        app.due_soon_job()
        
        # Assert
        assert mock_send_mail.call_count == 2  # One for each student
        mock_assignments.update_one.assert_called_once()
        
    @patch("app.assignments_collection")
    def test_due_soon_job_no_assignments(self, mock_assignments):
        # Setup - no assignments due
        mock_cursor = MagicMock()
        mock_assignments.find.return_value = mock_cursor
        mock_cursor.__iter__.return_value = []
        
        # Execute
        app.due_soon_job()
        
        # Assert - no updates were made
        mock_assignments.update_one.assert_not_called()