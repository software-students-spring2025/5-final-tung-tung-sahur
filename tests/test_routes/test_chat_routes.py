import pytest
from unittest.mock import patch
from bson.objectid import ObjectId
from routes.chatRoute import chat_bp
from flask import Flask


class TestChatRoutes:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.register_blueprint(chat_bp)
        app.secret_key = "test_secret_key"
        app.config["TESTING"] = True
        return app

    @patch("routes.chatRoute.chat_model")
    @patch("routes.chatRoute.user_model")
    def test_chat_with_post(self, mock_user_model, mock_chat_model, client):
        # Arrange
        mock_user_model.find_by_username.return_value = {"username": "user2"}
        mock_chat_model.send_message.return_value = "msgid"

        with client.session_transaction() as sess:
            sess["username"] = "user1"

        # Act
        response = client.post("/chat/with/user2", data={"message": "Hi"})

        # Assert
        assert response.status_code == 302
        assert response.location.endswith("/chat/with/user2")
        mock_chat_model.send_message.assert_called_once_with(
            sender="user1", receiver="user2", content="Hi"
        )
