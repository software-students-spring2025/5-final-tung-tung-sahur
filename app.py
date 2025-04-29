from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from routes import all_blueprints
import os
from dotenv import load_dotenv
import markdown as md
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from email_utils import send_mail
from bson.objectid import ObjectId

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config.update(
    SESSION_COOKIE_SECURE=True,  # Ensure this is True in production
    SESSION_COOKIE_SAMESITE="None",
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


# ───────────────────────── 24-hour reminder job ──────────────────────────
def due_soon_job() -> None:
    """Send one reminder e-mail for every assignment due in <24 h."""
    print("[scheduler] due_soon_job fired")  # confirm execution
    now = datetime.now(timezone.utc)
    limit = now + timedelta(hours=24)

    cur = assignments_collection.find(
        {
            "$and": [
                {"due_date": {"$gt": now.isoformat(), "$lte": limit.isoformat()}},
                {
                    "$or": [
                        {"reminder_sent": {"$exists": False}},
                        {"reminder_sent": False},
                    ]
                },
            ]
        }
    )

    for a in cur:
        subject = f"[DarkSpace] Assignment “{a['title']}” due in 24 h"
        body = (
            f"Reminder: assignment “{a['title']}” is due at {a['due_date']}.\n"
            "Please submit before the deadline."
        )

        for stu in users.find({"identity": "student", "email": {"$ne": None}}):
            try:
                send_mail(stu["email"], subject, body)
            except Exception as e:
                print(f"[reminder] mail to {stu['email']} failed: {e}")

        assignments_collection.update_one(
            {"_id": ObjectId(a["_id"])}, {"$set": {"reminder_sent": True}}
        )
        print("[reminder] sent for:", a["title"])


# ─────────────────── scheduler: run now + every hour ───────────────────
scheduler = BackgroundScheduler(timezone="UTC", daemon=True)
scheduler.add_job(
    due_soon_job,
    trigger=IntervalTrigger(minutes=1),
    next_run_time=datetime.now(timezone.utc),  # run immediately on startup
    id="due_reminder",
)
scheduler.start()
print("[scheduler] started")
# ─────────────────────────────────────────────────────────────────────────


for bp in all_blueprints:
    app.register_blueprint(bp)


@app.template_filter("markdown")
def markdown_filter(text):
    if text:
        return md.markdown(text, extensions=["fenced_code", "tables"])
    return ""


@app.template_filter("datetime_format")
def datetime_format(value):
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return value
    return value


# Used only for chat
@app.template_filter("chat_time_format")
def chat_time_format(value):
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return value
    return value


@app.route("/")
def home():

    if "username" in session:
        github_info = github_accounts.find_one({"username": session["username"]})
        identity = session.get("identity", "student")
        user_doc = users.find_one({"username": session["username"]})

        if user_doc:
            user_id = str(user_doc["_id"])
        else:
            return redirect(url_for("login"))  # Redirect if user_doc is None

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
                if isinstance(assignment.get("due_date"), str):
                    try:
                        due_date = datetime.fromisoformat(
                            assignment["due_date"].replace("Z", "+00:00")
                        )
                        time_diff = due_date - now
                        assignment["remaining_days"] = time_diff.days
                        # Add hours, minutes, seconds for precision
                        assignment["remaining_hours"] = time_diff.seconds // 3600
                        assignment["remaining_minutes"] = (
                            time_diff.seconds % 3600
                        ) // 60
                        assignment["remaining_seconds"] = time_diff.seconds % 60
                        assignment["overdue"] = time_diff.total_seconds() < 0
                    except ValueError:
                        assignment["remaining_days"] = 7  # Default value
                else:
                    assignment["remaining_days"] = 7  # Default value

        return render_template(
            "home.html",
            username=session.get("username"),
            user=user_doc,
            identity=identity,
            github_info=github_info,
            assignments=assignments,
            content_items=content_items,
            submissions=submission_dict if identity == "student" else None,
        )
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        identity = request.form["identity"]
        if identity == "teacher":
            input_code = request.form["input_code"]

        existing_user = users.find_one({"username": username})
        if existing_user:
            flash("User already exists", "danger")
            return redirect(url_for("register"))
        # Teacher need special permission
        if identity == "teacher":
            if input_code != os.getenv("TEACHER_INVITE_CODE"):
                flash("Invalid teacher invite code", "danger")
                return redirect(url_for("register"))

        users.insert_one(
            {
                "username": username,
                "password": generate_password_hash(password),
                "identity": identity,
                "github": None,
            }
        )
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = users.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            session["username"] = username
            session["identity"] = user.get("identity", "student")  # student as default
            return redirect(url_for("home"))

        flash("Invalid username or password", "danger")  # category=Bootstrap style
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def get_all_students():
    allUsers = users.find()
    allUsers = list(allUsers)
    allStudents = []
    for user in allUsers:
        if user["identity"] == "student":
            allStudents.append(user)
    return allStudents


# A page for only teachers to see all students
@app.route("/allStudents")
def all_students():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    identity = session.get("identity", "student")
    if identity != "teacher":
        return redirect(url_for("home"))
    allStudents = get_all_students()
    return render_template(
        "allStudents.html",
        allStudents=allStudents,
        username=username,
        identity=identity,
    )


def delete_student_and_github(username):

    # Delete the student from the users collection
    users.delete_one({"username": username})

    # Delete the student's GitHub account from the github_accounts collection
    github_accounts.delete_one({"username": username})


@app.route("/deleteStudent/<username>", methods=["POST"])
def delete_student(username):
    if "username" not in session:
        return redirect(url_for("login"))

    identity = session.get("identity", "student")
    if identity != "teacher":
        return redirect(url_for("home"))
    # Check if the deleted user is a student
    student = users.find_one({"username": username})
    if not student or student["identity"] != "student":
        return "User not found or not a student", 404
    # Delete the student and their GitHub account
    delete_student_and_github(username)
    return redirect(url_for("all_students"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)
