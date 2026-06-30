from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def _bool_env(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _smtp_config() -> dict[str, str | int | bool]:
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_email": os.getenv("MAIL_FROM", os.getenv("SMTP_USERNAME", "")),
        "from_name": os.getenv("MAIL_FROM_NAME", "RentalVerify"),
        "use_tls": _bool_env("SMTP_USE_TLS", True),
        "enabled": _bool_env("EMAIL_NOTIFICATIONS", True),
    }


def send_email(to_email: str, subject: str, body: str) -> bool:
    config = _smtp_config()
    if not config["enabled"]:
        return False
    if not config["username"] or not config["password"] or not config["from_email"]:
        logger.info("Email not sent: SMTP credentials are missing")
        return False

    message = EmailMessage()
    message["From"] = f'{config["from_name"]} <{config["from_email"]}>'
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(config["host"], int(config["port"]), timeout=20) as server:
            if config["use_tls"]:
                server.starttls(context=ssl.create_default_context())
            server.login(str(config["username"]), str(config["password"]))
            server.send_message(message)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False


def send_registration_email(full_name: str, email: str, role: str) -> bool:
    subject = "Welcome to RentalVerify"
    body = (
        f"Hi {full_name},\n\n"
        f"Your {role} account has been created successfully on RentalVerify.\n"
        "You can now log in and continue with your profile details.\n\n"
        "If you did not create this account, please ignore this email.\n"
    )
    return send_email(email, subject, body)


def send_verification_email(full_name: str, email: str, status: str) -> bool:
    pretty_status = status.replace("_", " ").strip().title()
    subject = f"RentalVerify account {pretty_status.lower()}"
    body = (
        f"Hi {full_name},\n\n"
        f"Your RentalVerify account has been {pretty_status.lower()}.\n"
        "You can log in to review your dashboard and next steps.\n\n"
        "If you have questions, contact support.\n"
    )
    return send_email(email, subject, body)
