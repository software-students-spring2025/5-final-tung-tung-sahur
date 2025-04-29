import os
import requests
import zipfile
from io import BytesIO
from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    url_for,
    jsonify,
    send_file,
    Response,
)
from bson.objectid import ObjectId
from pymongo import MongoClient
from models.content import ContentModel
from dotenv import load_dotenv
import base64
import mimetypes

# Import shared GitHub functions
from .githubRoute import get_repo_contents, is_repo_path_file

load_dotenv()

content_bp = Blueprint("content", __name__)

# Connect to database - consistent with app.py and githubRoute.py
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/gitBrightSpace")
client = MongoClient(mongo_uri)
db = client.get_database()
users = db["users"]
content_collection = db["content"]
github_accounts = db["github"]

# Create model instance
content_model = ContentModel(content_collection)


# Display all content items
@content_bp.route("/content")
def show_content():
    if not session.get("username"):
        return redirect(url_for("login"))

    identity = session.get("identity")
    username = session.get("username")

    if identity == "teacher":
        # If teacher, display all content items created by them
        user = users.find_one({"username": username})
        if not user:
            return "User not found", 404

        user_id = str(user["_id"])
        content_items = content_model.get_teacher_content(user_id)
        return render_template(
            "teacher_content.html",
            content_items=content_items,
            username=username,
            identity=identity,
        )
    else:
        # If student, display all available content
        content_items = content_model.get_all_content()
        return render_template(
            "student_content.html",
            content_items=content_items,
            username=username,
            identity=identity,
        )


# Create new content (teachers only)
@content_bp.route("/content/create", methods=["GET", "POST"])
def create_content():
    if not session.get("username") or session.get("identity") != "teacher":
        return redirect(url_for("home"))

    if request.method == "GET":
        # Get teacher's linked GitHub repositories
        github_info = github_accounts.find_one({"username": session.get("username")})
        return render_template(
            "create_content.html",
            github_info=github_info,
            username=session.get("username"),
            identity=session.get("identity"),
        )

    # Process POST request
    title = request.form.get("title")
    description = request.form.get("description")
    github_repo_path = request.form.get("github_repo_path")

    if not title or not description:
        return "Missing required fields", 400

    # Get current user ID
    user = users.find_one({"username": session.get("username")})
    if not user:
        return "User not found", 404

    # Get teacher's GitHub information
    github_info = github_accounts.find_one({"username": session.get("username")})

    # Build the GitHub repo URL
    github_repo_url = None
    if github_info and github_info.get("repo"):
        if github_repo_path:
            # Create URL with the selected path
            repo_name = github_info["repo"]
            github_repo_url = (
                f"https://github.com/{repo_name}/tree/main/{github_repo_path}"
            )
        elif github_info.get("repo_url"):
            # Use the default repository URL
            github_repo_url = github_info.get("repo_url")

    # Create new content with combined datetime
    content_id = content_model.create_content(
        teacher_id=str(user["_id"]),
        title=title,
        description=description,
        github_repo_url=github_repo_url,
        github_repo_path=github_repo_path,
    )

    return redirect(url_for("content.show_content"))


# View single content details
@content_bp.route("/content/<content_id>")
def view_content(content_id):
    if not session.get("username"):
        return redirect(url_for("login"))

    content_item = content_model.get_content(content_id)
    if not content_item:
        return "Content not found", 404

    # Convert ObjectId to string
    content_item["_id"] = str(content_item["_id"])

    identity = session.get("identity")
    username = session.get("username")

    return render_template(
        "content_detail.html",
        content=content_item,
        username=username,
        identity=identity,
    )


