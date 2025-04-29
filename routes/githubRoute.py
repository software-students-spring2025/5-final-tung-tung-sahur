import os
import requests
from flask import (
    Blueprint,
    redirect,
    request,
    session,
    url_for,
    render_template,
    jsonify,
)
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

github_bp = Blueprint("github", __name__)

client_id = os.getenv("GITHUB_CLIENT_ID")
client_secret = os.getenv("GITHUB_CLIENT_SECRET")

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/gitBrightSpace")
mongo_client = MongoClient(mongo_uri)
db = mongo_client.get_database()
users = db["users"]
github_accounts = db["github"]


@github_bp.route("/github/link")
def github_link():
    # Redirect user to GitHub for authorization
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}&scope=read:user,repo&prompt=login"
    )
    return redirect(github_auth_url)


@github_bp.route("/github/callback")
def github_callback():
    code = request.args.get("code")
    if not code:
        return "Missing code", 400

    # Step 1: Exchange code for access token
    token_response = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={"client_id": client_id, "client_secret": client_secret, "code": code},
    )
    token_json = token_response.json()
    access_token = token_json.get("access_token")
    if not access_token:
        return "Failed to get access token", 400

    # Step 2: Get user info from GitHub API
    user_response = requests.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"token {access_token}",
            "Accept": "application/json",
        },
    )
    github_user = user_response.json()

    # Step 3: Store info in MongoDB
    current_username = session.get("username")
    if not current_username:
        return "Not logged in", 403

    user = users.find_one({"username": current_username})
    if not user:
        return "User not found", 404

    github_doc = {
        "username": current_username,
        "github_id": github_user["id"],
        "github_login": github_user["login"],
        "name": github_user.get("name"),
        "avatar_url": github_user.get("avatar_url"),
        "access_token": access_token,
        "repo": None,
        "repo_url": None,
    }

    # Check if this GitHub account is already linked to another user
    existing_github_account = github_accounts.find_one({"github_id": github_user["id"]})
    if existing_github_account:
        if existing_github_account["username"] != current_username:
            # Unlink the existing account
            github_accounts.delete_one({"github_id": github_user["id"]})
            # Link the new account
            github_accounts.replace_one(
                {"username": current_username}, github_doc, upsert=True
            )
            return redirect(url_for("home"))
    # If the GitHub account is not linked to another user, link it
    github_accounts.replace_one({"username": current_username}, github_doc, upsert=True)
    return redirect(url_for("home"))


@github_bp.route("/github/unlink")
def github_unlink():
    current_username = session.get("username")
    if not current_username:
        return "Not logged in", 403

    # Remove GitHub account from MongoDB
    github_accounts.delete_one({"username": current_username})
    return redirect(url_for("home"))


# Show all the repositories of the user
@github_bp.route("/github/repo/link")
def github_repo_link():
    current_username = session.get("username")
    if not current_username:
        return "Not logged in", 403

    # Get the GitHub account info
    github_account = github_accounts.find_one({"username": current_username})
    if not github_account:
        return "GitHub account not linked", 404

    # List all repositories for the user
    access_token = github_account["access_token"]
    headers = {"Authorization": f"token {access_token}", "Accept": "application/json"}
    repo_response = requests.get("https://api.github.com/user/repos", headers=headers)
    repos = repo_response.json()
    if not repos:
        return "No repositories found", 404
    # Render a template to select a repository
    return render_template(
        "select_repo.html",
        repos=repos,
        username=session["username"],
        identity=session.get("identity", "student"),
    )


@github_bp.route("/github/repo/link", methods=["POST"])
def github_repo_link_post():
    current_username = session.get("username")
    if not current_username:
        return "Not logged in", 403

    # Get the selected repository from the form
    selected_repo = request.form.get("repo")
    if not selected_repo:
        return "No repository selected", 400
    repo_url = f"https://github.com/{selected_repo}"
    github_accounts.update_one(
        {"username": current_username},
        {"$set": {"repo": selected_repo, "repo_url": repo_url}},
    )
    return redirect(url_for("home"))


