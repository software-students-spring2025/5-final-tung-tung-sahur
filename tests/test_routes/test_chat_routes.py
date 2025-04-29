import pytest
from bson.objectid import ObjectId
from flask import Flask
from routes.chatRoute import chat_bp
from unittest.mock import patch

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
    def test_chat_with_post(self, mock_um, mock_cm, client, mock_mongo):
        mock_client, mock_db = mock_mongo
        mock_um.return_value.find_by_username.return_value = {"username": "user2"}
        mock_cm.return_value.send_message.return_value = "msgid"

        with client.session_transaction() as sess:
            sess['username'] = 'user1'

        rv = client.post('/chat/with/user2', data={"message": "Hi"})
        assert rv.status_code == 302
        assert rv.location.endswith('/chat/with/user2')
        mock_cm.return_value.send_message.assert_called_once_with(
            sender="user1", receiver="user2", content="Hi"
        )
