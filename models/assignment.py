# assignment.py
from pymongo.collection import Collection
from bson.objectid import ObjectId
from datetime import datetime


class AssignmentModel:
    def __init__(self, collection: Collection):
        self.collection = collection

    def create_assignment(
        self,
        teacher_id: str,
        title: str,
        description: str,
        due_date: str,
        github_repo_url: str = None,
        github_repo_path: str = None,
    ) -> str:
        """Create a new assignment"""
        assignment = {
            "teacher_id": teacher_id,
            "title": title,
            "description": description,
            "due_date": due_date,
            "github_repo_url": github_repo_url,
            "github_repo_path": github_repo_path,  # Added new field for repository path
            "created_at": datetime.now(),
            "reminder_sent": False,
        }
        result = self.collection.insert_one(assignment)
        return str(result.inserted_id)

    def get_assignment(self, assignment_id: str) -> dict | None:
        """Find assignment by ID"""
        return self.collection.find_one({"_id": ObjectId(assignment_id)})

    def get_teacher_assignments(self, teacher_id: str) -> list:
        """Find all assignments by teacher ID"""
        return list(
            self.collection.find({"teacher_id": teacher_id}).sort("created_at", -1)
        )

    def get_all_assignments(self) -> list:
        """Find all assignments"""
        return list(self.collection.find().sort("created_at", -1))

    def update_assignment(self, assignment_id: str, update_data: dict) -> bool:
        """Update assignment information"""
        result = self.collection.update_one(
            {"_id": ObjectId(assignment_id)}, {"$set": update_data}
        )
        return result.modified_count > 0

    def delete_assignment(self, assignment_id: str) -> bool:
        """Delete assignment"""
        result = self.collection.delete_one({"_id": ObjectId(assignment_id)})
        return result.deleted_count > 0
