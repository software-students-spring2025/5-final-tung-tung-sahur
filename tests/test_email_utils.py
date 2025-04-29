import pytest
from unittest.mock import MagicMock, patch
import smtplib
import ssl
from email.message import EmailMessage


class TestEmailUtils:
    @patch("smtplib.SMTP_SSL")
    @patch("ssl.create_default_context")
    def test_send_mail(self, mock_ssl_context, mock_smtp_ssl):
        # Setup
        mock_context = MagicMock()
        mock_ssl_context.return_value = mock_context

        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = mock_smtp

        # Import the function to test
        from email_utils import send_mail

        # Execute
        send_mail("test@example.com", "Test Subject", "Test Body")

        # Verify
        mock_ssl_context.assert_called_once()
        mock_smtp_ssl.assert_called_once_with("smtp.163.com", 465, context=mock_context)

        # Verify login and send_message were called
        mock_smtp.login.assert_called_once()
        mock_smtp.send_message.assert_called_once()

        # Verify the message content
        msg = mock_smtp.send_message.call_args[0][0]
        assert msg["From"] == "13601583609@163.com"
        assert msg["To"] == "test@example.com"
        assert msg["Subject"] == "Test Subject"
        assert "Test Body" in msg.get_content()

    @patch("smtplib.SMTP_SSL")
    @patch("ssl.create_default_context")
    def test_send_mail_exception(self, mock_ssl_context, mock_smtp_ssl):
        # Setup
        mock_context = MagicMock()
        mock_ssl_context.return_value = mock_context

        # Make login raise exception
        mock_smtp = MagicMock()
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(
            535, b"Authentication failed"
        )
        mock_smtp_ssl.return_value.__enter__.return_value = mock_smtp

        # Import the function to test
        from email_utils import send_mail

        # Execute and verify exception is raised
        with pytest.raises(smtplib.SMTPAuthenticationError):
            send_mail("test@example.com", "Test Subject", "Test Body")

        # Verify login was called but not send_message
        mock_smtp.login.assert_called_once()
        mock_smtp.send_message.assert_not_called()
