from typing import Annotated

from fastapi import APIRouter, Depends
from redis import Redis
from sqlalchemy import text

from app_api.deps import SystemDb
from app_api.ratelimit import get_redis

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz(db: SystemDb, redis: Annotated[Redis, Depends(get_redis)]) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    redis.ping()
    return {"status": "ok"}
