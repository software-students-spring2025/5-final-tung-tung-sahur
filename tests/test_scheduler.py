# tests/test_scheduler.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from bson.objectid import ObjectId

class TestScheduler:
    @patch('app.send_mail')
    @patch('app.MongoClient')
    def test_due_soon_job(self, mock_mongo_client, mock_send_mail):
        # Setup
        mock_db = MagicMock()
        mock_mongo_client.return_value.get_database.return_value = mock_db
        
        # Current time
        now = datetime.now(timezone.utc)
        
        # Create mock assignments due soon
        mock_assignments = [
            {
                "_id": ObjectId(),
                "title": "Assignment 1",
                "due_date": (now + timedelta(hours=12)).isoformat()
            },
            {
                "_id": ObjectId(),
                "title": "Assignment 2",
                "due_date": (now + timedelta(hours=23)).isoformat()
            }
        ]
        
        # Mock the find method for assignments
        mock_db.assignments_collection.find.return_value = mock_assignments
        
        # Mock students with emails
        mock_students = [
            {"username": "student1", "identity": "student", "email": "student1@example.com"},
            {"username": "student2", "identity": "student", "email": "student2@example.com"}
        ]
        mock_db.users.find.return_value = mock_students
        
        # Import the function to test
        from app import due_soon_job
        
        # Execute
        due_soon_job()
        
        # Verify
        # Should send 2 emails (2 students) for each of 2 assignments = 4 emails
        assert mock_send_mail.call_count == 4
        
        # Verify the update for each assignment
        assert mock_db.assignments_collection.update_one.call_count == 2
        
        # Check that we're setting reminder_sent to True
        for call in mock_db.assignments_collection.update_one.call_args_list:
            assert call[0][1] == {"$set": {"reminder_sent": True}}