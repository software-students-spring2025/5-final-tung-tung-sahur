# user.py
from pymongo.collection import Collection
from werkzeug.security import generate_password_hash, check_password_hash


class UserModel:
    def __init__(self, collection: Collection):
        self.collection = collection

    def create_user(
        self, username: str, email: str, password: str, identity: str
    ) -> str:
        hashed_password = generate_password_hash(password)
        user = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "github": None,
            "identity": identity,  # "student" or "teacher"
        }
        result = self.collection.insert_one(user)
        return str(result.inserted_id)

    def find_by_username(self, username: str):
        return self.collection.find_one({"username": username})

    def verify_user(self, username: str, password: str) -> bool:
        user = self.find_by_username(username)
        if user and check_password_hash(user["password"], password):
            return True
        return False

    def find_by_id(self, user_id: str):
        from bson.objectid import ObjectId

        return self.collection.find_one({"_id": ObjectId(user_id)})
