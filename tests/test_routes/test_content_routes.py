import pytest
from unittest.mock import MagicMock, patch
from bson.objectid import ObjectId
from routes.contentRoute import content_bp
from flask import Flask, session

class TestContentRoutes:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.register_blueprint(content_bp)
        app.secret_key = "test_secret_key"
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        with app.test_client() as client:
            yield client
    
    @patch('routes.contentRoute.ContentModel')
    def test_show_content_teacher(self, mock_content_model, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        # Mock user
        mock_db.users.find_one.return_value = {
            "_id": ObjectId("60d21b4667d0d8992e610c85"),
            "username": "teacher",
            "identity": "teacher"
        }
        
        # Mock content items
        mock_content_items = [
            {"_id": ObjectId(), "title": "Lecture 1"},
            {"_id": ObjectId(), "title": "Lecture 2"}
        ]
        mock_content_model.return_value.get_teacher_content.return_value = mock_content_items
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.get('/content')
        
        # Verify
        assert response.status_code == 404
        assert b"Lecture 1" in response.data
        assert b"Lecture 2" in response.data
        
        # Verify calls
        mock_db.users.find_one.assert_called_once_with({"username": "teacher"})
        mock_content_model.return_value.get_teacher_content.assert_called_once()
    
    @patch('routes.contentRoute.ContentModel')
    def test_show_content_student(self, mock_content_model, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        # Mock content items
        mock_content_items = [
            {"_id": ObjectId(), "title": "Lecture 1"},
            {"_id": ObjectId(), "title": "Lecture 2"}
        ]
        mock_content_model.return_value.get_all_content.return_value = mock_content_items
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'student'
            sess['identity'] = 'student'
            
        response = client.get('/content')
        
        # Verify
        assert response.status_code == 200
        assert b"Lecture 1" in response.data
        assert b"Lecture 2" in response.data
        
        # Verify calls
        mock_content_model.return_value.get_all_content.assert_called_once()
    
    @patch('routes.contentRoute.ContentModel')
    def test_create_content_get(self, mock_content_model, client, mock_mongo):
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
            
        response = client.get('/content/create')
        
        # Verify
        assert response.status_code == 200
        assert b"Create new lecture material" in response.data
        
        # Verify calls
        mock_db.github_accounts.find_one.assert_called_once_with({"username": "teacher"})
    
    @patch('routes.contentRoute.ContentModel')
    def test_create_content_post(self, mock_content_model, client, mock_mongo):
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
        
        # Mock content creation
        mock_content_model.return_value.create_content.return_value = "new_content_id"
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        form_data = {
            "title": "Test Content",
            "description": "Test Description",
            "github_repo_path": "lectures/test"
        }
        response = client.post('/content/create', data=form_data)
        
        # Verify
        assert response.status_code == 404
        assert response.location == "/content"
        
        # Verify database calls
        mock_db.users.find_one.assert_called_once_with({"username": "teacher"})
        mock_db.github_accounts.find_one.assert_called_once_with({"username": "teacher"})
        mock_content_model.return_value.create_content.assert_called_once()
        
        # Verify create_content call arguments
        call_args = mock_content_model.return_value.create_content.call_args[1]
        assert call_args["teacher_id"] == str(ObjectId("60d21b4667d0d8992e610c85"))
        assert call_args["title"] == "Test Content"
        assert call_args["description"] == "Test Description"
        assert "github_repo_url" in call_args
        assert call_args["github_repo_path"] == "lectures/test"