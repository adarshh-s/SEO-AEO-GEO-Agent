import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from sqlalchemy import func, select

from app_api.deps import Member, Tenant, TenantDb
from app_api.errors import ApiError, not_found
from app_api.ratelimit import client_ip
from app_api.routers.sites import get_site
from app_api.schemas.reports import (
    GenerateReportIn,
    ReportOut,
    SendTestDigestIn,
    SendTestDigestOut,
)
from app_api.services import audit as audit_service
from app_api.task_dispatcher import dispatch_task
from app_core.brand import BRAND
from app_core.models import (
    AiCheck,
    Audit,
    Fix,
    Keyword,
    Report,
    User,
)
from app_core.reports.pdf import generate_audit_pdf
from app_core.tenancy import scoped

router = APIRouter(prefix="/sites/{site_id}/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=201)
def generate_report(
    site_id: uuid.UUID,
    payload: GenerateReportIn,
    request: Request,
    ctx: Member,
    db: TenantDb,
) -> Report:
    """Generate executive PDF report for a website based on latest audit data."""
    site = get_site(db, ctx, site_id)

    audit_entry: Audit | None = None
    if payload.audit_id:
        audit_entry = db.scalar(
            scoped(select(Audit), Audit, ctx).where(
                Audit.id == payload.audit_id,
                Audit.site_id == site.id,
            )
        )
        if not audit_entry:
            raise not_found("audit")
    else:
        audit_entry = db.scalar(
            scoped(select(Audit), Audit, ctx)
            .where(
                Audit.site_id == site.id,
                Audit.status == "completed",
            )
            .order_by(Audit.created_at.desc())
        )

    # Reports are built from a completed audit; audits crawl the site, which only the worker
    # does (process-isolated SSRF protection), so don't crawl inside an API request.
    if not audit_entry or audit_entry.status != "completed":
        raise ApiError(
            409, "audit_required", "Run an audit for this website first, then generate the report."
        )

    # Compile metrics
    keywords_count = (
        db.scalar(
            scoped(select(func.count()), Keyword, ctx)
            .select_from(Keyword)
            .where(Keyword.site_id == site.id)
        )
        or 0
    )
    fixes_count = (
        db.scalar(
            scoped(select(func.count()), Fix, ctx)
            .select_from(Fix)
            .where(Fix.site_id == site.id, Fix.status == "deployed")
        )
        or 0
    )
    ai_checks_count = (
        db.scalar(
            scoped(select(func.count()), AiCheck, ctx)
            .select_from(AiCheck)
            .where(AiCheck.site_id == site.id, AiCheck.brand_mentioned.is_(True))
        )
        or 0
    )

    metrics_summary = {
        "overall_score": audit_entry.score,
        "category_scores": audit_entry.category_scores,
        "summary": audit_entry.summary,
        "keywords_count": keywords_count,
        "fixes_deployed": fixes_count,
        "ai_mentions": ai_checks_count,
    }

    pdf_bytes = generate_audit_pdf(
        domain=site.domain,
        overall_score=audit_entry.score,
        category_scores=audit_entry.category_scores,
        summary=audit_entry.summary,
        issues=audit_entry.issues,
        generated_at=datetime.now(UTC),
        language=payload.language,
    )

    title = (
        f"{BRAND['product_name']} SEO & AI Search Report - {site.domain}"
        if payload.language == "en"
        else f"تقرير {BRAND['product_name']} لتحسين محركات البحث والذكاء الاصطناعي - {site.domain}"
    )

    report = Report(
        id=uuid.uuid4(),
        org_id=ctx.org_id,
        site_id=site.id,
        audit_id=audit_entry.id,
        report_type=payload.report_type,
        title=title,
        language=payload.language,
        status="completed",
        metrics_summary=metrics_summary,
        pdf_bytes=pdf_bytes,
    )
    db.add(report)
    db.commit()

    audit_service.record(
        db,
        "report.generated",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="report",
        target_id=report.id,
        data={"site_id": str(site.id), "language": payload.language},
        ip=client_ip(request),
    )
    db.commit()

    return report


@router.get("", response_model=list[ReportOut])
def list_reports(
    site_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> list[Report]:
    """List generated reports for a website."""
    site = get_site(db, ctx, site_id)
    reports = db.scalars(
        scoped(select(Report), Report, ctx)
        .where(Report.site_id == site.id)
        .order_by(Report.created_at.desc())
    ).all()
    return list(reports)


@router.get("/{report_id}", response_model=ReportOut)
def get_report_meta(
    site_id: uuid.UUID,
    report_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> Report:
    """Get metadata for a generated report."""
    get_site(db, ctx, site_id)
    report = db.scalar(
        scoped(select(Report), Report, ctx).where(
            Report.id == report_id,
            Report.site_id == site_id,
        )
    )
    if not report:
        raise not_found("report")
    return report


@router.get("/{report_id}/download")
def download_report_pdf(
    site_id: uuid.UUID,
    report_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> Response:
    """Download the PDF file for a generated report."""
    site = get_site(db, ctx, site_id)
    report = db.scalar(
        scoped(select(Report), Report, ctx).where(
            Report.id == report_id,
            Report.site_id == site_id,
        )
    )
    if not report or not report.pdf_bytes:
        raise not_found("report")

    filename = (
        f"{BRAND['brand_slug']}-report-{site.domain}-{report.created_at.strftime('%Y%m%d')}.pdf"
    )
    return Response(
        content=report.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )


@router.post("/digest/send-test", response_model=SendTestDigestOut)
def send_test_digest(
    site_id: uuid.UUID,
    payload: SendTestDigestIn,
    ctx: Member,
    db: TenantDb,
) -> SendTestDigestOut:
    """Send an immediate test weekly digest email."""
    site = get_site(db, ctx, site_id)

    recipient = payload.recipient_email
    if not recipient:
        user = db.get(User, ctx.user_id)
        recipient = user.email if user else None

    if not recipient:
        raise ApiError(400, "recipient_required", "Recipient email is required.")

    dispatch_task(
        "app_worker.tasks.digest.send_site_weekly_digest",
        args=[str(site.id), recipient, payload.language],
        queue="default",
    )
    return SendTestDigestOut(
        status="queued",
        message=f"Test digest is on its way to {recipient}",
        emails_sent=0,
    )
