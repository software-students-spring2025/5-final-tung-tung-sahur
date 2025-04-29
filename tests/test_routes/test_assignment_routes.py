# tests/test_routes/test_assignment_routes.py (modified)
import pytest
from unittest.mock import MagicMock, patch
from bson.objectid import ObjectId
from datetime import datetime
from routes.assignmentRoute import assignment_bp
from flask import Flask

class TestAssignmentRoutes:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.register_blueprint(assignment_bp)
        app.secret_key = "test_secret_key"
        app.config['TESTING'] = True
        return app
    
    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.SubmissionModel')
    def test_show_assignments_teacher(self, mock_submission_model, mock_assignment_model, mock_render_template, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        # Mock user
        mock_db.users.find_one.return_value = {
            "_id": ObjectId("60d21b4667d0d8992e610c85"),
            "username": "teacher",
            "identity": "teacher"
        }
        
        # Mock assignments
        mock_assignments = [
            {"_id": ObjectId(), "title": "Assignment 1"},
            {"_id": ObjectId(), "title": "Assignment 2"}
        ]
        mock_assignment_model.return_value.get_teacher_assignments.return_value = mock_assignments
        
        # Mock the render_template function to return a string
        mock_render_template.return_value = "Rendered Template"
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.get('/assignments')
        
        # Verify
        mock_render_template.assert_called_once()
        mock_assignment_model.return_value.get_teacher_assignments.assert_called_once()