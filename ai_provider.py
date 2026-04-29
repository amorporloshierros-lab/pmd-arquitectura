"""
ai_provider.py
--------------
Orquesta la llamada al LLM con failover automático:

    Intento 1: Claude (Anthropic)
        ↓ si falla por rate-limit, cuota agotada o error recuperable
    Intento 2: Gemini (Google)
        ↓ si también falla
    → devuelve mensaje de error elegante y registra el incidente

Expone una única función: generate_response(history) -> str
donde `history` es una lista de dicts {"role": "user"|"assistant", "content": str}.
"""

from __future__ import annotations

import logging
from typing import Literal

import anthropic
import google.generativeai as genai

import config
from system_prompt import get_system_prompt

logger = logging.getLogger("lucas.provider")

# ---- Clientes perezosos (se inicializan al primer uso) ----
_anthropic_client: anthropic.Anthropic | None = None
_gemini_ready: bool = False


def _get_anthropic_client() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _anthropic_client


def _ensure_gemini() -> None:
    global _gemini_ready
    if not _gemini_ready:
        genai.configure(api_key=config.GEMINI_API_KEY)
        _gemini_ready = True


# ---- Errores recuperables (disparan failover) ----
RECOVERABLE_ANTHROPIC = (
    anthropic.RateLimitError,
    anthropic.APITimeoutError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
    anthropic.APIStatusError,  # 529 overloaded, etc.
)


def _call_claude(history: list[dict], context: str = "landing") -> str:
    """Llama a Claude. Lanza la excepción original si falla."""
    client = _get_anthropic_client()

    # Filtrar mensajes válidos (Claude no acepta contenido vacío)
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in history
        if m.get("content", "").strip()
    ]

    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=get_system_prompt(context),
        messages=messages,
    )
    # Concatenar bloques de texto
    text_parts = [block.text for block in response.content if hasattr(block, "text")]
    return "".join(text_parts).strip()


def _call_gemini(history: list[dict], context: str = "landing") -> str:
    """Llama a Gemini. Lanza la excepción original si falla."""
    _ensure_gemini()

    model = genai.GenerativeModel(
        model_name=config.GEMINI_MODEL,
        system_instruction=get_system_prompt(context),
    )

    # Gemini usa roles "user" y "model" (no "assistant")
    gemini_history = []
    for msg in history[:-1]:  # todos menos el último
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    chat = model.start_chat(history=gemini_history)
    last_user_msg = history[-1]["content"] if history else "Hola"
    response = chat.send_message(last_user_msg)

    return (response.text or "").strip()


def generate_response(
    history: list[dict],
    context: str = "landing",
) -> tuple[str, Literal["claude", "gemini", "error"]]:
    """
    Genera la respuesta de Lucas usando Claude primero y Gemini como fallback.

    Args:
        history: lista de mensajes en formato [{"role": "user"|"assistant", "content": str}]
        context: "landing" | "presupuestador" | "mi-hogar" — overlay del system prompt

    Returns:
        tupla (respuesta, proveedor_usado)
        Si ambos fallan, proveedor_usado == "error" y la respuesta es un
        mensaje genérico para el cliente.
    """
    # ---- Intento 1: Claude ----
    try:
        text = _call_claude(history, context)
        if text:
            logger.info("Respuesta generada con Claude (%d chars, context=%s)", len(text), context)
            return text, "claude"
        raise RuntimeError("Claude devolvió respuesta vacía")

    except RECOVERABLE_ANTHROPIC as exc:
        logger.warning("Claude falló con error recuperable: %s — probando Gemini", exc)

    except Exception as exc:  # pylint: disable=broad-except
        # Errores como AuthenticationError (401), BadRequestError, etc.
        # Aun así intentamos Gemini — mejor dar una respuesta que cortar al cliente.
        logger.error("Claude falló con error no recuperable: %s — probando Gemini", exc)

    # ---- Intento 2: Gemini ----
    try:
        text = _call_gemini(history, context)
        if text:
            logger.info("Respuesta generada con Gemini — FAILOVER (%d chars, context=%s)", len(text), context)
            return text, "gemini"
        raise RuntimeError("Gemini devolvió respuesta vacía")

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Gemini también falló: %s", exc)

    # ---- Ambos fallaron ----
    fallback = (
        "Disculpe, tuve un inconveniente momentáneo del sistema. "
        "¿Podría reformular su consulta en un instante? Sigo a su disposición. 🙏"
    )
    return fallback, "error"
