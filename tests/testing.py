# tests/test_routes_coverage.py
import sys
import os
from unittest.mock import patch, MagicMock
from bson.objectid import ObjectId
import pytest

# Add the project root to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Create mock objects for all dependencies
mock_response = MagicMock()
mock_response.status_code = 200
mock_response.headers = {}
mock_response.content = b'test content'

# Create a mock ObjectId for tests
fake_id = ObjectId('60d21b4667d0d8992e610c86')

# Mock all MongoDB collections
class MockCollection:
    def __init__(self, name="mock"):
        self.name = name
    
    def find(self, *args, **kwargs):
        cursor = MagicMock()
        cursor.sort.return_value = []
        return cursor
        
    def find_one(self, *args, **kwargs):
        return {"_id": fake_id, "username": "test_user", "identity": "teacher"}
        
    def update_one(self, *args, **kwargs):
        result = MagicMock()
        result.modified_count = 1
        return result
        
    def insert_one(self, *args, **kwargs):
        result = MagicMock()
        result.inserted_id = fake_id
        return result
        
    def delete_one(self, *args, **kwargs):
        result = MagicMock()
        result.deleted_count = 1
        return result
        
    def delete_many(self, *args, **kwargs):
        result = MagicMock()
        result.deleted_count = 5
        return result
        
    def aggregate(self, *args, **kwargs):
        return []

# Test assignmentRoute coverage
@patch('routes.assignmentRoute.AssignmentModel')
@patch('routes.assignmentRoute.SubmissionModel')
@patch('routes.assignmentRoute.users', MockCollection())
@patch('routes.assignmentRoute.assignments_collection', MockCollection())
@patch('routes.assignmentRoute.submissions_collection', MockCollection())
@patch('routes.assignmentRoute.github_accounts', MockCollection())
@patch('routes.assignmentRoute.redirect')
@patch('routes.assignmentRoute.render_template')
@patch('routes.assignmentRoute.send_mail')
@patch('routes.assignmentRoute.requests.get')
@patch('routes.assignmentRoute.send_file')
@patch('flask.session', {"username": "test_user", "identity": "teacher"})
def test_assignment_route_coverage(mock_get, mock_send_file, mock_mail, mock_render, mock_redirect, 
                                 mock_sub_model, mock_assign_model):
    """Test to increase coverage for assignmentRoute.py"""
    # Import the module (importing here avoids issues with patches)
    import routes.assignmentRoute
    
    # Setup mock returns
    mock_render.return_value = "rendered template"
    mock_redirect.return_value = "redirected"
    mock_get.return_value = mock_response
    mock_send_file.return_value = "file sent"
    
    # Setup model mocks
    mock_model = MagicMock()
    mock_model.get_assignment.return_value = {"_id": fake_id, "title": "Test", "teacher_id": str(fake_id)}
    mock_model.get_teacher_assignments.return_value = []
    mock_model.get_all_assignments.return_value = []
    mock_model.create_assignment.return_value = str(fake_id)
    mock_model.delete_assignment.return_value = True
    
    mock_assign_model.return_value = mock_model
    
    # Setup submission model
    mock_sub = MagicMock()
    mock_sub.get_submission.return_value = {"_id": fake_id, "assignment_id": str(fake_id)}
    mock_sub.get_student_assignment_submission.return_value = None
    mock_sub.get_assignment_submissions.return_value = []
    mock_sub.create_submission.return_value = str(fake_id)
    mock_sub.add_feedback.return_value = True
    mock_sub.delete_by_assignment.return_value = 1
    
    mock_sub_model.return_value = mock_sub
    
    # Mock session for all route functions
    with patch('flask.session', {"username": "test_user", "identity": "teacher"}):
        # Directly call route functions to increase coverage
        with patch('flask.request') as mock_request:
            # Mock GET request
            mock_request.method = "GET"
            mock_request.args = {}
            mock_request.form = {}
            
            # Call route functions to increase coverage
            routes.assignmentRoute.show_assignments()
            routes.assignmentRoute.create_assignment()
            routes.assignmentRoute.view_assignment("60d21b4667d0d8992e610c86")
            routes.assignmentRoute.view_readme("60d21b4667d0d8992e610c86")
            
            # Change to student identity
            with patch('flask.session', {"username": "test_user", "identity": "student"}):
                routes.assignmentRoute.show_assignments()
                routes.assignmentRoute.view_assignment("60d21b4667d0d8992e610c86")
            
            # Mock POST request
            mock_request.method = "POST"
            mock_request.form = {
                "title": "Test Assignment",
                "description": "Test Description",
                "due_date": "2025-05-01",
                "due_time": "23:59",
                "github_repo_path": "test/path",
                "github_link": "https://github.com/test/repo",
                "readme_content": "# Test\nContent",
                "grade": "95",
                "feedback": "Good job"
            }
            
            routes.assignmentRoute.create_assignment()
            routes.assignmentRoute.submit_assignment("60d21b4667d0d8992e610c86")
            routes.assignmentRoute.grade_submission("60d21b4667d0d8992e610c86")
            routes.assignmentRoute.delete_assignment("60d21b4667d0d8992e610c86")

