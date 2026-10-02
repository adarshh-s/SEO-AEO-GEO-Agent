"""Diagnosis router for triggering page-by-page competitor gap analysis."""

import uuid

from fastapi import APIRouter
from sqlalchemy import desc, select

from app_api.deps import Member, Tenant, TenantDb
from app_api.errors import not_found
from app_api.routers.sites import get_site
from app_api.schemas.diagnose import DiagnosisOut, DiagnosisTriggerIn
from app_api.task_dispatcher import dispatch_task
from app_core.models import AiPrompt, Diagnosis, Keyword
from app_core.tenancy import scoped

router = APIRouter(prefix="/sites/{site_id}", tags=["diagnose"])


@router.post("/diagnose", response_model=DiagnosisOut, status_code=202)
def trigger_diagnosis(
    site_id: uuid.UUID,
    body: DiagnosisTriggerIn,
    ctx: Member,
    db: TenantDb,
) -> Diagnosis:
    site = get_site(db, ctx, site_id)

    # Validate target exists
    if body.target_type == "keyword":
        kw = db.scalar(
            scoped(select(Keyword), Keyword, ctx).where(
                Keyword.id == body.target_id, Keyword.site_id == site.id
            )
        )
        if not kw:
            raise not_found("keyword")
    elif body.target_type == "prompt":
        prompt = db.scalar(
            scoped(select(AiPrompt), AiPrompt, ctx).where(
                AiPrompt.id == body.target_id, AiPrompt.site_id == site.id
            )
        )
        if not prompt:
            raise not_found("prompt")

    diag = Diagnosis(
        id=uuid.uuid4(),
        org_id=ctx.org_id,
        site_id=site.id,
        target_type=body.target_type,
        target_id=body.target_id,
        status="pending",
    )
    db.add(diag)
    db.commit()

    dispatch_task(
        "app_worker.tasks.diagnose.run_diagnosis",
        args=[str(diag.id)],
        queue="agents",
    )
    return diag


@router.get("/diagnoses/{diagnosis_id}", response_model=DiagnosisOut)
def read_diagnosis(
    site_id: uuid.UUID,
    diagnosis_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> Diagnosis:
    site = get_site(db, ctx, site_id)
    diag = db.scalar(
        scoped(select(Diagnosis), Diagnosis, ctx).where(
            Diagnosis.id == diagnosis_id, Diagnosis.site_id == site.id
        )
    )
    if not diag:
        raise not_found("diagnosis")
    return diag


@router.get("/diagnoses", response_model=list[DiagnosisOut])
def list_diagnoses(
    site_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> list[Diagnosis]:
    site = get_site(db, ctx, site_id)
    return list(
        db.scalars(
            scoped(select(Diagnosis), Diagnosis, ctx)
            .where(Diagnosis.site_id == site.id)
            .order_by(desc(Diagnosis.created_at))
            .limit(20)
        )
    )
