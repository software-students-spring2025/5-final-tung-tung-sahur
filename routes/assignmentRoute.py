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
from models.assignment import AssignmentModel
from models.submission import SubmissionModel
from email_utils import send_mail
from dotenv import load_dotenv
import base64
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path

# Import shared GitHub functions
from .githubRoute import get_repo_contents, is_repo_path_file

load_dotenv()


def send_receipt_html(to_addr: str, title: str) -> None:
    """Send HTML receipt with loader.png embedded."""
    from_addr = "13601583609@163.com"
    smtp_server = "smtp.163.com"
    smtp_port = 465
    login = from_addr
    password = os.getenv("Email_password")

    msg = MIMEMultipart("related")
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = f"[DarkSpace] Submission received – {title}"

    # HTML body, reference cid:loader
    html = f"""
    <html>
      <body style="font-family:Arial,Helvetica,sans-serif">
        <h2>Submission received</h2>
        <p>Your submission for <strong>{title}</strong> has been stored.</p>
        <p>You can modify it again before the deadline.</p>
        <img src="cid:loader" width="64" height="64" alt="loader">
        <p style="margin-top:25px">— DarkSpace automatic mailer</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(html, "html"))

    # attach loader.png (put文件在 static/img/loader.png)
    loader_path = Path(__file__).parent.parent / "static" / "img" / "loader.png"
    with open(loader_path, "rb") as f:
        img = MIMEImage(f.read())
        img.add_header("Content-ID", "<loader>")
        img.add_header("Content-Disposition", "inline", filename="loader.png")
        msg.attach(img)

    import smtplib, ssl

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, smtp_port, context=ctx) as server:
        server.login(login, password)
        server.send_message(msg)


assignment_bp = Blueprint("assignment", __name__)

# Connect to database - consistent with app.py and githubRoute.py
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/gitBrightSpace")
client = MongoClient(mongo_uri)
db = client.get_database()
users = db["users"]
assignments_collection = db["assignments"]
submissions_collection = db["submissions"]
github_accounts = db["github"]

# Create model instances
assignment_model = AssignmentModel(assignments_collection)
submission_model = SubmissionModel(submissions_collection)


# Display all assignments list
@assignment_bp.route("/assignments")
def show_assignments():
    if not session.get("username"):
        return redirect(url_for("login"))

    identity = session.get("identity")
    username = session.get("username")

    if identity == "teacher":
        # If teacher, display all assignments created by them
        user = users.find_one({"username": username})
        if not user:
            return "User not found", 404

        user_id = str(user["_id"])
        assignments = assignment_model.get_teacher_assignments(user_id)
        return render_template(
            "teacher_assignments.html",
            assignments=assignments,
            username=username,
            identity=identity,
        )
    else:
        # If student, display all available assignments
        assignments = assignment_model.get_all_assignments()
        # Process date format and calculate remaining days
        now = datetime.now()
        for assignment in assignments:
            if isinstance(assignment.get("due_date"), str):
                try:
                    due_date = datetime.fromisoformat(
                        assignment["due_date"].replace("Z", "+00:00")
                    )
                    time_diff = due_date - now
                    assignment["remaining_days"] = time_diff.days
                    # Add hours, minutes, seconds for precision
                    assignment["remaining_hours"] = time_diff.seconds // 3600
                    assignment["remaining_minutes"] = (time_diff.seconds % 3600) // 60
                    assignment["remaining_seconds"] = time_diff.seconds % 60
                    assignment["overdue"] = time_diff.total_seconds() < 0
                except ValueError:
                    assignment["remaining_days"] = 7  # Default value
            else:
                assignment["remaining_days"] = 7  # Default value
        # Get all submissions for this student
        user = users.find_one({"username": username})
        if not user:
            return "User not found", 404

        user_id = str(user["_id"])
        submissions = submission_model.get_student_submissions(user_id)

        # Create a dictionary with assignment ID as key and submission object as value
        submission_dict = {}
        for sub in submissions:
            submission_dict[sub["assignment_id"]] = sub

        return render_template(
            "student_assignments.html",
            assignments=assignments,
            submissions=submission_dict,
            username=username,
            identity=identity,
            datetime=datetime,
            abs=abs,
        )


# Add a new route to list repository contents for assignment creation
@assignment_bp.route("/assignments/list_repo_contents")
def list_repo_contents():
    if not session.get("username") or session.get("identity") != "teacher":
        return jsonify({"error": "Unauthorized"}), 403

    # Get current teacher's GitHub account information
    github_info = github_accounts.find_one({"username": session.get("username")})
    if not github_info or not github_info.get("repo"):
        return jsonify({"error": "No GitHub repository linked"}), 400

    access_token = github_info["access_token"]
    repo_path = github_info["repo"]  # Format: "username/repo"

    # Parse repository information
    owner, repo = repo_path.split("/")

    # Get optional path parameter from request
    path = request.args.get("path", "")

    try:
        # Use the shared function to get repository contents
        contents = get_repo_contents(owner, repo, access_token, path)

        # Handle single file response case
        if not isinstance(contents, list):
            contents = [contents]

        # Format return data
        formatted_contents = []
        for item in contents:
            content_item = {
                "name": item["name"],
                "path": item["path"],
                "type": item["type"],
                "size": item.get("size", 0),
                "download_url": item.get("download_url", ""),
                "url": item["url"],
            }
            formatted_contents.append(content_item)

        # Sort: directories first, then by name
        formatted_contents.sort(
            key=lambda x: (0 if x["type"] == "dir" else 1, x["name"])
        )

        return jsonify(formatted_contents)
    except Exception as e:
        return jsonify({"error": f"GitHub API error: {str(e)}"}), 400


# Create new assignment (teachers only)
@assignment_bp.route("/assignments/create", methods=["GET", "POST"])
def create_assignment():
    if not session.get("username") or session.get("identity") != "teacher":
        return redirect(url_for("home"))

    if request.method == "GET":
        # Get teacher's linked GitHub repositories
        github_info = github_accounts.find_one({"username": session.get("username")})
        return render_template(
            "create_assignment.html",
            github_info=github_info,
            username=session.get("username"),
            identity=session.get("identity"),
        )

    # Process POST request
    title = request.form.get("title")
    description = request.form.get("description")
    due_date = request.form.get("due_date")
    due_time = request.form.get("due_time")
    github_repo_path = request.form.get("github_repo_path")

    if not title or not description or not due_date or not due_time:
        return "Missing required fields", 400

    # Combine date and time into ISO format datetime string
    due_datetime = f"{due_date}T{due_time}:00"

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

    # Create new assignment with combined datetime
    assignment_id = assignment_model.create_assignment(
        teacher_id=str(user["_id"]),
        title=title,
        description=description,
        due_date=due_datetime,
        github_repo_url=github_repo_url,
        github_repo_path=github_repo_path,
    )
    # ── NEW: fetch all student addresses and mail them
    students = users.find({"identity": "student", "email": {"$ne": None}})
    subject = f"[DarkSpace] New assignment: {title}"
    body = (
        f"Hello student,\n\nA new assignment “{title}” has been posted.\n"
        f"Due: {due_datetime}\n\n"
        f"{description}\n\nPlease submit before the deadline."
    )
    for stu in students:
        try:
            send_mail(stu["email"], subject, body)
        except Exception as e:
            print(f"Mail to {stu['email']} failed: {e}")

    return redirect(url_for("assignment.show_assignments"))


# View single assignment details
@assignment_bp.route("/assignments/<assignment_id>")
def view_assignment(assignment_id):
    if not session.get("username"):
        return redirect(url_for("login"))

    assignment = assignment_model.get_assignment(assignment_id)
    if not assignment:
        return "Assignment not found", 404

    # Convert ObjectId to string
    assignment["_id"] = str(assignment["_id"])

    identity = session.get("identity")
    username = session.get("username")

    # Get user information
    user = users.find_one({"username": username})
    if not user:
        return "User not found", 404

    user_id = str(user["_id"])

    if identity == "teacher":
        # If teacher, also get all student submissions for this assignment
        submissions = submission_model.get_assignment_submissions(assignment_id)

        # Get username for each submission's student
        for sub in submissions:
            student = users.find_one({"_id": ObjectId(sub["student_id"])})
            if student:
                sub["student_username"] = student["username"]
            else:
                sub["student_username"] = "Unknown"
            sub["_id"] = str(sub["_id"])

        return render_template(
            "teacher_assignment_detail.html",
            assignment=assignment,
            submissions=submissions,
            username=username,
            identity=identity,
        )
    else:
        # If student, check if already submitted
        submission = submission_model.get_student_assignment_submission(
            user_id, assignment_id
        )

        # Get student's GitHub account information
        github_info = github_accounts.find_one({"username": username})

        return render_template(
            "student_assignment_detail.html",
            assignment=assignment,
            submission=submission,
            github_info=github_info,
            username=username,
            identity=identity,
        )


# Student assignment submission
@assignment_bp.route("/assignments/<assignment_id>/submit", methods=["POST"])
def submit_assignment(assignment_id):
    if not session.get("username") or session.get("identity") != "student":
        return redirect(url_for("home"))

    # Get form data
    github_link = request.form.get("github_link")
    readme_content = request.form.get("readme_content")

    if not github_link:
        return "Missing GitHub repository link", 400

    # Get student ID
    student = users.find_one({"username": session.get("username")})
    if not student:
        return "User not found", 404

    student_id = str(student["_id"])

    # Check if already submitted
    existing_submission = submission_model.get_student_assignment_submission(
        student_id, assignment_id
    )
    if existing_submission:
        # Update submission
        submission_model.update_submission(
            str(existing_submission["_id"]),
            {
                "github_link": github_link,
                "readme_content": readme_content,
                "submitted_at": datetime.now(),
                "status": "submitted",
            },
        )
    else:
        # Create new submission
        submission_model.create_submission(
            student_id=student_id,
            assignment_id=assignment_id,
            github_link=github_link,
            readme_content=readme_content,
        )

    return redirect(url_for("assignment.show_assignments", assignment_id=assignment_id))


# Teacher grading and feedback
@assignment_bp.route("/submissions/<submission_id>/grade", methods=["POST"])
def grade_submission(submission_id):
    if not session.get("username") or session.get("identity") != "teacher":
        return redirect(url_for("home"))

    # Get form data
    grade = request.form.get("grade")
    feedback = request.form.get("feedback")

    if not grade or not feedback:
        return "Missing grade or feedback", 400

    # Convert grade to float
    try:
        grade_float = float(grade)
    except ValueError:
        return "Invalid grade format", 400

    # Add grade and feedback
    success = submission_model.add_feedback(submission_id, grade_float, feedback)
    if not success:
        return "Failed to update submission", 500

    # Get submission information to redirect to assignment details page
    submission = submission_model.get_submission(submission_id)
    return redirect(
        url_for("assignment.view_assignment", assignment_id=submission["assignment_id"])
    )


# Download code from GitHub and package it
@assignment_bp.route("/assignments/<assignment_id>/download")
def download_assignment(assignment_id):
    if not session.get("username"):
        return redirect(url_for("login"))

    assignment = assignment_model.get_assignment(assignment_id)
    if not assignment:
        return "Assignment not found", 404

    # Get GitHub repository URL and path
    github_repo_url = assignment.get("github_repo_url")
    github_repo_path = assignment.get("github_repo_path", "")

    if not github_repo_url:
        return "No GitHub repository associated with this assignment", 400

    # Get teacher's GitHub access token (assignment creator)
    teacher = users.find_one({"_id": ObjectId(assignment["teacher_id"])})
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
    assignment_title = assignment.get("title", "assignment").replace(" ", "_")

    return send_file(
        memory_file,
        download_name=f"{assignment_title}.zip",
        as_attachment=True,
        mimetype="application/zip",
    )


# View student submission README
@assignment_bp.route("/submissions/<submission_id>/readme")
def view_readme(submission_id):
    if not session.get("username"):
        return redirect(url_for("login"))

    submission = submission_model.get_submission(submission_id)
    if not submission:
        return "Submission not found", 404

    # Check access permissions
    identity = session.get("identity")
    username = session.get("username")

    if identity == "student":
        # Students can only view their own submissions
        user = users.find_one({"username": username})
        if not user or str(user["_id"]) != submission["student_id"]:
            return "Unauthorized", 403

    # Return README content
    readme_content = submission.get("readme_content", "No README content available")
    return render_template(
        "view_readme.html",
        readme_content=readme_content,
        submission=submission,
        username=username,
        identity=identity,
    )


# Delete an assignment and related submissions (Teacher only)
@assignment_bp.route("/assignments/<assignment_id>/delete", methods=["POST"])
def delete_assignment(assignment_id):
    if not session.get("username") or session.get("identity") != "teacher":
        return redirect(url_for("home"))

    # Get assignment to check if the current teacher is the owner
    assignment = assignment_model.get_assignment(assignment_id)
    if not assignment:
        return "Assignment not found", 404

    # Check if current user is the teacher who created this assignment
    user = users.find_one({"username": session.get("username")})
    if str(user["_id"]) != assignment["teacher_id"]:
        return "Unauthorized - You can only delete your own assignments", 403

    # Delete all related submissions
    submission_count = submission_model.delete_by_assignment(assignment_id)

    # Delete the assignment
    success = assignment_model.delete_assignment(assignment_id)

    if success:
        return redirect(url_for("assignment.show_assignments"))
    else:
        return "Failed to delete assignment", 500


@assignment_bp.route("/assignments/<assignment_id>/preview/<path:file_path>")
def preview_assignment_file(assignment_id, file_path):
    """
    Preview a file from GitHub without storing it on the server.
    Handles different file types including markdown, code files, and PDFs.
    """
    if not session.get("username"):
        return redirect(url_for("login"))

    # Get assignment details
    assignment = assignment_model.get_assignment(assignment_id)
    if not assignment:
        return "Assignment not found", 404

    # Get GitHub repository information from the assignment or teacher
    github_repo_path = assignment.get("github_repo_path", "")

    # Get teacher's GitHub access token
    teacher = users.find_one({"_id": ObjectId(assignment["teacher_id"])})
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
            item=assignment,
            item_type="assignment",
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
            item=assignment,
            item_type="assignment",
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
            item=assignment,
            item_type="assignment",
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


# Add a route to browse assignment files
@assignment_bp.route("/assignments/<assignment_id>/browse")
def browse_assignment_files(assignment_id):
    """Browse the files of an assignment"""
    if not session.get("username"):
        return redirect(url_for("login"))

    assignment = assignment_model.get_assignment(assignment_id)
    if not assignment:
        return "Assignment not found", 404

    # Get GitHub repository information
    github_repo_path = assignment.get("github_repo_path", "")

    # Get teacher's GitHub access token
    teacher = users.find_one({"_id": ObjectId(assignment["teacher_id"])})
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

    # Determine path to browse (from query param or from assignment)
    browse_path = request.args.get("path", github_repo_path)

    # If it's a direct file, redirect to preview
    if browse_path and is_repo_path_file(owner, repo, access_token, browse_path):
        return redirect(
            url_for(
                "assignment.preview_assignment_file",
                assignment_id=assignment_id,
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
            content_item = {
                "name": item["name"],
                "path": item["path"],
                "type": item["type"],
                "size": item.get("size", 0),
                "download_url": item.get("download_url"),
                "url": item["url"],
            }
            formatted_contents.append(content_item)

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
            "browse_assignment_files.html",
            assignment=assignment,
            contents=formatted_contents,
            current_path=browse_path,
            breadcrumbs=breadcrumbs,
            base_path=github_repo_path,
            username=session.get("username"),
            identity=session.get("identity"),
        )

    except Exception as e:
        return f"Error accessing repository: {str(e)}", 400


# Student repository file browser
@assignment_bp.route("/assignments/<assignment_id>/select-file")
def select_submission_file(assignment_id):
    """Browse student's repository to select a Markdown file for submission"""
    if not session.get("username") or session.get("identity") != "student":
        return redirect(url_for("home"))

    assignment = assignment_model.get_assignment(assignment_id)
    if not assignment:
        return "Assignment not found", 404

    # Get student's GitHub information
    github_info = github_accounts.find_one({"username": session.get("username")})
    if not github_info or not github_info.get("repo"):
        return "You need to link a GitHub repository first", 400

    # Get repository access token
    access_token = github_info["access_token"]
    repo_path = github_info["repo"]

    # Parse repository information
    owner, repo = repo_path.split("/")

    # Determine path to browse (from query param)
    browse_path = request.args.get("path", "")

    # If it's a direct file, check if it's a markdown file
    if browse_path and is_repo_path_file(owner, repo, access_token, browse_path):
        if browse_path.lower().endswith((".md", ".markdown")):
            # Allow direct submission
            return redirect(
                url_for(
                    "assignment.submit_markdown_assignment",
                    assignment_id=assignment_id,
                    markdown_path=browse_path,
                )
            )
        else:
            # Not a markdown file - redirect back to folder view
            parent_path = "/".join(browse_path.split("/")[:-1])
            return redirect(
                url_for(
                    "assignment.select_submission_file",
                    assignment_id=assignment_id,
                    path=parent_path,
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
            content_item = {
                "name": item["name"],
                "path": item["path"],
                "type": item["type"],
                "size": item.get("size", 0),
                "download_url": item.get("download_url"),
                "url": item["url"],
            }
            formatted_contents.append(content_item)

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
            "student_repo_browser.html",
            assignment=assignment,
            contents=formatted_contents,
            current_path=browse_path,
            breadcrumbs=breadcrumbs,
            username=session.get("username"),
            identity=session.get("identity"),
        )

    except Exception as e:
        return f"Error accessing repository: {str(e)}", 400


# Submit assignment using selected markdown file
@assignment_bp.route(
    "/assignments/<assignment_id>/submit-markdown", methods=["GET", "POST"]
)
def submit_markdown_assignment(assignment_id):
    """Submit assignment using a markdown file from the student's repository"""
    if not session.get("username") or session.get("identity") != "student":
        return redirect(url_for("home"))

    # This route can be accessed directly with GET (preview) or POST (submit)
    if request.method == "POST":
        markdown_path = request.form.get("markdown_path")
    else:
        markdown_path = request.args.get("markdown_path")

    if not markdown_path:
        return "No markdown file selected", 400

    # Get assignment
    assignment = assignment_model.get_assignment(assignment_id)
    if not assignment:
        return "Assignment not found", 404

    # Get student's GitHub information
    github_info = github_accounts.find_one({"username": session.get("username")})
    if not github_info or not github_info.get("repo"):
        return "You need to link a GitHub repository first", 400

    # Get repository access token and info
    access_token = github_info["access_token"]
    repo_path = github_info["repo"]

    # Parse repository information
    owner, repo = repo_path.split("/")

    # Create the GitHub repository URL
    github_repo_url = f"https://github.com/{repo_path}"

    # Get student ID
    student = users.find_one({"username": session.get("username")})
    if not student:
        return "User not found", 404

    student_id = str(student["_id"])

    try:
        # Check if path is a valid markdown file
        if not is_repo_path_file(owner, repo, access_token, markdown_path):
            return "Invalid file path", 400

        if not markdown_path.lower().endswith((".md", ".markdown")):
            return "Selected file is not a markdown file", 400

        # Get markdown content
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3.raw",
        }
        api_url = (
            f"https://api.github.com/repos/{owner}/{repo}/contents/{markdown_path}"
        )
        response = requests.get(api_url, headers=headers)

        if response.status_code != 200:
            return f"Error fetching file: {response.status_code}", 404

        readme_content = response.content.decode("utf-8")

        # If GET method, show preview before submission
        if request.method == "GET":
            return render_template(
                "markdown_preview_submission.html",
                assignment=assignment,
                markdown_path=markdown_path,
                markdown_content=readme_content,
                username=session.get("username"),
                identity=session.get("identity"),
            )

        # If POST method, submit the assignment
        # Check if already submitted
        existing_submission = submission_model.get_student_assignment_submission(
            student_id, assignment_id
        )

        # Create file URL for direct linking
        file_url = f"https://github.com/{repo_path}/blob/main/{markdown_path}"

        if existing_submission:
            # Update submission
            submission_model.update_submission(
                str(existing_submission["_id"]),
                {
                    "github_link": file_url,
                    "readme_content": readme_content,
                    "submitted_at": datetime.now(),
                    "status": "submitted",
                },
            )
        else:
            # Create new submission
            submission_model.create_submission(
                student_id=student_id,
                assignment_id=assignment_id,
                github_link=file_url,
                readme_content=readme_content,
            )

        # send receipt mail -----------------------------------------
        if student.get("email"):
            send_receipt_html(student["email"], assignment["title"])
        # -----------------------------------------------------------

        return redirect(
            url_for("assignment.view_assignment", assignment_id=assignment_id)
        )

    except Exception as e:
        return f"Error processing markdown file: {str(e)}", 500
