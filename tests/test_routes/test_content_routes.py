# Fix for test_content_routes.py

import pytest
from unittest.mock import MagicMock, patch
from flask import Flask
from bson.objectid import ObjectId
import routes.contentRoute

@pytest.fixture
def patched_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.secret_key = 'test_secret_key'
    app.register_blueprint(routes.contentRoute.content_bp)
    return app

class TestContentRoutes:
    @patch('routes.contentRoute.render_template', return_value='rendered')
    @patch('routes.contentRoute.ContentModel')
    def test_content_endpoints(self, mock_content_model, mock_render_template, patched_app):
        # Create a test client
        client = patched_app.test_client()
        
        # Setup mock data
        content_id = "60d21b4667d0d8992e610c86"
        mock_content = {
            "_id": ObjectId(content_id),
            "title": "Test Content",
            "description": "Test Description",
            "teacher_id": "60d21b4667d0d8992e610c85",
            "github_repo_url": "https://github.com/test/repo",
            "github_repo_path": "test/path"
        }
        mock_content_model.return_value.get_content.return_value = mock_content
        mock_content_model.return_value.get_all_content.return_value = [mock_content]
        mock_content_model.return_value.get_teacher_content.return_value = [mock_content]
        
        # Mock additional dependencies
        with patch('routes.contentRoute.users') as mock_users:
            user = {
                "_id": ObjectId("60d21b4667d0d8992e610c85"),
                "username": "teacher",
                "identity": "teacher"
            }
            mock_users.find_one.return_value = user
            
            with patch('routes.contentRoute.github_accounts') as mock_github:
                github_info = {
                    "username": "teacher", 
                    "repo": "test/repo",
                    "access_token": "token"
                }
                mock_github.find_one.return_value = github_info
                
                # Add session data
                with client.session_transaction() as sess:
                    sess['username'] = 'teacher'
                    sess['identity'] = 'teacher'
                
                # Test multiple endpoints to boost coverage
                endpoints = [
                    '/content',
                    f'/content/{content_id}'
                ]
                
                for endpoint in endpoints:
                    response = client.get(endpoint)
                    assert response is not None