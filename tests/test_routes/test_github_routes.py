import pytest
from unittest.mock import MagicMock, patch
import json
import requests
from routes.githubRoute import github_bp
from flask import Flask, session

class TestGitHubRoutes:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.register_blueprint(github_bp)
        app.secret_key = "test_secret_key"
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        with app.test_client() as client:
            yield client
    
    @patch('routes.githubRoute.requests')
    @patch('routes.githubRoute.os')
    def test_github_link(self, mock_os, mock_requests, client):
        # Setup
        mock_os.getenv.return_value = "test_client_id"
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            
        response = client.get('/github/link')
        
        # Verify
        assert response.status_code == 302
        assert "github.com/login/oauth/authorize" in response.location
        assert "test_client_id" in response.location
    
    @patch('routes.githubRoute.requests.post')
    @patch('routes.githubRoute.requests.get')
    @patch('routes.githubRoute.os')
    def test_github_callback_success(self, mock_os, mock_get, mock_post, client, mock_mongo):
        # Setup mocks
        mock_client, mock_db = mock_mongo
        
        mock_os.getenv.side_effect = lambda key, default=None: {
            "GITHUB_CLIENT_ID": "test_client_id",
            "GITHUB_CLIENT_SECRET": "test_client_secret",
            "MONGO_URI": "test_mongo_uri"
        }.get(key, default)
        
        mock_post.return_value = MagicMock(
            json=MagicMock(return_value={"access_token": "test_access_token"})
        )
        
        mock_get.return_value = MagicMock(
            json=MagicMock(return_value={
                "id": 12345,
                "login": "githubuser",
                "name": "GitHub User",
                "avatar_url": "https://github.com/avatar.png"
            })
        )
        
        # Mock MongoDB
        mock_db.users.find_one.return_value = {"_id": "user_id", "username": "testuser"}
        mock_db.github_accounts.find_one.return_value = None
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            
        response = client.get('/github/callback?code=test_code')
        
        # Verify
        assert response.status_code == 302
        assert response.location == "/home"
        
        # Verify API calls
        mock_post.assert_called_once()
        mock_get.assert_called_once()
        
        # Verify database operations
        mock_db.github_accounts.replace_one.assert_called_once()
        
    @patch('routes.githubRoute.requests.get')
    def test_github_repo_link(self, mock_get, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        mock_db.github_accounts.find_one.return_value = {
            "username": "testuser",
            "access_token": "test_token"
        }
        
        # Mock repos response
        mock_get.return_value = MagicMock(
            json=MagicMock(return_value=[
                {"name": "repo1", "full_name": "user/repo1", "description": "Test Repo 1"},
                {"name": "repo2", "full_name": "user/repo2", "description": "Test Repo 2"}
            ])
        )
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            sess['identity'] = 'student'
            
        response = client.get('/github/repo/link')
        
        # Verify
        assert response.status_code == 200
        assert b"Select Repository" in response.data
        assert b"user/repo1" in response.data
        assert b"user/repo2" in response.data
        
        # Verify API call
        mock_get.assert_called_once()
        
    def test_github_repo_files(self, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        # Mock data
        mock_db.github_accounts.find_one.return_value = {
            "username": "testuser",
            "access_token": "test_token",
            "repo": "user/repo"
        }
        
        # Patch the list_repo_files_recursive function
        with patch('routes.githubRoute.list_repo_files_recursive') as mock_list_files:
            mock_list_files.return_value = [
                {"name": "file1.py", "path": "file1.py", "download_url": "https://github.com/file1.py"},
                {"name": "file2.py", "path": "file2.py", "download_url": "https://github.com/file2.py"}
            ]
            
            # Execute
            with client.session_transaction() as sess:
                sess['username'] = 'testuser'
                sess['identity'] = 'student'
                
            response = client.get('/github/repo/files')
            
            # Verify
            assert response.status_code == 200
            assert b"file1.py" in response.data
            assert b"file2.py" in response.data
            
            # Verify function call
            mock_list_files.assert_called_once()