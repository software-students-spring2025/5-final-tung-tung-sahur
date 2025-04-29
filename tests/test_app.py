# tests/test_app.py
import pytest
import os
from unittest.mock import MagicMock, patch
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from flask import session

class TestApp:
    @patch('app.MongoClient')
    def test_home_logged_in_teacher(self, mock_mongo_client, client, sample_teacher_user, sample_github_info):
        # Setup mocks
        with patch('app.AssignmentModel'), patch('app.ContentModel'):
            # Set session
            with client.session_transaction() as sess:
                sess['username'] = 'teacher'
                sess['identity'] = 'teacher'
            
            # Execute
            response = client.get('/')
            
            # Verify basic response
            assert response.status_code == 200
            assert b'identity' in response.data

    @patch('app.MongoClient')
    def test_home_logged_in_student(self, mock_mongo_client, client, sample_student_user, sample_github_info):
        # Setup mocks
        with patch('app.AssignmentModel'), patch('app.SubmissionModel'), patch('app.ContentModel'):
            # Set session
            with client.session_transaction() as sess:
                sess['username'] = 'student'
                sess['identity'] = 'student'
            
            # Execute
            response = client.get('/')
            
            # Verify basic response
            assert response.status_code == it200
            assert b'identity' in response.data

    def test_home_not_logged_in(self, client):
        # Execute
        response = client.get('/')
        
        # Verify redirect to login
        assert response.status_code == 302
        assert '/login' in response.location
    
    @patch('app.MongoClient')
    def test_register_get(self, mock_mongo_client, client):
        # Execute
        response = client.get('/register')
        
        # Verify
        assert response.status_code == 200
        assert b'Register' in response.data
        assert b'Username' in response.data
        assert b'Password' in response.data
        assert b'Identity' in response.data
    
    @patch('app.MongoClient')
    def test_register_post_success(self, mock_mongo_client, client):
        # Setup mock db
        mock_db = MagicMock()
        mock_mongo_client.return_value.get_database.return_value = mock_db
        mock_db.users.find_one.return_value = None  # User doesn't exist
        
        # Execute
        response = client.post('/register', data={
            'username': 'newuser',
            'password': 'password123',
            'identity': 'student'
        })
        
        # Verify
        assert response.status_code == 302
        assert response.location == '/login'
        mock_db.users.insert_one.assert_called_once()
    
    @patch('app.MongoClient')
    def test_login_get(self, mock_mongo_client, client):
        # Execute
        response = client.get('/login')
        
        # Verify
        assert response.status_code == 200
        assert b'Login' in response.data
        
    @patch('app.MongoClient')
    @patch('app.check_password_hash')
    def test_login_post_success(self, mock_check_password, mock_mongo_client, client):
        # Setup
        mock_db = MagicMock()
        mock_mongo_client.return_value.get_database.return_value = mock_db
        
        # Mock user lookup
        mock_db.users.find_one.return_value = {
            'username': 'testuser',
            'password': 'hashed_password',
            'identity': 'student'
        }
        
        # Mock password check
        mock_check_password.return_value = True
        
        # Execute
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        # Verify
        assert response.status_code == 302
        assert response.location == '/'
        
        # Verify database calls
        mock_db.users.find_one.assert_called_once_with({"username": "testuser"})
        mock_check_password.assert_called_once_with("hashed_password", "password123")
    
    def test_logout(self, client):
        # Setup session
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            sess['identity'] = 'student'
        
        # Execute
        response = client.get('/logout')
        
        # Verify
        assert response.status_code == 302
        assert response.location == '/login'
        
        # Check session cleared
        with client.session_transaction() as sess:
            assert 'username' not in sess