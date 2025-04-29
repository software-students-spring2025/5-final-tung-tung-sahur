# tests/test_routes/test_assignment_routes.py
import pytest
from unittest.mock import MagicMock, patch
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from routes.assignmentRoute import assignment_bp
from flask import Flask
from flask import jsonify

class TestAssignmentRoutes:
    @pytest.fixture
    def app(self):
        # Create a Flask app for testing
        app = Flask(__name__)
        app.register_blueprint(assignment_bp)
        app.secret_key = "test_secret_key"
        app.config['TESTING'] = True
        # Add this to resolve the 'home' endpoint BuildError
        @app.route('/home')
        def home():
            return "Home Page"
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
        
        # Mock the render_template function
        mock_render_template.return_value = "Rendered Template"
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.get('/assignments')
        
        # Verify template rendering
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "teacher_assignments.html" in args
        assert "assignments" in kwargs
        assert kwargs["assignments"] == mock_assignments
        
        # Verify model calls
        mock_assignment_model.return_value.get_teacher_assignments.assert_called_once()
    
    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.SubmissionModel')
    def test_show_assignments_student(self, mock_submission_model, mock_assignment_model, mock_render_template, client, mock_mongo):
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
                "due_date": (now + timedelta(days=7)).isoformat()  # Future date
            },
            {
                "_id": ObjectId(),
                "title": "Assignment 2",
                "due_date": (now - timedelta(days=7)).isoformat()  # Past date
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
        
        # Mock the render_template function
        mock_render_template.return_value = "Rendered Template"
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'student'
            sess['identity'] = 'student'
            
        response = client.get('/assignments')
        
        # Verify template rendering
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "student_assignments.html" in args
        assert "assignments" in kwargs
        assert "submissions" in kwargs
        
        # Verify model calls
        mock_assignment_model.return_value.get_all_assignments.assert_called_once()
        mock_submission_model.return_value.get_student_submissions.assert_called_once()
    
    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.github_accounts')
    def test_create_assignment_get(self, mock_github_accounts, mock_render_template, client):
        # Setup
        mock_github_accounts.find_one.return_value = {
            "username": "teacher",
            "repo": "teacher/repo",
            "access_token": "test_token"
        }
        
        # Mock the render_template function
        mock_render_template.return_value = "Rendered Template"
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.get('/assignments/create')
        
        # Verify template rendering
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "create_assignment.html" in args
        assert "github_info" in kwargs
    
    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.github_accounts')
    @patch('routes.assignmentRoute.send_mail')
    @patch('routes.assignmentRoute.url_for')
    def test_create_assignment_post(self, mock_url_for, mock_send_mail, mock_github_accounts, mock_users, mock_assignment_model, mock_redirect, client):
        # Setup
        # Mock url_for to avoid circular import issues
        mock_url_for.return_value = "/assignments"
        
        # Mock user
        mock_users.find_one.return_value = {
            "_id": ObjectId("60d21b4667d0d8992e610c85"),
            "username": "teacher",
            "identity": "teacher"
        }
        
        # Mock GitHub info
        mock_github_accounts.find_one.return_value = {
            "username": "teacher",
            "repo": "teacher/repo",
            "repo_url": "https://github.com/teacher/repo"
        }
        
        # Mock assignment creation
        mock_assignment_model.return_value.create_assignment.return_value = "new_assignment_id"
        
        # Mock students
        mock_users.find.return_value = [
            {"username": "student1", "email": "student1@example.com"},
            {"username": "student2", "email": "student2@example.com"}
        ]
        
        # Mock redirect
        mock_redirect.return_value = "Redirected"
        
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
        client.post('/assignments/create', data=form_data)
        
        # Verify model calls
        mock_assignment_model.return_value.create_assignment.assert_called_once()
        args, kwargs = mock_assignment_model.return_value.create_assignment.call_args
        assert kwargs["teacher_id"] == str(ObjectId("60d21b4667d0d8992e610c85"))
        assert kwargs["title"] == "Test Assignment"
        assert kwargs["description"] == "Test Description"
        assert "due_date" in kwargs
        assert kwargs["github_repo_path"] == "assignments/test"
        
        # Verify redirect
        mock_redirect.assert_called_once()
    
    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.SubmissionModel')
    @patch('routes.assignmentRoute.users')
    def test_view_assignment_teacher(self, mock_users, mock_submission_model, mock_assignment_model, mock_render_template, client):
        # Setup
        # Mock assignment
        assignment_id = "60d21b4667d0d8992e610c86"
        mock_assignment = {
            "_id": ObjectId(assignment_id),
            "title": "Test Assignment",
            "description": "Test Description",
            "teacher_id": "60d21b4667d0d8992e610c85"
        }
        mock_assignment_model.return_value.get_assignment.return_value = mock_assignment
        
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
        mock_users.find_one.side_effect = [
            # First call returns teacher info
            {"_id": ObjectId("60d21b4667d0d8992e610c85"), "username": "teacher", "identity": "teacher"},
            # Second call returns student info
            {"username": "student1"}
        ]
        
        # Mock the render_template function
        mock_render_template.return_value = "Rendered Template"
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.get(f'/assignments/{assignment_id}')
        
        # Verify model calls
        mock_assignment_model.return_value.get_assignment.assert_called_once_with(assignment_id)
        mock_submission_model.return_value.get_assignment_submissions.assert_called_once_with(assignment_id)
        
        # Verify template rendering
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "teacher_assignment_detail.html" in args
        assert "assignment" in kwargs
        assert "submissions" in kwargs

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.SubmissionModel')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.github_accounts')
    def test_view_assignment_student(self, mock_github_accounts, mock_users, mock_submission_model, mock_assignment_model, mock_render_template, client):
        # Setup
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
        mock_users.find_one.return_value = {
            "_id": ObjectId("60d21b4667d0d8992e610c87"),
            "username": "student",
            "identity": "student"
        }
        
        # Mock submission
        mock_submission = {
            "_id": ObjectId(),
            "student_id": "60d21b4667d0d8992e610c87",
            "assignment_id": assignment_id,
            "github_link": "https://github.com/student/repo",
            "status": "submitted"
        }
        mock_submission_model.return_value.get_student_assignment_submission.return_value = mock_submission
        
        # Mock GitHub info
        mock_github_accounts.find_one.return_value = {
            "username": "student",
            "repo": "student/repo",
            "repo_url": "https://github.com/student/repo"
        }
        
        # Mock the render_template function
        mock_render_template.return_value = "Rendered Template"
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'student'
            sess['identity'] = 'student'
            
        response = client.get(f'/assignments/{assignment_id}')
        
        # Verify model calls
        mock_assignment_model.return_value.get_assignment.assert_called_once_with(assignment_id)
        mock_submission_model.return_value.get_student_assignment_submission.assert_called_once()
        
        # Verify template rendering
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "student_assignment_detail.html" in args
        assert "assignment" in kwargs
        assert "submission" in kwargs
        assert "github_info" in kwargs

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.SubmissionModel')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.url_for')
    def test_submit_assignment(self, mock_url_for, mock_users, mock_submission_model, mock_redirect, client):
        # Setup
        assignment_id = "60d21b4667d0d8992e610c86"
        
        # Mock url_for to avoid circular import issues
        mock_url_for.side_effect = lambda endpoint, **kwargs: f"/{endpoint}/{kwargs.get('assignment_id', '')}"
        
        # Mock user
        mock_users.find_one.return_value = {
            "_id": ObjectId("60d21b4667d0d8992e610c87"),
            "username": "student",
            "identity": "student"
        }
        
        # Mock submission check (no existing submission)
        mock_submission_model.return_value.get_student_assignment_submission.return_value = None
        
        # Mock submission creation
        mock_submission_model.return_value.create_submission.return_value = "submission_id"
        
        # Mock redirect
        mock_redirect.return_value = "Redirected"
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'student'
            sess['identity'] = 'student'
            
        form_data = {
            "github_link": "https://github.com/student/repo",
            "readme_content": "This is my submission"
        }
        client.post(f'/assignments/{assignment_id}/submit', data=form_data)
        
        # Verify model calls
        mock_submission_model.return_value.get_student_assignment_submission.assert_called_once()
        mock_submission_model.return_value.create_submission.assert_called_once()
        
        # Verify submission creation arguments
        args, kwargs = mock_submission_model.return_value.create_submission.call_args
        assert kwargs["student_id"] == str(ObjectId("60d21b4667d0d8992e610c87"))
        assert kwargs["assignment_id"] == assignment_id
        assert kwargs["github_link"] == "https://github.com/student/repo"
        assert kwargs["readme_content"] == "This is my submission"
        
        # Verify redirect
        mock_redirect.assert_called_once()

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.SubmissionModel')
    @patch('routes.assignmentRoute.url_for')
    def test_grade_submission(self, mock_url_for, mock_submission_model, mock_redirect, client):
        # Setup
        submission_id = "60d21b4667d0d8992e610c89"
        
        # Mock url_for to avoid circular import issues
        mock_url_for.return_value = "/assignment.view_assignment/60d21b4667d0d8992e610c86"
        
        # Mock submission
        mock_submission = {
            "_id": ObjectId(submission_id),
            "assignment_id": "60d21b4667d0d8992e610c86"
        }
        mock_submission_model.return_value.get_submission.return_value = mock_submission
        
        # Mock feedback addition
        mock_submission_model.return_value.add_feedback.return_value = True
        
        # Mock redirect
        mock_redirect.return_value = "Redirected"
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        form_data = {
            "grade": "95.5",
            "feedback": "Great work!"
        }
        client.post(f'/submissions/{submission_id}/grade', data=form_data)
        
        # Verify model calls
        mock_submission_model.return_value.get_submission.assert_called_once_with(submission_id)
        mock_submission_model.return_value.add_feedback.assert_called_once()
        args, kwargs = mock_submission_model.return_value.add_feedback.call_args
        assert args[0] == submission_id
        assert float(args[1]) == 95.5
        assert args[2] == "Great work!"
        
        # Verify redirect
        mock_redirect.assert_called_once()

    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.SubmissionModel')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.url_for')
    def test_delete_assignment(self, mock_url_for, mock_redirect, mock_users, mock_submission_model, mock_assignment_model, client):
        # Setup
        assignment_id = "60d21b4667d0d8992e610c86"
        
        # Mock url_for to avoid circular import issues
        mock_url_for.return_value = "/assignment.show_assignments"
        
        # Mock assignment
        mock_assignment = {
            "_id": ObjectId(assignment_id),
            "teacher_id": "60d21b4667d0d8992e610c85",
            "title": "Test Assignment"
        }
        mock_assignment_model.return_value.get_assignment.return_value = mock_assignment
        
        # Mock user
        mock_users.find_one.return_value = {
            "_id": ObjectId("60d21b4667d0d8992e610c85"),
            "username": "teacher",
            "identity": "teacher"
        }
        
        # Mock submission deletion
        mock_submission_model.return_value.delete_by_assignment.return_value = 2
        
        # Mock assignment deletion
        mock_assignment_model.return_value.delete_assignment.return_value = True
        
        # Mock redirect
        mock_redirect.return_value = "Redirected"
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.post(f'/assignments/{assignment_id}/delete')
        
        # Verify model calls
        mock_assignment_model.return_value.get_assignment.assert_called_once_with(assignment_id)
        mock_submission_model.return_value.delete_by_assignment.assert_called_once_with(assignment_id)
        mock_assignment_model.return_value.delete_assignment.assert_called_once_with(assignment_id)
        
        # Verify redirect
        mock_redirect.assert_called_once()

    @patch('routes.assignmentRoute.send_file')
    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.github_accounts')
    @patch('routes.assignmentRoute.is_repo_path_file')
    @patch('routes.assignmentRoute.get_repo_contents')
    @patch('routes.assignmentRoute.zipfile.ZipFile')
    @patch('routes.assignmentRoute.BytesIO')
    def test_download_assignment(self, mock_bytesio, mock_zipfile, mock_get_contents, mock_is_direct_file, 
                                mock_github_accounts, mock_users, mock_assignment_model, mock_send_file, client):
        # Setup
        assignment_id = "60d21b4667d0d8992e610c86"
        
        # Mock assignment
        mock_assignment = {
            "_id": ObjectId(assignment_id),
            "teacher_id": "60d21b4667d0d8992e610c85",
            "title": "Test Assignment",
            "github_repo_url": "https://github.com/teacher/repo",
            "github_repo_path": "assignments/test"
        }
        mock_assignment_model.return_value.get_assignment.return_value = mock_assignment
        
        # Mock teacher
        mock_users.find_one.return_value = {
            "_id": ObjectId("60d21b4667d0d8992e610c85"),
            "username": "teacher"
        }
        
        # Mock GitHub info
        mock_github_accounts.find_one.return_value = {
            "username": "teacher",
            "repo": "teacher/repo",
            "access_token": "test_token"
        }
        
        # Mock direct file check (not a direct file)
        mock_is_direct_file.return_value = False
        
        # Mock get repo contents
        mock_get_contents.return_value = []
        
        # Mock BytesIO
        mock_memory_file = MagicMock()
        mock_bytesio.return_value = mock_memory_file
        
        # Mock send_file
        mock_send_file.return_value = "File Sent"
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'student'
            sess['identity'] = 'student'
            
        response = client.get(f'/assignments/{assignment_id}/download')
        
        # Verify model calls
        mock_assignment_model.return_value.get_assignment.assert_called_once_with(assignment_id)
        mock_users.find_one.assert_called_once()
        mock_github_accounts.find_one.assert_called_once()
        mock_is_direct_file.assert_called_once()
        mock_send_file.assert_called_once()

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.SubmissionModel')
    def test_view_readme(self, mock_submission_model, mock_render_template, client):
        # Setup
        submission_id = "60d21b4667d0d8992e610c89"
        
        # Mock submission
        mock_submission = {
            "_id": ObjectId(submission_id),
            "student_id": "60d21b4667d0d8992e610c87",
            "assignment_id": "60d21b4667d0d8992e610c86",
            "readme_content": "# My Submission\nThis is my homework.",
            "status": "submitted"
        }
        mock_submission_model.return_value.get_submission.return_value = mock_submission
        
        # Mock template rendering
        mock_render_template.return_value = "Rendered Template"
        
        # Execute teacher view
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.get(f'/submissions/{submission_id}/readme')
        
        # Verify model calls
        mock_submission_model.return_value.get_submission.assert_called_once_with(submission_id)
        
        # Verify template rendering
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "view_readme.html" in args
        assert "readme_content" in kwargs
        assert "submission" in kwargs
        assert kwargs["readme_content"] == "# My Submission\nThis is my homework."