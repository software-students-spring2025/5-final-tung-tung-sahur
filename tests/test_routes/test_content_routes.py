# tests/test_routes/test_content_routes.py (Fixed version)
import pytest
from unittest.mock import MagicMock, patch
from bson.objectid import ObjectId
from routes.contentRoute import content_bp
from flask import Flask, session

class TestContentRoutes:
    @pytest.fixture
    def app(self):
        # 创建一个测试用的Flask应用
        app = Flask(__name__)
        app.register_blueprint(content_bp)
        app.secret_key = "test_secret_key"
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        with app.test_client() as client:
            yield client
    
    @patch('routes.contentRoute.ContentModel')
    @patch('routes.contentRoute.render_template')  # 添加这个模拟以避免模板缺失错误
    def test_show_content_teacher(self, mock_render_template, mock_content_model, client, mock_mongo):
        # 设置
        mock_client, mock_db = mock_mongo
        
        # 模拟用户
        mock_db.users.find_one.return_value = {
            "_id": ObjectId("60d21b4667d0d8992e610c85"),
            "username": "teacher",
            "identity": "teacher"
        }
        
        # 模拟内容项目
        mock_content_items = [
            {"_id": ObjectId(), "title": "Lecture 1"},
            {"_id": ObjectId(), "title": "Lecture 2"}
        ]
        mock_content_model.return_value.get_teacher_content.return_value = mock_content_items
        
        # 模拟render_template函数以避免模板缺失错误
        mock_render_template.return_value = "Rendered Template"
        
        # 执行
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.get('/content')
        
        # 验证
        mock_db.users.find_one.assert_called_once_with({"username": "teacher"})
        mock_content_model.return_value.get_teacher_content.assert_called_once_with(str(ObjectId("60d21b4667d0d8992e610c85")))
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "teacher_content.html" in args
        assert "content_items" in kwargs
    
    @patch('routes.contentRoute.ContentModel')
    @patch('routes.contentRoute.render_template')  # 添加这个模拟以避免模板缺失错误
    def test_show_content_student(self, mock_render_template, mock_content_model, client, mock_mongo):
        # 设置
        mock_client, mock_db = mock_mongo
        
        # 模拟内容项目
        mock_content_items = [
            {"_id": ObjectId(), "title": "Lecture 1"},
            {"_id": ObjectId(), "title": "Lecture 2"}
        ]
        mock_content_model.return_value.get_all_content.return_value = mock_content_items
        
        # 模拟render_template函数以避免模板缺失错误
        mock_render_template.return_value = "Rendered Template"
        
        # 执行
        with client.session_transaction() as sess:
            sess['username'] = 'student'
            sess['identity'] = 'student'
            
        response = client.get('/content')
        
        # 验证
        mock_content_model.return_value.get_all_content.assert_called_once()
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "student_content.html" in args
        assert "content_items" in kwargs
    
    @patch('routes.contentRoute.ContentModel')
    @patch('routes.contentRoute.render_template')  # 添加这个模拟以避免模板缺失错误
    def test_create_content_get(self, mock_render_template, mock_content_model, client, mock_mongo):
        # 设置
        mock_client, mock_db = mock_mongo
        
        # 模拟GitHub信息
        mock_db.github_accounts.find_one.return_value = {
            "username": "teacher",
            "repo": "teacher/repo",
            "access_token": "test_token"
        }
        
        # 模拟render_template函数以避免模板缺失错误
        mock_render_template.return_value = "Rendered Template"
        
        # 执行
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.get('/content/create')
        
        # 验证
        mock_db.github_accounts.find_one.assert_called_once_with({"username": "teacher"})
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "create_content.html" in args
        assert "github_info" in kwargs
    
    @patch('routes.contentRoute.ContentModel')
    @patch('routes.contentRoute.redirect')  # 添加这个模拟以避免重定向错误
    def test_create_content_post(self, mock_redirect, mock_content_model, client, mock_mongo):
        # 设置
        mock_client, mock_db = mock_mongo
        
        # 模拟用户
        mock_db.users.find_one.return_value = {
            "_id": ObjectId("60d21b4667d0d8992e610c85"),
            "username": "teacher",
            "identity": "teacher"
        }
        
        # 模拟GitHub信息
        mock_db.github_accounts.find_one.return_value = {
            "username": "teacher",
            "repo": "teacher/repo",
            "repo_url": "https://github.com/teacher/repo"
        }
        
        # 模拟内容创建
        mock_content_model.return_value.create_content.return_value = "new_content_id"
        
        # 模拟重定向
        mock_redirect.return_value = "Redirected"
        
        # 执行
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        form_data = {
            "title": "Test Content",
            "description": "Test Description",
            "github_repo_path": "lectures/test"
        }
        response = client.post('/content/create', data=form_data)
        
        # 验证数据库调用
        mock_db.users.find_one.assert_called_once_with({"username": "teacher"})
        mock_db.github_accounts.find_one.assert_called_once_with({"username": "teacher"})
        mock_content_model.return_value.create_content.assert_called_once()
        
        # 验证create_content调用参数
        args, kwargs = mock_content_model.return_value.create_content.call_args
        assert kwargs["teacher_id"] == str(ObjectId("60d21b4667d0d8992e610c85"))
        assert kwargs["title"] == "Test Content"
        assert kwargs["description"] == "Test Description"
        assert "github_repo_url" in kwargs
        assert kwargs["github_repo_path"] == "lectures/test"
        
        # 验证重定向
        mock_redirect.assert_called_once_with(url_for('content.show_content'))
    
    @patch('routes.contentRoute.ContentModel')
    @patch('routes.contentRoute.render_template')
    def test_view_content(self, mock_render_template, mock_content_model, client):
        # 设置
        content_id = "60d21b4667d0d8992e610c88"
        mock_content = {
            "_id": ObjectId(content_id),
            "title": "Test Content",
            "description": "Test Description",
            "teacher_id": "60d21b4667d0d8992e610c85"
        }
        mock_content_model.return_value.get_content.return_value = mock_content
        
        # 模拟模板渲染
        mock_render_template.return_value = "Rendered Template"
        
        # 执行
        with client.session_transaction() as sess:
            sess['username'] = 'student'
            sess['identity'] = 'student'
            
        response = client.get(f'/content/{content_id}')
        
        # 验证
        mock_content_model.return_value.get_content.assert_called_once_with(content_id)
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "content_detail.html" in args
        assert "content" in kwargs