# tests/test_routes/test_chat_routes.py (Fixed version)
import pytest
from unittest.mock import MagicMock, patch
from bson.objectid import ObjectId
from routes.chatRoute import chat_bp
from flask import Flask, session

class TestChatRoutes:
    @pytest.fixture
    def app(self):
        # 创建一个测试用的Flask应用
        app = Flask(__name__)
        app.register_blueprint(chat_bp)
        app.secret_key = "test_secret_key"
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        with app.test_client() as client:
            yield client
    
    @patch('routes.chatRoute.ChatModel')
    @patch('routes.chatRoute.UserModel')
    def test_chat_index(self, mock_user_model, mock_chat_model, client, mock_mongo):
        # 设置
        mock_client, mock_db = mock_mongo
        
        # 模拟最近联系人
        mock_chat_model.return_value.get_recent_contacts.return_value = ["user2", "user3"]
        
        # 模拟所有联系人
        mock_db.user_collection.find.return_value = [
            {"username": "teacher1", "identity": "teacher"},
            {"username": "student1", "identity": "student"},
            {"username": "student2", "identity": "student"}
        ]
        
        # 模拟render_template
        with patch('routes.chatRoute.render_template') as mock_render_template:
            mock_render_template.return_value = "Rendered Template"
            
            # 执行
            with client.session_transaction() as sess:
                sess['username'] = 'user1'
                
            response = client.get('/chat/')
            
            # 验证
            mock_render_template.assert_called_once()
            mock_chat_model.return_value.get_recent_contacts.assert_called_once_with("user1")
    
    @patch('routes.chatRoute.ChatModel')
    @patch('routes.chatRoute.UserModel')
    def test_chat_with_get(self, mock_user_model, mock_chat_model, client, mock_mongo):
        # 设置
        mock_client, mock_db = mock_mongo
        
        # 模拟用户
        mock_user_model.return_value.find_by_username.return_value = {"username": "user2"}
        
        # 模拟最近联系人
        mock_chat_model.return_value.get_recent_contacts.return_value = ["user2", "user3"]
        
        # 模拟对话
        mock_chat_model.return_value.get_conversation.return_value = [
            {"sender": "user1", "receiver": "user2", "content": "Hello", "timestamp": "2025-04-01T10:00:00"},
            {"sender": "user2", "receiver": "user1", "content": "Hi", "timestamp": "2025-04-01T10:01:00"}
        ]
        
        # 模拟render_template
        with patch('routes.chatRoute.render_template') as mock_render_template:
            mock_render_template.return_value = "Rendered Template"
            
            # 执行
            with client.session_transaction() as sess:
                sess['username'] = 'user1'
                
            response = client.get('/chat/with/user2')
            
            # 验证
            mock_render_template.assert_called_once()
            mock_user_model.return_value.find_by_username.assert_called_once_with("user2")
            mock_chat_model.return_value.get_recent_contacts.assert_called_once_with("user1")
            mock_chat_model.return_value.get_conversation.assert_called_once_with("user1", "user2")
    
    @patch('routes.chatRoute.ChatModel')
    @patch('routes.chatRoute.UserModel')
    def test_chat_with_post(self, mock_user_model, mock_chat_model, client, mock_mongo):
        # 设置
        mock_client, mock_db = mock_mongo
        
        # 模拟用户
        mock_user_model.return_value.find_by_username.return_value = {"username": "user2"}
        
        # 模拟发送消息
        mock_chat_model.return_value.send_message.return_value = "message_id"
        
        # 执行
        with client.session_transaction() as sess:
            sess['username'] = 'user1'
            
        form_data = {"message": "Hello, user2!"}
        response = client.post('/chat/with/user2', data=form_data)
        
        # 验证
        assert response.status_code == 302
        assert response.location == "/chat/with/user2"
        
        # 验证调用
        mock_user_model.return_value.find_by_username.assert_called_once_with("user2")
        mock_chat_model.return_value.send_message.assert_called_once()
        args, kwargs = mock_chat_model.return_value.send_message.call_args
        
        # 检查参数
        if args:
            assert args[0] == "user1" # sender
            assert args[1] == "user2" # receiver
            assert args[2] == "Hello, user2!" # content
        else:
            assert kwargs["sender"] == "user1"
            assert kwargs["receiver"] == "user2"
            assert kwargs["content"] == "Hello, user2!"
    
    @patch('routes.chatRoute.ChatModel')
    @patch('routes.chatRoute.UserModel')
    def test_chat_with_nonexistent_user(self, mock_user_model, mock_chat_model, client, mock_mongo):
        # 设置
        mock_client, mock_db = mock_mongo
        
        # 模拟用户（未找到）
        mock_user_model.return_value.find_by_username.return_value = None
        
        # 模拟flash
        with patch('routes.chatRoute.flash') as mock_flash:
            # 执行
            with client.session_transaction() as sess:
                sess['username'] = 'user1'
                
            form_data = {"message": "Hello, nonexistent!"}
            response = client.post('/chat/with/nonexistent', data=form_data)
            
            # 验证
            assert response.status_code == 302
            
            # 验证调用
            mock_user_model.return_value.find_by_username.assert_called_once_with("nonexistent")
            mock_chat_model.return_value.send_message.assert_not_called()
            mock_flash.assert_called_once()