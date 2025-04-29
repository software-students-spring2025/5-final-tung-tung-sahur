import pytest
from flask import Flask
from routes.emailRoute import email_bp
from unittest.mock import patch

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(email_bp)
    app.secret_key = "test_secret_key"
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestEmailRoutes:
    @patch('routes.emailRoute.render_template')
    @patch('routes.emailRoute.users')
    def test_email_link_get(self, mock_users, mock_render, client):
        mock_users.find_one.return_value = {"username": "u", "email": "e@x"}
        with client.session_transaction() as sess:
            sess['username'] = 'u'
            sess['identity'] = 'student'

        rv = client.get('/email/link')
        mock_render.assert_called_once_with(
            "email_link.html",
            current_email="e@x",
            username="u",
            identity="student"
        )

    @patch('routes.emailRoute.redirect')
    @patch('routes.emailRoute.users')
    def test_email_link_post_valid(self, mock_users, mock_redirect, client):
        mock_users.update_one.return_value = None
        with client.session_transaction() as sess:
            sess['username'] = 'u'
        rv = client.post('/email/link', data={"email": "new@x.com"})
        mock_users.update_one.assert_called_once_with(
            {"username": "u"},
            {"$set": {"email": "new@x.com", "email_verified": False}}
        )
        mock_redirect.assert_called_once_with('home')

    @patch('routes.emailRoute.users')
    def test_email_link_post_invalid(self, mock_users, client):
        with client.session_transaction() as sess:
            sess['username'] = 'u'
        rv = client.post('/email/link', data={"email": "bad"})
        assert rv.status_code == 400
        assert b"Invalid e-mail address" in rv.data

    def test_not_logged_in(self, client):
        rv = client.get('/email/link')
        assert rv.status_code == 403
        rv = client.post('/email/link', data={"email": "x@x"})
        assert rv.status_code == 403
        rv = client.get('/email/unlink')
        assert rv.status_code == 403
