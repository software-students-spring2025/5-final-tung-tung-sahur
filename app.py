from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from routes import all_blueprints
import os
from dotenv import load_dotenv
import markdown as md
from datetime import datetime
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config.update(
    SESSION_COOKIE_SECURE=True,   # Ensure this is True in production
    SESSION_COOKIE_SAMESITE="None"
)
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/gitBrightSpace")
client = MongoClient(mongo_uri)
db = client.get_database()
users = db["users"]
github_accounts = db["github"]
assignments_collection = db["assignments"]
content_collection = db["content"]
submissions_collection = db["submissions"]

# Import models
from models.assignment import AssignmentModel
from models.submission import SubmissionModel
from models.content import ContentModel

# Create model instances
assignment_model = AssignmentModel(assignments_collection)
submission_model = SubmissionModel(submissions_collection)
content_model = ContentModel(content_collection)

for bp in all_blueprints:
    app.register_blueprint(bp)

@app.template_filter('markdown')
def markdown_filter(text):
    if text:
        return md.markdown(text, extensions=['fenced_code', 'tables'])
    return ""
@app.template_filter('datetime_format')
def datetime_format(value):
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return value
    return value

@app.route('/')
def home():
    if "username" in session:
        github_info = github_accounts.find_one({"username": session["username"]})
        identity = session.get("identity", "student")
        username = session.get("username")
        
        user = users.find_one({"username": username})
        if not user:
            return "User not found", 404
            
        user_id = str(user["_id"])
        
        # Get assignments based on user identity
        if identity == "teacher":
            assignments = assignment_model.get_teacher_assignments(user_id)
            content_items = content_model.get_teacher_content(user_id)
            
            # Add submission count to each assignment
            for assignment in assignments:
                assignment_id = str(assignment["_id"])
                submissions = submission_model.get_assignment_submissions(assignment_id)
                assignment["submission_count"] = len(submissions)
                
        else:  # Student
            assignments = assignment_model.get_all_assignments()
            content_items = content_model.get_all_content()
            
            # Get all submissions for this student
            submissions = submission_model.get_student_submissions(user_id)
            
            # Create a dictionary with assignment ID as key and submission object as value
            submission_dict = {}
            for sub in submissions:
                submission_dict[sub["assignment_id"]] = sub
                
            # Process date format and calculate remaining days for assignments
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
        
        return render_template("home.html", username=username,
                              identity=identity,
                              github_info=github_info,
                              assignments=assignments,
                              content_items=content_items,
                              submissions=submission_dict if identity == "student" else None)
    return redirect(url_for('login'))

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        identity = request.form['identity']  

        existing_user = users.find_one({"username": username})
        if existing_user:
            return "User already exists"

        users.insert_one({
            "username": username,
            "password": generate_password_hash(password),
            "identity": identity,
            "github": None        
        })
        return redirect(url_for('login'))

    return render_template("register.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        user = users.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            session["username"] = username
            session["identity"] = user.get("identity", "student")  #student as default
            return redirect(url_for('home'))

        return "Username or password is incorrect"

    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)