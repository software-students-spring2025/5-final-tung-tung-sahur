# models/chat.py
from pymongo.collection import Collection
from datetime import datetime, timezone
from bson.objectid import ObjectId


class ChatModel:
    def __init__(self, collection: Collection):
        self.collection = collection

    def send_message(self, sender: str, receiver: str, content: str) -> str:
        message = {
            "sender": sender,
            "receiver": receiver,
            "content": content,
            "timestamp": datetime.now(timezone.utc),
        }
        result = self.collection.insert_one(message)
        return str(result.inserted_id)

    def get_conversation(self, user1: str, user2: str) -> list:
        """Fetch all messages between user1 and user2 sorted by timestamp."""
        return list(
            self.collection.find(
                {
                    "$or": [
                        {"sender": user1, "receiver": user2},
                        {"sender": user2, "receiver": user1},
                    ]
                }
            ).sort("timestamp", 1)
        )

    def get_recent_contacts(self, username: str) -> list:
        """Fetch usernames chatted with, sorted by latest message timestamp (desc)."""
        pipeline = [
            {"$match": {"$or": [{"sender": username}, {"receiver": username}]}},
            {
                "$project": {
                    "other": {
                        "$cond": [
                            {"$eq": ["$sender", username]},
                            "$receiver",
                            "$sender",
                        ]
                    },
                    "timestamp": 1,
                }
            },
            {"$sort": {"timestamp": -1}},
            {"$group": {"_id": "$other", "latest_time": {"$first": "$timestamp"}}},
            {"$sort": {"latest_time": -1}},
        ]
        return [doc["_id"] for doc in self.collection.aggregate(pipeline)]
