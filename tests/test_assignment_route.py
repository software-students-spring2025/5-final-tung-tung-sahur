# tests/test_assignment_routes.py
import json
from datetime import datetime

import pytest
from flask import Flask
from unittest.mock import MagicMock, patch

# -----------------------------------------------------------------------------
#  Fixtures – build a minimal Flask app that only carries assignment_bp
# -----------------------------------------------------------------------------
@pytest.fixture
def app():
    """
    Build a minimal Flask app that registers only the blueprint we want to test.
    """
    from routes.assignmentRoute import assignment_bp  # import after mocks in tests

    app = Flask(__name__)
    app.secret_key = "unit_test_key"
    app.register_blueprint(assignment_bp)

    # a dummy home/login route so redirects resolve
    @app.route("/home")
    def home():  # pragma: no cover
        return "HOME"

    @app.route("/login")
    def login():  # pragma: no cover
        return "LOGIN"

    return app


@pytest.fixture
def client(app):
    return app.test_client()


# -----------------------------------------------------------------------------
#  Helper to inject a logged-in session
# -----------------------------------------------------------------------------
def login_session(client, username="alice", identity="teacher"):
    with client.session_transaction() as s:
        s["username"] = username
        s["identity"] = identity


# -----------------------------------------------------------------------------
#  Base patches applied in *every* test via autouse fixture
# -----------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def base_patches(monkeypatch):
    """
    Patch out DB collections, model instances, requests, 3rd-party helpers once
    for all tests.
    """
    import routes.assignmentRoute as mod

    # collections
    mod.users = MagicMock(name="users")
    mod.github_accounts = MagicMock(name="github_accounts")

    # model singletons created at import time
    mod.assignment_model = MagicMock(name="assignment_model")
    mod.submission_model = MagicMock(name="submission_model")

    # GitHub helpers
    mod.get_repo_contents = MagicMock(name="get_repo_contents")
    mod.is_repo_path_file = MagicMock(name="is_repo_path_file")

    # outbound e-mail helpers
    mod.send_mail = MagicMock(name="send_mail")
    mod.send_receipt_html = MagicMock(name="send_receipt_html")

    # requests.get mocked globally
    monkeypatch.setattr(mod, "requests", MagicMock())

    # templates → just return a string so we see status-200
    monkeypatch.setattr(mod, "render_template", MagicMock(return_value="OK"))

    yield


# =============================================================================
#  TESTS
# =============================================================================
class TestListRepoContents:
    def test_directory_listing_sorted(self, client):
        login_session(client, identity="teacher")

        # teacher has a linked repo
        from routes import assignmentRoute as mod

        mod.github_accounts.find_one.return_value = {
            "repo": "alice/demo",
            "access_token": "TOKEN",
        }

        # unsorted sample (file first, dir second)
        mod.get_repo_contents.return_value = [
            {"name": "b.py", "path": "b.py", "type": "file", "size": 1, "url": "u1"},
            {"name": "a", "path": "a", "type": "dir", "url": "u2"},
        ]

        resp = client.get("/assignments/list_repo_contents?path=src")
        assert resp.status_code == 200

        payload = json.loads(resp.data)
        # dir should come first after sort key
        assert [item["type"] for item in payload][:2] == ["dir", "file"]


class TestCreateAssignment:
    def test_get_form(self, client):
        login_session(client, identity="teacher")
        from routes import assignmentRoute as mod

        # no linked repo
        mod.github_accounts.find_one.return_value = None

        resp = client.get("/assignments/create")
        assert resp.status_code == 200
        mod.render_template.assert_called_once()

    def test_post_success(self, client):
        login_session(client, identity="teacher")
        from routes import assignmentRoute as mod

        mod.users.find_one.return_value = {
            "_id": "111",
            "username": "alice",
            "email": "alice@mail",
            "identity": "teacher",
        }
        mod.github_accounts.find_one.return_value = {
            "repo": "alice/demo",
            "repo_url": "https://github.com/alice/demo",
            "access_token": "TOKEN",
        }
        mod.assignment_model.create_assignment.return_value = "a1"
        mod.users.find.return_value = [
            {"email": "stu@mail", "identity": "student"}
        ]  # students list

        form = {
            "title": "HW1",
            "description": "desc",
            "due_date": "2025-05-10",
            "due_time": "23:59",
            "github_repo_path": "",
        }
        resp = client.post("/assignments/create", data=form, follow_redirects=False)
        assert resp.status_code == 302
        # verify DB write and emails
        mod.assignment_model.create_assignment.assert_called_once()
        mod.send_mail.assert_called_once()


