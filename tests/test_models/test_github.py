import pytest
from bson.objectid import ObjectId
from unittest.mock import MagicMock
from models.github import GitHubModel


class TestGitHubModel:
    @pytest.fixture
    def mock_collection(self):
        return MagicMock()

    @pytest.fixture
    def github_model(self, mock_collection):
        return GitHubModel(mock_collection)

    def test_bind_account_success(self, github_model, mock_collection):
        # Setup
        user_id = "60d21b4667d0d8992e610c85"
        github_id = 12345
        github_username = "githubuser"
        mock_collection.update_one.return_value = MagicMock(modified_count=1)

        # Execute
        result = github_model.bind_account(user_id, github_id, github_username)

        # Verify
        assert result is True
        mock_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(user_id)},
            {"$set": {"github": {"id": github_id, "username": github_username}}},
        )

    def test_bind_account_failure(self, github_model, mock_collection):
        # Setup
        user_id = "60d21b4667d0d8992e610c85"
        github_id = 12345
        github_username = "githubuser"
        mock_collection.update_one.return_value = MagicMock(modified_count=0)

        # Execute
        result = github_model.bind_account(user_id, github_id, github_username)

        # Verify
        assert result is False
        mock_collection.update_one.assert_called_once()

    def test_get_github_info_found(self, github_model, mock_collection):
        # Setup
        user_id = "60d21b4667d0d8992e610c85"
        expected_github_info = {"id": 12345, "username": "githubuser"}
        mock_collection.find_one.return_value = {"github": expected_github_info}

        # Execute
        result = github_model.get_github_info(user_id)

        # Verify
        assert result == expected_github_info
        mock_collection.find_one.assert_called_once_with({"_id": ObjectId(user_id)})

    def test_get_github_info_no_github(self, github_model, mock_collection):
        # Setup
        user_id = "60d21b4667d0d8992e610c85"
        mock_collection.find_one.return_value = {
            "username": "testuser"
        }  # No github field

        # Execute
        result = github_model.get_github_info(user_id)

        # Verify
        assert result is None
        mock_collection.find_one.assert_called_once_with({"_id": ObjectId(user_id)})

    def test_get_github_info_user_not_found(self, github_model, mock_collection):
        # Setup
        user_id = "60d21b4667d0d8992e610c85"
        mock_collection.find_one.return_value = None

        # Execute
        result = github_model.get_github_info(user_id)

        # Verify
        assert result is None
        mock_collection.find_one.assert_called_once_with({"_id": ObjectId(user_id)})

    def test_unbind_account_success(self, github_model, mock_collection):
        # Setup
        user_id = "60d21b4667d0d8992e610c85"
        mock_collection.update_one.return_value = MagicMock(modified_count=1)

        # Execute
        result = github_model.unbind_account(user_id)

        # Verify
        assert result is True
        mock_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(user_id)}, {"$unset": {"github": ""}}
        )

    def test_unbind_account_failure(self, github_model, mock_collection):
        # Setup
        user_id = "60d21b4667d0d8992e610c85"
        mock_collection.update_one.return_value = MagicMock(modified_count=0)

        # Execute
        result = github_model.unbind_account(user_id)

        # Verify
        assert result is False
        mock_collection.update_one.assert_called_once()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def session_data():
    return {"username": "testuser"}

@patch("routes.github.requests.post")
@patch("routes.github.requests.get")
def test_github_callback_success(mock_get, mock_post, client, session_data):
    mock_post.return_value.json.return_value = {"access_token": "fake-token"}
    mock_get.return_value.json.return_value = {
        "id": 12345,
        "login": "githubuser",
        "name": "GitHub User",
        "avatar_url": "https://example.com/avatar.png"
    }

    with client.session_transaction() as sess:
        sess["username"] = session_data["username"]

    response = client.get("/github/callback?code=fake-code")

    assert response.status_code == 302
    assert response.location.endswith(url_for("home"))

def test_github_link_redirect(client):
    response = client.get("/github/link")
    assert response.status_code == 302
    assert "github.com/login/oauth/authorize" in response.location

def test_github_callback_missing_code(client):
    response = client.get("/github/callback")
    assert response.status_code == 400
    assert b"Missing code" in response.data

@patch("routes.github.requests.get")
def test_github_repo_link_success(mock_get, client, session_data):
    mock_get.return_value.json.return_value = [
        {"full_name": "testuser/repo1"},
        {"full_name": "testuser/repo2"},
    ]

    with client.session_transaction() as sess:
        sess["username"] = session_data["username"]

    response = client.get("/github/repo/link")
    assert response.status_code == 200
    assert b"repo1" in response.data
    assert b"repo2" in response.data

@patch("routes.github.get_repo_contents")
def test_get_repository_contents_success(mock_get_repo_contents, client, session_data):
    mock_get_repo_contents.return_value = [
        {
            "name": "README.md",
            "path": "README.md",
            "type": "file",
            "size": 123,
            "download_url": "https://example.com/readme",
            "url": "https://api.github.com/repos/owner/repo/contents/README.md"
        }
    ]

    with client.session_transaction() as sess:
        sess["username"] = session_data["username"]

    response = client.get("/github/repo/contents")
    data = response.get_json()
    assert response.status_code == 200
    assert any(file["name"] == "README.md" for file in data)

def test_github_unlink_success(client, session_data):
    with client.session_transaction() as sess:
        sess["username"] = session_data["username"]

    response = client.get("/github/unlink")
    assert response.status_code == 302
    assert response.location.endswith(url_for("home"))