from flask import Flask, render_template, request, redirect, url_for, session
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
    SESSION_COOKIE_SECURE=True,   # Ensure this is True in production
    SESSION_COOKIE_SAMESITE="None"
)
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/gitBrightSpace")
client = MongoClient(mongo_uri)
db = client.get_database()
users = db["users"]
github_accounts = db["github"]
assignments_collection = db["assignments"]

# ───────────────────────── 24-hour reminder job ──────────────────────────
def due_soon_job() -> None:
    """Send one reminder e-mail for every assignment due in <24 h."""
    print("[scheduler] due_soon_job fired")          # confirm execution
    now   = datetime.now(timezone.utc)
    limit = now + timedelta(hours=24)

    cur = assignments_collection.find({
        "$and": [
            {"due_date": {"$gt": now.isoformat(), "$lte": limit.isoformat()}},
            {"$or": [{"reminder_sent": {"$exists": False}},
                     {"reminder_sent": False}]}
        ]
    })

    for a in cur:
        subject = f"[DarkSpace] Assignment “{a['title']}” due in 24 h"
        body    = (
            f"Reminder: assignment “{a['title']}” is due at {a['due_date']}.\n"
            "Please submit before the deadline."
        )

        for stu in users.find({"identity": "student", "email": {"$ne": None}}):
            try:
                send_mail(stu["email"], subject, body)
            except Exception as e:
                print(f"[reminder] mail to {stu['email']} failed: {e}")

        assignments_collection.update_one(
            {"_id": ObjectId(a["_id"])},
            {"$set": {"reminder_sent": True}}
        )
        print("[reminder] sent for:", a["title"])

# ─────────────────── scheduler: run now + every hour ───────────────────
scheduler = BackgroundScheduler(timezone="UTC", daemon=True)
scheduler.add_job(
    due_soon_job,
    trigger=IntervalTrigger(minutes=1),
    next_run_time=datetime.utcnow(),       # run immediately on startup
    id="due_reminder"
)
scheduler.start()
print("[scheduler] started")
# ─────────────────────────────────────────────────────────────────────────

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
    if "username" not in session:
        return redirect(url_for('login'))

    user_doc      = users.find_one({"username": session["username"]})
    github_info   = github_accounts.find_one({"username": session["username"]})
    return render_template(
        "home.html",
        username=user_doc["username"],
        identity=user_doc.get("identity", "student"),
        user=user_doc,
        github_info=github_info
    )


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

