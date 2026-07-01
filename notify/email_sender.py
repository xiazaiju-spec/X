from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText


def send_email_report(subject: str, markdown: str) -> None:
    enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    if not enabled:
        return

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("EMAIL_FROM") or username
    recipients = [item.strip() for item in os.getenv("EMAIL_TO", "").split(",") if item.strip()]

    if not all([host, username, password, sender]) or not recipients:
        raise ValueError("邮箱推送已启用，但 SMTP 或收件人配置不完整")

    message = MIMEText(markdown, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(recipients)

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(username, password)
        server.sendmail(sender, recipients, message.as_string())
