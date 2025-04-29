import pytest
from unittest.mock import patch, ANY
from bson.objectid import ObjectId
from routes.contentRoute import content_bp
from flask import Flask


class TestContentRoutes:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.register_blueprint(content_bp)
        app.secret_key = "test_secret_key"
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("routes.contentRoute.render_template")
    @patch("routes.contentRoute.users")
    @patch("routes.contentRoute.content_model")
    def test_show_content_teacher(self, mock_cm, mock_users, mock_render, client):
        mock_users.find_one.return_value = {
            "_id": ObjectId(),
            "username": "teacher",
            "identity": "teacher",
        }
        items = [{"_id": ObjectId(), "title": "L1"}, {"_id": ObjectId(), "title": "L2"}]
        mock_cm.get_teacher_content.return_value = items

        with client.session_transaction() as sess:
            sess["username"] = "teacher"
            sess["identity"] = "teacher"

        client.get("/content")
        mock_render.assert_called_once_with(
            "teacher_content.html",
            content_items=items,
            username="teacher",
            identity="teacher",
        )

    @patch("routes.contentRoute.render_template")
    @patch("routes.contentRoute.content_model")
    def test_show_content_student(self, mock_cm, mock_render, client):
        items = [{"_id": ObjectId(), "title": "L1"}, {"_id": ObjectId(), "title": "L2"}]
        mock_cm.get_all_content.return_value = items

        with client.session_transaction() as sess:
            sess["username"] = "student"
            sess["identity"] = "student"

        client.get("/content")
        mock_render.assert_called_once_with(
            "student_content.html",
            content_items=items,
            username="student",
            identity="student",
        )

    @patch("routes.contentRoute.render_template")
    @patch("routes.contentRoute.github_accounts")
    def test_create_content_get(self, mock_github, mock_render, client):
        mock_github.find_one.return_value = {
            "username": "teacher",
            "repo": "u/r",
            "access_token": "t",
        }
        with client.session_transaction() as sess:
            sess["username"] = "teacher"
            sess["identity"] = "teacher"

        client.get("/content/create")
        mock_render.assert_called_once_with(
            "create_content.html",
            github_info=mock_github.find_one.return_value,
            username="teacher",
            identity="teacher",
        )

    @patch("routes.contentRoute.redirect")
    @patch("routes.contentRoute.content_model")
    @patch("routes.contentRoute.github_accounts")
    @patch("routes.contentRoute.users")
    def test_create_content_post(
        self, mock_users, mock_github, mock_cm, mock_redirect, client
    ):
        mock_users.find_one.return_value = {
            "_id": ObjectId(),
            "username": "teacher",
            "identity": "teacher",
        }
        mock_github.find_one.return_value = {
            "repo": "u/r",
            "repo_url": "https://github.com/u/r",
        }
        mock_cm.create_content.return_value = "new_content"
        mock_redirect.return_value = "REDIR"

        with client.session_transaction() as sess:
            sess["username"] = "teacher"
            sess["identity"] = "teacher"

        data = {"title": "T", "description": "D", "github_repo_path": "p"}
        rv = client.post("/content/create", data=data)

        mock_cm.create_content.assert_called_once_with(
            teacher_id=str(mock_users.find_one.return_value["_id"]),
            title="T",
            description="D",
            github_repo_url="https://github.com/u/r/tree/main/p",
            github_repo_path="p",
        )
        # 至少被调用一次 redirect
        mock_redirect.assert_called_once_with(ANY)
        assert rv.get_data(as_text=True) == "REDIR"
