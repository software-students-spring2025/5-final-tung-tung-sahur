import pytest
from unittest.mock import patch, MagicMock
import os
import app


class TestAppEnvironment:
    @patch("app.os.getenv")
    def test_environment_variables(self, mock_getenv):
        # Mock env variables
        mock_getenv.side_effect = lambda key, default=None: {
            "SECRET_KEY": "test_secret",
            "MONGO_URI": "mongodb://localhost:27017/test_db",
            "FLASK_ENV": "testing",
            "GITHUB_CLIENT_ID": "github_id",
            "GITHUB_CLIENT_SECRET": "github_secret",
            "Email_password": "email_password",
            "TEACHER_INVITE_CODE": "test_code"
        }.get(key, default)
        
        # Reset app's MongoClient to force reload with our mocked env
        app.client = None
        
        # Execute by accessing app's variables - this will trigger env loading
        assert app.app.secret_key is not None
        
        # Assert our mocked env was used
        mock_getenv.assert_any_call("SECRET_KEY")
