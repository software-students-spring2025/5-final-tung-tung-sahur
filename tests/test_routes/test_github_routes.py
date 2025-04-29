import pytest
from unittest.mock import patch, MagicMock
from bson.objectid import ObjectId
from routes.githubRoute import github_bp, get_repo_contents, is_repo_path_file, list_repo_files_recursive
from flask import Flask, session


class TestGitHubRoutes:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.register_blueprint(github_bp)
        app.secret_key = "test_secret_key"
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("routes.githubRoute.redirect")
    @patch("routes.githubRoute.client_id")
    def test_github_link(self, mock_client_id, mock_redirect, client):
        # Setup
        mock_client_id.return_value = "fake_client_id"
        mock_redirect.return_value = "REDIRECT"

        # Execute
        response = client.get("/github/link")

        # Assert
        mock_redirect.assert_called_once()
        assert mock_redirect.call_args[0][0].startswith("https://github.com/login/oauth/authorize")

    @patch("routes.githubRoute.requests")
    @patch("routes.githubRoute.redirect")
    @patch("routes.githubRoute.client_id")
    @patch("routes.githubRoute.client_secret")
    @patch("routes.githubRoute.github_accounts")
    def test_github_callback(self, mock_accounts, mock_secret, mock_id, mock_redirect, mock_requests, client):
        # Setup
        mock_id.return_value = "fake_id"
        mock_secret.return_value = "fake_secret"
        
        # Mock token response
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {"access_token": "fake_token"}
        
        # Mock user response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "githubuser",
            "name": "Test User",
            "avatar_url": "https://github.com/avatar.png"
        }
        
        mock_requests.post.return_value = mock_token_response
        mock_requests.get.return_value = mock_user_response
        
        mock_redirect.return_value = "REDIRECT"
        
        # Mock session
        with client.session_transaction() as sess:
            sess["username"] = "testuser"

        # Mock database operations
        mock_accounts.find_one.return_value = None
        
        # Execute
        response = client.get("/github/callback?code=12345")
        
        # Assert
        mock_requests.post.assert_called_once()
        mock_requests.get.assert_called_once()
        mock_accounts.replace_one.assert_called_once()
        mock_redirect.assert_called_once()

    @patch("routes.githubRoute.requests.get")
    def test_get_repo_contents(self, mock_get):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"name": "file1.py", "type": "file"}]
        mock_get.return_value = mock_response
        
        # Execute
        result = get_repo_contents("owner", "repo", "token", "path")
        
        # Assert
        assert result == [{"name": "file1.py", "type": "file"}]
        mock_get.assert_called_once()

    @patch("routes.githubRoute.get_repo_contents")
    def test_is_repo_path_file(self, mock_get_contents):
        # Test when path is a file
        mock_get_contents.return_value = {"type": "file", "name": "file.py"}
        result = is_repo_path_file("owner", "repo", "token", "path/file.py")
        assert result is True
        
        # Test when path is a directory
        mock_get_contents.return_value = [{"type": "dir", "name": "dir"}]
        result = is_repo_path_file("owner", "repo", "token", "path/dir")
        assert result is False

    @patch("routes.githubRoute.get_repo_contents")
    def test_list_repo_files_recursive(self, mock_get_contents):
        # Test with a file
        mock_get_contents.return_value = {
            "name": "file.py", 
            "type": "file", 
            "path": "file.py",
            "download_url": "https://github.com/download/file.py"
        }
        
        result = list_repo_files_recursive("owner", "repo", "token", "file.py")
        assert len(result) == 1
        assert result[0]["name"] == "file.py"
        
        # Test with a directory containing a file
        mock_get_contents.side_effect = [
            [
                {
                    "name": "dir", 
                    "type": "dir", 
                    "path": "dir"
                }
            ],
            [
                {
                    "name": "nested.py", 
                    "type": "file", 
                    "path": "dir/nested.py",
                    "download_url": "https://github.com/download/dir/nested.py"
                }
            ]
        ]
        
        result = list_repo_files_recursive("owner", "repo", "token")
        assert len(result) == 1
        assert result[0]["name"] == "nested.py"