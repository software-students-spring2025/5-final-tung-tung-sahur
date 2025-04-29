import pytest
from flask import Flask, session
from bson.objectid import ObjectId
from unittest.mock import patch, MagicMock
import routes.githubRoute as githubRoute
import requests

@pytest.fixture
def app():
    app = Flask(__name__)
    app.secret_key = "secret"
    @app.route('/')
    def home():
        return "HOME"
    app.register_blueprint(githubRoute.github_bp)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_github_link_redirect(client):
    resp = client.get('/github/link')
    assert resp.status_code == 302
    assert "github.com/login/oauth/authorize" in resp.headers['Location']

@patch('routes.githubRoute.requests.post')
def test_github_callback_missing_code(mock_post, client):
    resp = client.get('/github/callback')
    assert resp.status_code == 400
    assert b"Missing code" in resp.data

@patch('routes.githubRoute.requests.post')
def test_github_callback_no_token(mock_post, client):
    mock_post.return_value.json.return_value = {}
    resp = client.get('/github/callback?code=123')
    assert resp.status_code == 400
    assert b"Failed to get access token" in resp.data

@patch('routes.githubRoute.requests.post')
@patch('routes.githubRoute.requests.get')
def test_github_callback_not_logged_in(mock_get, mock_post, client):
    mock_post.return_value.json.return_value = {'access_token': 'tok'}
    mock_get.return_value.json.return_value = {'id': 1, 'login': 'u'}
    resp = client.get('/github/callback?code=123')
    assert resp.status_code == 403

@patch('routes.githubRoute.requests.post')
@patch('routes.githubRoute.requests.get')
@patch('routes.githubRoute.github_accounts')
@patch('routes.githubRoute.users')
def test_github_callback_user_not_found(mock_users, mock_accounts, mock_get, mock_post, client):
    mock_post.return_value.json.return_value = {'access_token': 'tok'}
    mock_get.return_value.json.return_value = {'id': 2, 'login': 'u'}
    with client.session_transaction() as sess:
        sess['username'] = 'bob'
    mock_users.find_one.return_value = None
    resp = client.get('/github/callback?code=abc')
    assert resp.status_code == 404
    assert b"User not found" in resp.data

@patch('routes.githubRoute.requests.post')
@patch('routes.githubRoute.requests.get')
@patch('routes.githubRoute.github_accounts')
@patch('routes.githubRoute.users')
def test_github_callback_link_new_account(mock_users, mock_accounts, mock_get, mock_post, client):
    mock_post.return_value.json.return_value = {'access_token': 'tok'}
    mock_get.return_value.json.return_value = {
        'id': 3, 'login': 'u', 'name': 'n', 'avatar_url': 'a'
    }
    with client.session_transaction() as sess:
        sess['username'] = 'alice'
    mock_users.find_one.return_value = {'_id': ObjectId(), 'username': 'alice'}
    mock_accounts.find_one.return_value = None
    resp = client.get('/github/callback?code=xyz')
    assert resp.status_code == 302  # 重定向到 home

@patch('routes.githubRoute.requests.post')
@patch('routes.githubRoute.requests.get')
@patch('routes.githubRoute.github_accounts')
@patch('routes.githubRoute.users')
def test_github_callback_override_existing(mock_users, mock_accounts, mock_get, mock_post, client):
    mock_post.return_value.json.return_value = {'access_token': 'tok'}
    mock_get.return_value.json.return_value = {'id': 4, 'login': 'x'}
    with client.session_transaction() as sess:
        sess['username'] = 'john'
    mock_users.find_one.return_value = {'_id': ObjectId(), 'username': 'john'}
    mock_accounts.find_one.return_value = {'github_id': 4, 'username': 'other'}
    resp = client.get('/github/callback?code=zzz')
    assert resp.status_code == 302

def test_github_unlink_not_logged(client):
    resp = client.get('/github/unlink')
    assert resp.status_code == 403

@patch('routes.githubRoute.github_accounts')
def test_github_unlink_success(mock_accounts, client):
    with client.session_transaction() as sess:
        sess['username'] = 'sam'
    resp = client.get('/github/unlink')
    assert resp.status_code == 302
    mock_accounts.delete_one.assert_called_once_with({"username": "sam"})

def test_repo_link_not_logged(client):
    resp = client.get('/github/repo/link')
    assert resp.status_code == 403

@patch('routes.githubRoute.github_accounts')
def test_repo_link_no_account(mock_accounts, client):
    with client.session_transaction() as sess:
        sess['username'] = 'sam'
    mock_accounts.find_one.return_value = None
    resp = client.get('/github/repo/link')
    assert resp.status_code == 404

@patch('routes.githubRoute.requests.get')
@patch('routes.githubRoute.github_accounts')
def test_repo_link_no_repos(mock_accounts, mock_get, client):
    with client.session_transaction() as sess:
        sess['username'] = 'tim'
    mock_accounts.find_one.return_value = {'access_token': 't'}
    mock_get.return_value.json.return_value = []
    resp = client.get('/github/repo/link')
    assert resp.status_code == 404
    assert b"No repositories found" in resp.data

@patch('routes.githubRoute.github_accounts')
@patch('routes.githubRoute.requests.get')
@patch('routes.githubRoute.render_template')
def test_repo_link_success(mock_rt, mock_get, mock_accounts, client):
    with client.session_transaction() as sess:
        sess['username'] = 'tim'
        sess['identity'] = 'teacher'
    mock_accounts.find_one.return_value = {'access_token': 't'}
    mock_get.return_value.json.return_value = [{'name': 'r'}]
    mock_rt.return_value = "OK"
    resp = client.get('/github/repo/link')
    mock_rt.assert_called_once()

