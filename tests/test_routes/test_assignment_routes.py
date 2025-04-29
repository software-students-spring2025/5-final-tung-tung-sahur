import pytest
from unittest.mock import MagicMock, patch
from bson.objectid import ObjectId
from datetime import datetime
from routes.assignmentRoute import assignment_bp
from flask import Flask, session

class TestAssignmentRoutes:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.register_blueprint(assignment_bp)
        app.secret_key = "test_secret_key"
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        with app.test_client() as client:
            yield client
    
    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.SubmissionModel')
    def test_show_assignments_teacher(self, mock_submission_model, mock_assignment_model, client, mock_mongo):
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
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.get('/assignments')
        
        # Verify
        assert response.status_code == 200
        assert b"Assignment 1" in response.data
        assert b"Assignment 2" in response.data
        
        # Verify calls
        mock_db.users.find_one.assert_called_once_with({"username": "teacher"})
        mock_assignment_model.return_value.get_teacher_assignments.assert_called_once()
    
    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.SubmissionModel')
    def test_show_assignments_student(self, mock_submission_model, mock_assignment_model, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        # Mock user
        mock_db.users.find_one.return_value = {
            "_id": ObjectId("60d21b4667d0d8992e610c85"),
            "username": "student",
            "identity": "student"
        }
        
        # Mock assignments with due dates
        now = datetime.now()
        mock_assignments = [
            {
                "_id": ObjectId(),
                "title": "Assignment 1",
                "due_date": (now.replace(year=now.year + 1)).isoformat()  # Future date
            },
            {
                "_id": ObjectId(),
                "title": "Assignment 2",
                "due_date": (now.replace(year=now.year - 1)).isoformat()  # Past date
            }
        ]
        mock_assignment_model.return_value.get_all_assignments.return_value = mock_assignments
        
        # Mock submissions
        mock_submissions = [
            {
                "assignment_id": str(mock_assignments[0]["_id"]),
                "status": "submitted"
            }
        ]
        mock_submission_model.return_value.get_student_submissions.return_value = mock_submissions
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'student'
            sess['identity'] = 'student'
            
        response = client.get('/assignments')
        
        # Verify
        assert response.status_code == 200
        assert b"Assignment 1" in response.data
        assert b"Assignment 2" in response.data
        
        # Verify calls
        mock_db.users.find_one.assert_called_once_with({"username": "student"})
        mock_assignment_model.return_value.get_all_assignments.assert_called_once()
        mock_submission_model.return_value.get_student_submissions.assert_called_once()
    
    @patch('routes.assignmentRoute.AssignmentModel')
    def test_create_assignment_get(self, mock_assignment_model, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        # Mock GitHub info
        mock_db.github_accounts.find_one.return_value = {
            "username": "teacher",
            "repo": "teacher/repo",
            "access_token": "test_token"
        }
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.get('/assignments/create')
        
        # Verify
        assert response.status_code == 200
        assert b"Create new assignment" in response.data
        
        # Verify calls
        mock_db.github_accounts.find_one.assert_called_once_with({"username": "teacher"})
    
    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.send_mail')
    def test_create_assignment_post(self, mock_send_mail, mock_assignment_model, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        # Mock user
        mock_db.users.find_one.return_value = {
            "_id": ObjectId("60d21b4667d0d8992e610c85"),
            "username": "teacher",
            "identity": "teacher"
        }
        
        # Mock GitHub info
        mock_db.github_accounts.find_one.return_value = {
            "username": "teacher",
            "repo": "teacher/repo",
            "repo_url": "https://github.com/teacher/repo"
        }
        
        # Mock assignment creation
        mock_assignment_model.return_value.create_assignment.return_value = "new_assignment_id"
        
        # Mock students
        mock_db.users.find.return_value = [
            {"username": "student1", "email": "student1@example.com"},
            {"username": "student2", "email": "student2@example.com"}
        ]
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        form_data = {
            "title": "Test Assignment",
            "description": "Test Description",
            "due_date": "2025-05-01",
            "due_time": "23:59",
            "github_repo_path": "assignments/test"
        }
        response = client.post('/assignments/create', data=form_data)
        
        # Verify
        assert response.status_code == 302
        assert response.location == "/assignments"
        
        # Verify database calls
        mock_db.users.find_one.assert_called_once_with({"username": "teacher"})
        mock_db.github_accounts.find_one.assert_called_once_with({"username": "teacher"})
        mock_assignment_model.return_value.create_assignment.assert_called_once()
        
        # Verify email sending
        assert mock_send_mail.call_count == 2  # One for each student
    
    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.SubmissionModel')
    def test_view_assignment_teacher(self, mock_submission_model, mock_assignment_model, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        # Mock assignment
        assignment_id = "60d21b4667d0d8992e610c86"
        mock_assignment = {
            "_id": ObjectId(assignment_id),
            "title": "Test Assignment",
            "description": "Test Description",
            "teacher_id": "60d21b4667d0d8992e610c85"
        }
        mock_assignment_model.return_value.get_assignment.return_value = mock_assignment
        
        # Mock user
        mock_db.users.find_one.return_value = {
            "_id": ObjectId("60d21b4667d0d8992e610c85"),
            "username": "teacher",
            "identity": "teacher"
        }
        
        # Mock submissions
        mock_submissions = [
            {
                "_id": ObjectId(),
                "student_id": "60d21b4667d0d8992e610c87",
                "status": "submitted"
            }
        ]
        mock_submission_model.return_value.get_assignment_submissions.return_value = mock_submissions
        
        # Mock student username lookup
        student = {"username": "student1"}
        mock_db.users.find_one.side_effect = [
            # First call is for the teacher
            {"_id": ObjectId("60d21b4667d0d8992e610c85"), "username": "teacher", "identity": "teacher"},
            # Second call is for the student
            student
        ]
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.get(f'/assignments/{assignment_id}')
        
        # Verify
        assert response.status_code == 200
        assert b"Test Assignment" in response.data
        assert b"student1" in response.data
        
        # Verify calls
        mock_assignment_model.return_value.get_assignment.assert_called_once_with(assignment_id)
        mock_submission_model.return_value.get_assignment_submissions.assert_called_once_with(assignment_id)