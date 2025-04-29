import pytest
from unittest.mock import MagicMock, patch
from routes.emailRoute import email_bp
from flask import Flask, session

class TestEmailRoutes:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.register_blueprint(email_bp)
        app.secret_key = "test_secret_key"
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        with app.test_client() as client:
            yield client
    
    def test_email_link_get(self, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        # Mock user with email
        mock_db.users.find_one.return_value = {
            "username": "testuser",
            "email": "test@example.com"
        }
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            sess['identity'] = 'student'
            
        response = client.get('/email/link')
        
        # Verify
        assert response.status_code == 200
        assert b"Bind your e-mail" in response.data
        assert b"test@example.com" in response.data
        
        # Verify calls
        mock_db.users.find_one.assert_called_once_with({"username": "testuser"}, {"email": 1})
    
    def test_email_link_post_valid(self, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            
        form_data = {"email": "new@example.com"}
        response = client.post('/email/link', data=form_data)
        
        # Verify
        assert response.status_code == 302
        assert response.location == "/home"
        
        # Verify database update
        mock_db.users.update_one.assert_called_once_with(
            {"username": "testuser"},
            {"$set": {"email": "new@example.com", "email_verified": False}}
        )
    
    def test_email_link_post_invalid(self, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            
        form_data = {"email": "invalid-email"}
        response = client.post('/email/link', data=form_data)
        
        # Verify
        assert response.status_code == 400
        assert b"Invalid e-mail address" in response.data
        
        # Verify no database update
        mock_db.users.update_one.assert_not_called()
    
# tests/test_routes/test_email_routes.py (continued)
    def test_email_unlink(self, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            
        response = client.get('/email/unlink')
        
        # Verify
        assert response.status_code == 302
        assert response.location == "/home"
        
        # Verify database update
        mock_db.users.update_one.assert_called_once_with(
            {"username": "testuser"},
            {"$set": {"email": None, "email_verified": False}}
        )
    
    def test_email_routes_not_logged_in(self, client):
        # Test GET /email/link
        response = client.get('/email/link')
        assert response.status_code == 403
        assert b"Not logged in" in response.data
        
        # Test POST /email/link
        response = client.post('/email/link', data={"email": "test@example.com"})
        assert response.status_code == 403
        assert b"Not logged in" in response.data
        
        # Test /email/unlink
        response = client.get('/email/unlink')
        assert response.status_code == 403
        assert b"Not logged in" in response.data