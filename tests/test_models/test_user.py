import pytest
from bson.objectid import ObjectId
from unittest.mock import MagicMock, patch
from models.user import UserModel
from werkzeug.security import generate_password_hash


class TestUserModel:
    @pytest.fixture
    def mock_collection(self):
        return MagicMock()

    @pytest.fixture
    def user_model(self, mock_collection):
        return UserModel(mock_collection)

    def test_create_user(self, user_model, mock_collection):
        # Setup
        mock_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId("60d21b4667d0d8992e610c85")
        )

        # Execute
        result = user_model.create_user(
            "testuser", "test@example.com", "password123", "student"
        )

        # Verify
        assert isinstance(result, str)
        assert len(result) == 24  # ObjectId as string has 24 chars
        mock_collection.insert_one.assert_called_once()

        # Check the argument passed to insert_one
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["username"] == "testuser"
        assert call_args["email"] == "test@example.com"
        assert call_args["identity"] == "student"
        assert call_args["github"] is None
        # Check that password is hashed
        assert call_args["password"] != "password123"

    def test_find_by_username(self, user_model, mock_collection):
        # Setup
        expected_user = {"username": "testuser", "email": "test@example.com"}
        mock_collection.find_one.return_value = expected_user

        # Execute
        result = user_model.find_by_username("testuser")

        # Verify
        assert result == expected_user
        mock_collection.find_one.assert_called_once_with({"username": "testuser"})

    def test_find_by_username_not_found(self, user_model, mock_collection):
        # Setup
        mock_collection.find_one.return_value = None

        # Execute
        result = user_model.find_by_username("nonexistent")

        # Verify
        assert result is None
        mock_collection.find_one.assert_called_once_with({"username": "nonexistent"})

    def test_verify_user_valid(self, user_model, mock_collection):
        # Setup
        hashed_password = generate_password_hash("password123")
        mock_collection.find_one.return_value = {
            "username": "testuser",
            "password": hashed_password,
        }

        # Execute
        result = user_model.verify_user("testuser", "password123")

        # Verify
        assert result is True
        mock_collection.find_one.assert_called_once_with({"username": "testuser"})

    def test_verify_user_invalid_password(self, user_model, mock_collection):
        # Setup
        hashed_password = generate_password_hash("password123")
        mock_collection.find_one.return_value = {
            "username": "testuser",
            "password": hashed_password,
        }

        # Execute
        result = user_model.verify_user("testuser", "wrongpassword")

        # Verify
        assert result is False
        mock_collection.find_one.assert_called_once_with({"username": "testuser"})

    def test_verify_user_nonexistent(self, user_model, mock_collection):
        # Setup
        mock_collection.find_one.return_value = None

        # Execute
        result = user_model.verify_user("nonexistent", "password123")

        # Verify
        assert result is False
        mock_collection.find_one.assert_called_once_with({"username": "nonexistent"})

    def test_find_by_id(self, user_model, mock_collection):
        # Setup
        user_id = "60d21b4667d0d8992e610c85"
        expected_user = {"_id": ObjectId(user_id), "username": "testuser"}
        mock_collection.find_one.return_value = expected_user

        # Execute
        result = user_model.find_by_id(user_id)

        # Verify
        assert result == expected_user
        mock_collection.find_one.assert_called_once_with({"_id": ObjectId(user_id)})