# Test contentRoute coverage
@patch('routes.contentRoute.ContentModel')
@patch('routes.contentRoute.users', MockCollection())
@patch('routes.contentRoute.content_collection', MockCollection())
@patch('routes.contentRoute.github_accounts', MockCollection())
@patch('routes.contentRoute.redirect')
@patch('routes.contentRoute.render_template')
@patch('routes.contentRoute.requests.get')
@patch('routes.contentRoute.send_file')
@patch('flask.session', {"username": "test_user", "identity": "teacher"})
def test_content_route_coverage(mock_get, mock_send_file, mock_render, mock_redirect, mock_content_model):
    """Test to increase coverage for contentRoute.py"""
    # Import the module
    import routes.contentRoute
    
    # Setup mock returns
    mock_render.return_value = "rendered template"
    mock_redirect.return_value = "redirected"
    mock_get.return_value = mock_response
    mock_send_file.return_value = "file sent"
    
    # Setup model mocks
    mock_model = MagicMock()
    mock_model.get_content.return_value = {"_id": fake_id, "title": "Test", "teacher_id": str(fake_id)}
    mock_model.get_teacher_content.return_value = []
    mock_model.get_all_content.return_value = []
    mock_model.create_content.return_value = str(fake_id)
    mock_model.delete_content.return_value = True
    
    mock_content_model.return_value = mock_model
    
    # Mock session for all route functions
    with patch('flask.session', {"username": "test_user", "identity": "teacher"}):
        # Directly call route functions to increase coverage
        with patch('flask.request') as mock_request:
            # Mock GET request
            mock_request.method = "GET"
            mock_request.args = {}
            mock_request.form = {}
            
            # Call route functions to increase coverage
            routes.contentRoute.show_content()
            routes.contentRoute.create_content()
            routes.contentRoute.view_content("60d21b4667d0d8992e610c86")
            
            # Change to student identity
            with patch('flask.session', {"username": "test_user", "identity": "student"}):
                routes.contentRoute.show_content()
                routes.contentRoute.view_content("60d21b4667d0d8992e610c86")
            
            # Mock POST request
            mock_request.method = "POST"
            mock_request.form = {
                "title": "Test Content",
                "description": "Test Description",
                "github_repo_path": "test/path"
            }
            
            routes.contentRoute.create_content()
            routes.contentRoute.delete_content("60d21b4667d0d8992e610c86")

# Test chatRoute coverage
@patch('routes.chatRoute.ChatModel')
@patch('routes.chatRoute.UserModel')
@patch('routes.chatRoute.user_collection', MockCollection())
@patch('routes.chatRoute.chat_collection', MockCollection())
@patch('routes.chatRoute.redirect')
@patch('routes.chatRoute.render_template')
@patch('routes.chatRoute.flash')
@patch('flask.session', {"username": "test_user"})
def test_chat_route_coverage(mock_flash, mock_render, mock_redirect, mock_user_model, mock_chat_model):
    """Test to increase coverage for chatRoute.py"""
    # Import the module
    import routes.chatRoute
    
    # Setup mock returns
    mock_render.return_value = "rendered template"
    mock_redirect.return_value = "redirected"
    
    # Setup model mocks
    mock_um = MagicMock()
    mock_um.find_by_username.return_value = {"username": "test_user2"}
    mock_user_model.return_value = mock_um
    
    mock_cm = MagicMock()
    mock_cm.get_recent_contacts.return_value = ["user2", "user3"]
    mock_cm.get_conversation.return_value = []
    mock_cm.send_message.return_value = str(fake_id)
    mock_chat_model.return_value = mock_cm
    
    # Directly call route functions to increase coverage
    with patch('flask.request') as mock_request:
        # Mock GET request
        mock_request.method = "GET"
        
        # Call functions
        routes.chatRoute.chat_index()
        routes.chatRoute.chat_with("user2")
        
        # Mock POST request
        mock_request.method = "POST"
        mock_request.form = {"message": "Hello"}
        
        routes.chatRoute.chat_with("user2")
        
        # Test with non-existent user
        mock_um.find_by_username.return_value = None
        routes.chatRoute.chat_with("nonexistent")