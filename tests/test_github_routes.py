# tests/test_github_routes.py
import json
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask

# ---------------------------------------------------------------------------
# Build a minimal Flask app that only contains the GitHub blueprint
# ---------------------------------------------------------------------------
@pytest.fixture
def app():
    from routes.githubRoute import github_bp  # import inside fixture to avoid circulars

    app = Flask(__name__)
    app.secret_key = "test_secret"
    app.register_blueprint(github_bp)

    # dummy home route so url_for('home') works
    @app.route("/home")
    def home():  # pragma: no cover
        return "home"

    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestGithubBlueprint:
    # ---------- /github/link ----------
    def test_github_link_redirects(self, client):
        resp = client.get("/github/link")
        assert resp.status_code == 302
        assert resp.headers["Location"].startswith(
            "https://github.com/login/oauth/authorize"
        )

    # ---------- /github/callback (error branch) ----------
    def test_github_callback_missing_code(self, client):
        resp = client.get("/github/callback")  # no ?code=
        assert resp.status_code == 400
        assert b"Missing code" in resp.data

    # ---------- /github/callback (happy path) ----------
    @patch("routes.githubRoute.github_accounts")
    @patch("routes.githubRoute.users")
    @patch("routes.githubRoute.requests.get")
    @patch("routes.githubRoute.requests.post")
    def test_github_callback_success(
        self,
        mock_post,
        mock_get,
        mock_users,
        mock_github_accounts,
        client,
    ):
        # 1) fake GitHub oauth token exchange
        mock_post.return_value.json.return_value = {"access_token": "TOKEN123"}

        # 2) fake GitHub /user API
        mock_get.return_value.json.return_value = {
            "id": 42,
            "login": "octocat",
            "name": "Octo Cat",
            "avatar_url": "http://example.com/ava",
        }

        # 3) fake local user + github collections
        mock_users.find_one.return_value = {"username": "alice"}
        mock_github_accounts.find_one.return_value = None

        # populate login session
        with client.session_transaction() as s:
            s["username"] = "alice"

        resp = client.get("/github/callback?code=abc123")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/home")

        # ensure DB write happened
        mock_github_accounts.replace_one.assert_called_once()
        mock_post.assert_called_once()
        mock_get.assert_called_once()

    # ---------- /github/repo/link (list repos) ----------
    @patch("routes.githubRoute.render_template")
    @patch("routes.githubRoute.requests.get")
    @patch("routes.githubRoute.github_accounts")
    def test_repo_link_lists_repos(
        self,
        mock_github_accounts,
        mock_requests_get,
        mock_render,
        client,
    ):
        mock_render.return_value = "OK"
        with client.session_transaction() as s:
            s["username"] = "alice"

        mock_github_accounts.find_one.return_value = {
            "access_token": "TOKEN123",
        }
        mock_requests_get.return_value.json.return_value = [
            {"full_name": "alice/demo", "name": "demo"}
        ]

        resp = client.get("/github/repo/link")
        assert resp.status_code == 200
        mock_render.assert_called_once()

    # ---------- /github/repo/contents (API) ----------
    @patch("routes.githubRoute.get_repo_contents")
    @patch("routes.githubRoute.github_accounts")
    def test_get_repository_contents_root(
        self, mock_github_accounts, mock_get_contents, client
    ):
        with client.session_transaction() as s:
            s["username"] = "alice"

        mock_github_accounts.find_one.return_value = {
            "repo": "alice/demo",
            "access_token": "TOKEN123",
        }
        mock_get_contents.return_value = [
            {
                "name": "src",
                "path": "src",
                "type": "dir",
                "size": 0,
                "url": "u",
            },
            {
                "name": "README.md",
                "path": "README.md",
                "type": "file",
                "size": 10,
                "download_url": "d",
                "url": "u2",
            },
        ]

        resp = client.get("/github/repo/contents")
        assert resp.status_code == 200
        payload = json.loads(resp.data)
        # dir first, file second
        assert [item["name"] for item in payload] == ["src", "README.md"]

    # ---------- Pure-Python helper: list_repo_files_recursive ----------
    @patch("routes.githubRoute.get_repo_contents")
    def test_list_repo_files_recursive(self, mock_get):
        """
        Directory structure mocked:

        ├── file1.py
        └── subdir
            └── file2.txt
        """
        from routes.githubRoute import list_repo_files_recursive

        mock_get.side_effect = [
            [
                {"name": "file1.py", "path": "file1.py", "type": "file", "download_url": "u1"},
                {"name": "subdir", "path": "subdir", "type": "dir"},
            ],
            [
                {
                    "name": "file2.txt",
                    "path": "subdir/file2.txt",
                    "type": "file",
                    "download_url": "u2",
                }
            ],
        ]

        result = list_repo_files_recursive("alice", "demo", "TOKEN123")
        assert len(result) == 2
        assert {f["path"] for f in result} == {"file1.py", "subdir/file2.txt"}

