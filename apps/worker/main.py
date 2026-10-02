"""Vercel entrypoint for worker service."""

from app_worker.main import app

__all__ = ["app"]
