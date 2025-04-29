# tests/test_routes/test_content_preview.py
import base64
import pytest
from bson.objectid import ObjectId
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def login(client):
    # 默认以 student 登录
    with client.session_transaction() as sess:
        sess['username'] = 'stu'
        sess['identity'] = 'student'

class TestContentPreview:

    @patch('routes.contentRoute.render_template')
    @patch('routes.contentRoute.requests.get')
    @patch('routes.contentRoute.github_accounts')
    @patch('routes.contentRoute.users')
    @patch('routes.contentRoute.content_model')
    def test_preview_markdown(self, mock_cm, mock_users, mock_acc, mock_get, mock_render, client):
        cid = str(ObjectId())
        # 模拟 content
        mock_cm.get_content.return_value = {
            "_id": ObjectId(cid),
            "teacher_id": str(ObjectId()),
            "github_repo_path": ""
        }
        # 模拟 teacher lookup
        mock_users.find_one.return_value = {"_id": ObjectId(), "username": "t"}
        # 模拟 GitHub 账号
        mock_acc.find_one.return_value = {"access_token": "tok", "repo": "u/r"}
        # 模拟 GitHub API 返回
        resp = MagicMock(status_code=200, content=b"# Hello")
        mock_get.return_value = resp

        client.get(f'/content/{cid}/preview/README.md')
        mock_render.assert_called_once_with(
            'preview_markdown.html',
            content="# Hello",
            file_name="README.md",
            item=mock_cm.get_content.return_value,
            item_type='content',
            username='stu',
            identity='student'
        )

    @patch('routes.contentRoute.render_template')
    @patch('routes.contentRoute.requests.get')
    @patch('routes.contentRoute.github_accounts')
    @patch('routes.contentRoute.users')
    @patch('routes.contentRoute.content_model')
    def test_preview_code(self, mock_cm, mock_users, mock_acc, mock_get, mock_render, client):
        cid = str(ObjectId())
        mock_cm.get_content.return_value = {
            "_id": ObjectId(cid),
            "teacher_id": str(ObjectId()),
            "github_repo_path": ""
        }
        mock_users.find_one.return_value = {"_id": ObjectId(), "username": "t"}
        mock_acc.find_one.return_value = {"access_token": "tok", "repo": "u/r"}
        resp = MagicMock(status_code=200, content=b'print("hi")')
        mock_get.return_value = resp

        client.get(f'/content/{cid}/preview/script.py')
        mock_render.assert_called_once_with(
            'preview_code.html',
            content='print("hi")',
            file_name='script.py',
            language='py',
            item=mock_cm.get_content.return_value,
            item_type='content',
            username='stu',
            identity='student'
        )

    @patch('routes.contentRoute.render_template')
    @patch('routes.contentRoute.requests.get')
    @patch('routes.contentRoute.github_accounts')
    @patch('routes.contentRoute.users')
    @patch('routes.contentRoute.content_model')
    def test_preview_pdf(self, mock_cm, mock_users, mock_acc, mock_get, mock_render, client):
        cid = str(ObjectId())
        mock_cm.get_content.return_value = {
            "_id": ObjectId(cid),
            "teacher_id": str(ObjectId()),
            "github_repo_path": ""
        }
        mock_users.find_one.return_value = {"_id": ObjectId(), "username": "t"}
        mock_acc.find_one.return_value = {"access_token": "tok", "repo": "u/r"}
        pdf_bytes = b"%PDF-1.4 data"
        resp = MagicMock(status_code=200, content=pdf_bytes)
        mock_get.return_value = resp

        client.get(f'/content/{cid}/preview/doc.pdf')
        args, kwargs = mock_render.call_args
        assert args[0] == 'preview_pdf.html'
        # PDF data 应该以 data:application/pdf;base64, 开头
        assert kwargs['pdf_data'].startswith('data:application/pdf;base64,')
        assert kwargs['file_name'] == 'doc.pdf'
        assert kwargs['item'] == mock_cm.get_content.return_value

    @patch('routes.contentRoute.requests.get')
    @patch('routes.contentRoute.github_accounts')
    @patch('routes.contentRoute.users')
    @patch('routes.contentRoute.content_model')
    def test_preview_fallback_binary(self, mock_cm, mock_users, mock_acc, mock_get, client):
        cid = str(ObjectId())
        mock_cm.get_content.return_value = {
            "_id": ObjectId(cid),
            "teacher_id": str(ObjectId()),
            "github_repo_path": ""
        }
        mock_users.find_one.return_value = {"_id": ObjectId(), "username": "t"}
        mock_acc.find_one.return_value = {"access_token": "tok", "repo": "u/r"}
        # 非 200 或非特定后缀，都返回 Response
        resp = MagicMock(status_code=200, content=b"data")
        mock_get.return_value = resp

        r = client.get(f'/content/{cid}/preview/file.unknown')
        # 应该直接返回二进制
        assert r.status_code == 200
        # Content-Disposition header 包含文件名
        assert 'attachment; filename=file.unknown' in r.headers['Content-Disposition']
        assert r.data == b"data"
