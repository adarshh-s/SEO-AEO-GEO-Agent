"""FastAPI application."""

import uuid
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app_api.deps import CSRF_HEADER, ORG_HEADER
from app_api.routers import (
    admin,
    audits,
    auth,
    diagnose,
    fixes,
    health,
    integrations,
    onboarding,
    orgs,
    plans,
    public,
    reports,
    sites,
    tracking,
    verification,
)
from app_core.brand import PRODUCT_NAME
from app_core.logging import configure_logging
from app_core.settings import get_settings


def _init_sentry(dsn: str | None, env: str) -> None:
    if not dsn:  # D11: Sentry only when configured
        return
    import sentry_sdk

    sentry_sdk.init(dsn=dsn, environment=env, traces_sample_rate=0.05, send_default_pii=False)


class ApiPrefixMiddleware:
    """ASGI middleware to strip /api prefix from request path when routed through Vercel."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "")
            if path.startswith("/api/"):
                scope["path"] = path[4:]
            elif path == "/api":
                scope["path"] = "/"
        await self.app(scope, receive, send)


def create_app() -> FastAPI:
    s = get_settings()
    configure_logging(s.log_level, s.log_json)
    _init_sentry(s.sentry_dsn, s.env)

    app = FastAPI(title=f"{PRODUCT_NAME} API", version="0.1.0")
    app.add_middleware(ApiPrefixMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", CSRF_HEADER, ORG_HEADER],
    )

    @app.middleware("http")
    # type: ignore[no-untyped-def]
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "validation_error",
                    "message": "Some fields are invalid.",
                    "fields": [
                        {"loc": [str(p) for p in e["loc"]], "msg": e["msg"]} for e in exc.errors()
                    ],
                }
            },
        )

    for module in (
        health,
        auth,
        orgs,
        sites,
        onboarding,
        plans,
        admin,
        tracking,
        fixes,
        diagnose,
        verification,
        integrations,
        audits,
        reports,
        public,
    ):
        app.include_router(module.router)
    return app


app = create_app()
