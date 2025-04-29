# tests/test_app_routes.py
import pytest
from unittest.mock import MagicMock, patch
from app import app

class TestAppRoutes:
    @patch('app.users')
    def test_all_students_route(self, mock_users, client):
        # Setup
        mock_users.find.return_value = [
            {"username": "student1", "identity": "student"},
            {"username": "teacher1", "identity": "teacher"},
            {"username": "student2", "identity": "student"}
        ]
        
        # Execute with teacher login
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.get('/allStudents')
        
        # Verify
        assert response.status_code == 200
        assert b"student1" in response.data
        assert b"student2" in response.data
        
    @patch('app.users')
    def test_delete_student_route(self, mock_users, client):
        # Setup
        mock_users.find_one.return_value = {
            "username": "student1", 
            "identity": "student"
        }
        
        # Execute with teacher login
        with client.session_transaction() as sess:
            sess['username'] = 'teacher'
            sess['identity'] = 'teacher'
            
        response = client.post('/deleteStudent/student1')
        
        # Verify
        assert response.status_code == 302
        assert response.location == "/allStudents"
        mock_users.delete_one.assert_called_once_with({"username": "student1"})