# Download content from GitHub
@content_bp.route("/content/<content_id>/download")
def download_content(content_id):
    if not session.get("username"):
        return redirect(url_for("login"))

    content_item = content_model.get_content(content_id)
    if not content_item:
        return "Content not found", 404

    # Get GitHub repository URL and path
    github_repo_url = content_item.get("github_repo_url")
    github_repo_path = content_item.get("github_repo_path", "")

    if not github_repo_url:
        return "No GitHub repository associated with this content", 400

    # Get teacher's GitHub access token (content creator)
    teacher = users.find_one({"_id": ObjectId(content_item["teacher_id"])})
    if not teacher:
        return "Teacher not found", 404

    teacher_username = teacher.get("username")
    github_info = github_accounts.find_one({"username": teacher_username})
    if not github_info or not github_info.get("access_token"):
        return "Teacher GitHub account not linked or missing access token", 400

    access_token = github_info["access_token"]

    # Get repository path from linked repository
    repo_path = github_info.get("repo")
    if not repo_path:
        # Fall back to parsing the URL if no linked repo
        # Assume URL format is https://github.com/username/repo
        repo_parts = github_repo_url.strip("/").split("/")
        if len(repo_parts) < 5:
            return "Invalid GitHub repository URL", 400
        owner = repo_parts[-2]
        repo = repo_parts[-1]
    else:
        # Use the linked repository
        owner, repo = repo_path.split("/")

    # Get the name of the selected folder or file
    selected_folder_name = ""
    if github_repo_path:
        selected_folder_name = github_repo_path.split("/")[-1]

    # Check if selected path is a file
    try:
        is_direct_file = is_repo_path_file(owner, repo, access_token, github_repo_path)

        # If it's a direct file, download and return it without ZIP
        if is_direct_file:
            # Get file content directly
            content_info = get_repo_contents(
                owner, repo, access_token, github_repo_path
            )
            download_url = content_info.get("download_url")
            if download_url:
                file_response = requests.get(
                    download_url,
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/vnd.github+json",
                    },
                )
                if file_response.status_code == 200:
                    memory_file = BytesIO(file_response.content)
                    memory_file.seek(0)

                    # Get filename from path
                    filename = github_repo_path.split("/")[-1]

                    return send_file(
                        memory_file,
                        download_name=filename,
                        as_attachment=True,
                        mimetype="application/octet-stream",  # Generic binary
                    )
    except Exception as e:
        # Log the error but continue with ZIP creation as fallback
        print(f"Error checking if path is a file: {str(e)}")

    # Create a ZIP file in memory (for folders or multiple files)
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        # Recursively get repository contents
        def fetch_repo_contents(path):
            try:
                # Get contents using shared function
                contents = get_repo_contents(owner, repo, access_token, path)

                # Handle single file response case
                if not isinstance(contents, list):
                    contents = [contents]

                for item in contents:
                    item_path = item["path"]
                    item_type = item["type"]

                    if item_type == "file":
                        # Get file content
                        download_url = item["download_url"]
                        file_response = requests.get(
                            download_url,
                            headers={
                                "Authorization": f"token {access_token}",
                                "Accept": "application/vnd.github+json",
                            },
                        )
                        if file_response.status_code == 200:
                            # Build the path for the file in the ZIP
                            if github_repo_path and item_path.startswith(
                                github_repo_path
                            ):
                                # Get the part after the selected path
                                rel_path = item_path[len(github_repo_path) :].lstrip(
                                    "/"
                                )
                                # Add the selected folder as the top level directory
                                zip_path = os.path.join(selected_folder_name, rel_path)
                            else:
                                # This shouldn't normally happen but as a fallback
                                zip_path = item_path

                            # Add file to zip
                            zf.writestr(zip_path, file_response.content)

                    elif item_type == "dir":
                        # Recursively process subdirectory
                        fetch_repo_contents(item_path)
            except Exception as e:
                print(f"Error fetching repository contents for {path}: {str(e)}")

        # Start recursive content retrieval
        fetch_repo_contents(github_repo_path)

    # Set file pointer to beginning
    memory_file.seek(0)

    # Generate download filename
    content_title = content_item.get("title", "content").replace(" ", "_")

    return send_file(
        memory_file,
        download_name=f"{content_title}.zip",
        as_attachment=True,
        mimetype="application/zip",
    )


@content_bp.route("/content/<content_id>/preview/<path:file_path>")
def preview_content_file(content_id, file_path):
    """
    Preview a file from GitHub without storing it on the server.
    Handles different file types including markdown, code files, and PDFs.
    """
    if not session.get("username"):
        return redirect(url_for("login"))

    # Get content details
    content_item = content_model.get_content(content_id)
    if not content_item:
        return "Content not found", 404

    # Get GitHub repository information from the content or teacher
    github_repo_path = content_item.get("github_repo_path", "")

    # Get teacher's GitHub access token
    teacher = users.find_one({"_id": ObjectId(content_item["teacher_id"])})
    if not teacher:
        return "Teacher not found", 404

    teacher_username = teacher.get("username")
    github_info = github_accounts.find_one({"username": teacher_username})
    if not github_info or not github_info.get("access_token"):
        return "Teacher GitHub account not linked or missing access token", 400

    access_token = github_info["access_token"]

    # Get repository owner and name
    repo_path = github_info.get("repo")
    if not repo_path:
        return "No repository linked", 400

    owner, repo = repo_path.split("/")

    # Determine the full path to the file in the repository
    # If we're viewing a specific file within a directory
    if github_repo_path and not file_path.startswith(github_repo_path):
        full_path = f"{github_repo_path}/{file_path}"
    else:
        full_path = file_path

    # Make a request to the GitHub API to get the file content
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3.raw",
    }

    # Get file content via GitHub API
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{full_path}"
    response = requests.get(api_url, headers=headers)

    if response.status_code != 200:
        return f"Error fetching file: {response.status_code}", 404

    # Detect file type based on extension
    file_extension = os.path.splitext(file_path)[1].lower()

    # Get the file content
    file_content = response.content

    # Handle different file types
    if file_extension in [".md", ".markdown"]:
        # For markdown, we'll render it with GitHub styling
        # Get content as text and pass it directly to the template
        content_text = file_content.decode("utf-8")

        # Render the markdown template with the content
        return render_template(
            "preview_markdown.html",
            content=content_text,
            file_name=os.path.basename(file_path),
            item=content_item,
            item_type="content",
            username=session.get("username"),
            identity=session.get("identity"),
        )

    elif file_extension in [".py", ".c", ".cpp", ".h", ".js", ".html", ".css", ".java"]:
        # For code files, show with syntax highlighting
        content_text = file_content.decode("utf-8")

        return render_template(
            "preview_code.html",
            content=content_text,
            file_name=os.path.basename(file_path),
            language=file_extension[1:],  # Remove the dot from extension
            item=content_item,
            item_type="content",
            username=session.get("username"),
            identity=session.get("identity"),
        )

    elif file_extension == ".pdf":
        # For PDFs, we can embed using an iframe or object tag
        # Create a data URI for the PDF content
        pdf_base64 = base64.b64encode(file_content).decode("utf-8")
        pdf_data_uri = f"data:application/pdf;base64,{pdf_base64}"

        return render_template(
            "preview_pdf.html",
            pdf_data=pdf_data_uri,
            file_name=os.path.basename(file_path),
            item=content_item,
            item_type="content",
            username=session.get("username"),
            identity=session.get("identity"),
        )
    else:
        # For unsupported file types, prompt download
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        return Response(
            file_content,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": f"attachment; filename={os.path.basename(file_path)}",
            },
        )


