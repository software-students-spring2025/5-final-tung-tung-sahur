import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask import Flask, session

# Add the parent directory to the path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def app():
    """Create a Flask app for testing"""
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    flask_app.secret_key = "test_secret_key"
    return flask_app


@pytest.fixture
def client(app):
    """Create a test client"""
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_mongo():
    """Create a mock MongoDB client with all necessary collections"""
    # Mock client
    mock_client = MagicMock(spec=MongoClient)

    # Mock database
    mock_db = MagicMock()
    mock_client.return_value.get_database.return_value = mock_db

    # Mock collections
    mock_db.users = MagicMock()
    mock_db.github_accounts = MagicMock()
    mock_db.assignments = MagicMock()
    mock_db.submissions = MagicMock()
    mock_db.content = MagicMock()
    mock_db.chats = MagicMock()
    mock_db.assignments_collection = MagicMock()
    mock_db.submissions_collection = MagicMock()
    mock_db.content_collection = MagicMock()
    mock_db.user_collection = MagicMock()

    return mock_client, mock_db


@pytest.fixture
def sample_user_id():
    return str(ObjectId())


@pytest.fixture
def sample_teacher_user(sample_user_id):
    return {
        "_id": ObjectId(sample_user_id),
        "username": "teacher",
        "email": "teacher@example.com",
        "password": "hashed_password",
        "identity": "teacher",
    }


@pytest.fixture
def sample_student_user(sample_user_id):
    return {
        "_id": ObjectId(sample_user_id),
        "username": "student",
        "email": "student@example.com",
        "password": "hashed_password",
        "identity": "student",
    }


@pytest.fixture
def sample_github_info():
    return {
        "username": "testuser",
        "github_id": 12345,
        "github_login": "githubuser",
        "name": "GitHub User",
        "avatar_url": "https://github.com/avatar.png",
        "access_token": "test_token",
        "repo": "githubuser/repo",
        "repo_url": "https://github.com/githubuser/repo",
    }


@pytest.fixture
def sample_assignment_id():
    return str(ObjectId())


@pytest.fixture
def sample_assignment(sample_assignment_id, sample_user_id):
    return {
        "_id": ObjectId(sample_assignment_id),
        "teacher_id": sample_user_id,
        "title": "Test Assignment",
        "description": "This is a test assignment",
        "due_date": "2025-05-01T23:59:00",
        "github_repo_url": "https://github.com/teacher/repo",
        "github_repo_path": "assignments/hw1",
        "created_at": "2025-04-01T10:00:00",
        "reminder_sent": False,
    }


@pytest.fixture
def sample_submission_id():
    return str(ObjectId())


@pytest.fixture
def sample_submission(sample_submission_id, sample_user_id, sample_assignment_id):
    return {
        "_id": ObjectId(sample_submission_id),
        "student_id": sample_user_id,
        "assignment_id": sample_assignment_id,
        "github_link": "https://github.com/student/repo",
        "readme_content": "# Submission\nThis is my homework.",
        "submitted_at": "2025-04-15T14:30:00",
        "grade": None,
        "feedback": None,
        "status": "submitted",
    }


@pytest.fixture
def sample_content_id():
    return str(ObjectId())


@pytest.fixture
def sample_content(sample_content_id, sample_user_id):
    return {
        "_id": ObjectId(sample_content_id),
        "teacher_id": sample_user_id,
        "title": "Introduction to Python",
        "description": "Learn the basics of Python programming",
        "github_repo_url": "https://github.com/teacher/repo",
        "github_repo_path": "lectures/python-intro",
        "created_at": "2025-03-15T09:00:00",
    }


@pytest.fixture
def mock_collection():
    """Create a mock MongoDB collection"""
    return MagicMock()


@pytest.fixture
def chat_model(mock_collection):
    """Create a ChatModel instance with a mock collection"""
    from models.chat import ChatModel

    return ChatModel(mock_collection)


@pytest.fixture
def user_model(mock_collection):
    """Create a UserModel instance with a mock collection"""
    from models.user import UserModel

    return UserModel(mock_collection)


@pytest.fixture
def github_model(mock_collection):
    """Create a GitHubModel instance with a mock collection"""
    from models.github import GitHubModel

    return GitHubModel(mock_collection)


@pytest.fixture
def assignment_model(mock_collection):
    """Create an AssignmentModel instance with a mock collection"""
    from models.assignment import AssignmentModel

    return AssignmentModel(mock_collection)


@pytest.fixture
def submission_model(mock_collection):
    """Create a SubmissionModel instance with a mock collection"""
    from models.submission import SubmissionModel

    return SubmissionModel(mock_collection)


@pytest.fixture
def content_model(mock_collection):
    """Create a ContentModel instance with a mock collection"""
    from models.content import ContentModel

    return ContentModel(mock_collection)
