import pytest
import os
from unittest.mock import MagicMock, patch
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from flask import session

class TestApp:
    @patch('app.MongoClient')
    def test_home_logged_in_teacher(self, mock_mongo_client, client, sample_teacher_user, sample_github_info):
        # Setup
        mock_db = MagicMock()
        mock_mongo_client.return_value.get_database.return_value = mock_db
        
        user_id = str(sample_teacher_user["_id"])
        
        # Mock user lookup
        mock_db.users.find_one.return_value = sample_teacher_user
        
        # Mock GitHub info
        mock_db.github_accounts.find_one.return_value = sample_github_info
        
        # Mock assignments
        mock_assignments = [
            {"_id": ObjectId(), "title": "Assignment 1"},
            {"_id": ObjectId(), "title": "Assignment 2"}
        ]
        
        # Mock content
        mock_content = [
            {"_id": ObjectId(), "title": "Lecture 1"},
            {"_id": ObjectId(), "title": "Lecture 2"}
        ]
        
        # Setup mocks for AssignmentModel and ContentModel
        with patch('app.AssignmentModel') as mock_assignment_model:
            with patch('app.ContentModel') as mock_content_model:
                mock_assignment_model.return_value.get_teacher_assignments.return_value = mock_assignments
                mock_content_model.return_value.get_teacher_content.return_value = mock_content
                
                # Execute
                with client.session_transaction() as sess:
                    sess['username'] = 'teacher'
                    sess['identity'] = 'teacher'
                    
                response = client.get('/')
                
                # Verify
                assert response.status_code == 200
                assert b"Welcome back, teacher" in response.data
                assert b"Assignment 1" in response.data
                assert b"Assignment 2" in response.data
                assert b"Lecture 1" in response.data
                assert b"Lecture 2" in response.data
                
                # Verify calls
                mock_db.users.find_one.assert_called_with({"username": "teacher"})
                mock_db.github_accounts.find_one.assert_called_with({"username": "teacher"})
                mock_assignment_model.return_value.get_teacher_assignments.assert_called_with(user_id)
                mock_content_model.return_value.get_teacher_content.assert_called_with(user_id)
    
    @patch('app.MongoClient')
    def test_home_logged_in_student(self, mock_mongo_client, client, sample_student_user, sample_github_info):
        # Setup
        mock_db = MagicMock()
        mock_mongo_client.return_value.get_database.return_value = mock_db
        
        user_id = str(sample_student_user["_id"])
        
        # Mock user lookup
        mock_db.users.find_one.return_value = sample_student_user
        
        # Mock GitHub info
        mock_db.github_accounts.find_one.return_value = sample_github_info
        
        # Mock assignments with due dates
        now = datetime.now()
        mock_assignments = [
            {
                "_id": ObjectId(),
                "title": "Assignment 1",
                "due_date": (now + timedelta(days=7)).isoformat()  # Future date
            },
            {
                "_id": ObjectId(),
                "title": "Assignment 2",
                "due_date": (now - timedelta(days=7)).isoformat()  # Past date
            }
        ]
        
        # Mock content
        mock_content = [
            {"_id": ObjectId(), "title": "Lecture 1"},
            {"_id": ObjectId(), "title": "Lecture 2"}
        ]
        
        # Mock submissions
        mock_submissions = [
            {
                "assignment_id": str(mock_assignments[0]["_id"]),
                "status": "submitted"
            }
        ]
        
        # Setup mocks for AssignmentModel, SubmissionModel, and ContentModel
        with patch('app.AssignmentModel') as mock_assignment_model:
            with patch('app.SubmissionModel') as mock_submission_model:
                with patch('app.ContentModel') as mock_content_model:
                    mock_assignment_model.return_value.get_all_assignments.return_value = mock_assignments
                    mock_submission_model.return_value.get_student_submissions.return_value = mock_submissions
                    mock_content_model.return_value.get_all_content.return_value = mock_content
                    
                    # Execute
                    with client.session_transaction() as sess:
                        sess['username'] = 'student'
                        sess['identity'] = 'student'
                        
                    response = client.get('/')
                    
                    # Verify
                    assert response.status_code == 200
                    assert b"Welcome back, student" in response.data
                    assert b"Assignment 1" in response.data
                    assert b"Assignment 2" in response.data
                    
                    # Verify calls
                    mock_db.users.find_one.assert_called_with({"username": "student"})
                    mock_db.github_accounts.find_one.assert_called_with({"username": "student"})
                    mock_assignment_model.return_value.get_all_assignments.assert_called_once()
                    mock_submission_model.return_value.get_student_submissions.assert_called_with(user_id)
                    mock_content_model.return_value.get_all_content.assert_called_once()
    
    def test_home_not_logged_in(self, client):
        # Execute
        response = client.get('/')
        
        # Verify
        assert response.status_code == 302
        assert response.location == "/login"
    
    @patch('app.MongoClient')
    def test_register_get(self, mock_mongo_client, client):
        # Execute
        response = client.get('/register')
        
        # Verify
        assert response.status_code == 200
        assert b"Register" in response.data
        assert b"Username" in response.data
        assert b"Password" in response.data
        assert b"Identity" in response.data
    
    @patch('app.MongoClient')
    def test_register_post_success(self, mock_mongo_client, client):
        # Setup
        mock_db = MagicMock()
        mock_mongo_client.return_value.get_database.return_value = mock_db
        
        # Mock user lookup (user doesn't exist)
        mock_db.users.find_one.return_value = None
        
        # Execute
        form_data = {
            "username": "newuser",
            "password": "password123",
            "identity": "student"
        }
        response = client.post('/register', data=form_data)
        
        # Verify
        assert response.status_code == 302
        assert response.location == "/login"
        
        # Verify database calls
        mock_db.users.find_one.assert_called_once_with({"username": "newuser"})
        mock_db.users.insert_one.assert_called_once()
        
        # Check the inserted user data
        inserted_user = mock_db.users.insert_one.call_args[0][0]
        assert inserted_user["username"] == "newuser"
        assert inserted_user["password"] != "password123"  # Password should be hashed
        assert inserted_user["identity"] == "student"
        assert inserted_user["github"] is None
    
    @patch('app.MongoClient')
    def test_register_post_user_exists(self, mock_mongo_client, client):
        # Setup
        mock_db = MagicMock()
        mock_mongo_client.return_value.get_database.return_value = mock_db
        
        # Mock user lookup (user exists)
        mock_db.users.find_one.return_value = {"username": "existinguser"}
        
        # Execute
        form_data = {
            "username": "existinguser",
            "password": "password123",
            "identity": "student"
        }
        response = client.post('/register', data=form_data)
        
        # Verify
        assert response.status_code == 200
        assert b"User already exists" in response.data
        
        # Verify database calls
        mock_db.users.find_one.assert_called_once_with({"username": "existinguser"})
        mock_db.users.insert_one.assert_not_called()
    
    @patch('app.MongoClient')
    @patch('app.check_password_hash')
    def test_login_post_success(self, mock_check_password, mock_mongo_client, client):
        # Setup
        mock_db = MagicMock()
        mock_mongo_client.return_value.get_database.return_value = mock_db
        
        # Mock user lookup
        mock_db.users.find_one.return_value = {
            "username": "testuser",
            "password": "hashed_password",
            "identity": "student"
        }
        
        # Mock password check
        mock_check_password.return_value = True
        
        # Execute
        form_data = {
            "username": "testuser",
            "password": "password123"
        }
        response = client.post('/login', data=form_data)
        
        # Verify
        assert response.status_code == 302
        assert response.location == "/"
        
        # Verify session values
        with client.session_transaction() as sess:
            assert sess["username"] == "testuser"
            assert sess["identity"] == "student"
            
        # Verify database calls
        mock_db.users.find_one.assert_called_once_with({"username": "testuser"})
        mock_check_password.assert_called_once_with("hashed_password", "password123")
    
    @patch('app.MongoClient')
    @patch('app.check_password_hash')
    def test_login_post_invalid_password(self, mock_check_password, mock_mongo_client, client):
        # Setup
        mock_db = MagicMock()
        mock_mongo_client.return_value.get_database.return_value = mock_db
        
        # Mock user lookup
        mock_db.users.find_one.return_value = {
            "username": "testuser",
            "password": "hashed_password",
            "identity": "student"
        }
        
        # Mock password check
        mock_check_password.return_value = False
        
        # Execute
        form_data = {
            "username": "testuser",
            "password": "wrong_password"
        }
        response = client.post('/login', data=form_data)
        
        # Verify
        assert response.status_code == 200
        assert b"Username or password is incorrect" in response.data
        
        # Verify database calls
        mock_db.users.find_one.assert_called_once_with({"username": "testuser"})
        mock_check_password.assert_called_once_with("hashed_password", "wrong_password")
    
    @patch('app.MongoClient')
    def test_login_post_user_not_found(self, mock_mongo_client, client):
        # Setup
        mock_db = MagicMock()
        mock_mongo_client.return_value.get_database.return_value = mock_db
        
        # Mock user lookup (user not found)
        mock_db.users.find_one.return_value = None
        
        # Execute
        form_data = {
            "username": "nonexistent",
            "password": "password123"
        }
        response = client.post('/login', data=form_data)
        
        # Verify
        assert response.status_code == 200
        assert b"Username or password is incorrect" in response.data
        
        # Verify database calls
        mock_db.users.find_one.assert_called_once_with({"username": "nonexistent"})
    
    def test_logout(self, client):
        # Setup - add session data
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            sess['identity'] = 'student'
        
        # Execute
        response = client.get('/logout')
        
        # Verify
        assert response.status_code == 302
        assert response.location == "/login"
        
        # Verify session is cleared
        with client.session_transaction() as sess:
            assert 'username' not in sess
            assert 'identity' not in sess
    
    @patch('app.MongoClient')
    def test_all_students(self, mock_mongo_client, client):
        # Setup
        mock_db = MagicMock()
        mock_mongo_client.return_value.get_database.return_value = mock_db
        
        # Mock all users
        mock_db.users.find.return_value = [
            {"username": "student1", "identity": "student", "email": "student1@example.com"},
            {"username": "teacher1", "identity": "teacher", "email": "teacher1@example.com"},
            {"username": "student2", "identity": "student", "email": "student2@example.com"}
        ]
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.get('/allStudents')
        
        # Verify
        assert response.status_code == 200
        assert b"student1" in response.data
        assert b"student2" in response.data
        assert b"teacher1" not in response.data  # Teachers should not be listed
        
        # Verify database calls
        mock_db.users.find.assert_called_once()
    
    @patch('app.MongoClient')
    def test_all_students_not_teacher(self, mock_mongo_client, client):
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'student'
            sess['identity'] = 'student'
            
        response = client.get('/allStudents')
        
        # Verify - should redirect to home
        assert response.status_code == 302
        assert response.location == "/home"
    
    @patch('app.MongoClient')
    def test_delete_student(self, mock_mongo_client, client):
        # Setup
        mock_db = MagicMock()
        mock_mongo_client.return_value.get_database.return_value = mock_db
        
        # Mock student lookup
        mock_db.users.find_one.return_value = {
            "username": "student1",
            "identity": "student"
        }
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.post('/deleteStudent/student1')
        
        # Verify
        assert response.status_code == 302
        assert response.location == "/allStudents"
        
        # Verify database calls
        mock_db.users.find_one.assert_called_once_with({"username": "student1"})
        mock_db.users.delete_one.assert_called_once_with({"username": "student1"})
        mock_db.github_accounts.delete_one.assert_called_once_with({"username": "student1"})
    
    @patch('app.MongoClient')
    def test_delete_student_not_found(self, mock_mongo_client, client):
        # Setup
        mock_db = MagicMock()
        mock_mongo_client.return_value.get_database.return_value = mock_db
        
        # Mock student lookup (not found)
        mock_db.users.find_one.return_value = None
        
        # Execute
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.post('/deleteStudent/nonexistent')
        
        # Verify
        assert response.status_code == 404
        assert b"User not found or not a student" in response.data
        
        # Verify database calls
        mock_db.users.find_one.assert_called_once_with({"username": "nonexistent"})
        mock_db.users.delete_one.assert_not_called()
        mock_db.github_accounts.delete_one.assert_not_called()