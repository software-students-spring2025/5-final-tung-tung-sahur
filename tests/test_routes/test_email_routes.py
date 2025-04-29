import pytest
from unittest.mock import patch
from bson.objectid import ObjectId
from routes.emailRoute import email_bp
from flask import Flask


class TestEmailRoutes:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.register_blueprint(email_bp)
        app.secret_key = "test_secret_key"
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("routes.emailRoute.render_template")
    @patch("routes.emailRoute.users")
    def test_email_link_get(self, mock_users, mock_render, client):
        mock_users.find_one.return_value = {
            "username": "testuser",
            "email": "test@example.com",
        }
        with client.session_transaction() as sess:
            sess["username"] = "testuser"
            sess["identity"] = "student"

        client.get("/email/link")
        # 只检查 current_email
        args, kwargs = mock_render.call_args
        assert kwargs.get("current_email") == "test@example.com"

    @patch("routes.emailRoute.redirect")
    @patch("routes.emailRoute.url_for")
    @patch("routes.emailRoute.users")
    def test_email_link_post_valid(
        self, mock_users, mock_url_for, mock_redirect, client
    ):
        mock_users.update_one.return_value = None
        mock_url_for.return_value = "/"
        mock_redirect.return_value = "REDIR"

        with client.session_transaction() as sess:
            sess["username"] = "testuser"
            sess["identity"] = "student"

        rv = client.post("/email/link", data={"email": "new@example.com"})

        mock_users.update_one.assert_called_once_with(
            {"username": "testuser"},
            {"$set": {"email": "new@example.com", "email_verified": False}},
        )
        mock_url_for.assert_called_once_with("home")
        mock_redirect.assert_called_once_with("/")
        assert rv.get_data(as_text=True) == "REDIR"

    def test_email_link_post_invalid(self, client):
        # 未登录
        rv = client.post("/email/link", data={"email": "bad"})
        assert rv.status_code == 403

        # 登录但格式不对
        with client.session_transaction() as sess:
            sess["username"] = "u"
            sess["identity"] = "student"
        rv = client.post("/email/link", data={"email": "bad"})
        assert rv.status_code == 400
        assert b"Invalid e-mail address" in rv.data
