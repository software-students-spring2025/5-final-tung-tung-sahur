import pytest
from unittest.mock import patch
from bson.objectid import ObjectId
from routes.contentRoute import content_bp
from flask import Flask

class TestContentRoutes:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.register_blueprint(content_bp)
        app.secret_key = "test_secret_key"
        app.config['TESTING'] = True
        return app

    @patch('routes.contentRoute.render_template')
    @patch('routes.contentRoute.users')
    @patch('routes.contentRoute.content_model')
    def test_show_content_teacher(self, mock_content_model, mock_users, mock_render, client):
        # Arrange
        mock_users.find_one.return_value = {
            "_id": ObjectId(), "username": "teacher", "identity": "teacher"
        }
        items = [
            {"_id": ObjectId(), "title": "Lecture 1"},
            {"_id": ObjectId(), "title": "Lecture 2"}
        ]
        mock_content_model.get_teacher_content.return_value = items

        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        # Act
        rv = client.get('/content')

        # Assert
        mock_render.assert_called_once_with(
            "teacher_content.html",
            content_items=items,
            username="teacher",
            identity="teacher"
        )

    @patch('routes.contentRoute.render_template')
    @patch('routes.contentRoute.content_model')
    def test_show_content_student(self, mock_content_model, mock_render, client):
        # Arrange
        items = [
            {"_id": ObjectId(), "title": "Lecture 1"},
            {"_id": ObjectId(), "title": "Lecture 2"}
        ]
        mock_content_model.get_all_content.return_value = items

        with client.session_transaction() as sess:
            sess['username'] = 'student'
            sess['identity'] = 'student'

        # Act
        rv = client.get('/content')

        # Assert
        mock_render.assert_called_once_with(
            "student_content.html",
            content_items=items,
            username="student",
            identity="student"
        )

    @patch('routes.contentRoute.render_template')
    @patch('routes.contentRoute.github_accounts')
    def test_create_content_get(self, mock_github, mock_render, client):
        # Arrange
        mock_github.find_one.return_value = {
            "username": "teacher", "repo": "u/r", "access_token": "t"
        }
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        # Act
        rv = client.get('/content/create')

        # Assert
        mock_render.assert_called_once_with(
            "create_content.html",
            github_info=mock_github.find_one.return_value,
            username="teacher",
            identity="teacher"
        )

    @patch('routes.contentRoute.redirect')
    @patch('routes.contentRoute.content_model')
    @patch('routes.contentRoute.github_accounts')
    @patch('routes.contentRoute.users')
    def test_create_content_post(self, mock_users, mock_github, mock_content_model, mock_redirect, client):
        # Arrange
        mock_users.find_one.return_value = {
            "_id": ObjectId(), "username": "teacher", "identity": "teacher"
        }
        mock_github.find_one.return_value = {
            "repo": "u/r", "repo_url": "https://github.com/u/r"
        }
        mock_content_model.create_content.return_value = "new_content"
        mock_redirect.return_value = "REDIR"

        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        data = {"title": "T", "description": "D", "github_repo_path": "p"}

        # Act
        rv = client.post('/content/create', data=data)

        # Assert
        mock_content_model.create_content.assert_called_once_with(
            teacher_id=str(mock_users.find_one.return_value["_id"]),
            title="T",
            description="D",
            github_repo_url="https://github.com/u/r/tree/main/p",
            github_repo_path="p"
        )
        mock_redirect.assert_called_once_with(
            # 注意：此处 url_for 已经在入口函数里被调用，所以我们只关心 redirect 被调用
            pytest.ANY
        )
        assert rv == "REDIR"
