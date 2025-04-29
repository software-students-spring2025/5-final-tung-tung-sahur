# tests/test_routes/test_email_routes.py (improved)
import pytest
from unittest.mock import MagicMock, patch
from routes.emailRoute import email_bp
from flask import Flask

class TestEmailRoutes:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.register_blueprint(email_bp)
        app.secret_key = "test_secret_key"
        app.config['TESTING'] = True
        return app
    
    @patch('routes.emailRoute.users')
    def test_email_link_get(self, mock_users, client):
        # Setup
        mock_users.find_one.return_value = {
            "username": "testuser",
            "email": "test@example.com"
        }
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            sess['identity'] = 'student'
        
        with patch('routes.emailRoute.render_template') as mock_render_template:
            mock_render_template.return_value = "Rendered Template"
            response = client.get('/email/link')
            
            # Verify
            mock_render_template.assert_called_once()
            args, kwargs = mock_render_template.call_args
            assert args[0] == "email_link.html"
            assert kwargs["current_email"] == "test@example.com"
    
    @patch('routes.emailRoute.users')
    def test_email_link_post_valid(self, mock_users, client):
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            
        form_data = {"email": "new@example.com"}
        
        with patch('routes.emailRoute.redirect') as mock_redirect:
            mock_redirect.return_value = "Redirected"
            response = client.post('/email/link', data=form_data)
            
            # Verify
            mock_users.update_one.assert_called_once_with(
                {"username": "testuser"},
                {"$set": {"email": "new@example.com", "email_verified": False}}
            )
            mock_redirect.assert_called_once()
    
    @patch('routes.emailRoute.users')
    def test_email_link_post_invalid(self, mock_users, client):
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            
        form_data = {"email": "invalid-email"}
        response = client.post('/email/link', data=form_data)
        
        # Verify
        assert response.status_code == 400
        assert b"Invalid e-mail address" in response.data
        
        # Verify no database update
        mock_users.update_one.assert_not_called()
    
    @patch('routes.emailRoute.users')
    def test_email_unlink(self, mock_users, client):
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        with patch('routes.emailRoute.redirect') as mock_redirect:
            mock_redirect.return_value = "Redirected"
            response = client.get('/email/unlink')
            
            # Verify
            mock_users.update_one.assert_called_once_with(
                {"username": "testuser"},
                {"$set": {"email": None, "email_verified": False}}
            )
            mock_redirect.assert_called_once()
    
    def test_email_routes_not_logged_in(self, client):
        # Test GET /email/link without login
        response = client.get('/email/link')
        assert response.status_code == 403
        assert b"Not logged in" in response.data
        
        # Test POST /email/link without login
        response = client.post('/email/link', data={"email": "test@example.com"})
        assert response.status_code == 403
        assert b"Not logged in" in response.data
        
        # Test /email/unlink without login
        response = client.get('/email/unlink')
        assert response.status_code == 403
        assert b"Not logged in" in response.data