class TestSubmitAssignment:
    def test_student_submit_new(self, client):
        login_session(client, username="bob", identity="student")
        from routes import assignmentRoute as mod

        mod.users.find_one.return_value = {"_id": "stu1", "username": "bob"}
        mod.submission_model.get_student_assignment_submission.return_value = None

        resp = client.post(
            "/assignments/aid123/submit",
            data={"github_link": "https://g", "readme_content": "readme"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        mod.submission_model.create_submission.assert_called_once()


class TestSubmitMarkdownFlow:
    aid = "aid321"
    mpath = "docs/report.md"

    def setup_mock_common(self):
        from routes import assignmentRoute as mod

        # assignment exists
        mod.assignment_model.get_assignment.return_value = {
            "_id": self.aid,
            "title": "HW",
            "teacher_id": "t1",
            "github_repo_path": "",
        }
        # student GitHub info
        mod.github_accounts.find_one.return_value = {
            "repo": "bob/demo",
            "access_token": "TOKEN",
        }
        # student record
        mod.users.find_one.return_value = {
            "_id": "stu1",
            "username": "bob",
            "email": "bob@mail",
        }
        # helpers
        mod.is_repo_path_file.return_value = True
        # mock raw file fetch
        mod.requests.get.return_value.status_code = 200
        mod.requests.get.return_value.content = b"# Title\n"

    def test_preview_get(self, client):
        login_session(client, username="bob", identity="student")
        self.setup_mock_common()

        url = f"/assignments/{self.aid}/submit-markdown?markdown_path={self.mpath}"
        resp = client.get(url)
        assert resp.status_code == 200
        from routes.assignmentRoute import render_template

        render_template.assert_called_once_with(
            "markdown_preview_submission.html",
            assignment={"_id": self.aid, "title": "HW", "teacher_id": "t1", "github_repo_path": ""},
            markdown_path=self.mpath,
            markdown_content="# Title\n",
            username="bob",
            identity="student",
        )

    def test_submit_post(self, client):
        login_session(client, username="bob", identity="student")
        self.setup_mock_common()

        from routes import assignmentRoute as mod

        mod.submission_model.get_student_assignment_submission.return_value = None

        resp = client.post(
            f"/assignments/{self.aid}/submit-markdown",
            data={"markdown_path": self.mpath},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        mod.submission_model.create_submission.assert_called_once()
        # receipt mail sent
        mod.send_receipt_html.assert_called_once()


class TestDeleteAssignment:
    def test_delete_ok(self, client):
        login_session(client, identity="teacher")
        from routes import assignmentRoute as mod

        # assignment belongs to teacher
        mod.assignment_model.get_assignment.return_value = {
            "teacher_id": "t1"
        }
        mod.users.find_one.return_value = {"_id": "t1"}
        mod.assignment_model.delete_assignment.return_value = True

        resp = client.post("/assignments/aid123/delete", follow_redirects=False)
        assert resp.status_code == 302
        mod.assignment_model.delete_assignment.assert_called_once()
        mod.submission_model.delete_by_assignment.assert_called_once_with("aid123")


class TestPreviewAndBrowse:
    def test_preview_markdown_file(self, client):
        login_session(client)
        from routes import assignmentRoute as mod

        mod.assignment_model.get_assignment.return_value = {
            "teacher_id": "60d21b4667d0d8992e610c85",
            "github_repo_path": "",
        }
        mod.users.find_one.side_effect = [
            {"_id": "t1", "username": "alice"},  # teacher lookup
        ]
        mod.github_accounts.find_one.return_value = {
            "repo": "alice/demo",
            "access_token": "TOKEN",
        }
        # file request
        mod.requests.get.return_value.status_code = 200
        mod.requests.get.return_value.content = b"# README\n"

        url = "/assignments/aid123/preview/README.md"
        resp = client.get(url)
        assert resp.status_code == 200
        mod.render_template.assert_called_once()

    def test_browse_directory(self, client):
        login_session(client)
        from routes import assignmentRoute as mod

        mod.assignment_model.get_assignment.return_value = {
            "teacher_id": "60d21b4667d0d8992e610c85",
            "github_repo_path": "src",
        }
        mod.users.find_one.side_effect = [
            {"_id": "60d21b4667d0d8992e610c85", "username": "alice"},  # teacher lookup
        ]
        mod.github_accounts.find_one.return_value = {
            "repo": "alice/demo",
            "access_token": "TOKEN",
        }
        # browsing root → list dirs/files
        mod.is_repo_path_file.return_value = False
        mod.get_repo_contents.return_value = [
            {"name": "src", "path": "src", "type": "dir", "url": "u"},
            {"name": "main.py", "path": "main.py", "type": "file", "url": "u2"},
        ]
        resp = client.get("/assignments/aid123/browse")
        assert resp.status_code == 200
        mod.render_template.assert_called_once()


class TestSelectSubmissionFile:
    def test_redirect_when_selecting_markdown(self, client):
        login_session(client, username="bob", identity="student")
        from routes import assignmentRoute as mod

        mod.assignment_model.get_assignment.return_value = {"title": "Hw"}
        mod.github_accounts.find_one.return_value = {
            "repo": "bob/demo",
            "access_token": "TOKEN",
        }
        mod.is_repo_path_file.return_value = True

        resp = client.get(
            "/assignments/aid321/select-file?path=report.md", follow_redirects=False
        )
        # should redirect to submit-markdown route
        assert resp.status_code == 302
        assert "/submit-markdown" in resp.headers["Location"]


from datetime import timedelta
import io, contextlib


class TestShowAssignmentsStudent:
    def test_student_view(self, client):
        login_session(client, username="bob", identity="student")
        from routes import assignmentRoute as mod

        now = datetime.now()
        mod.assignment_model.get_all_assignments.return_value = [
            {
                "_id": "a1",
                "due_date": (now + timedelta(days=2)).isoformat(),
            },
            {
                "_id": "a2",
                "due_date": (now - timedelta(days=1)).isoformat(),  # 已超期
            },
        ]
        mod.users.find_one.return_value = {"_id": "stu1", "username": "bob"}
        mod.submission_model.get_student_submissions.return_value = []

        mod.render_template.reset_mock()
        resp = client.get("/assignments")
        assert resp.status_code == 200

        _, kwargs = mod.render_template.call_args
        assign_list = kwargs["assignments"]
        assert assign_list[0]["remaining_days"] >= 0
        assert assign_list[1]["overdue"] is True



class TestViewAssignmentTeacher:
    def test_teacher_detail(self, client):
        login_session(client, identity="teacher")
        from routes import assignmentRoute as mod

        mod.render_template.reset_mock()

        aid = "a100"
        teacher_oid = "60d21b4667d0d8992e610c85"
        student_oid = "60d21b4667d0d8992e610c86"

        mod.assignment_model.get_assignment.return_value = {
            "_id": aid,
            "teacher_id": teacher_oid,
        }
        mod.submission_model.get_assignment_submissions.return_value = [
            {"student_id": student_oid, "_id": "sub1"}
        ]
        mod.users.find_one.side_effect = [
            {"_id": teacher_oid, "username": "alice"},
            {"_id": student_oid, "username": "bob"},
        ]

        resp = client.get(f"/assignments/{aid}")
        assert resp.status_code == 200
        _, kwargs = mod.render_template.call_args
        assert kwargs["submissions"][0]["student_username"] == "bob"



class TestGradeSubmission:
    def test_grade_ok(self, client):
        login_session(client, identity="teacher")
        from routes import assignmentRoute as mod

        mod.submission_model.add_feedback.return_value = True
        mod.submission_model.get_submission.return_value = {"assignment_id": "a1"}

        resp = client.post(
            "/submissions/s1/grade", data={"grade": "95", "feedback": "good"}
        )
        assert resp.status_code == 302
        mod.submission_model.add_feedback.assert_called_once_with("s1", 95.0, "good")



class TestBrowseRedirectPreview:
    def test_browse_redirects(self, client):
        login_session(client)
        from routes import assignmentRoute as mod

        aid = "a1"
        teacher_oid = "60d21b4667d0d8992e610c85"
        mod.assignment_model.get_assignment.return_value = {
            "teacher_id": teacher_oid,
            "github_repo_path": "docs",
        }
        mod.users.find_one.side_effect = [
            {"_id": teacher_oid, "username": "alice"},
        ]
        mod.github_accounts.find_one.return_value = {
            "repo": "alice/demo",
            "access_token": "TOKEN",
        }
        mod.is_repo_path_file.return_value = True

        resp = client.get(
            f"/assignments/{aid}/browse?path=docs/report.md", follow_redirects=False
        )
        assert resp.status_code == 302
        assert "/preview/" in resp.headers["Location"]



class TestPreviewCodeFile:
    def test_preview_py(self, client):
        login_session(client)
        from routes import assignmentRoute as mod

        teacher_oid = "60d21b4667d0d8992e610c85"
        mod.assignment_model.get_assignment.return_value = {
            "teacher_id": teacher_oid,
            "github_repo_path": "",
        }
        mod.users.find_one.side_effect = [
            {"_id": teacher_oid, "username": "alice"},
        ]
        mod.github_accounts.find_one.return_value = {
            "repo": "alice/demo",
            "access_token": "TOKEN",
        }
        mod.requests.get.return_value.status_code = 200
        mod.requests.get.return_value.content = b"print('hello')"

        mod.render_template.reset_mock()
        resp = client.get("/assignments/a1/preview/main.py")
        assert resp.status_code == 200
        assert mod.render_template.call_args[0][0] == "preview_code.html"


# ---------------------------------------------------------------------------
#  /assignments/<id>/select-file 
# ---------------------------------------------------------------------------
class TestSelectSubmissionList:
    def test_list_directory(self, client):
        login_session(client, username="bob", identity="student")
        from routes import assignmentRoute as mod

        mod.assignment_model.get_assignment.return_value = {"title": "Hw"}
        mod.github_accounts.find_one.return_value = {
            "repo": "bob/demo",
            "access_token": "TOKEN",
        }
        mod.is_repo_path_file.return_value = False
        mod.get_repo_contents.return_value = [
            {"name": "docs", "path": "docs", "type": "dir", "url": "u"},
            {
                "name": "report.md",
                "path": "docs/report.md",
                "type": "file",
                "url": "u2",
            },
        ]

        resp = client.get("/assignments/aid321/select-file?path=docs")
        assert resp.status_code == 200


class TestSubmitMarkdownInvalidExt:
    def test_invalid_extension(self, client):
        login_session(client, username="bob", identity="student")
        from routes import assignmentRoute as mod

        mod.assignment_model.get_assignment.return_value = {"title": "HW"}
        mod.github_accounts.find_one.return_value = {
            "repo": "bob/demo",
            "access_token": "TOKEN",
        }
        mod.is_repo_path_file.return_value = True  

        resp = client.get(
            "/assignments/aid321/submit-markdown?markdown_path=notes.txt"
        )
        assert resp.status_code == 400


# -----------------------------------------------------------------------------
#  HOW TO RUN
# -----------------------------------------------------------------------------
#   pytest tests/test_assignment_routes.py \
#         --cov=routes.assignmentRoute --cov-report=term-missing -q
#
#   Expect statement coverage of ≈80 % for routes/assignmentRoute.py