@github_bp.route("/github/repo/unlink")
def github_repo_unlink():
    current_username = session.get("username")
    if not current_username:
        return "Not logged in", 403

    # Get the GitHub account info
    github_account = github_accounts.find_one({"username": current_username})
    if not github_account:
        return "GitHub account not linked", 404

    # Unlink the repository but keep the GitHub account linked
    github_accounts.update_one(
        {"username": current_username}, {"$set": {"repo": None, "repo_url": None}}
    )

    return redirect(url_for("home"))


# Function to get repository contents (file or directory)
def get_repo_contents(owner, repo, token, path=""):
    """Get repository contents (files or directories) from GitHub API"""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"GitHub API error: {response.text}")

    return response.json()


# Function to recursively get all files in a repository
def list_repo_files_recursive(owner, repo, token, path=""):
    """Recursively list all files in a repository or subdirectory"""
    try:
        items = get_repo_contents(owner, repo, token, path)

        # Handle single file response
        if not isinstance(items, list):
            items = [items]

        all_files = []

        for item in items:
            if item["type"] == "file":
                all_files.append(
                    {
                        "name": item["name"],
                        "path": item["path"],
                        "download_url": item["download_url"],
                    }
                )
            elif item["type"] == "dir":
                all_files.extend(
                    list_repo_files_recursive(owner, repo, token, item["path"])
                )

        return all_files
    except Exception as e:
        print(f"Error listing repository files: {str(e)}")
        return []


# Check if a repository path is a file
def is_repo_path_file(owner, repo, token, path):
    """Check if the specified path in repository is a file"""
    try:
        content = get_repo_contents(owner, repo, token, path)
        # If it's a single item (not a list), check if it's a file
        return not isinstance(content, list) and content.get("type") == "file"
    except Exception:
        return False


# Route to get formatted repository contents (files and directories)
@github_bp.route("/github/repo/contents")
def get_repository_contents():
    """API to get repository contents for a specific path"""
    current_username = session.get("username")
    if not current_username:
        return jsonify({"error": "Not logged in"}), 403

    github_account = github_accounts.find_one({"username": current_username})
    if not github_account or not github_account.get("repo"):
        return jsonify({"error": "No GitHub repository linked"}), 400

    access_token = github_account["access_token"]
    repo_path = github_account["repo"]

    # Parse repository information
    owner, repo = repo_path.split("/")

    # Get path parameter
    path = request.args.get("path", "")

    try:
        contents = get_repo_contents(owner, repo, access_token, path)

        # Format the response
        if not isinstance(contents, list):
            contents = [contents]

        formatted_contents = []
        for item in contents:
            formatted_contents.append(
                {
                    "name": item["name"],
                    "path": item["path"],
                    "type": item["type"],
                    "size": item.get("size", 0),
                    "download_url": item.get("download_url", ""),
                    "url": item["url"],
                }
            )

        # Sort: directories first, then by name
        formatted_contents.sort(
            key=lambda x: (0 if x["type"] == "dir" else 1, x["name"])
        )

        return jsonify(formatted_contents)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Route to list all files in a repository (for legacy compatibility)
@github_bp.route("/github/repo/files")
def github_repo_files():
    current_username = session.get("username")
    if not current_username:
        return "Not logged in", 403

    github_account = github_accounts.find_one({"username": current_username})
    if not github_account:
        return "GitHub account not linked", 404

    access_token = github_account["access_token"]
    selected_repo = github_account["repo"]
    if not selected_repo:
        return "No repository linked", 400

    owner, repo = selected_repo.split("/")

    try:
        files = list_repo_files_recursive(owner, repo, access_token)
    except Exception as e:
        return f"Failed to fetch repository files: {str(e)}", 400

    return render_template(
        "repo_files.html",
        files=files,
        username=session["username"],
        identity=session.get("identity", "student"),
    )
