# email_utils.py
import os, smtplib, ssl
from email.message import EmailMessage

FROM_EMAIL = "13601583609@163.com"
SMTP_SERVER = "smtp.163.com"
SMTP_PORT = 465
SMTP_LOGIN = "13601583609@163.com"
SMTP_PASS = os.getenv("Email_password")  # keep secret in .env


def send_mail(to_addr: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = FROM_EMAIL
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=ctx) as smtp:
        smtp.login(SMTP_LOGIN, SMTP_PASS)
        smtp.send_message(msg)
