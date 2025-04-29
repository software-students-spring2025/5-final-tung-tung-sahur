import pytest
from bson.objectid import ObjectId
from unittest.mock import MagicMock, patch
from models.github import GitHubModel
from flask import url_for


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
