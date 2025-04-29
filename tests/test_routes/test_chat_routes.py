import pytest
from unittest.mock import MagicMock, patch
from bson.objectid import ObjectId
from routes.chatRoute import chat_bp
from flask import Flask, session

class TestChatRoutes:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.register_blueprint(chat_bp)
        app.secret_key = "test_secret_key"
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        with app.test_client() as client:
            yield client
    
    # @patch('routes.chatRoute.ChatModel')
    # @patch('routes.chatRoute.UserModel')
    # def test_chat_index(self, mock_user_model, mock_chat_model, client, mock_mongo):
    #     # Setup
    #     mock_client, mock_db = mock_mongo
        
    #     # Mock recent contacts
    #     mock_chat_model.return_value.get_recent_contacts.return_value = ["user2", "user3"]
        
    #     # Mock all contacts
    #     mock_db.user_collection.find.return_value = [
    #         {"username": "teacher1", "identity": "teacher"},
    #         {"username": "student1", "identity": "student"},
    #         {"username": "student2", "identity": "student"}
    #     ]
        
    #     # Execute
    #     with client.session_transaction() as sess:
    #         sess['username'] = 'user1'
            
    #     response = client.get('/chat/')
        
    #     # Verify
    #     assert response.status_code == 200
    #     assert b"user2" in response.data
    #     assert b"user3" in response.data
    #     assert b"teacher1" in response.data
    #     assert b"student1" in response.data
    #     assert b"student2" in response.data
        
    #     # Verify calls
    #     mock_chat_model.return_value.get_recent_contacts.assert_not_called_with("user1")
    
    # @patch('routes.chatRoute.ChatModel')
    # @patch('routes.chatRoute.UserModel')
    # def test_chat_with_get(self, mock_user_model, mock_chat_model, client, mock_mongo):
    #     # Setup
    #     mock_client, mock_db = mock_mongo
        
    #     # Mock user
    #     mock_user_model.return_value.find_by_username.return_value = {"username": "user2"}
        
    #     # Mock recent contacts
    #     mock_chat_model.return_value.get_recent_contacts.return_value = ["user2", "user3"]
        
    #     # Mock all contacts
    #     mock_db.user_collection.find.return_value = [
    #         {"username": "teacher1", "identity": "teacher"},
    #         {"username": "student1", "identity": "student"},
    #         {"username": "student2", "identity": "student"}
    #     ]
        
    #     # Mock conversation
    #     mock_chat_model.return_value.get_conversation.return_value = [
    #         {"sender": "user1", "receiver": "user2", "content": "Hello", "timestamp": "2025-04-01T10:00:00"},
    #         {"sender": "user2", "receiver": "user1", "content": "Hi", "timestamp": "2025-04-01T10:01:00"}
    #     ]
        
    #     # Execute
    #     with client.session_transaction() as sess:
    #         sess['username'] = 'user1'
            
    #     response = client.get('/chat/with/user2')
        
    #     # Verify
    #     assert response.status_code == 200
    #     assert b"user2" in response.data
    #     assert b"Hello" in response.data
    #     assert b"Hi" in response.data
        
    #     # Verify calls
    #     mock_user_model.return_value.find_by_username.assert_called_once_with("user2")
    #     mock_chat_model.return_value.get_recent_contacts.assert_called_once_with("user1")
    #     mock_chat_model.return_value.get_conversation.assert_called_once_with("user1", "user2")
    
    @patch('routes.chatRoute.ChatModel')
    @patch('routes.chatRoute.UserModel')
    def test_chat_with_post(self, mock_user_model, mock_chat_model, client, mock_mongo):
        # Setup
        mock_client, mock_db = mock_mongo
        
        # Mock user
        mock_user_model.return_value.find_by_username.return_value = {"username": "user2"}
        
        # Mock send message
        mock_chat_model.return_value.send_message.return_value = "message_id"
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'user1'
            
        form_data = {"message": "Hello, user2!"}
        response = client.post('/chat/with/user2', data=form_data)
        
        # Verify
        assert response.status_code == 302
        assert response.location == "/chat/with/user2"
        
        # Verify calls
        # mock_user_model.return_value.find_by_username.assert_not_called_with("user2")
        mock_chat_model.return_value.send_message.assert_called_once_with(
            sender="user1", receiver="user2", content="Hello, user2!"
        )
    
    # @patch('routes.chatRoute.ChatModel')
    # @patch('routes.chatRoute.UserModel')
    # def test_chat_with_nonexistent_user(self, mock_user_model, mock_chat_model, client, mock_mongo):
    #     # Setup
    #     mock_client, mock_db = mock_mongo
        
    #     # Mock user (not found)
    #     mock_user_model.return_value.find_by_username.return_value = None
        
    #     # Execute
    #     with client.session_transaction() as sess:
    #         sess['username'] = 'user1'
            
    #     form_data = {"message": "Hello, nonexistent!"}
    #     response = client.post('/chat/with/nonexistent', data=form_data)
        
    #     # Verify
    #     assert response.status_code == 302
    #     assert "flash" in response.location
        
    #     # Verify calls
    #     mock_user_model.return_value.find_by_username.assert_called_once_with("nonexistent")
    #     mock_chat_model.return_value.send_message.assert_not_called()