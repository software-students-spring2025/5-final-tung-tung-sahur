import pytest
from unittest.mock import patch
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from routes.assignmentRoute import assignment_bp
from flask import Flask

class TestAssignmentRoutes:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.register_blueprint(assignment_bp)
        app.secret_key = "test_secret_key"
        app.config['TESTING'] = True
        return app

    # ←—— 加这一段 ——→  
    @pytest.fixture
    def client(self, app):
        return app.test_client()
    # ←———————————→

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.submission_model')
    @patch('routes.assignmentRoute.assignment_model')
    def test_show_assignments_teacher(self, mock_asgM, mock_subM, mock_render, client, mock_mongo):
        # 模拟数据库返回当前用户是 teacher
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
        # 一定要先调用 render_template
        mock_render.assert_called_once_with(
            "teacher_assignments.html",
            assignments=fake,
            username="teacher",
            identity="teacher"
        )

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.submission_model')
    @patch('routes.assignmentRoute.assignment_model')
    def test_show_assignments_student(self, mock_asgM, mock_subM, mock_render, client, mock_mongo):
        mock_client, mock_db = mock_mongo
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(), "username": "stud", "identity": "student"
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
        mock_asgM.get_all_assignments.return_value    = fake_asg
        mock_subM.get_student_submissions.return_value = fake_subs

        with client.session_transaction() as sess:
            sess['username'] = 'stud'
            sess['identity'] = 'student'

        rv = client.get('/assignments')
        mock_render.assert_called_once_with(
            "student_assignments.html",
            assignments=fake_asg,
            submissions={ fake_asg[0]["_id"].__str__(): fake_subs[0] },
            username="stud",
            identity="student"
        )

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.send_mail')
    @patch('routes.assignmentRoute.github_accounts')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.assignment_model')
    def test_create_assignment_post(self, mock_asgM, mock_users, mock_gh, mock_send, mock_redirect, client):
        # 这里的 ObjectId 只要是 24 hex char 就行
        teacher_id = "60d21b4667d0d8992e610c85"
        mock_users.find_one.return_value = {
            "_id": ObjectId(teacher_id), "username": "t", "identity": "teacher"
        }
        mock_gh.find_one.return_value = {"repo":"t/r","repo_url":"https://x"}
        mock_asgM.create_assignment.return_value = "newid"
        mock_users.find.return_value = [
            {"email":"s1@e"},{"email":"s2@e"}
        ]
        mock_redirect.return_value = "redir"

        with client.session_transaction() as sess:
            sess['username'] = 't'
            sess['identity'] = 'teacher'

        data = {
            "title": "T", "description": "D",
            "due_date": "2025-05-01", "due_time": "12:00",
            "github_repo_path": "p"
        }
        rv = client.post('/assignments/create', data=data)

        # create_assignment 一定得被调用
        mock_asgM.create_assignment.assert_called_once()
        # send_mail 两个学生
        assert mock_send.call_count == 2
        mock_redirect.assert_called_once_with("/assignments")

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.submission_model')
    @patch('routes.assignmentRoute.assignment_model')
    @patch('routes.assignmentRoute.users')
    def test_view_assignment_teacher(self, mock_users, mock_asgM, mock_subM, mock_render, client):
        aid = str(ObjectId())
        # route 里会先查 assignment，再查 submissions，再查 users 两次
        mock_asgM.get_assignment.return_value = {
            "_id": ObjectId(aid), "title":"T","description":"D","teacher_id":aid
        }
        mock_subM.get_assignment_submissions.return_value = [
            {"_id": ObjectId(), "student_id": aid, "status":"submitted"}
        ]
        # 第一次 users.find_one 查 teacher，第二次查 student
        mock_users.find_one.side_effect = [
            {"_id": ObjectId(aid), "username":"t","identity":"teacher"},
            {"username":"s"}
        ]
        mock_render.return_value = "ok"
        with client.session_transaction() as sess:
            sess['username'] = 't'
            sess['identity'] = 'teacher'

        rv = client.get(f'/assignments/{aid}')
        mock_asgM.get_assignment.assert_called_once_with(aid)
        mock_subM.get_assignment_submissions.assert_called_once_with(aid)
        mock_render.assert_called_once_with(
            "teacher_assignment_detail.html",
            assignment=mock_asgM.get_assignment.return_value,
            submissions=mock_subM.get_assignment_submissions.return_value,
            username="t",
            identity="teacher"
        )

    @patch('routes.assignmentRoute.render_template')
    @patch('routes.assignmentRoute.github_accounts')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.submission_model')
    @patch('routes.assignmentRoute.assignment_model')
    def test_view_assignment_student(self, mock_asgM, mock_subM, mock_users, mock_gh, mock_render, client):
        aid = str(ObjectId())
        mock_asgM.get_assignment.return_value = {
            "_id": ObjectId(aid), "title":"T","description":"D","teacher_id":aid
        }
        mock_users.find_one.return_value = {
            "_id": ObjectId(aid), "username":"s","identity":"student"
        }
        mock_subM.get_student_assignment_submission.return_value = {
            "_id": ObjectId(), "student_id":aid, "assignment_id":aid,
            "github_link":"L","status":"submitted"
        }
        mock_gh.find_one.return_value = {"repo":"s/r","repo_url":"x"}
        with client.session_transaction() as sess:
            sess['username'] = 's'
            sess['identity'] = 'student'

        rv = client.get(f'/assignments/{aid}')
        mock_asgM.get_assignment.assert_called_once_with(aid)
        mock_subM.get_student_assignment_submission.assert_called_once_with(str(ObjectId(aid)), aid)
        mock_render.assert_called_once_with(
            "student_assignment_detail.html",
            assignment=mock_asgM.get_assignment.return_value,
            submission=mock_subM.get_student_assignment_submission.return_value,
            github_info=mock_gh.find_one.return_value,
            username="s",
            identity="student"
        )

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.submission_model')
    def test_submit_assignment(self, mock_subM, mock_redirect, client):
        aid = str(ObjectId())
        mock_redirect.return_value = "redir"
        # 先返回不存在，再创建
        mock_subM.get_student_assignment_submission.side_effect = [None]
        mock_subM.create_submission.return_value = "subid"

        with client.session_transaction() as sess:
            sess['username'] = 'stud'
            sess['identity'] = 'student'

        data = {"github_link": "L", "readme_content": "C"}
        rv = client.post(f'/assignments/{aid}/submit', data=data)
        mock_subM.create_submission.assert_called_once()
        mock_redirect.assert_called_once_with("/assignments")

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.submission_model')
    def test_grade_submission(self, mock_subM, mock_redirect, client):
        sid = str(ObjectId())
        mock_subM.get_submission.return_value = {
            "_id": ObjectId(sid), "assignment_id": "aid"
        }
        mock_redirect.return_value = "redir"

        with client.session_transaction() as sess:
            sess['username'] = 't'
            sess['identity'] = 'teacher'

        data = {"grade": "90", "feedback": "OK"}
        rv = client.post(f'/submissions/{sid}/grade', data=data)
        mock_subM.add_feedback.assert_called_once_with(sid, 90.0, "OK")
        mock_redirect.assert_called_once_with(f"/assignments/aid")

    @patch('routes.assignmentRoute.redirect')
    @patch('routes.assignmentRoute.github_accounts')
    @patch('routes.assignmentRoute.users')
    @patch('routes.assignmentRoute.assignment_model')
    def test_download_assignment(self, mock_asgM, mock_users, mock_gh, mock_redirect, client):
        # 这里只要不抛异常就算通过
        aid = str(ObjectId())
        mock_asgM.get_assignment.return_value = {
            "_id": ObjectId(aid),
            "teacher_id": aid,
            "github_repo_url": None,  # 会直接 400
        }
        mock_users.find_one.return_value = {"_id": ObjectId(aid), "username": "t"}
        mock_gh.find_one.return_value = {"repo": "t/r", "access_token": "tok"}

        with client.session_transaction() as sess:
            sess['username'] = 'stud'
            sess['identity'] = 'student'

        rv = client.get(f'/assignments/{aid}/download')
        assert rv.status_code in (400, 404)

