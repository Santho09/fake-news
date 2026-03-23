from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def smtp_is_configured() -> bool:
    return bool(os.getenv("SMTP_HOST", "").strip() and os.getenv("SMTP_FROM_EMAIL", "").strip())


def send_password_reset_email(*, to_email: str, reset_url: str) -> None:
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587").strip() or "587")
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", "").strip()
    from_name = os.getenv("SMTP_FROM_NAME", "NewsVeritas").strip() or "NewsVeritas"
    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes"}

    if not host or not from_email:
        raise RuntimeError("SMTP is not configured (missing SMTP_HOST or SMTP_FROM_EMAIL)")

    msg = EmailMessage()
    msg["Subject"] = "Reset your NewsVeritas password"
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.set_content(
        "You requested a password reset for your NewsVeritas account.\n\n"
        f"Open this link to reset your password:\n{reset_url}\n\n"
        "If you did not request this, you can safely ignore this email."
    )

    with smtplib.SMTP(host, port, timeout=20) as server:
        if use_tls:
            server.starttls()
        if username and password:
            server.login(username, password)
        server.send_message(msg)
