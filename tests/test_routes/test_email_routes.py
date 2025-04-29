import pytest
from unittest.mock import patch
from routes.emailRoute import email_bp
from flask import Flask

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(email_bp)
    app.secret_key = "test_secret_key"
    app.config['TESTING'] = True
    @app.route('/')
    def home():
        return "home"
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestEmailRoutes:
    @patch('routes.emailRoute.users')
    @patch('routes.emailRoute.render_template')
    def test_email_link_get(self, mock_render_template, mock_users, client):
        mock_users.find_one.return_value = {"username":"u","email":"e@x"}
        mock_render_template.return_value = "ok"
        with client.session_transaction() as sess:
            sess['username'] = 'u'; sess['identity']='student'
        resp = client.get('/email/link')
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert args[0] == "email_link.html"
        assert kwargs["current_email"] == "e@x"

    @patch('routes.emailRoute.users')
    def test_email_link_post_valid(self, mock_users, client):
        mock_users.update_one.return_value = None
        with client.session_transaction() as sess:
            sess['username'] = 'u'; sess['identity']='student'
        with patch('routes.emailRoute.redirect') as mock_redirect:
            mock_redirect.return_value = "redir"
            resp = client.post('/email/link', data={"email":"new@x"})
            mock_users.update_one.assert_called_once_with(
                {"username":"u"},
                {"$set":{"email":"new@x","email_verified":False}}
            )
            mock_redirect.assert_called_once()
            assert resp.data == b"redir"

    @patch('routes.emailRoute.users')
    def test_email_link_post_invalid(self, mock_users, client):
        with client.session_transaction() as sess:
            sess['username'] = 'u'
        resp = client.post('/email/link', data={"email":"bad"})
        assert resp.status_code == 400
        assert b"Invalid e-mail address" in resp.data
        mock_users.update_one.assert_not_called()

    def test_unlogged(self, client):
        resp = client.get('/email/link')
        assert resp.status_code == 403
        resp = client.post('/email/link', data={"email":"x@x"})
        assert resp.status_code == 403
        resp = client.get('/email/unlink')
        assert resp.status_code == 403
