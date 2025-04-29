# tests/test_routes/test_email_routes.py (Fixed version)
import pytest
from unittest.mock import MagicMock, patch
from routes.emailRoute import email_bp
from flask import Flask

class TestEmailRoutes:
    @pytest.fixture
    def app(self):
        # 创建一个测试用的Flask应用
        app = Flask(__name__)
        app.register_blueprint(email_bp)
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
    
    @patch('routes.emailRoute.users')
    def test_email_link_get(self, mock_users, client):
        # 设置
        mock_users.find_one.return_value = {
            "username": "testuser",
            "email": "test@example.com"
        }
        
        # 执行
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            sess['identity'] = 'student'
        
        with patch('routes.emailRoute.render_template') as mock_render_template:
            mock_render_template.return_value = "Rendered Template"
            response = client.get('/email/link')
            
            # 验证
            mock_render_template.assert_called_once()
            args, kwargs = mock_render_template.call_args
            assert args[0] == "email_link.html"
            assert kwargs["current_email"] == "test@example.com"

    @patch('routes.emailRoute.users')
    def test_email_link_post_valid(self, mock_users, client):
        # 设置
        mock_users.update_one.return_value = MagicMock(modified_count=1)
        
        # 执行
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        with patch('routes.emailRoute.redirect') as mock_redirect:
            mock_redirect.return_value = "Redirected"
            
            # 提交有效的电子邮件地址
            response = client.post('/email/link', data={"email": "new@example.com"})
            
            # 验证数据库更新
            mock_users.update_one.assert_called_once_with(
                {"username": "testuser"},
                {"$set": {"email": "new@example.com", "email_verified": False}}
            )
            
            # 验证重定向
            mock_redirect.assert_called_once_with('/home')
    
    @patch('routes.emailRoute.users')
    def test_email_link_post_invalid(self, mock_users, client):
        # 执行
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            
        form_data = {"email": "invalid-email"}
        response = client.post('/email/link', data=form_data)
        
        # 验证
        assert response.status_code == 400
        assert b"Invalid e-mail address" in response.data
        
        # 验证没有数据库更新
        mock_users.update_one.assert_not_called()
    
    @patch('routes.emailRoute.users')
    def test_email_unlink(self, mock_users, client):
        # 执行
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        with patch('routes.emailRoute.redirect') as mock_redirect:
            mock_redirect.return_value = "Redirected"
            response = client.get('/email/unlink')
            
            # 验证
            mock_users.update_one.assert_called_once_with(
                {"username": "testuser"},
                {"$set": {"email": None, "email_verified": False}}
            )
            mock_redirect.assert_called_once_with('/home')
    
    def test_email_routes_not_logged_in(self, client):
        # 测试不登录的情况下访问/email/link
        response = client.get('/email/link')
        assert response.status_code == 403
        assert b"Not logged in" in response.data
        
        # 测试不登录的情况下POST /email/link
        response = client.post('/email/link', data={"email": "test@example.com"})
        assert response.status_code == 403
        assert b"Not logged in" in response.data
        
        # 测试不登录的情况下访问/email/unlink
        response = client.get('/email/unlink')
        assert response.status_code == 403
        assert b"Not logged in" in response.data