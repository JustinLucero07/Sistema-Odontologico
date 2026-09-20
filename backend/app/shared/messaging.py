"""Outbound messaging behind one interface.

The rule this module exists to enforce: **a message is never recorded as sent
unless something actually sent it.** A clinic that believes a reminder went out
stops calling the patient, so a comfortable lie here costs a real appointment.

With no credentials configured the default provider records the message as
`simulado` — visibly not `enviado` — and the outbox says so on screen.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# What a message can be. `simulado` is deliberately distinct from `enviado`:
# collapsing the two is exactly the lie this module refuses to tell.
STATUS_PENDING = "pendiente"
STATUS_SENT = "enviado"
STATUS_FAILED = "fallido"
STATUS_SIMULATED = "simulado"
STATUS_CANCELLED = "cancelado"


@dataclass
class DeliveryResult:
    status: str
    provider: str
    provider_message_id: str | None = None
    error: str | None = None


class MessagingProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    async def send(self, to: str, body: str) -> DeliveryResult: ...

    @property
    def is_live(self) -> bool:
        """Whether this provider can really reach a phone. The UI reads it to
        tell the user what will actually happen when they press send."""
        return False


class ConsoleProvider(MessagingProvider):
    """The default. Writes the message to the log and reports `simulado`.

    Nothing leaves the server, and the record says so, so a demo can never be
    mistaken for a working integration."""

    name = "console"

    async def send(self, to: str, body: str) -> DeliveryResult:
        logger.info("[mensaje simulado] para=%s cuerpo=%r", to, body[:200])
        return DeliveryResult(status=STATUS_SIMULATED, provider=self.name)


class WhatsAppCloudProvider(MessagingProvider):
    """Meta's WhatsApp Cloud API.

    Only constructed when a token and a phone-number id are configured; see
    `get_messaging`. A failure here is reported as `fallido` with the API's own
    message, never swallowed into a success."""

    name = "whatsapp_cloud"

    def __init__(self, token: str, phone_number_id: str, api_version: str = "v21.0"):
        self.token = token
        self.phone_number_id = phone_number_id
        self.endpoint = (
            f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        )

    @property
    def is_live(self) -> bool:
        return True

    async def send(self, to: str, body: str) -> DeliveryResult:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            # Meta wants the number in E.164 without the leading '+'.
            "to": to.lstrip("+").replace(" ", "").replace("-", ""),
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(self.endpoint, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            return DeliveryResult(
                status=STATUS_FAILED, provider=self.name, error=f"Error de red: {exc}"
            )

        if response.status_code >= 400:
            # Meta's own wording is far more useful than anything generic we
            # could substitute ("número no está en WhatsApp", "plantilla no
            # aprobada"), so it is kept verbatim.
            detail = response.text[:400]
            try:
                detail = response.json()["error"]["message"]
            except (ValueError, KeyError, TypeError):
                pass
            return DeliveryResult(status=STATUS_FAILED, provider=self.name, error=detail)

        message_id = None
        try:
            message_id = response.json()["messages"][0]["id"]
        except (ValueError, KeyError, IndexError, TypeError):
            pass
        return DeliveryResult(
            status=STATUS_SENT, provider=self.name, provider_message_id=message_id
        )


def get_messaging() -> MessagingProvider:
    """Live provider when it is fully configured, console otherwise.

    A half-configured integration falls back rather than failing at send time:
    a missing token is a deployment problem, not a reason to lose the message."""
    settings = get_settings()
    if settings.WHATSAPP_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID:
        return WhatsAppCloudProvider(
            settings.WHATSAPP_TOKEN,
            settings.WHATSAPP_PHONE_NUMBER_ID,
            settings.WHATSAPP_API_VERSION,
        )
    return ConsoleProvider()
