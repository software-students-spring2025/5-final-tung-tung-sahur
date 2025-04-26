from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from routes import all_blueprints
import os
from dotenv import load_dotenv
import markdown as md
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

for bp in all_blueprints:
    app.register_blueprint(bp)

@app.template_filter('markdown')
def markdown_filter(text):
    if text:
        return md.markdown(text, extensions=['fenced_code', 'tables'])
    return ""

@app.route('/')
def home():
    if "username" in session:
        github_info = github_accounts.find_one({"username": session["username"]})
        return render_template("home.html", username=session["username"],
                               identity=session.get("identity", "student"),
                               github_info=github_info)
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
