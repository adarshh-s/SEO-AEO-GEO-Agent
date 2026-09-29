"""Payment provider interface: placeholder only (decision D20).

No implementation exists until Phase 7, which adds Moyasar or Tap first (SAR, mada,
Apple Pay) and Stripe second. Plans are assigned manually by platform admins until then.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass
class CheckoutSession:
    url: str
    provider_reference: str


@dataclass
class WebhookEvent:
    type: str
    provider_reference: str
    payload: dict


class PaymentProvider(Protocol):
    name: str

    def create_checkout(
        self, *, org_id: str, plan_code: str, amount: Decimal, currency: str, return_url: str
    ) -> CheckoutSession: ...

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> WebhookEvent: ...

    def cancel_subscription(self, *, provider_subscription_id: str) -> None: ...
