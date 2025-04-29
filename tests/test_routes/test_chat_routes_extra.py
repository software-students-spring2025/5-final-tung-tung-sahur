# tests/test_routes/test_chat_routes_extra.py
import pytest
from unittest.mock import patch, MagicMock
import routes.chatRoute as CR

@pytest.fixture(autouse=True)
def clear_session(client):
    with client.session_transaction() as sess:
        sess.clear()
    yield
    with client.session_transaction() as sess:
        sess.clear()

class TestChatRoutesExtra:

    @patch('routes.chatRoute.redirect')
    @patch('routes.chatRoute.url_for')
    def test_chat_index_not_logged_in(self, mock_url_for, mock_redirect, client):
        mock_url_for.return_value = '/login'
        r = client.get('/chat/')
        mock_url_for.assert_called_once_with('login')
        mock_redirect.assert_called_once_with('/login')

    @patch('routes.chatRoute.render_template')
    @patch('routes.chatRoute.get_all_contacts')
    @patch('routes.chatRoute.chat_model')
    def test_chat_index_logged_in(self, mock_chat, mock_get_all, mock_render, client):
        # 模拟会话
        with client.session_transaction() as sess:
            sess['username'] = 'u'

        mock_chat.get_recent_contacts.return_value = ['a','b']
        mock_get_all.return_value = {'student': ['s'], 'teacher': ['t']}
        r = client.get('/chat/')
        mock_render.assert_called_once_with(
            "chat.html",
            contacts=['a','b'],
            all_contacts={'student':['s'],'teacher':['t']},
            selected=None,
            messages=[]
        )

    @patch('routes.chatRoute.redirect')
    @patch('routes.chatRoute.url_for')
    def test_chat_with_self(self, mock_url_for, mock_redirect, client):
        with client.session_transaction() as sess:
            sess['username'] = 'u'
        mock_url_for.return_value = '/chat/'
        r = client.get('/chat/with/u')
        mock_url_for.assert_called_once_with('chat.chat_index')
        mock_redirect.assert_called_once_with('/chat/')

    @patch('routes.chatRoute.render_template')
    @patch('routes.chatRoute.get_all_contacts')
    @patch('routes.chatRoute.chat_model')
    def test_chat_with_get(self, mock_chat, mock_get_all, mock_render, client):
        with client.session_transaction() as sess:
            sess['username'] = 'u'
        mock_chat.get_recent_contacts.return_value = ['x']
        mock_chat.get_conversation.return_value = [{'txt':'h'}]
        mock_get_all.return_value = {'student': [], 'teacher': []}

        r = client.get('/chat/with/v')
        mock_render.assert_called_once_with(
            "chat.html",
            contacts=['x'],
            all_contacts={'student':[],'teacher':[]},
            selected='v',
            messages=[{'txt':'h'}]
        )

    @patch('routes.chatRoute.redirect')
    @patch('routes.chatRoute.url_for')
    def test_chat_with_post_not_logged_in(self, mock_url_for, mock_redirect, client):
        # 没登录时 POST 也应跳 login
        mock_url_for.return_value = '/login'
        r = client.post('/chat/with/x', data={'message':'hi'})
        mock_url_for.assert_called_once_with('login')
        mock_redirect.assert_called_once_with('/login')
