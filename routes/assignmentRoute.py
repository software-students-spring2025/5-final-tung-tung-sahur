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
from dotenv import load_dotenv

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
                    due_date = datetime.strptime(assignment['due_date'], '%Y-%m-%d')
                    assignment['remaining_days'] = (due_date - now).days
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
    github_repo_url = request.form.get("github_repo_url")
    
    if not title or not description or not due_date:
        return "Missing required fields", 400
        
    # Get current user ID
    user = users.find_one({"username": session.get("username")})
    if not user:
        return "User not found", 404
        
    # Create new assignment
    assignment_id = assignment_model.create_assignment(
        teacher_id=str(user["_id"]),
        title=title,
        description=description,
        due_date=due_date,
        github_repo_url=github_repo_url
    )
    
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
        
    # Get GitHub repository URL
    github_repo_url = assignment.get("github_repo_url")
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
    
    # Parse GitHub repository information
    # Assume URL format is https://github.com/username/repo
    repo_parts = github_repo_url.strip("/").split("/")
    if len(repo_parts) < 5:
        return "Invalid GitHub repository URL", 400
        
    owner = repo_parts[-2]
    repo = repo_parts[-1]
    
    # Get repository content
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Get repository's default branch
    repo_info_url = f"https://api.github.com/repos/{owner}/{repo}"
    repo_response = requests.get(repo_info_url, headers=headers)
    if repo_response.status_code != 200:
        return f"Failed to fetch repository info: {repo_response.text}", 400
        
    default_branch = repo_response.json().get("default_branch", "main")
    
    # Create a ZIP file in memory
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        # Recursively get repository contents
        def fetch_repo_contents(path=""):
            contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
            if path:
                contents_url += f"?ref={default_branch}"
            else:
                contents_url += f"?ref={default_branch}"
                
            contents_response = requests.get(contents_url, headers=headers)
            if contents_response.status_code != 200:
                return
                
            contents = contents_response.json()
            
            # Handle single file or directory list
            if not isinstance(contents, list):
                contents = [contents]
                
            for item in contents:
                item_path = item["path"]
                item_type = item["type"]
                
                if item_type == "file":
                    # Get file content
                    download_url = item["download_url"]
                    file_response = requests.get(download_url, headers=headers)
                    if file_response.status_code == 200:
                        zf.writestr(item_path, file_response.content)
                elif item_type == "dir":
                    # Recursively process subdirectory
                    fetch_repo_contents(item_path)
        
        # Start recursive content retrieval
        fetch_repo_contents()
    
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