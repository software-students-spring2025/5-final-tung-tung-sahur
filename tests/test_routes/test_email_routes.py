# tests/test_routes/test_email_routes.py
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
        return app
    
    # Tests already in the file...
    
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