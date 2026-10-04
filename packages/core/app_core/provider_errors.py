"""Errors shared by all external providers (kept separate to avoid import cycles)."""


class ProviderNotConfigured(RuntimeError):
    """A real provider is missing its API key or model (set them in env)."""
