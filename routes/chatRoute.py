# routes/chatRoutes.py
from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    url_for,
    abort,
    flash,
)
from models.chat import ChatModel
from models.user import UserModel
from bson.objectid import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
import os

load_dotenv()
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/gitBrightSpace")
mongo_client = MongoClient(mongo_uri)
db = mongo_client.get_database()

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")
chat_collection = db["chats"]
user_collection = db["users"]
user_model = UserModel(user_collection)
chat_model = ChatModel(chat_collection)


def get_all_contacts(current_username):
    users = user_collection.find({"username": {"$ne": current_username}})
    grouped = {"student": [], "teacher": []}
    for user in users:
        identity = user.get("identity")
        if identity in grouped:
            grouped[identity].append(user["username"])
    return grouped


@chat_bp.route("/")
def chat_index():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    contacts = chat_model.get_recent_contacts(username)
    all_contacts = get_all_contacts(username)

    return render_template(
        "chat.html",
        contacts=contacts,
        all_contacts=all_contacts,
        selected=None,
        messages=[],
    )


@chat_bp.route("/with/<contact>", methods=["GET", "POST"])
def chat_with(contact):
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]

    if contact == username:
        flash("You cannot chat with yourself.", "warning")
        return redirect(url_for("chat.chat_index"))

    # if not user_model.find_by_username(contact):
    #     abort(404, description="User not found")

    if request.method == "POST":
        message = request.form.get("message")
        if not user_model.find_by_username(contact):
            flash("You cannot chat with someone who does not exists now", "danger")
            return redirect(url_for("chat.chat_with", contact=contact))
        if message:
            chat_model.send_message(sender=username, receiver=contact, content=message)
            return redirect(url_for("chat.chat_with", contact=contact))

    messages = chat_model.get_conversation(username, contact)
    contacts = chat_model.get_recent_contacts(username)
    all_contacts = get_all_contacts(username)

    return render_template(
        "chat.html",
        contacts=contacts,
        all_contacts=all_contacts,
        selected=contact,
        messages=messages,
    )
