# tests/test_routes/test_content_routes_extra.py

import pytest
from bson.objectid import ObjectId
from unittest.mock import patch, MagicMock

# 注意：所有测试都通过 client fixture 提供的测试客户端来发请求

class TestContentRoutesExtra:

    @patch('routes.contentRoute.render_template')
    @patch('routes.contentRoute.users')
    @patch('routes.contentRoute.content_model')
    def test_show_content_teacher(self, mock_cm, mock_users, mock_render, client):
        # 模拟当前用户是 teacher
        mock_users.find_one.return_value = {"_id": ObjectId(), "username": "t", "identity": "teacher"}
        fake_items = [{"_id": ObjectId(), "title": "T1"}]
        mock_cm.get_teacher_content.return_value = fake_items

        with client.session_transaction() as sess:
            sess['username'] = 't'
            sess['identity'] = 'teacher'

        resp = client.get('/content')
        # 应该渲染 teacher_content.html
        mock_render.assert_called_once_with(
            "teacher_content.html",
            content_items=fake_items,
            username="t",
            identity="teacher"
        )

    @patch('routes.contentRoute.render_template')
    @patch('routes.contentRoute.content_model')
    def test_show_content_student(self, mock_cm, mock_render, client):
        # 模拟当前用户是 student
        fake_items = [{"_id": ObjectId(), "title": "C1"}]
        mock_cm.get_all_content.return_value = fake_items

        with client.session_transaction() as sess:
            sess['username'] = 's'
            sess['identity'] = 'student'

        resp = client.get('/content')
        # 应该渲染 student_content.html
        mock_render.assert_called_once_with(
            "student_content.html",
            content_items=fake_items,
            username="s",
            identity="student"
        )

    @patch('routes.contentRoute.render_template')
    @patch('routes.contentRoute.github_accounts')
    def test_create_content_get_teacher(self, mock_accounts, mock_render, client):
        # GET /content/create 教师分支
        github_info = {"repo": "u/r", "repo_url": "https://github.com/u/r"}
        mock_accounts.find_one.return_value = github_info

        with client.session_transaction() as sess:
            sess['username'] = 't'
            sess['identity'] = 'teacher'

        resp = client.get('/content/create')
        mock_render.assert_called_once_with(
            "create_content.html",
            github_info=github_info,
            username="t",
            identity="teacher"
        )

    @patch('routes.contentRoute.redirect')
    @patch('routes.contentRoute.url_for')
    def test_create_content_get_unauthorized(self, mock_url_for, mock_redirect, client):
        # GET /content/create 非教师应该跳回 home
        mock_url_for.return_value = "/home"
        with client.session_transaction() as sess:
            sess['username'] = 's'
            sess['identity'] = 'student'

        resp = client.get('/content/create')
        mock_url_for.assert_called_once_with('home')
        mock_redirect.assert_called_once_with('/home')

    @patch('routes.contentRoute.content_model')
    def test_create_content_post_missing_fields(self, mock_cm, client):
        # POST /content/create 缺少必选字段应返回 400
        with client.session_transaction() as sess:
            sess['username'] = 't'
            sess['identity'] = 'teacher'

        resp = client.post('/content/create', data={"title": "T"})
        assert resp.status_code == 400
        assert b"Missing required fields" in resp.data

    @patch('routes.contentRoute.redirect')
    @patch('routes.contentRoute.url_for')
    def test_view_content_not_logged_in(self, mock_url_for, mock_redirect, client):
        # GET /content/<id> 未登录应跳 login
        mock_url_for.return_value = "/login"
        # 不在 session 中设置 username
        resp = client.get(f'/content/{ObjectId()}')
        mock_url_for.assert_called_once_with('login')
        mock_redirect.assert_called_once_with('/login')

    @patch('routes.contentRoute.render_template')
    @patch('routes.contentRoute.content_model')
    def test_view_content_found(self, mock_cm, mock_render, client):
        # GET /content/<id> 登录且存在 content -> 渲染 detail 模板
        cid = str(ObjectId())
        mock_cm.get_content.return_value = {"_id": ObjectId(cid), "title": "X"}

        with client.session_transaction() as sess:
            sess['username'] = 'u'
            sess['identity'] = 'student'

        resp = client.get(f'/content/{cid}')
        # 转换后的 _id 应该是 str(cid)
        expected_content = {"_id": cid, "title": "X"}
        mock_render.assert_called_once_with(
            "content_detail.html",
            content=expected_content,
            username="u",
            identity="student"
        )

    @patch('routes.contentRoute.content_model')
    def test_download_content_no_repo(self, mock_cm, client):
        # GET /content/<id>/download 如果 content.github_repo_url 为空 -> 400
        cid = str(ObjectId())
        mock_cm.get_content.return_value = {
            "_id": ObjectId(cid),
            "teacher_id": str(ObjectId()),
            "github_repo_url": None
        }
        with client.session_transaction() as sess:
            sess['username'] = 'u'

        resp = client.get(f'/content/{cid}/download')
        assert resp.status_code == 400
        assert b"No GitHub repository associated with this content" in resp.data
