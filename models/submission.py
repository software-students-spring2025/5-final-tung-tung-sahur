# submission.py
from pymongo.collection import Collection
from bson.objectid import ObjectId
from datetime import datetime

class SubmissionModel:
    def __init__(self, collection: Collection):
        self.collection = collection

    def create_submission(self, student_id: str, assignment_id: str, 
                         github_link: str, readme_content: str = None) -> str:
        """Submit an assignment"""
        submission = {
            "student_id": student_id,
            "assignment_id": assignment_id,
            "github_link": github_link,
            "readme_content": readme_content,
            "submitted_at": datetime.now(),
            "grade": None,
            "feedback": None,
            "status": "submitted"  # 可以是 submitted, graded 等
        }
        result = self.collection.insert_one(submission)
        return str(result.inserted_id)

    def get_submission(self, submission_id: str) -> dict | None:
        """Find submission by ID"""
        return self.collection.find_one({"_id": ObjectId(submission_id)})

    def get_student_submissions(self, student_id: str) -> list:
        """Find all submissions by student ID"""
        return list(self.collection.find({"student_id": student_id}).sort("submitted_at", -1))

    def get_assignment_submissions(self, assignment_id: str) -> list:
        """Find all submissions for a specific assignment"""
        return list(self.collection.find({"assignment_id": assignment_id}).sort("submitted_at", -1))
        
    def get_student_assignment_submission(self, student_id: str, assignment_id: str) -> dict | None:
        """Find submission by student ID and assignment ID"""
        return self.collection.find_one({
            "student_id": student_id,
            "assignment_id": assignment_id
        })

    def update_submission(self, submission_id: str, update_data: dict) -> bool:
        """Update submission information"""
        result = self.collection.update_one(
            {"_id": ObjectId(submission_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
        
    def add_feedback(self, submission_id: str, grade: float, feedback: str) -> bool:
        """Add feedback and grade to a submission"""
        update_data = {
            "grade": grade,
            "feedback": feedback,
            "status": "graded",
            "graded_at": datetime.now()
        }
        return self.update_submission(submission_id, update_data)