"""
notifications.py
----------------
Sistema de alertas para PMD:
  - Aviso inmediato cuando alguien reserva una reunión.
  - Aviso automático 15 minutos antes de cada reunión.

Canales soportados (uno, otro o ambos):
  1. Telegram Bot  — vía TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID.
  2. Webhook genérico — vía NOTIFY_WEBHOOK_URL (n8n, Zapier, Make, etc.).

Configuración en .env (todo opcional):
    TELEGRAM_BOT_TOKEN=123456:ABC...
    TELEGRAM_CHAT_ID=5551112233
    NOTIFY_WEBHOOK_URL=https://n8n.ejemplo.com/webhook/pmd

Cómo crear el bot de Telegram (1 minuto, gratis):
  1. Abrir Telegram y hablar con @BotFather
  2. /newbot → ponele un nombre y un username (ej: pmd_alerts_bot)
  3. Te da un TOKEN → pegalo en TELEGRAM_BOT_TOKEN
  4. Mandarle "/start" al bot desde el celular donde querés recibir los avisos
  5. Para obtener tu chat_id:
     curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
     buscar "chat":{"id":NÚMERO} — ese NÚMERO es TELEGRAM_CHAT_ID
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

import config

logger = logging.getLogger("lucas.notifications")

# NOTA: las variables de entorno se leen EN CADA LLAMADA, no al importar el
# módulo. Así no importa si notifications.py se importa antes que config.py
# cargue el .env — siempre vemos el valor vigente al momento de enviar.
def _token() -> str: return os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
def _chat()  -> str: return os.getenv("TELEGRAM_CHAT_ID", "").strip()
def _webhook() -> str: return os.getenv("NOTIFY_WEBHOOK_URL", "").strip()

AR_TZ = timezone(timedelta(hours=-3))

# Archivo que registra qué reservas ya tuvieron aviso "15 min antes" enviado,
# para no duplicar si el servidor se reinicia.
_SENT_ALERTS_FILE = config.LOGS_DIR / "alerts_sent.txt"


def _mark_sent(key: str) -> None:
    try:
        with _SENT_ALERTS_FILE.open("a", encoding="utf-8") as f:
            f.write(key + "\n")
    except Exception:  # pylint: disable=broad-except
        pass


def _already_sent(key: str) -> bool:
    try:
        if not _SENT_ALERTS_FILE.exists():
            return False
        return key in _SENT_ALERTS_FILE.read_text(encoding="utf-8").splitlines()
    except Exception:  # pylint: disable=broad-except
        return False


async def send_telegram(text: str) -> bool:
    """Manda un mensaje al bot de Telegram configurado. Usa HTML para formato."""
    token = _token()
    chat  = _chat()
    if not token or not chat:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json={
                "chat_id": chat,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            })
            if r.status_code != 200:
                logger.warning("Telegram respondió %s: %s", r.status_code, r.text[:200])
                return False
            return True
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("No se pudo enviar a Telegram: %s", exc)
        return False


async def send_webhook(payload: dict[str, Any]) -> bool:
    """Manda el evento a un webhook genérico (n8n/Zapier/Make)."""
    url = _webhook()
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
            return 200 <= r.status_code < 300
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("No se pudo enviar al webhook: %s", exc)
        return False


def _format_booking_for_telegram(booking: dict[str, Any], prefix: str) -> str:
    """Arma el texto HTML con los datos de la reserva."""
    slot_key = booking.get("slot_key", "")
    date, hhmm = ("—", "--:--")
    if "_" in slot_key:
        date, raw = slot_key.split("_")
        hhmm = raw[:2] + ":" + raw[2:] if len(raw) == 4 else raw
    name  = booking.get("nombre", "—")
    wsp   = booking.get("whatsapp", "—")
    email = booking.get("email", "—")
    canal = booking.get("canal", "videollamada")
    notas = booking.get("notas", "")

    return (
        f"<b>{prefix}</b>\n"
        f"🗓️ <b>{date}</b> · {hhmm}\n"
        f"👤 {name}\n"
        f"📱 <code>{wsp}</code>\n"
        f"✉️ {email}\n"
        f"🎥 Canal: {canal}"
        + (f"\n📝 {notas}" if notas else "")
    )


async def notify_new_booking(booking: dict[str, Any]) -> None:
    """Llamar cuando se crea una reserva nueva en /api/book."""
    logger.info("Disparando notificación de nueva reserva: %s", booking.get("slot_key"))
    text = _format_booking_for_telegram(booking, "📅 NUEVA REUNIÓN AGENDADA")
    await asyncio.gather(
        send_telegram(text),
        send_webhook({"event": "new_booking", "booking": booking}),
    )


async def notify_upcoming(booking: dict[str, Any]) -> None:
    """Llamar cuando faltan 15 minutos para la reunión."""
    slot_key = booking.get("slot_key", "")
    if _already_sent(slot_key):
        return
    _mark_sent(slot_key)

    logger.info("Disparando recordatorio 15 min antes: %s", slot_key)
    text = _format_booking_for_telegram(booking, "⏰ REUNIÓN EN 15 MINUTOS")
    await asyncio.gather(
        send_telegram(text),
        send_webhook({"event": "upcoming_15min", "booking": booking}),
    )


async def reminder_loop() -> None:
    """Corre en background cada 60s. Chequea si hay reuniones en los próximos
    15 minutos y dispara el aviso. Se arranca desde main.py al boot."""
    from agenda import upcoming_bookings  # import local para evitar ciclos

    logger.info("Reminder loop iniciado (chequea cada 60s)")
    while True:
        try:
            bookings = await asyncio.to_thread(upcoming_bookings)
            now = datetime.now(AR_TZ)
            window_end = now + timedelta(minutes=15)

            for b in bookings:
                slot_key = b.get("slot_key", "")
                if "_" not in slot_key:
                    continue
                try:
                    date_str, hhmm = slot_key.split("_")
                    dt = datetime.strptime(
                        f"{date_str} {hhmm[:2]}:{hhmm[2:]}",
                        "%Y-%m-%d %H:%M"
                    ).replace(tzinfo=AR_TZ)
                except Exception:  # pylint: disable=broad-except
                    continue

                # Reunión en los próximos 15 min Y todavía no pasó
                if now <= dt <= window_end:
                    await notify_upcoming(b)

        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Error en reminder_loop: %s", exc)

        await asyncio.sleep(60)  # chequea cada minuto


def is_configured() -> dict[str, bool]:
    """Útil para /api/health — muestra qué canales están activos."""
    return {
        "telegram": bool(_token() and _chat()),
        "webhook": bool(_webhook()),
    }
