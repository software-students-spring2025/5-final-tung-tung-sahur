import os
import requests
import zipfile
from io import BytesIO
from datetime import datetime
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify, send_file
from bson.objectid import ObjectId
from pymongo import MongoClient
from models.assignment import AssignmentModel
from models.submission import SubmissionModel
from email_utils import send_mail
from dotenv import load_dotenv
# Import shared GitHub functions
from .githubRoute import get_repo_contents, is_repo_path_file

load_dotenv()

assignment_bp = Blueprint('assignment', __name__)

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
@assignment_bp.route('/assignments')
def show_assignments():
    if not session.get("username"):
        return redirect(url_for('login'))
        
    identity = session.get("identity")
    username = session.get("username")
    
    if identity == "teacher":
        # If teacher, display all assignments created by them
        user = users.find_one({"username": username})
        if not user:
            return "User not found", 404
            
        user_id = str(user["_id"])
        assignments = assignment_model.get_teacher_assignments(user_id)
        return render_template("teacher_assignments.html", assignments=assignments, username=username, identity=identity)
    else:
        # If student, display all available assignments
        assignments = assignment_model.get_all_assignments()
        # Process date format and calculate remaining days
        now = datetime.now()
        for assignment in assignments:
            if isinstance(assignment.get('due_date'), str):
                try:
                    due_date = datetime.fromisoformat(assignment['due_date'].replace('Z', '+00:00'))
                    time_diff = due_date - now
                    assignment['remaining_days'] = time_diff.days
                    # Add hours, minutes, seconds for precision
                    assignment['remaining_hours'] = time_diff.seconds // 3600
                    assignment['remaining_minutes'] = (time_diff.seconds % 3600) // 60
                    assignment['remaining_seconds'] = time_diff.seconds % 60
                    assignment['overdue'] = time_diff.total_seconds() < 0
                except ValueError:
                    assignment['remaining_days'] = 7  # Default value
            else:
                assignment['remaining_days'] = 7  # Default value
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
            
        return render_template("student_assignments.html", 
                              assignments=assignments, 
                              submissions=submission_dict,
                              username=username, 
                              identity=identity,
                              datetime=datetime,
                              abs=abs)

# Add a new route to list repository contents for assignment creation
@assignment_bp.route('/assignments/list_repo_contents')
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
                "url": item["url"]
            }
            formatted_contents.append(content_item)
        
        # Sort: directories first, then by name
        formatted_contents.sort(key=lambda x: (0 if x["type"] == "dir" else 1, x["name"]))
        
        return jsonify(formatted_contents)
    except Exception as e:
        return jsonify({"error": f"GitHub API error: {str(e)}"}), 400

# Create new assignment (teachers only)
@assignment_bp.route('/assignments/create', methods=["GET", "POST"])
def create_assignment():
    if not session.get("username") or session.get("identity") != "teacher":
        return redirect(url_for('home'))
        
    if request.method == "GET":
        # Get teacher's linked GitHub repositories
        github_info = github_accounts.find_one({"username": session.get("username")})
        return render_template("create_assignment.html", 
                              github_info=github_info,
                              username=session.get("username"),
                              identity=session.get("identity"))
                              
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
            github_repo_url = f"https://github.com/{repo_name}/tree/main/{github_repo_path}"
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
        github_repo_path=github_repo_path
    )
    # ── NEW: fetch all student addresses and mail them
    students = users.find({"identity": "student", "email": {"$ne": None}})
    subject  = f"[DarkSpace] New assignment: {title}"
    body     = (
        f"Hello student,\n\nA new assignment “{title}” has been posted.\n"
        f"Due: {due_datetime}\n\n"
        f"{description}\n\nPlease submit before the deadline."
    )
    for stu in students:
        try:
            send_mail(stu["email"], subject, body)
        except Exception as e:
            print(f"Mail to {stu['email']} failed: {e}")
        
        return redirect(url_for('assignment.show_assignments'))

