"""API errors. The frontend translates `code`; `message` is an English fallback."""

from typing import Any

from fastapi import HTTPException


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, **extra: Any) -> None:
        super().__init__(
            status_code=status_code, detail={"code": code, "message": message, **extra}
        )


def not_found(what: str = "resource") -> ApiError:
    # Also used for other orgs' resources: never reveal that they exist.
    return ApiError(404, "not_found", f"{what} not found")


def forbidden(message: str = "You don't have permission to do this.") -> ApiError:
    return ApiError(403, "forbidden", message)


def unauthorized(message: str = "Not signed in.") -> ApiError:
    return ApiError(401, "unauthorized", message)
