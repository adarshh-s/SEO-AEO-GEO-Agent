from datetime import datetime

from pydantic import BaseModel


class VerificationStatusOut(BaseModel):
    domain: str
    verified: bool
    verified_at: datetime | None
    verification_method: str | None
    token: str
    meta_tag: str
    dns_txt_record: str


class VerifyAttemptOut(BaseModel):
    verified: bool
    method: str | None = None
    message: str
