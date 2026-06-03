"""SMTP mail helpers. Configure via environment variables:

    SMTP_HOST      – e.g. smtp.protonmail.ch
    SMTP_PORT      – default 587
    SMTP_USER      – login username
    SMTP_PASSWORD  – login password
    SMTP_FROM      – From address shown in emails
"""

import logging
import os
import smtplib
from email.message import EmailMessage

log = logging.getLogger(__name__)


def send_mail(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = os.environ["SMTP_FROM"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", 587))
    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)


def send_verification_email(to: str, token: str, base_url: str) -> None:
    link = f"{base_url}/verify/{token}"
    send_mail(
        to,
        "Bevestig je e-mailadres – Scubaduikers",
        (
            "Bedankt voor je registratie!\n\n"
            "Klik op de onderstaande link om je e-mailadres te bevestigen:\n\n"
            f"  {link}\n\n"
            "Deze link is 24 uur geldig.\n\n"
            "Als je geen account hebt aangemaakt, kun je deze e-mail negeren."
        ),
    )


def send_password_reset_email(to: str, token: str, base_url: str) -> None:
    link = f"{base_url}/reset-password/{token}"
    send_mail(
        to,
        "Wachtwoord opnieuw instellen – Scubaduikers",
        (
            "We hebben een verzoek ontvangen om je wachtwoord opnieuw in te stellen.\n\n"
            "Klik op de onderstaande link om een nieuw wachtwoord in te stellen:\n\n"
            f"  {link}\n\n"
            "Deze link is 1 uur geldig.\n\n"
            "Als je dit niet hebt aangevraagd, kun je deze e-mail negeren."
        ),
    )