def test_repo_link_post_not_logged(client):
    resp = client.post('/github/repo/link', data={})
    assert resp.status_code == 403

@patch('routes.githubRoute.github_accounts')
def test_repo_link_post_no_selected(mock_accounts, client):
    with client.session_transaction() as sess:
        sess['username'] = 'u'
    resp = client.post('/github/repo/link', data={})
    assert resp.status_code == 400

@patch('routes.githubRoute.github_accounts')
def test_repo_link_post_success(mock_accounts, client):
    with client.session_transaction() as sess:
        sess['username'] = 'u'
    resp = client.post('/github/repo/link', data={'repo': 'o/repo'})
    assert resp.status_code == 302
    mock_accounts.update_one.assert_called_once_with(
        {"username": "u"},
        {"$set": {"repo": "o/repo", "repo_url": "https://github.com/o/repo"}}
    )

def test_repo_unlink_not_logged(client):
    resp = client.get('/github/repo/unlink')
    assert resp.status_code == 403

@patch('routes.githubRoute.github_accounts')
def test_repo_unlink_no_account(mock_accounts, client):
    with client.session_transaction() as sess:
        sess['username'] = 'u'
    mock_accounts.find_one.return_value = None
    resp = client.get('/github/repo/unlink')
    assert resp.status_code == 404

@patch('routes.githubRoute.github_accounts')
def test_repo_unlink_success(mock_accounts, client):
    with client.session_transaction() as sess:
         sess['username'] = 'sam'
    resp = client.get('/github/repo/unlink')
    assert resp.status_code == 302
    mock_accounts.update_one.assert_called_once_with(
        {"username": "sam"},
        {"$set": {"repo": None, "repo_url": None}}
    )

def test_get_repo_contents_success(monkeypatch):
    class R:
        status_code = 200
        def json(self): return {'x':1}
    monkeypatch.setattr(requests, 'get', lambda *a, **k: R())
    assert githubRoute.get_repo_contents('o','r','t','p') == {'x':1}

def test_get_repo_contents_failure(monkeypatch):
    class R:
        status_code = 404
        text = 'err'
        def json(self): return {}
    monkeypatch.setattr(requests, 'get', lambda *a, **k: R())
    with pytest.raises(Exception):
        githubRoute.get_repo_contents('o','r','t','p')

def test_list_repo_files_recursive(monkeypatch):
    def fake_contents(o, r, t, path):
        if path == '':
            return [
                {'type':'dir','path':'d'},
                {'type':'file','name':'f','path':'f','download_url':'u'}
            ]
        return {'type':'file','name':'g','path':'d/g','download_url':'u2'}
    monkeypatch.setattr(githubRoute, 'get_repo_contents', fake_contents)
    files = githubRoute.list_repo_files_recursive('o','r','t','')
    names = {f['name'] for f in files}
    assert names == {'f','g'}

def test_is_repo_path_file(monkeypatch):
    monkeypatch.setattr(githubRoute, 'get_repo_contents', lambda o,r,t,p: {'type':'file'})
    assert githubRoute.is_repo_path_file('','','','')
    monkeypatch.setattr(githubRoute, 'get_repo_contents', lambda o,r,t,p: [{'type':'file'}])
    assert not githubRoute.is_repo_path_file('','','','')
    monkeypatch.setattr(githubRoute, 'get_repo_contents', lambda *a, **k: (_ for _ in ()).throw(Exception()))
    assert not githubRoute.is_repo_path_file('','','','')

@patch('routes.githubRoute.github_accounts')
def test_get_repository_contents_not_logged(mock_acc, client):
    resp = client.get('/github/repo/contents')
    assert resp.status_code == 403

@patch('routes.githubRoute.github_accounts')
def test_get_repository_contents_no_repo(mock_acc, client):
    with client.session_transaction() as sess:
        sess['username'] = 'u'
    mock_acc.find_one.return_value = {}
    resp = client.get('/github/repo/contents')
    assert resp.status_code == 400

@patch('routes.githubRoute.get_repo_contents')
@patch('routes.githubRoute.github_accounts')
def test_get_repository_contents_success(mock_acc, mock_get, client):
    with client.session_transaction() as sess:
        sess['username'] = 'u'
    mock_acc.find_one.return_value = {'repo':'o/r','access_token':'t'}
    mock_get.return_value = [
        {'name':'n', 'path':'p', 'type':'file', 'size': 123,
         'download_url':'d_url', 'url':'u_url'}
    ]
    resp = client.get('/github/repo/contents')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert data[0]['name'] == 'n'
    assert data[0]['url'] == 'u_url'

@patch('routes.githubRoute.github_accounts')
@patch('routes.githubRoute.list_repo_files_recursive')
@patch('routes.githubRoute.render_template')
def test_github_repo_files(mock_rt, mock_list, mock_acc, client):
    with client.session_transaction() as sess:
        sess['username'] = 'u'
    mock_acc.find_one.return_value = {'repo':'o/r','access_token':'t'}
    mock_list.return_value = [{'name':'x'}]
    mock_rt.return_value = "OK"
    resp = client.get('/github/repo/files')
    mock_rt.assert_called_once()
    assert resp.status_code == 200
