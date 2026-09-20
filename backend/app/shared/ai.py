"""The assistant layer.

Two rules govern everything here, and both are enforced in code rather than
trusted to a prompt:

  1. **The assistant never invents clinical content.** Its context is assembled
     server-side from the patient's own records. It is told, in the system
     prompt, that it may not diagnose, may not recommend treatment and may not
     state prices — and its output is then SCANNED for those things before
     anyone sees it.

  2. **Its output is always a draft for a person.** Nothing it writes reaches
     the clinical record on its own. A human reads it, edits it, and the record
     carries that human's name.

With no API key the assistant is OFF. It does not degrade into a canned
paragraph, because a plausible sentence nobody generated is worse than a clear
"not configured".
"""

import re
from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings


class AiUnavailable(RuntimeError):
    """Raised when no assistant is configured. Callers turn this into a plain
    message rather than a fabricated answer."""


class AiProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    async def complete(self, system: str, user: str) -> str: ...

    @property
    def is_available(self) -> bool:
        return False


class DisabledAiProvider(AiProvider):
    name = "disabled"

    async def complete(self, system: str, user: str) -> str:
        raise AiUnavailable(
            "El asistente no está configurado. Añada ANTHROPIC_API_KEY para activarlo."
        )


class AnthropicProvider(AiProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str, max_tokens: int):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

    @property
    def is_available(self) -> bool:
        return True

    async def complete(self, system: str, user: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages", json=payload, headers=headers
            )
        if response.status_code >= 400:
            detail = response.text[:300]
            try:
                detail = response.json()["error"]["message"]
            except (ValueError, KeyError, TypeError):
                pass
            raise AiUnavailable(f"El asistente respondió con un error: {detail}")

        data = response.json()
        return "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        ).strip()


def get_ai() -> AiProvider:
    settings = get_settings()
    if settings.ANTHROPIC_API_KEY:
        return AnthropicProvider(
            settings.ANTHROPIC_API_KEY, settings.AI_MODEL, settings.AI_MAX_TOKENS
        )
    return DisabledAiProvider()


# ---- Guardrails ---------------------------------------------------------

BASE_SYSTEM_PROMPT = """Eres un asistente administrativo de una clínica dental.

Trabajas ÚNICAMENTE con la información del paciente que se te entrega en el
mensaje. Reglas estrictas:

- NO emitas diagnósticos ni los sugieras. Si el registro contiene un
  diagnóstico, puedes citarlo indicando que ya estaba registrado.
- NO recomiendes tratamientos ni indiques cuál debería hacerse.
- NO menciones precios, importes, tarifas ni costos bajo ninguna circunstancia.
- NO inventes fechas, piezas dentales, alergias ni antecedentes. Si un dato no
  está en el contexto, di explícitamente que no consta en el registro.
- Escribe en español neutro, claro y breve.

Lo que produces es un BORRADOR que un profesional leerá, editará y decidirá si
usa. Nunca afirmes que algo se ha hecho o se hará."""

# Anything that looks like money. The assistant is told not to price; this is
# what checks whether it listened.
_MONEY_PATTERNS = [
    re.compile(r"[$€£]\s?\d", re.IGNORECASE),
    re.compile(r"\b\d[\d.,]*\s?(usd|eur|dólares|dolares|euros|pesos)\b", re.IGNORECASE),
    re.compile(r"\b(precio|costo|coste|tarifa|importe|valor)\s+(de\s+)?[$€£]?\s?\d", re.IGNORECASE),
]

_DIAGNOSIS_PATTERNS = [
    re.compile(r"\b(diagnostico|diagnóstico)\s+(es|sería|seria|probable|presuntivo)\b", re.IGNORECASE),
    re.compile(r"\b(padece|presenta un cuadro de|se trata de un caso de)\b", re.IGNORECASE),
    re.compile(r"\brecomiendo\s+(realizar|un|una|el|la)\b", re.IGNORECASE),
]


class GuardrailViolation(RuntimeError):
    """The assistant produced something it was told not to. The draft is
    discarded rather than shown: a caught violation that still reaches the
    screen was never really caught."""

    def __init__(self, kind: str, excerpt: str):
        self.kind = kind
        self.excerpt = excerpt
        super().__init__(f"El borrador fue descartado por contener {kind}: «{excerpt}»")


def check_output(text: str) -> None:
    """Scans a draft for the two things the assistant must never produce.

    This runs on every completion. It is deliberately blunt: a false positive
    costs one regenerated draft, a false negative puts an invented price or a
    machine-made diagnosis in front of a patient."""
    for pattern in _MONEY_PATTERNS:
        match = pattern.search(text)
        if match:
            raise GuardrailViolation("importes o precios", match.group(0))
    for pattern in _DIAGNOSIS_PATTERNS:
        match = pattern.search(text)
        if match:
            raise GuardrailViolation("un diagnóstico o una recomendación clínica", match.group(0))
