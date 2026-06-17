"""Send CP via SMTP email."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .database import settings


def send_cp_email(recipient_email: str, html_body: str, company_name: str) -> None:
    """Send CP HTML as email body via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_user
    msg["To"] = recipient_email
    msg["Subject"] = f"Коммерческое предложение — {company_name}"

    text = f"Коммерческое предложение для {company_name}\n\nОтправлено ИНТПЭЙ"
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
