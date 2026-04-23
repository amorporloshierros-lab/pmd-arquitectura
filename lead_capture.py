"""
lead_capture.py
---------------
Detecta cuando el cliente deja su contacto durante la conversación con Lucas,
extrae los datos calificados (tipo de obra, m², nivel, WhatsApp/email) y los
dispara hacia todos los canales configurados:

    1. Email SMTP (Gmail)
    2. Google Sheets (fila nueva)
    3. Webhook (Zapier/Make/n8n)

Cada canal se ejecuta aislado — si uno falla, los demás siguen.
"""

from __future__ import annotations

import json
import logging
import re
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import httpx

import config

logger = logging.getLogger("lucas.leads")

# ---- Expresiones para detectar contacto en el texto libre ----
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# WhatsApp Argentina: admite +54, 54, 011, 15, o 10-13 dígitos consecutivos
PHONE_RE = re.compile(r"(?:\+?54\s?)?(?:9\s?)?(?:11|15)?[\s\-.]?\d[\d\s\-.]{7,15}\d")

# ---- Niveles (para inferir precio en el lead) ----
PRICE_BY_LEVEL = {
    "eco confort": 410,
    "eco": 410,
    "estandar": 600,
    "estándar": 600,
    "premium": 800,
    "elite lujo": 1100,
    "élite lujo": 1100,
    "elite": 1100,
    "lujo": 1100,
}


def extract_contact(text: str) -> dict[str, str | None]:
    """Extrae email y/o teléfono de un mensaje."""
    email_match = EMAIL_RE.search(text)
    phone_match = PHONE_RE.search(text)

    email = email_match.group(0) if email_match else None

    phone = None
    if phone_match:
        raw = phone_match.group(0)
        # Normalizar: solo dígitos y +
        digits = re.sub(r"[^\d+]", "", raw)
        # Filtrar falsos positivos (dni, m2, precio)
        if len(re.sub(r"[^\d]", "", digits)) >= 9:
            phone = digits

    return {"email": email, "phone": phone}


def detect_level_and_m2(conversation_text: str) -> dict[str, Any]:
    """Analiza el texto completo de la conversación para inferir m² y nivel."""
    lower = conversation_text.lower()

    # Nivel
    level = None
    price_per_m2 = None
    for key, price in PRICE_BY_LEVEL.items():
        if key in lower:
            level = key.title()
            price_per_m2 = price
            break

    # m² — buscar "120 m2", "120m²", "120 metros", "120 m"
    m2 = None
    m2_match = re.search(r"(\d{2,4})\s*(?:m2|m²|metros cuadrados|mts|metros)", lower)
    if m2_match:
        try:
            m2 = int(m2_match.group(1))
        except ValueError:
            pass

    # Tipo de obra
    obra_tipo = None
    if any(w in lower for w in ["desde cero", "construir", "construccion", "construcción"]):
        obra_tipo = "Construcción desde cero"
    elif any(w in lower for w in ["reforma", "remodel", "refaccion", "refacción"]):
        obra_tipo = "Reforma"
    elif "ampliac" in lower:
        obra_tipo = "Ampliación"

    total_usd = (m2 * price_per_m2) if (m2 and price_per_m2) else None

    return {
        "m2": m2,
        "level": level,
        "price_per_m2": price_per_m2,
        "total_usd_estimado": total_usd,
        "obra_tipo": obra_tipo,
    }


def build_lead_payload(
    session_id: str,
    contact: dict[str, str | None],
    conversation_text: str,
    full_history: list[dict],
) -> dict[str, Any]:
    """Arma el objeto lead con todos los datos calificados."""
    qualified = detect_level_and_m2(conversation_text)

    return {
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "email": contact.get("email"),
        "whatsapp": contact.get("phone"),
        "tipo_obra": qualified.get("obra_tipo"),
        "m2": qualified.get("m2"),
        "nivel": qualified.get("level"),
        "precio_m2_usd": qualified.get("price_per_m2"),
        "total_usd_estimado": qualified.get("total_usd_estimado"),
        "mensajes_totales": len(full_history),
        "conversacion": full_history,
    }


# ---------- Canal 1: Email ----------

