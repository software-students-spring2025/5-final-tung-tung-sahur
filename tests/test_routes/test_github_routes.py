# tests/test_routes/test_github_routes.py (New file)
import pytest
from unittest.mock import MagicMock, patch
from bson.objectid import ObjectId
from routes.githubRoute import github_bp
from flask import Flask, session

class TestGithubRoutes:
    @pytest.fixture
    def app(self):
        # 创建一个测试用的Flask应用
        app = Flask(__name__)
        app.register_blueprint(github_bp)
        app.secret_key = "test_secret_key"
        app.config['TESTING'] = True
        # 添加这个来解决'home'端点的BuildError
        @app.route('/home')
        def home():
            return "Home Page"
        return app
    
    @pytest.fixture
    def client(self, app):
        with app.test_client() as client:
            yield client
    
    @patch('routes.githubRoute.client_id', 'test_client_id')
    def test_github_link(self, client):
        # 执行
        response = client.get('/github/link')
        
        # 验证重定向到GitHub OAuth
        assert response.status_code == 302
        assert "github.com/login/oauth/authorize" in response.location
        assert "test_client_id" in response.location
    
    @patch('routes.githubRoute.requests')
    @patch('routes.githubRoute.client_id', 'test_client_id')
    @patch('routes.githubRoute.client_secret', 'test_client_secret')
    def test_github_callback(self, mock_requests, client):
        # 设置token响应
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {"access_token": "test_token"}
        mock_requests.post.return_value = mock_token_response
        
        # 设置用户响应
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "github_user",
            "name": "GitHub User",
            "avatar_url": "https://avatar.url"
        }
        mock_requests.get.return_value = mock_user_response
        
        # 执行会话
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            
        with patch('routes.githubRoute.users') as mock_users, \
             patch('routes.githubRoute.github_accounts') as mock_github_accounts, \
             patch('routes.githubRoute.redirect') as mock_redirect:
            
            # 设置用户
            mock_users.find_one.return_value = {
                "_id": ObjectId("60d21b4667d0d8992e610c85"),
                "username": "testuser"
            }
            
            # 设置github账号检查
            mock_github_accounts.find_one.return_value = None
            mock_redirect.return_value = "Redirected"
            
            # 执行
            response = client.get('/github/callback?code=test_code')
            
            # 验证请求
            mock_requests.post.assert_called_once()
            mock_requests.get.assert_called_once()
            
            # 验证数据库操作
            mock_github_accounts.replace_one.assert_called_once()
            
            # 验证重定向
            mock_redirect.assert_called_once_with('/home')
    
    @patch('routes.githubRoute.github_accounts')
    def test_github_unlink(self, mock_github_accounts, client):
        # 设置
        with patch('routes.githubRoute.redirect') as mock_redirect:
            mock_redirect.return_value = "Redirected"
            
            # 执行
            with client.session_transaction() as sess:
                sess['username'] = 'testuser'
                
            response = client.get('/github/unlink')
            
            # 验证
            mock_github_accounts.delete_one.assert_called_once_with({"username": "testuser"})
            mock_redirect.assert_called_once_with('/home')
    
    @patch('routes.githubRoute.requests')
    @patch('routes.githubRoute.github_accounts')
    def test_github_repo_link_get(self, mock_github_accounts, mock_requests, client):
        # 设置
        mock_github_account = {
            "username": "testuser",
            "access_token": "test_token"
        }
        mock_github_accounts.find_one.return_value = mock_github_account
        
        # 模拟仓库响应
        mock_repo_response = MagicMock()
        mock_repo_response.json.return_value = [
            {"full_name": "testuser/repo1", "description": "Test Repo 1"},
            {"full_name": "testuser/repo2", "description": "Test Repo 2"}
        ]
        mock_requests.get.return_value = mock_repo_response
        
        # 模拟模板渲染
        with patch('routes.githubRoute.render_template') as mock_render_template:
            mock_render_template.return_value = "Rendered Template"
            
            # 执行
            with client.session_transaction() as sess:
                sess['username'] = 'testuser'
                
            response = client.get('/github/repo/link')
            
            # 验证
            mock_github_accounts.find_one.assert_called_once_with({"username": "testuser"})
            mock_requests.get.assert_called_once()
            mock_render_template.assert_called_once()
            args, kwargs = mock_render_template.call_args
            assert "select_repo.html" in args
            assert "repos" in kwargs
            
    @patch('routes.githubRoute.github_accounts')
    def test_github_repo_link_post(self, mock_github_accounts, client):
        # 设置
        with patch('routes.githubRoute.redirect') as mock_redirect:
            mock_redirect.return_value = "Redirected"
            
            # 执行
            with client.session_transaction() as sess:
                sess['username'] = 'testuser'
                
            form_data = {"repo": "testuser/repo1"}
            response = client.post('/github/repo/link', data=form_data)
            
            # 验证
            mock_github_accounts.update_one.assert_called_once_with(
                {"username": "testuser"},
                {"$set": {
                    "repo": "testuser/repo1",
                    "repo_url": "https://github.com/testuser/repo1"
                }}
            )
            mock_redirect.assert_called_once_with('/home')
    
    def test_get_repo_contents_function(self):
        # 测试get_repo_contents函数
        with patch('routes.githubRoute.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"name": "file1.py", "type": "file", "path": "file1.py", "download_url": "https://download/file1.py"},
                {"name": "dir1", "type": "dir", "path": "dir1"}
            ]
            mock_requests.get.return_value = mock_response
            
            # 导入函数
            from routes.githubRoute import get_repo_contents
            
            # 执行
            result = get_repo_contents("owner", "repo", "token", "path")
            
            # 验证
            assert result == mock_response.json.return_value
            mock_requests.get.assert_called_once()