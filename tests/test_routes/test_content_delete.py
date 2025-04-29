# tests/test_routes/test_content_delete.py
import pytest
from bson.objectid import ObjectId
from unittest.mock import patch, MagicMock

class TestContentDelete:

    @patch('routes.contentRoute.redirect')
    @patch('routes.contentRoute.url_for')
    def test_delete_not_logged_in(self, mock_url_for, mock_redirect, client):
            mock_url_for.return_value = '/home'
            with client.session_transaction() as sess:
                sess.clear()
            r = client.post(f'/content/{ObjectId()}/delete')

    @patch('routes.contentRoute.redirect')
    @patch('routes.contentRoute.url_for')
    @patch('routes.contentRoute.content_model')
    @patch('routes.contentRoute.users')
    def test_delete_success(self, mock_users, mock_cm, mock_url_for, mock_redirect, client):
        cid = str(ObjectId())
        teacher_id = str(ObjectId())
        # content 属于 this teacher
        mock_cm.get_content.return_value = {'_id': ObjectId(cid), 'teacher_id': teacher_id}
        # users.lookup 得到当前用户 ID
        mock_users.find_one.return_value = {'_id': ObjectId(teacher_id), 'username': 't'}
        mock_cm.delete_content.return_value = True
        mock_url_for.return_value = '/content'

        with client.session_transaction() as sess:
            sess['username'] = 't'; sess['identity'] = 'teacher'

        r = client.post(f'/content/{cid}/delete')
        mock_url_for.assert_called_once_with('content.show_content')
        mock_redirect.assert_called_once_with('/content')

    @patch('routes.contentRoute.content_model')
    @patch('routes.contentRoute.users')
    def test_delete_unauthorized_teacher_mismatch(self, mock_users, mock_cm, client):
        cid = str(ObjectId())
        # content 不属于当前 teacher
        mock_cm.get_content.return_value = {'_id': ObjectId(cid), 'teacher_id': str(ObjectId())}
        mock_users.find_one.return_value = {'_id': ObjectId(), 'username': 't'}
        with client.session_transaction() as sess:
            sess['username'] = 't'; sess['identity'] = 'teacher'

        r = client.post(f'/content/{cid}/delete')
        assert r.status_code == 403
        assert b"Unauthorized" in r.data
