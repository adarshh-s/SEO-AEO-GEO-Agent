import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GenerateReportIn(BaseModel):
    audit_id: uuid.UUID | None = None
    language: str = Field(default="en", pattern="^(en|ar)$")
    report_type: str = Field(default="audit", pattern="^(audit|executive_summary)$")


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site_id: uuid.UUID
    audit_id: uuid.UUID | None = None
    report_type: str
    title: str
    language: str
    status: str
    metrics_summary: dict[str, Any]
    created_at: datetime


class SendTestDigestIn(BaseModel):
    recipient_email: str | None = None
    language: str = Field(default="en", pattern="^(en|ar)$")


class SendTestDigestOut(BaseModel):
    status: str
    message: str
    emails_sent: int