# View single assignment details
@assignment_bp.route('/assignments/<assignment_id>')
def view_assignment(assignment_id):
    if not session.get("username"):
        return redirect(url_for('login'))
        
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
            
        return render_template("teacher_assignment_detail.html", 
                              assignment=assignment,
                              submissions=submissions,
                              username=username,
                              identity=identity)
    else:
        # If student, check if already submitted
        submission = submission_model.get_student_assignment_submission(user_id, assignment_id)
        
        # Get student's GitHub account information
        github_info = github_accounts.find_one({"username": username})
        
        return render_template("student_assignment_detail.html",
                              assignment=assignment,
                              submission=submission,
                              github_info=github_info,
                              username=username,
                              identity=identity)

# Student assignment submission
@assignment_bp.route('/assignments/<assignment_id>/submit', methods=["POST"])
def submit_assignment(assignment_id):
    if not session.get("username") or session.get("identity") != "student":
        return redirect(url_for('home'))
        
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
    existing_submission = submission_model.get_student_assignment_submission(student_id, assignment_id)
    if existing_submission:
        # Update submission
        submission_model.update_submission(
            str(existing_submission["_id"]),
            {
                "github_link": github_link,
                "readme_content": readme_content,
                "submitted_at": datetime.now(),
                "status": "submitted"
            }
        )
    else:
        # Create new submission
        submission_model.create_submission(
            student_id=student_id,
            assignment_id=assignment_id,
            github_link=github_link,
            readme_content=readme_content
        )
    
    return redirect(url_for('assignment.view_assignment', assignment_id=assignment_id))

# Teacher grading and feedback
@assignment_bp.route('/submissions/<submission_id>/grade', methods=["POST"])
def grade_submission(submission_id):
    if not session.get("username") or session.get("identity") != "teacher":
        return redirect(url_for('home'))
        
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
    return redirect(url_for('assignment.view_assignment', assignment_id=submission["assignment_id"]))

# Download code from GitHub and package it
@assignment_bp.route('/assignments/<assignment_id>/download')
def download_assignment(assignment_id):
    if not session.get("username"):
        return redirect(url_for('login'))
        
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
        selected_folder_name = github_repo_path.split('/')[-1]
    
    # Check if selected path is a file
    try:
        is_direct_file = is_repo_path_file(owner, repo, access_token, github_repo_path)
        
        # If it's a direct file, download and return it without ZIP
        if is_direct_file:
            # Get file content directly
            content_info = get_repo_contents(owner, repo, access_token, github_repo_path)
            download_url = content_info.get("download_url")
            if download_url:
                file_response = requests.get(download_url, headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github+json"
                })
                if file_response.status_code == 200:
                    memory_file = BytesIO(file_response.content)
                    memory_file.seek(0)
                    
                    # Get filename from path
                    filename = github_repo_path.split('/')[-1]
                    
                    return send_file(
                        memory_file,
                        download_name=filename,
                        as_attachment=True,
                        mimetype='application/octet-stream'  # Generic binary
                    )
    except Exception as e:
        # Log the error but continue with ZIP creation as fallback
        print(f"Error checking if path is a file: {str(e)}")
    
    # Create a ZIP file in memory (for folders or multiple files)
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
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
                        file_response = requests.get(download_url, headers={
                            "Authorization": f"token {access_token}",
                            "Accept": "application/vnd.github+json"
                        })
                        if file_response.status_code == 200:
                            # Build the path for the file in the ZIP
                            if github_repo_path and item_path.startswith(github_repo_path):
                                # Get the part after the selected path
                                rel_path = item_path[len(github_repo_path):].lstrip('/')
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
        mimetype='application/zip'
    )

# View student submission README
@assignment_bp.route('/submissions/<submission_id>/readme')
def view_readme(submission_id):
    if not session.get("username"):
        return redirect(url_for('login'))
        
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
    return render_template("view_readme.html", 
                          readme_content=readme_content,
                          submission=submission,
                          username=username,
                          identity=identity)

# Delete an assignment and related submissions (Teacher only)
@assignment_bp.route('/assignments/<assignment_id>/delete', methods=["POST"])
def delete_assignment(assignment_id):
    if not session.get("username") or session.get("identity") != "teacher":
        return redirect(url_for('home'))
        
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
        return redirect(url_for('assignment.show_assignments'))
    else:
        return "Failed to delete assignment", 500