# Add a route to browse content files
@content_bp.route("/content/<content_id>/browse")
def browse_content_files(content_id):
    """Browse the files of a content item"""
    if not session.get("username"):
        return redirect(url_for("login"))

    content_item = content_model.get_content(content_id)
    if not content_item:
        return "Content not found", 404

    # Get GitHub repository information
    github_repo_path = content_item.get("github_repo_path", "")

    # Get teacher's GitHub access token
    teacher = users.find_one({"_id": ObjectId(content_item["teacher_id"])})
    if not teacher:
        return "Teacher not found", 404

    teacher_username = teacher.get("username")
    github_info = github_accounts.find_one({"username": teacher_username})
    if not github_info or not github_info.get("access_token"):
        return "Teacher GitHub account not linked or missing access token", 400

    access_token = github_info["access_token"]

    # Get repository owner and name
    repo_path = github_info.get("repo")
    if not repo_path:
        return "No repository linked", 400

    owner, repo = repo_path.split("/")

    # Determine path to browse (from query param or from content)
    browse_path = request.args.get("path", github_repo_path)

    # If it's a direct file, redirect to preview
    if browse_path and is_repo_path_file(owner, repo, access_token, browse_path):
        return redirect(
            url_for(
                "content.preview_content_file",
                content_id=content_id,
                file_path=browse_path,
            )
        )

    # Get contents of path
    try:
        contents = get_repo_contents(owner, repo, access_token, browse_path)

        # Handle single file response case
        if not isinstance(contents, list):
            contents = [contents]

        # Format contents for display
        formatted_contents = []
        for item in contents:
            file_info = {
                "name": item["name"],
                "path": item["path"],
                "type": item["type"],
                "size": item.get("size", 0),
                "download_url": item.get("download_url"),
                "url": item["url"],
            }
            formatted_contents.append(file_info)

        # Sort by type and name
        formatted_contents.sort(
            key=lambda x: (0 if x["type"] == "dir" else 1, x["name"])
        )

        # Compute breadcrumb paths
        breadcrumbs = []
        if browse_path:
            current_path = ""
            parts = browse_path.split("/")
            for i, part in enumerate(parts):
                if i > 0:
                    current_path += "/"
                current_path += part
                breadcrumbs.append({"name": part, "path": current_path})

        return render_template(
            "browse_content_files.html",
            content_item=content_item,
            contents=formatted_contents,
            current_path=browse_path,
            breadcrumbs=breadcrumbs,
            base_path=github_repo_path,
            username=session.get("username"),
            identity=session.get("identity"),
        )

    except Exception as e:
        return f"Error accessing repository: {str(e)}", 400


# Delete content (Teacher only)
@content_bp.route("/content/<content_id>/delete", methods=["POST"])
def delete_content(content_id):
    if not session.get("username") or session.get("identity") != "teacher":
        return redirect(url_for("home"))

    # Get content to check if the current teacher is the owner
    content_item = content_model.get_content(content_id)
    if not content_item:
        return "Content not found", 404

    # Check if current user is the teacher who created this content
    user = users.find_one({"username": session.get("username")})
    if str(user["_id"]) != content_item["teacher_id"]:
        return "Unauthorized - You can only delete your own content", 403

    # Delete the content
    success = content_model.delete_content(content_id)

    if success:
        return redirect(url_for("content.show_content"))
    else:
        return "Failed to delete content", 500
