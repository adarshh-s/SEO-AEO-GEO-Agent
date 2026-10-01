"""EmailProvider: console (tests/dev), SMTP (Mailpit locally, or any SMTP), Resend (prod, D19)."""

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from functools import lru_cache
from typing import Protocol

import httpx

from app_core.brand import BRAND
from app_core.logging import get_logger
from app_core.settings import Settings, get_settings

log = get_logger(__name__)


@dataclass
class Email:
    to: str
    subject: str
    text: str
    html: str | None = None


class EmailProvider(Protocol):
    def send(self, email: Email) -> None: ...


class ConsoleEmailProvider:
    """Keeps sent emails in memory and logs them. Used in tests and when nothing is configured."""

    def __init__(self) -> None:
        self.outbox: list[Email] = []

    def send(self, email: Email) -> None:
        self.outbox.append(email)
        log.info("email.console", to=email.to, subject=email.subject)


class SmtpEmailProvider:
    def __init__(self, settings: Settings) -> None:
        self.s = settings

    def send(self, email: Email) -> None:
        msg = EmailMessage()
        msg["From"] = f"{BRAND['email_from_name']} <{self.s.email_from_address}>"
        msg["To"] = email.to
        msg["Subject"] = email.subject
        msg.set_content(email.text)
        if email.html:
            msg.add_alternative(email.html, subtype="html")
        with smtplib.SMTP(self.s.smtp_host, self.s.smtp_port, timeout=15) as smtp:
            if self.s.smtp_starttls:
                smtp.starttls()
            if self.s.smtp_username:
                smtp.login(self.s.smtp_username, self.s.smtp_password or "")
            smtp.send_message(msg)


class ResendEmailProvider:
    def __init__(self, settings: Settings) -> None:
        self.s = settings

    def send(self, email: Email) -> None:
        payload = {
            "from": f"{BRAND['email_from_name']} <{self.s.email_from_address}>",
            "to": [email.to],
            "subject": email.subject,
            "text": email.text,
        }
        if email.html:
            payload["html"] = email.html
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {self.s.resend_api_key}"},
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()


@lru_cache
def get_email_provider() -> EmailProvider:
    s = get_settings()
    if s.email_provider == "smtp":
        return SmtpEmailProvider(s)
    if s.email_provider == "resend":
        return ResendEmailProvider(s)
    return ConsoleEmailProvider()
