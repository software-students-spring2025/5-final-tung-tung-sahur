import pytest
from unittest.mock import patch
from bson.objectid import ObjectId
from routes.contentRoute import content_bp
from flask import Flask

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
    @patch('routes.contentRoute.ContentModel')
    def test_show_content_teacher(self, mock_content_model, client, mock_mongo):
        mock_client, mock_db = mock_mongo
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(), "username":"teacher","identity":"teacher"
        }
        mock_content_model.return_value.get_teacher_content.return_value = [
            {"_id": ObjectId(),"title":"L1"},
            {"_id": ObjectId(),"title":"L2"}
        ]
        with client.session_transaction() as sess:
            sess['username']='teacher'; sess['identity']='teacher'
        resp = client.get('/content')
        assert resp.status_code == 200
        assert b"L1" in resp.data and b"L2" in resp.data
        mock_db.users.find_one.assert_called_once_with({"username":"teacher"})
        mock_content_model.return_value.get_teacher_content.assert_called_once()

    @patch('routes.contentRoute.ContentModel')
    def test_show_content_student(self, mock_content_model, client, mock_mongo):
        mock_client, mock_db = mock_mongo
        mock_content_model.return_value.get_all_content.return_value = [
            {"_id": ObjectId(),"title":"L1"},
            {"_id": ObjectId(),"title":"L2"}
        ]
        with client.session_transaction() as sess:
            sess['username']='student'; sess['identity']='student'
        resp = client.get('/content')
        assert resp.status_code == 200
        assert b"L1" in resp.data and b"L2" in resp.data
        mock_content_model.return_value.get_all_content.assert_called_once()

    @patch('routes.contentRoute.ContentModel')
    def test_create_content_get(self, mock_content_model, client, mock_mongo):
        mock_client, mock_db = mock_mongo
        mock_db.github_accounts.find_one.return_value = {"repo":"u/r","access_token":"t"}
        with client.session_transaction() as sess:
            sess['username']='teacher'; sess['identity']='teacher'
        resp = client.get('/content/create')
        assert resp.status_code == 200
        assert b"Create new lecture material" in resp.data
        mock_db.github_accounts.find_one.assert_called_once_with({"username":"teacher"})

    @patch('routes.contentRoute.ContentModel')
    def test_create_content_post(self, mock_content_model, client, mock_mongo):
        mock_client, mock_db = mock_mongo
        mock_db.users.find_one.return_value = {"_id":ObjectId(),"username":"teacher","identity":"teacher"}
        mock_db.github_accounts.find_one.return_value = {"repo":"u/r","repo_url":"https://x"}
        mock_content_model.return_value.create_content.return_value = "cid"
        with client.session_transaction() as sess:
            sess['username']='teacher'; sess['identity']='teacher'
        data = {"title":"T","description":"D","github_repo_path":"p"}
        resp = client.post('/content/create', data=data)
        assert resp.status_code == 302
        assert resp.location.endswith("/content")
        mock_db.users.find_one.assert_called_once_with({"username":"teacher"})
        mock_db.github_accounts.find_one.assert_called_once_with({"username":"teacher"})
        mock_content_model.return_value.create_content.assert_called_once()
        _, kwargs = mock_content_model.return_value.create_content.call_args
        assert kwargs["title"] == "T" and kwargs["description"] == "D"
        assert kwargs["github_repo_path"] == "p"
