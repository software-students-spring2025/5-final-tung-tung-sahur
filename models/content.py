# content.py
from pymongo.collection import Collection
from bson.objectid import ObjectId
from datetime import datetime


class ContentModel:
    def __init__(self, collection: Collection):
        self.collection = collection

    def create_content(
        self,
        teacher_id: str,
        title: str,
        description: str,
        github_repo_url: str = None,
        github_repo_path: str = None,
    ) -> str:
        """Create a new content item"""
        content = {
            "teacher_id": teacher_id,
            "title": title,
            "description": description,
            "github_repo_url": github_repo_url,
            "github_repo_path": github_repo_path,
            "created_at": datetime.now(),
        }
        result = self.collection.insert_one(content)
        return str(result.inserted_id)

    def get_content(self, content_id: str) -> dict | None:
        """Find content by ID"""
        return self.collection.find_one({"_id": ObjectId(content_id)})

    def get_teacher_content(self, teacher_id: str) -> list:
        """Find all content by teacher ID"""
        return list(
            self.collection.find({"teacher_id": teacher_id}).sort("created_at", -1)
        )

    def get_all_content(self) -> list:
        """Find all content"""
        return list(self.collection.find().sort("created_at", -1))

    def update_content(self, content_id: str, update_data: dict) -> bool:
        """Update content information"""
        result = self.collection.update_one(
            {"_id": ObjectId(content_id)}, {"$set": update_data}
        )
        return result.modified_count > 0

    def delete_content(self, content_id: str) -> bool:
        """Delete content"""
        result = self.collection.delete_one({"_id": ObjectId(content_id)})
        return result.deleted_count > 0
