import pytest
from unittest.mock import patch, MagicMock
import routes.assignmentRoute as ar
import os
from io import BytesIO
import base64
from flask import Flask


class TestRouteHelpers:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.secret_key = "test_secret_key"
        return app

    @patch("routes.assignmentRoute.MIMEMultipart")
    @patch("routes.assignmentRoute.MIMEText")
    @patch("routes.assignmentRoute.MIMEImage")
    @patch("routes.assignmentRoute.Path")
    @patch("routes.assignmentRoute.smtplib.SMTP_SSL")
    @patch("routes.assignmentRoute.ssl.create_default_context")
    def test_send_receipt_html(self, mock_ssl, mock_smtp, mock_path, mock_img, mock_text, mock_multipart):
        # Setup mocks
        mock_msg = MagicMock()
        mock_multipart.return_value = mock_msg
        
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.__truediv__.return_value = mock_path_instance
        
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"image_data"
        mock_path_instance.open.return_value = mock_file
        
        mock_img_instance = MagicMock()
        mock_img.return_value = mock_img_instance
        
        mock_text_instance = MagicMock()
        mock_text.return_value = mock_text_instance
        
        mock_ssl_context = MagicMock()
        mock_ssl.return_value = mock_ssl_context
        
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        
        # Execute
        ar.send_receipt_html("test@example.com", "Test Assignment")
        
        # Assert
        mock_multipart.assert_called_once_with("related")
        mock_path.assert_called_once()
        mock_file.__enter__.return_value.read.assert_called_once()
        mock_img.assert_called_once_with(b"image_data")
        mock_img_instance.add_header.assert_any_call("Content-ID", "<loader>")
        mock_msg.attach.assert_any_call(mock_text_instance)
        mock_msg.attach.assert_any_call(mock_img_instance)
        mock_smtp.assert_called_once()
        mock_smtp_instance.login.assert_called_once()
        mock_smtp_instance.send_message.assert_called_once_with(mock_msg)