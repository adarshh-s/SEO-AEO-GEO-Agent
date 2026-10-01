"""Platform connectors protocol and result data structures."""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ConnectionTestResult:
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentResult:
    ok: bool
    message: str
    external_reference: str | None = None
    previous_state: dict[str, Any] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackResult:
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class PlatformConnector(Protocol):
    provider_name: str

    def test_connection(
        self, config: dict[str, Any], credentials: dict[str, Any]
    ) -> ConnectionTestResult: ...

    def deploy_fix(
        self,
        *,
        target_url: str,
        fix_type: str,
        title: str,
        payload: dict[str, Any],
        config: dict[str, Any],
        credentials: dict[str, Any],
        site_key: str,
        previous_state: dict[str, Any] | None = None,
    ) -> DeploymentResult: ...

    def rollback_fix(
        self,
        *,
        target_url: str,
        fix_type: str,
        external_reference: str | None,
        previous_state: dict[str, Any] | None,
        config: dict[str, Any],
        credentials: dict[str, Any],
    ) -> RollbackResult: ...
