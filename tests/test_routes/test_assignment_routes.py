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
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("routes.assignmentRoute.render_template")
    @patch("routes.assignmentRoute.users")
    @patch("routes.assignmentRoute.submission_model")
    @patch("routes.assignmentRoute.assignment_model")
    def test_show_assignments_teacher(
        self, mock_asgM, mock_subM, mock_users, mock_render, client
    ):
        # Arrange
        mock_users.find_one.return_value = {
            "_id": ObjectId(),
            "username": "teacher",
            "identity": "teacher",
        }
        fake = [{"_id": ObjectId(), "title": "A1"}, {"_id": ObjectId(), "title": "A2"}]
        mock_asgM.get_teacher_assignments.return_value = fake

        with client.session_transaction() as sess:
            sess["username"] = "teacher"
            sess["identity"] = "teacher"

        # Act
        client.get("/assignments")

        # Assert
        mock_render.assert_called_once_with(
            "teacher_assignments.html",
            assignments=fake,
            username="teacher",
            identity="teacher",
        )

    @patch("routes.assignmentRoute.render_template")
    @patch("routes.assignmentRoute.users")
    @patch("routes.assignmentRoute.submission_model")
    @patch("routes.assignmentRoute.assignment_model")
    def test_show_assignments_student(
        self, mock_asgM, mock_subM, mock_users, mock_render, client
    ):
        # Arrange
        now = datetime.now()
        fake_asg = [
            {
                "_id": ObjectId(),
                "title": "A1",
                "due_date": (now + timedelta(days=1)).isoformat(),
            },
            {
                "_id": ObjectId(),
                "title": "A2",
                "due_date": (now - timedelta(days=1)).isoformat(),
            },
        ]
        fake_subs = [{"assignment_id": str(fake_asg[0]["_id"]), "status": "submitted"}]
        mock_users.find_one.return_value = {
            "_id": ObjectId(),
            "username": "student",
            "identity": "student",
        }
        mock_asgM.get_all_assignments.return_value = fake_asg
        mock_subM.get_student_submissions.return_value = fake_subs

        with client.session_transaction() as sess:
            sess["username"] = "student"
            sess["identity"] = "student"

        # Act
        client.get("/assignments")

        # Expected dict
        expected = {str(fake_asg[0]["_id"]): fake_subs[0]}
        # Assert
        mock_render.assert_called_once_with(
            "student_assignments.html",
            assignments=fake_asg,
            submissions=expected,
            username="student",
            identity="student",
            datetime=datetime,
            abs=abs,
        )

    @patch("routes.assignmentRoute.redirect")
    @patch("routes.assignmentRoute.users")
    @patch("routes.assignmentRoute.submission_model")
    def test_submit_assignment(self, mock_subM, mock_users, mock_redirect, client):
        # Arrange
        aid = str(ObjectId())
        mock_subM.get_student_assignment_submission.return_value = None
        mock_subM.create_submission.return_value = "subid"
        mock_users.find_one.return_value = {
            "_id": ObjectId(),
            "username": "stud",
            "identity": "student",
        }
        mock_redirect.return_value = "REDIR"

        with client.session_transaction() as sess:
            sess["username"] = "stud"
            sess["identity"] = "student"

        data = {"github_link": "L", "readme_content": "C"}

        # Act
        rv = client.post(f"/assignments/{aid}/submit", data=data)

        # Assert calls
        sid = str(mock_users.find_one.return_value["_id"])
        mock_subM.get_student_assignment_submission.assert_called_once_with(sid, aid)
        mock_subM.create_submission.assert_called_once_with(
            student_id=sid, assignment_id=aid, github_link="L", readme_content="C"
        )
        mock_redirect.assert_called_once()
        # Check returned body
        assert rv.get_data(as_text=True) == "REDIR"