class TestGithubBlueprintExtra:
    # ---------- /github/unlink ----------
    @patch("routes.githubRoute.github_accounts")
    def test_github_unlink(self, mock_github_acc, client):
        with client.session_transaction() as s:
            s["username"] = "alice"

        resp = client.get("/github/unlink")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/home")
        mock_github_acc.delete_one.assert_called_once_with({"username": "alice"})

    # ---------- /github/repo/link  (POST) ----------
    @patch("routes.githubRoute.github_accounts")
    def test_repo_link_post(self, mock_github_acc, client):
        with client.session_transaction() as s:
            s["username"] = "alice"

        resp = client.post("/github/repo/link", data={"repo": "alice/demo"})
        assert resp.status_code == 302
        mock_github_acc.update_one.assert_called_once_with(
            {"username": "alice"},
            {
                "$set": {
                    "repo": "alice/demo",
                    "repo_url": "https://github.com/alice/demo",
                }
            },
        )

    # ---------- /github/repo/unlink ----------
    @patch("routes.githubRoute.github_accounts")
    def test_repo_unlink(self, mock_github_acc, client):
        with client.session_transaction() as s:
            s["username"] = "alice"
        mock_github_acc.find_one.return_value = {"username": "alice"}

        resp = client.get("/github/repo/unlink")
        assert resp.status_code == 302
        mock_github_acc.update_one.assert_called_once()

    # ---------- /github/repo/files ----------
    @patch("routes.githubRoute.render_template")
    @patch("routes.githubRoute.list_repo_files_recursive")
    @patch("routes.githubRoute.github_accounts")
    def test_repo_files_view(
        self,
        mock_accounts,
        mock_list,
        mock_render,
        client,
    ):
        with client.session_transaction() as s:
            s["username"] = "alice"
        mock_accounts.find_one.return_value = {
            "access_token": "TOKEN",
            "repo": "alice/demo",
        }
        mock_list.return_value = [{"path": "README.md"}]
        mock_render.return_value = "OK"

        resp = client.get("/github/repo/files")
        assert resp.status_code == 200
        mock_render.assert_called_once()

    # ---------- Helper: is_repo_path_file ----------
    @patch("routes.githubRoute.get_repo_contents")
    def test_is_repo_path_file(self, mock_get):
        from routes.githubRoute import is_repo_path_file

        mock_get.return_value = {"type": "file"}
        assert is_repo_path_file("alice", "demo", "tok", "README.md") is True

        mock_get.return_value = [{"type": "file"}]  # list ⇒ treated as dir
        assert is_repo_path_file("alice", "demo", "tok", "") is False

    # ---------- list_repo_files_recursive error branch ----------
    @patch("routes.githubRoute.get_repo_contents")
    def test_list_repo_files_recursive_error(self, mock_get):
        from routes.githubRoute import list_repo_files_recursive

        mock_get.side_effect = Exception("boom")
        # should not raise, but return empty list
        assert list_repo_files_recursive("o", "r", "t") == []

    # ---------- /github/repo/contents : invalid session ----------
    def test_get_repo_contents_not_logged_in(self, client):
        resp = client.get("/github/repo/contents")
        assert resp.status_code == 403