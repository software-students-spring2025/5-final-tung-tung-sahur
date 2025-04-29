import pytest
from bson.objectid import ObjectId
from flask import Flask
from routes.contentRoute import content_bp
from unittest.mock import patch

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(content_bp)
    app.secret_key = "test_secret_key"
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestContentRoutes:
    @patch('routes.contentRoute.render_template')
    @patch('routes.contentRoute.content_model')
    @patch('routes.contentRoute.users')
    def test_show_content_teacher(self, mock_users, mock_cm, mock_render, client, mock_mongo):
        mock_client, mock_db = mock_mongo
        mock_users.find_one.return_value = {
            "_id": ObjectId(), "username": "teacher", "identity": "teacher"
        }
        fake = [
            {"_id": ObjectId(), "title": "L1"},
            {"_id": ObjectId(), "title": "L2"}
        ]
        mock_cm.get_teacher_content.return_value = fake

        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        rv = client.get('/content')
        mock_render.assert_called_once_with(
            'teacher_content.html',
            content_items=fake,
            username='teacher',
            identity='teacher'
        )

    @patch('routes.contentRoute.render_template')
    @patch('routes.contentRoute.content_model')
    @patch('routes.contentRoute.users')
    def test_show_content_student(self, mock_users, mock_cm, mock_render, client, mock_mongo):
        mock_client, mock_db = mock_mongo
        fake = [
            {"_id": ObjectId(), "title": "L1"},
            {"_id": ObjectId(), "title": "L2"}
        ]
        mock_cm.get_all_content.return_value = fake
        mock_users.find_one.return_value = {
            "_id": ObjectId(), "username": "student", "identity": "student"
        }

        with client.session_transaction() as sess:
            sess['username'] = 'student'
            sess['identity'] = 'student'

        rv = client.get('/content')
        mock_render.assert_called_once_with(
            'student_content.html',
            content_items=fake,
            username='student',
            identity='student'
        )

    @patch('routes.contentRoute.render_template')
    @patch('routes.contentRoute.content_model')
    @patch('routes.contentRoute.github_accounts')
    @patch('routes.contentRoute.users')
    def test_create_content_get(self, mock_users, mock_gh, mock_cm, mock_render, client):
        mock_gh.find_one.return_value = {
            "username": "teacher", "repo": "t/r", "access_token": "t"
        }
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        rv = client.get('/content/create')
        mock_render.assert_called_once_with(
            'create_content.html',
            github_info=mock_gh.find_one.return_value,
            username='teacher',
            identity='teacher'
        )

    @patch('routes.contentRoute.redirect')
    @patch('routes.contentRoute.content_model')
    @patch('routes.contentRoute.github_accounts')
    @patch('routes.contentRoute.users')
    def test_create_content_post(self, mock_users, mock_gh, mock_cm, mock_redirect, client):
        mock_users.find_one.return_value = {
            "_id": ObjectId(), "username": "teacher", "identity": "teacher"
        }
        mock_gh.find_one.return_value = {"repo": "t/r", "repo_url": "u"}
        mock_cm.create_content.return_value = "cid"

        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        data = {
            "title": "T",
            "description": "D",
            "github_repo_path": "p"
        }
        rv = client.post('/content/create', data=data)
        mock_cm.create_content.assert_called_once()
        mock_redirect.assert_called_once_with('/content')
