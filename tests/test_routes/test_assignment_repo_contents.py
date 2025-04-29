import pytest
from flask import Flask, session
from unittest.mock import patch, MagicMock
import routes.assignmentRoute as assignmentRoute

@pytest.fixture
def app():
    app = Flask(__name__)
    app.secret_key = "testkey"
    app.register_blueprint(assignmentRoute.assignment_bp)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_list_repo_contents_unauthorized(client):
    resp = client.get('/assignments/list_repo_contents')
    assert resp.status_code == 403
    assert b"Unauthorized" in resp.data

@patch('routes.assignmentRoute.github_accounts')
def test_list_repo_contents_no_repo(mock_accounts, client):
    with client.session_transaction() as sess:
        sess['username'] = 't'
        sess['identity'] = 'teacher'
    mock_accounts.find_one.return_value = {}
    resp = client.get('/assignments/list_repo_contents')
    assert resp.status_code == 400
    assert b"No GitHub repository linked" in resp.data

@patch('routes.assignmentRoute.get_repo_contents')
@patch('routes.assignmentRoute.github_accounts')
def test_list_repo_contents_success(mock_accounts, mock_get, client):
    with client.session_transaction() as sess:
        sess['username'] = 't'
        sess['identity'] = 'teacher'
    mock_accounts.find_one.return_value = {
        "username": "t", "repo": "u/r", "access_token": "tok"
    }
    # simulate directory listing
    mock_get.return_value = [
        {"name":"f1","path":"p1","type":"dir","url":"u"},
        {"name":"f2","path":"p2","type":"file","url":"u"}
    ]
    resp = client.get('/assignments/list_repo_contents?path=sub')
    assert resp.status_code == 200
    data = resp.get_json()
    # directories first
    assert data[0]["type"] == "dir"
    assert data[1]["type"] == "file"
