import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

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
        return False


class ConsoleProvider(MessagingProvider):
    name = "console"

    async def send(self, to: str, body: str) -> DeliveryResult:
        logger.info("[mensaje simulado] para=%s cuerpo=%r", to, body[:200])
        return DeliveryResult(status=STATUS_SIMULATED, provider=self.name)


class WhatsAppCloudProvider(MessagingProvider):
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
    settings = get_settings()
    if settings.WHATSAPP_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID:
        return WhatsAppCloudProvider(
            settings.WHATSAPP_TOKEN,
            settings.WHATSAPP_PHONE_NUMBER_ID,
            settings.WHATSAPP_API_VERSION,
        )
    return ConsoleProvider()
