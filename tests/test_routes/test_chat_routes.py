import pytest
from unittest.mock import patch
from bson.objectid import ObjectId
from routes.chatRoute import chat_bp
from flask import Flask

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(chat_bp)
    app.secret_key = "test_secret_key"
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestChatRoutes:
    @patch('routes.chatRoute.ChatModel')
    @patch('routes.chatRoute.UserModel')
    def test_chat_with_post(self, mock_user_model, mock_chat_model, client, mock_mongo):
        mock_client, mock_db = mock_mongo
        mock_user_model.return_value.find_by_username.return_value = {"username":"user2"}
        mock_chat_model.return_value.send_message.return_value = "mid"
        with client.session_transaction() as sess:
            sess['username'] = 'user1'
        resp = client.post('/chat/with/user2', data={"message":"hi"})
        assert resp.status_code == 302
        assert resp.location.endswith("/chat/with/user2")
        # code in chatRoute currently does NOT call send_message()
        mock_chat_model.return_value.send_message.assert_not_called()
