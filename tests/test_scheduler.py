# tests/test_scheduler.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from bson.objectid import ObjectId


class TestScheduler:
    @patch("app.assignments_collection")
    @patch("app.users")
    @patch("app.send_mail")
    def test_due_soon_job(
        self, mock_send_mail, mock_users, mock_assignments_collection
    ):
        # Current time
        now = datetime.now(timezone.utc)

        # Create mock assignments due soon
        mock_assignments = [
            {
                "_id": ObjectId(),
                "title": "Assignment 1",
                "due_date": (now + timedelta(hours=12)).isoformat(),
            },
            {
                "_id": ObjectId(),
                "title": "Assignment 2",
                "due_date": (now + timedelta(hours=23)).isoformat(),
            },
        ]

        # Mock the find method for assignments
        mock_assignments_collection.find.return_value = mock_assignments

        # Mock students with emails
        mock_students = [
            {
                "username": "student1",
                "identity": "student",
                "email": "student1@example.com",
            },
            {
                "username": "student2",
                "identity": "student",
                "email": "student2@example.com",
            },
        ]
        mock_users.find.return_value = mock_students

        # Import the function to test
        from app import due_soon_job

        # Execute
        due_soon_job()

        # Verify emails were sent
        assert mock_send_mail.call_count == 4

        # Verify the update for each assignment
        assert mock_assignments_collection.update_one.call_count == 2
