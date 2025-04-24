# github.py
from pymongo.collection import Collection
from bson.objectid import ObjectId

class GitHubModel:
    def __init__(self, user_collection: Collection):
        self.user_collection = user_collection

    def bind_account(self, user_id: str, github_id: int, github_username: str) -> bool:
        """Bind GitHub account to user by updating user document."""
        result = self.user_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "github": {
                    "id": github_id,
                    "username": github_username
                }
            }}
        )
        return result.modified_count > 0

    def get_github_info(self, user_id: str) -> dict | None:
        """Retrieve GitHub info for a given user."""
        user = self.user_collection.find_one({"_id": ObjectId(user_id)})
        if user and "github" in user:
            return user["github"]
        return None

    def unbind_account(self, user_id: str) -> bool:
        """Remove GitHub info from user."""
        result = self.user_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$unset": {
                "github": ""
            }}
        )
        return result.modified_count > 0