def send_lead_email(lead: dict[str, Any]) -> bool:
    """Envía el lead por email SMTP. Devuelve True si tuvo éxito."""
    if not config.lead_channels_enabled()["email"]:
        logger.info("Email no configurado — se omite")
        return False

    try:
        subject = f"[PMD · Lucas] Nuevo lead — {lead.get('tipo_obra') or 'consulta'}"
        body_lines = [
            "Nuevo lead capturado por Lucas (chatbot web).",
            "",
            f"📅 Fecha: {lead['timestamp']}",
            f"🆔 Session: {lead['session_id']}",
            "",
            "─── DATOS DEL CLIENTE ───",
            f"📱 WhatsApp: {lead.get('whatsapp') or '(no dejó)'}",
            f"✉️  Email:    {lead.get('email') or '(no dejó)'}",
            "",
            "─── CALIFICACIÓN ───",
            f"🏗️  Tipo de obra: {lead.get('tipo_obra') or '(sin definir)'}",
            f"📐 Metros²:      {lead.get('m2') or '(sin definir)'}",
            f"✨ Nivel:         {lead.get('nivel') or '(sin definir)'}",
            f"💵 USD/m²:        {lead.get('precio_m2_usd') or '—'}",
            f"💰 Total USD est: {lead.get('total_usd_estimado') or '—'}",
            "",
            "─── CONVERSACIÓN COMPLETA ───",
        ]
        for msg in lead.get("conversacion", []):
            role = "Cliente" if msg.get("role") == "user" else "Lucas"
            body_lines.append(f"[{role}]: {msg.get('content', '')}")
            body_lines.append("")

        body = "\n".join(body_lines)

        mime = MIMEMultipart("alternative")
        mime["Subject"] = subject
        mime["From"] = config.SMTP_USER
        mime["To"] = config.LEAD_RECIPIENT
        mime.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
            smtp.send_message(mime)

        logger.info("Lead enviado por email a %s", config.LEAD_RECIPIENT)
        return True

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Falló el envío de email: %s", exc)
        return False


# ---------- Canal 2: Google Sheets ----------

def append_lead_to_sheets(lead: dict[str, Any]) -> bool:
    """Agrega una fila con el lead en la planilla configurada."""
    if not config.lead_channels_enabled()["sheets"]:
        logger.info("Google Sheets no configurado — se omite")
        return False

    try:
        import gspread  # import tardío para no penalizar arranque si no se usa
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        sa_path = config.ROOT_DIR / config.GOOGLE_SA_PATH
        creds = Credentials.from_service_account_file(str(sa_path), scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(config.GOOGLE_SHEETS_ID)

        # Buscar o crear la hoja
        try:
            ws = sh.worksheet(config.GOOGLE_SHEETS_TAB)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=config.GOOGLE_SHEETS_TAB, rows=1000, cols=12)
            ws.append_row([
                "Timestamp", "Session ID", "WhatsApp", "Email",
                "Tipo obra", "m²", "Nivel", "USD/m²", "Total USD est",
                "Mensajes", "Origen"
            ])

        ws.append_row([
            lead["timestamp"],
            lead["session_id"],
            lead.get("whatsapp") or "",
            lead.get("email") or "",
            lead.get("tipo_obra") or "",
            lead.get("m2") or "",
            lead.get("nivel") or "",
            lead.get("precio_m2_usd") or "",
            lead.get("total_usd_estimado") or "",
            lead.get("mensajes_totales") or 0,
            "Chatbot web Lucas",
        ])

        logger.info("Lead agregado a Google Sheets")
        return True

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Falló la escritura en Google Sheets: %s", exc)
        return False


# ---------- Canal 3: Webhook ----------

def post_lead_to_webhook(lead: dict[str, Any]) -> bool:
    """Envía el lead al webhook configurado (Zapier/Make/n8n)."""
    if not config.lead_channels_enabled()["webhook"]:
        logger.info("Webhook no configurado — se omite")
        return False

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(config.LEAD_WEBHOOK_URL, json=lead)
            resp.raise_for_status()
        logger.info("Lead enviado al webhook (%s)", resp.status_code)
        return True

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Falló el envío al webhook: %s", exc)
        return False


# ---------- Orquestador ----------

def dispatch_lead(
    session_id: str,
    contact: dict[str, str | None],
    conversation_text: str,
    full_history: list[dict],
) -> dict[str, bool]:
    """
    Dispara el lead a TODOS los canales configurados.
    Si un canal falla, los demás siguen.

    Returns:
        dict con el estado de cada canal: {"email": bool, "sheets": bool, "webhook": bool}
    """
    lead = build_lead_payload(session_id, contact, conversation_text, full_history)

    # Guardar una copia local siempre, aunque fallen todos los canales
    _save_local_backup(lead)

    return {
        "email": send_lead_email(lead),
        "sheets": append_lead_to_sheets(lead),
        "webhook": post_lead_to_webhook(lead),
    }


def _save_local_backup(lead: dict[str, Any]) -> None:
    """Guarda el lead como JSON local en logs/leads/ para que nunca se pierda."""
    try:
        leads_dir = config.LOGS_DIR / "leads"
        leads_dir.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"{ts}_{lead['session_id']}.json"
        (leads_dir / filename).write_text(
            json.dumps(lead, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Lead guardado como backup local: %s", filename)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("No se pudo guardar backup local: %s", exc)
