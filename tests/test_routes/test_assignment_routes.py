import pytest
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from flask import Flask
from routes.assignmentRoute import assignment_bp
from unittest.mock import patch

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(assignment_bp)
    app.secret_key = "test_secret_key"
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestAssignmentRoutes:
    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.submission_model')
    @patch('routes.assignmentRoute.assignment_model')
    def test_show_assignments_teacher(self, mock_asgM, mock_subM, mock_render, client, mock_mongo):
        mock_client, mock_db = mock_mongo
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(), "username": "teacher", "identity": "teacher"
        }
        fake = [
            {"_id": ObjectId(), "title": "A1"},
            {"_id": ObjectId(), "title": "A2"}
        ]
        mock_asgM.get_teacher_assignments.return_value = fake

        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        rv = client.get('/assignments')
        mock_render.assert_called_once_with(
            "teacher_assignments.html",
            assignments=fake,
            username="teacher",
            identity="teacher"
        )
        mock_asgM.get_teacher_assignments.assert_called_once()

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.submission_model')
    @patch('routes.assignmentRoute.assignment_model')
    def test_show_assignments_student(self, mock_asgM, mock_subM, mock_render, client, mock_mongo):
        mock_client, mock_db = mock_mongo
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(), "username": "student", "identity": "student"
        }
        now = datetime.now()
        fake_asg = [
            {
                "_id": ObjectId(),
                "title": "A1",
                "due_date": (now + timedelta(days=1)).isoformat()
            },
            {
                "_id": ObjectId(),
                "title": "A2",
                "due_date": (now - timedelta(days=1)).isoformat()
            },
        ]
        fake_subs = [
            {"assignment_id": str(fake_asg[0]["_id"]), "status": "submitted"}
        ]
        mock_asgM.get_all_assignments.return_value = fake_asg
        mock_subM.get_student_submissions.return_value = fake_subs

        with client.session_transaction() as sess:
            sess['username'] = 'student'
            sess['identity'] = 'student'

        rv = client.get('/assignments')
        mock_render.assert_called_once()
        tpl = mock_render.call_args[0][0]
        ctx = mock_render.call_args[1]
        assert tpl == "student_assignments.html"
        assert ctx["assignments"] == fake_asg
        # submissions dict should map assignment_id to submission
        assert ctx["submissions"] == {str(fake_asg[0]["_id"]): fake_subs[0]}
        mock_asgM.get_all_assignments.assert_called_once()
        mock_subM.get_student_submissions.assert_called_once()

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.github_accounts')
    def test_create_assignment_get(self, mock_gh, mock_render, client):
        mock_gh.find_one.return_value = {
            "username": "t", "repo": "t/r", "access_token": "token"
        }
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        rv = client.get('/assignments/create')
        mock_render.assert_called_once_with(
            "create_assignment.html",
            github_info=mock_gh.find_one.return_value,
            username="teacher",
            identity="teacher"
        )

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.send_mail')
    @patch('routes.assignmentRoute.github_accounts')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.assignment_model')
    def test_create_assignment_post(self, mock_asgM, mock_users, mock_gh, mock_send, mock_redirect, client):
        mock_users.find_one.return_value = {
            "_id": ObjectId("60d21b"), "username": "teacher", "identity": "teacher"
        }
        mock_gh.find_one.return_value = {
            "username": "teacher", "repo": "t/r", "repo_url": "u"
        }
        mock_users.find.return_value = [{"email": "s1"}, {"email": "s2"}]
        mock_asgM.create_assignment.return_value = "newid"
        mock_redirect.return_value = "redir"

        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        data = {
            "title": "T",
            "description": "D",
            "due_date": "2025-05-01",
            "due_time": "23:59",
            "github_repo_path": "p"
        }
        rv = client.post('/assignments/create', data=data)
        mock_asgM.create_assignment.assert_called_once()
        assert mock_send.call_count == 2
        mock_redirect.assert_called_once()

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.submission_model')
    @patch('routes.assignmentRoute.assignment_model')
    @patch('routes.assignmentRoute.users')
    def test_view_assignment_teacher(self, mock_users, mock_asgM, mock_subM, mock_render, client):
        aid = str(ObjectId())
        stub_asg = {
            "_id": ObjectId(aid),
            "title": "T",
            "description": "D",
            "teacher_id": str(ObjectId())
        }
        mock_asgM.get_assignment.return_value = stub_asg
        mock_subM.get_assignment_submissions.return_value = [
            {"_id": ObjectId(), "student_id": "X", "status": "submitted"}
        ]
        mock_users.find_one.side_effect = [
            {"_id": ObjectId(), "username": "teacher", "identity": "teacher"},
            {"username": "stud"}
        ]

        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        rv = client.get(f'/assignments/{aid}')
        mock_asgM.get_assignment.assert_called_once_with(aid)
        mock_subM.get_assignment_submissions.assert_called_once_with(aid)
        mock_render.assert_called_once()

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.github_accounts')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.submission_model')
    @patch('routes.assignmentRoute.assignment_model')
    def test_view_assignment_student(self, mock_asgM, mock_subM, mock_users, mock_gh, mock_render, client):
        aid = str(ObjectId())
        mock_asgM.get_assignment.return_value = {
            "_id": ObjectId(aid),
            "title": "T",
            "description": "D",
            "teacher_id": "X"
        }
        mock_users.find_one.return_value = {
            "_id": ObjectId(), "username": "stu", "identity": "student"
        }
        mock_subM.get_student_assignment_submission.return_value = {
            "_id": ObjectId(),
            "assignment_id": aid,
            "github_link": "L",
            "status": "submitted"
        }
        mock_gh.find_one.return_value = {"repo": "u/r", "repo_url": "u"}

        with client.session_transaction() as sess:
            sess['username'] = 'stu'
            sess['identity'] = 'student'

        rv = client.get(f'/assignments/{aid}')
        mock_asgM.get_assignment.assert_called_once_with(aid)
        mock_subM.get_student_assignment_submission.assert_called_once()
        mock_render.assert_called_once()

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.submission_model')
    @patch('routes.assignmentRoute.users')
    def test_submit_assignment(self, mock_users, mock_subM, mock_redirect, client):
        aid = str(ObjectId())
        mock_users.find_one.return_value = {
            "_id": ObjectId(), "username": "stu", "identity": "student"
        }
        mock_subM.get_student_assignment_submission.return_value = None
        mock_subM.create_submission.return_value = "subid"
        mock_redirect.return_value = "redir"

        with client.session_transaction() as sess:
            sess['username'] = 'stu'
            sess['identity'] = 'student'

        data = {"github_link": "L", "readme_content": "C"}
        rv = client.post(f'/assignments/{aid}/submit', data=data)
        mock_subM.get_student_assignment_submission.assert_called_once()
        mock_subM.create_submission.assert_called_once()
        mock_redirect.assert_called_once()

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.submission_model')
    def test_grade_submission(self, mock_subM, mock_redirect, client):
        sid = str(ObjectId())
        mock_subM.get_submission.return_value = {
            "_id": ObjectId(sid), "assignment_id": "A"
        }
        mock_subM.add_feedback.return_value = True
        mock_redirect.return_value = "redir"

        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        data = {"grade": "90", "feedback": "OK"}
        rv = client.post(f'/submissions/{sid}/grade', data=data)
        mock_subM.add_feedback.assert_called_once_with(sid, 90.0, "OK")
        mock_redirect.assert_called_once()

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.submission_model')
    @patch('routes.assignmentRoute.assignment_model')
    @patch('routes.assignmentRoute.users')
    def test_delete_assignment(self, mock_users, mock_asgM, mock_subM, mock_redirect, client):
        aid = str(ObjectId())
        mock_asgM.get_assignment.return_value = {
            "_id": ObjectId(aid),
            "teacher_id": str(ObjectId())
        }
        mock_users.find_one.return_value = {
            "_id": ObjectId(), "username": "teacher", "identity": "teacher"
        }
        mock_subM.delete_by_assignment.return_value = 2
        mock_asgM.delete_assignment.return_value = True
        mock_redirect.return_value = "redir"

        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        rv = client.post(f'/assignments/{aid}/delete')
        mock_asgM.get_assignment.assert_called_once_with(aid)
        mock_subM.delete_by_assignment.assert_called_once_with(aid)
        mock_asgM.delete_assignment.assert_called_once_with(aid)
        mock_redirect.assert_called_once()

    @patch('routes.assignmentRoute.send_file')
    @patch('routes.assignmentRoute.requests')
    @patch('routes.assignmentRoute.github_accounts')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.assignment_model')
    def test_download_assignment(self, mock_asgM, mock_users, mock_gh, mock_req, mock_send_file, client):
        aid = str(ObjectId())
        mock_asgM.get_assignment.return_value = {
            "_id": ObjectId(aid),
            "teacher_id": str(ObjectId()),
            "github_repo_url": "u",
            "github_repo_path": "p"
        }
        mock_users.find_one.return_value = {"_id": ObjectId(), "username": "stu"}
        mock_gh.find_one.return_value = {"repo": "u/r", "access_token": "t"}

        with patch('routes.assignmentRoute.is_repo_path_file') as m_file:
            m_file.return_value = False
            with patch('routes.assignmentRoute.zipfile.ZipFile'), \
                 patch('routes.assignmentRoute.BytesIO') as m_b:
                m_b.return_value = object()
                with patch('routes.assignmentRoute.get_repo_contents') as m_gc:
                    m_gc.return_value = []
                    with client.session_transaction() as sess:
                        sess['username'] = 'stu'
                        sess['identity'] = 'student'
                    rv = client.get(f'/assignments/{aid}/download')
                    mock_asgM.get_assignment.assert_called_once_with(aid)
                    mock_send_file.assert_called_once()

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.submission_model')
    def test_view_readme(self, mock_subM, mock_render, client):
        sid = str(ObjectId())
        mock_subM.get_submission.return_value = {
            "_id": ObjectId(sid),
            "student_id": str(ObjectId()),
            "readme_content": "# hi",
            "assignment_id": str(ObjectId()),
            "status": "submitted"
        }

        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        rv = client.get(f'/submissions/{sid}/readme')
        mock_subM.get_submission.assert_called_once_with(sid)
        mock_render.assert_called_once_with(
            'view_readme.html',
            readme_content="# hi",
            submission=mock_subM.get_submission.return_value,
            username='teacher',
            identity='teacher'
        )
