# routes/emailRoute.py
import re
from flask import Blueprint, render_template, request, redirect, url_for, session
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/gitBrightSpace")
client = MongoClient(mongo_uri)
db = client.get_database()
users = db["users"]

email_bp = Blueprint("email", __name__)

EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


# ──────────────────────────────── add / edit ────────────────────────────────
@email_bp.route("/email/link", methods=["GET", "POST"])
def email_link():
    if "username" not in session:
        return "Not logged in", 403

    if request.method == "POST":
        address = request.form.get("email", "").strip()
        if not EMAIL_RE.match(address):
            return "Invalid e-mail address", 400

        users.update_one(
            {"username": session["username"]},
            {"$set": {"email": address, "email_verified": False}},
        )
        return redirect(url_for("home"))

    # GET  →  show the mini form
    current = users.find_one({"username": session["username"]}, {"email": 1})
    return render_template(
        "email_link.html",
        current_email=current.get("email") if current else None,
        username=session["username"],
        identity=session.get("identity", "student"),
    )


# ──────────────────────────────── unlink ────────────────────────────────
@email_bp.route("/email/unlink")
def email_unlink():
    if "username" not in session:
        return "Not logged in", 403
    users.update_one(
        {"username": session["username"]},
        {"$set": {"email": None, "email_verified": False}},
    )
    return redirect(url_for("home"))
