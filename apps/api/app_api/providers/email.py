"""Re-export: the email provider lives in app_core so the worker (digests) can use it too."""

from app_core.email import (
    ConsoleEmailProvider,
    Email,
    EmailProvider,
    ResendEmailProvider,
    SmtpEmailProvider,
    get_email_provider,
)

__all__ = [
    "ConsoleEmailProvider",
    "Email",
    "EmailProvider",
    "ResendEmailProvider",
    "SmtpEmailProvider",
    "get_email_provider",
]
