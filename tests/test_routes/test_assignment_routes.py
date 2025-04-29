import pytest
from unittest.mock import MagicMock, patch
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from routes.assignmentRoute import assignment_bp
from flask import Flask

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
    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.SubmissionModel')
    def test_show_assignments_teacher(self, mock_submission_model, mock_assignment_model, mock_render_template, client, mock_mongo):
        mock_client, mock_db = mock_mongo
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(), "username": "teacher", "identity": "teacher"
        }
        mock_assignments = [
            {"_id": ObjectId(), "title": "A1"},
            {"_id": ObjectId(), "title": "A2"}
        ]
        mock_assignment_model.return_value.get_teacher_assignments.return_value = mock_assignments
        mock_render_template.return_value = "ok"

        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'

        resp = client.get('/assignments')

        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "teacher_assignments.html" in args
        assert "assignments" in kwargs
        mock_assignment_model.return_value.get_teacher_assignments.assert_called_once()

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.SubmissionModel')
    def test_show_assignments_student(self, mock_submission_model, mock_assignment_model, mock_render_template, client, mock_mongo):
        mock_client, mock_db = mock_mongo
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(), "username": "student", "identity": "student"
        }
        now = datetime.now()
        mock_asg = [
            {"_id": ObjectId(), "title": "A1", "due_date": (now+timedelta(days=1)).isoformat()},
            {"_id": ObjectId(), "title": "A2", "due_date": (now-timedelta(days=1)).isoformat()},
        ]
        mock_assignment_model.return_value.get_all_assignments.return_value = mock_asg
        mock_submission_model.return_value.get_student_submissions.return_value = [
            {"assignment_id": str(mock_asg[0]["_id"]), "status": "submitted"}
        ]
        mock_render_template.return_value = "ok"

        with client.session_transaction() as sess:
            sess['username'] = 'student'
            sess['identity'] = 'student'

        resp = client.get('/assignments')

        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "student_assignments.html" in args
        assert "assignments" in kwargs
        assert "submissions" in kwargs
        mock_assignment_model.return_value.get_all_assignments.assert_called_once()
        mock_submission_model.return_value.get_student_submissions.assert_called_once()

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.github_accounts')
    def test_create_assignment_get(self, mock_github_accounts, mock_render_template, client):
        mock_github_accounts.find_one.return_value = {"repo": "u/r", "access_token": "t"}
        mock_render_template.return_value = "ok"
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
        resp = client.get('/assignments/create')
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "create_assignment.html" in args
        assert "github_info" in kwargs

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.send_mail')
    @patch('routes.assignmentRoute.github_accounts')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.AssignmentModel')
    def test_create_assignment_post(self, mock_assignment_model, mock_users, mock_github_accounts, mock_send_mail, mock_redirect, client):
        mock_users.find_one.return_value = {"_id": ObjectId(), "username": "teacher", "identity": "teacher"}
        mock_github_accounts.find_one.return_value = {"repo": "u/r", "repo_url": "https://x",}
        mock_assignment_model.return_value.create_assignment.return_value = "newid"
        mock_users.find.return_value = [
            {"email": "s1@e"}, {"email": "s2@e"}
        ]
        mock_redirect.return_value = "redir"
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'; sess['identity']='teacher'
        data = {
            "title": "T", "description":"D",
            "due_date":"2025-05-01","due_time":"12:00",
            "github_repo_path":"p"
        }
        resp = client.post('/assignments/create', data=data)
        # create_assignment should be called once
        mock_assignment_model.return_value.create_assignment.assert_called_once()
        _, kwargs = mock_assignment_model.return_value.create_assignment.call_args
        assert kwargs["title"] == "T"
        assert "2025-05-01T12:00:00" in kwargs["due_date"]
        # send_mail twice
        assert mock_send_mail.call_count == 2
        mock_redirect.assert_called_once()

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.SubmissionModel')
    @patch('routes.assignmentRoute.AssignmentModel')
    @patch('routes.assignmentRoute.users')
    def test_view_assignment_teacher(self, mock_users, mock_assignment_model, mock_submission_model, mock_render_template, client):
        aid = str(ObjectId())
        mock_assignment_model.return_value.get_assignment.return_value = {
            "_id": ObjectId(aid), "title":"T","description":"D","teacher_id":str(ObjectId())
        }
        mock_submission_model.return_value.get_assignment_submissions.return_value = [
            {"_id": ObjectId(), "student_id": str(ObjectId()), "status":"submitted"}
        ]
        # first users.find_one for teacher, second for student username
        mock_users.find_one.side_effect = [
            {"_id": ObjectId(), "username":"teacher","identity":"teacher"},
            {"username":"stu"}
        ]
        mock_render_template.return_value = "ok"
        with client.session_transaction() as sess:
            sess['username']='teacher'; sess['identity']='teacher'
        resp = client.get(f'/assignments/{aid}')
        mock_assignment_model.return_value.get_assignment.assert_called_once_with(aid)
        mock_submission_model.return_value.get_assignment_submissions.assert_called_once_with(aid)
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "teacher_assignment_detail.html" in args
        assert "assignment" in kwargs and "submissions" in kwargs

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.github_accounts')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.SubmissionModel')
    @patch('routes.assignmentRoute.AssignmentModel')
    def test_view_assignment_student(self, mock_assignment_model, mock_submission_model, mock_users, mock_github_accounts, mock_render_template, client):
        aid = str(ObjectId())
        mock_assignment_model.return_value.get_assignment.return_value = {
            "_id": ObjectId(aid), "title":"T","description":"D","teacher_id":str(ObjectId())
        }
        mock_users.find_one.return_value = {"_id": ObjectId(), "username":"stu","identity":"student"}
        mock_submission_model.return_value.get_student_assignment_submission.return_value = {
            "_id": ObjectId(), "student_id":str(ObjectId()), "assignment_id":aid, "github_link":"L", "status":"submitted"
        }
        mock_github_accounts.find_one.return_value = {"repo":"u/r","repo_url":"x"}
        mock_render_template.return_value = "ok"
        with client.session_transaction() as sess:
            sess['username']='stu'; sess['identity']='student'
        resp = client.get(f'/assignments/{aid}')
        mock_assignment_model.return_value.get_assignment.assert_called_once_with(aid)
        mock_submission_model.return_value.get_student_assignment_submission.assert_called_once()
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "student_assignment_detail.html" in args
        assert "assignment" in kwargs and "submission" in kwargs and "github_info" in kwargs

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.SubmissionModel')
    @patch('routes.assignmentRoute.users')
    def test_submit_assignment(self, mock_users, mock_submission_model, mock_redirect, client):
        aid = str(ObjectId())
        mock_users.find_one.return_value = {"_id": ObjectId(), "username":"stu","identity":"student"}
        mock_submission_model.return_value.get_student_assignment_submission.return_value = None
        mock_submission_model.return_value.create_submission.return_value = "subid"
        mock_redirect.return_value = "redir"
        with client.session_transaction() as sess:
            sess['username']='stu'; sess['identity']='student'
        data = {"github_link":"L","readme_content":"C"}
        resp = client.post(f'/assignments/{aid}/submit', data=data)
        # should check existing then create
        mock_submission_model.return_value.get_student_assignment_submission.assert_called_once()
        mock_submission_model.return_value.create_submission.assert_called_once()
        _, kwargs = mock_submission_model.return_value.create_submission.call_args
        assert kwargs["assignment_id"] == aid
        assert kwargs["readme_content"] == "C"
        mock_redirect.assert_called_once()

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.SubmissionModel')
    def test_grade_submission(self, mock_submission_model, mock_redirect, client):
        sid = str(ObjectId())
        mock_submission_model.return_value.get_submission.return_value = {"_id": ObjectId(sid), "assignment_id": str(ObjectId())}
        mock_submission_model.return_value.add_feedback.return_value = True
        mock_redirect.return_value = "redir"
        with client.session_transaction() as sess:
            sess['username']='teacher'; sess['identity']='teacher'
        data = {"grade":"90","feedback":"OK"}
        resp = client.post(f'/submissions/{sid}/grade', data=data)
        mock_submission_model.return_value.add_feedback.assert_called_with(sid, 90.0, "OK")
        mock_submission_model.return_value.get_submission.assert_called_once_with(sid)
        mock_redirect.assert_called_once()

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.SubmissionModel')
    @patch('routes.assignmentRoute.AssignmentModel')
    def test_delete_assignment(self, mock_assignment_model, mock_submission_model, client):
        aid = str(ObjectId())
        mock_assignment_model.return_value.get_assignment.return_value = {"_id": ObjectId(aid), "teacher_id":str(ObjectId())}
        with patch('routes.assignmentRoute.users') as mock_users:
            mock_users.find_one.return_value = {"_id": ObjectId(), "username":"teacher","identity":"teacher"}
            mock_submission_model.return_value.delete_by_assignment.return_value = 2
            mock_assignment_model.return_value.delete_assignment.return_value = True
            mock_redirect = patch('routes.assignmentRoute.redirect').start()
            mock_redirect.return_value = "redir"
            with client.session_transaction() as sess:
                sess['username']='teacher'; sess['identity']='teacher'
            resp = client.post(f'/assignments/{aid}/delete')
            mock_assignment_model.return_value.get_assignment.assert_called_once_with(aid)
            mock_submission_model.return_value.delete_by_assignment.assert_called_once_with(aid)
            mock_assignment_model.return_value.delete_assignment.assert_called_once_with(aid)
            patch.stopall()

    @patch('routes.assignmentRoute.send_file')
    @patch('routes.assignmentRoute.requests')
    @patch('routes.assignmentRoute.github_accounts')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.AssignmentModel')
    def test_download_assignment(self, mock_assignment_model, mock_users, mock_github_accounts, mock_requests, mock_send_file, client):
        aid = str(ObjectId())
        mock_assignment_model.return_value.get_assignment.return_value = {
            "_id": ObjectId(aid),
            "teacher_id": str(ObjectId()),
            "github_repo_url":"u","github_repo_path":"p"
        }
        mock_users.find_one.return_value = {"_id":ObjectId(),"username":"stu"}
        mock_github_accounts.find_one.return_value = {"repo":"u/r","access_token":"t"}
        with patch('routes.assignmentRoute.is_repo_path_file') as mock_is_file:
            mock_is_file.return_value = False
            with patch('routes.assignmentRoute.zipfile.ZipFile'), patch('routes.assignmentRoute.BytesIO') as mock_b:
                mock_b.return_value = MagicMock()
                with patch('routes.assignmentRoute.get_repo_contents') as mock_gc:
                    mock_gc.return_value = []
                    with client.session_transaction() as sess:
                        sess['username']='stu'; sess['identity']='student'
                    resp = client.get(f'/assignments/{aid}/download')
                    mock_assignment_model.return_value.get_assignment.assert_called_once_with(aid)
                    mock_users.find_one.assert_called_once()
                    mock_github_accounts.find_one.assert_called_once()
                    mock_is_file.assert_called_once()
                    mock_send_file.assert_called_once()

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.SubmissionModel')
    def test_view_readme(self, mock_submission_model, mock_render_template, client):
        sid = str(ObjectId())
        mock_submission_model.return_value.get_submission.return_value = {
            "_id": ObjectId(sid), "student_id":str(ObjectId()), "readme_content":"# hi", "assignment_id":str(ObjectId()), "status":"submitted"
        }
        mock_render_template.return_value = "ok"
        with client.session_transaction() as sess:
            sess['username']='teacher'; sess['identity']='teacher'
        resp = client.get(f'/submissions/{sid}/readme')
        mock_submission_model.return_value.get_submission.assert_called_once_with(sid)
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        assert "view_readme.html" in args
        assert kwargs["readme_content"].startswith("# hi")
        assert "submission" in kwargs
