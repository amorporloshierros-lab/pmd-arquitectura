"""
agenda.py
---------
Sistema mínimo de agenda de reuniones para PMD.

- `next_available_slots(n=3)` devuelve los próximos N horarios disponibles
  contemplando fines de semana y slots ya reservados.
- `book_slot(payload)` registra una reserva (se persiste a logs/leads/ y al
  Excel acumulativo).

Horarios base: lunes a viernes 10:00, 11:30, 15:00, 16:30 (hora Argentina).
En esta primera versión no hay conflictos con Google Calendar — se asume
que el equipo confirma manualmente cada reserva que entra por el log.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import config
from excel_leads import append_lead

logger = logging.getLogger("lucas.agenda")

AR_TZ = timezone(timedelta(hours=-3))

# Horarios base que ofrecemos. Cambiá esta lista si PMD amplia horarios.
BASE_SLOTS_HHMM: list[tuple[int, int]] = [
    (10, 0),
    (11, 30),
    (15, 0),
    (16, 30),
]

BOOKINGS_DIR: Path = config.LOGS_DIR / "bookings"
BOOKINGS_DIR.mkdir(exist_ok=True)


def _is_business_day(dt: datetime) -> bool:
    """True si es lunes-viernes."""
    return dt.weekday() < 5  # 0=lun, 4=vie


def _load_taken_keys() -> set[str]:
    """Retorna el set de strings 'YYYY-MM-DD_HHMM' ya reservados."""
    taken = set()
    if not BOOKINGS_DIR.exists():
        return taken
    for path in BOOKINGS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            key = data.get("slot_key")
            if key:
                taken.add(key)
        except Exception:  # pylint: disable=broad-except
            continue
    return taken


def next_available_slots(n: int = 3) -> list[dict[str, Any]]:
    """Devuelve los próximos N horarios disponibles a partir de ahora + 1h.
    Se saltan fines de semana y slots ya reservados. Formato de cada slot:

    {
        "key":    "2026-04-23_1130",
        "iso":    "2026-04-23T11:30:00-03:00",
        "day":    "miércoles",
        "date":   "23 de abril",
        "time":   "11:30",
        "label":  "Miércoles 23 de abril · 11:30"
    }
    """
    taken = _load_taken_keys()
    now = datetime.now(AR_TZ) + timedelta(hours=1)  # ventana mínima 1h
    slots: list[dict[str, Any]] = []

    days_names = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    months_names = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]

    # Iteramos hasta 14 días buscando slots disponibles
    for delta_days in range(0, 14):
        day = now + timedelta(days=delta_days)
        if not _is_business_day(day):
            continue

        for hh, mm in BASE_SLOTS_HHMM:
            slot_dt = day.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if slot_dt <= now:
                continue

            key = f"{slot_dt.strftime('%Y-%m-%d')}_{hh:02d}{mm:02d}"
            if key in taken:
                continue

            day_name = days_names[slot_dt.weekday()]
            month = months_names[slot_dt.month - 1]
            time_str = slot_dt.strftime("%H:%M")

            slots.append({
                "key": key,
                "iso": slot_dt.isoformat(),
                "day": day_name,
                "date": f"{slot_dt.day} de {month}",
                "time": time_str,
                "label": f"{day_name.capitalize()} {slot_dt.day} de {month} · {time_str}",
            })

            if len(slots) >= n:
                return slots

    return slots


def book_slot(payload: dict[str, Any]) -> dict[str, Any]:
    """Registra una reserva. payload debe contener slot_key + datos de contacto.

    Returns:
        {"ok": True, "booking_id": "...", "slot_key": "..."}
    """
    slot_key = payload.get("slot_key")
    if not slot_key:
        return {"ok": False, "error": "slot_key es requerido"}

    taken = _load_taken_keys()
    if slot_key in taken:
        return {"ok": False, "error": "Ese horario ya fue tomado por otro cliente"}

    booking_id = datetime.now(AR_TZ).strftime("%Y%m%d-%H%M%S")
    record = {
        "booking_id": booking_id,
        "slot_key": slot_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "nombre": payload.get("nombre", ""),
        "email": payload.get("email", ""),
        "whatsapp": payload.get("whatsapp", ""),
        "canal": payload.get("canal", "videollamada"),
        "notas": payload.get("notas", ""),
        "session_id": payload.get("session_id", ""),
    }

    # Persistir JSON por booking
    try:
        path = BOOKINGS_DIR / f"{booking_id}_{slot_key}.json"
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("No se pudo guardar booking JSON: %s", exc)

    # También al Excel acumulativo como lead con origen=agenda
    excel_payload = {
        "origen": "agenda",
        "nombre": record["nombre"],
        "email": record["email"],
        "whatsapp": record["whatsapp"],
        "mensaje": f"Reserva {slot_key} canal={record['canal']} notas={record['notas']}",
    }
    try:
        append_lead(excel_payload)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("No se pudo meter booking al Excel: %s", exc)

    logger.info(
        "Reserva agendada: id=%s slot=%s nombre=%s email=%s wsp=%s canal=%s",
        booking_id, slot_key, record["nombre"], record["email"],
        record["whatsapp"], record["canal"],
    )
    return {"ok": True, "booking_id": booking_id, "slot_key": slot_key}


def upcoming_bookings() -> list[dict[str, Any]]:
    """Lista todas las reservas futuras (para dashboard del equipo)."""
    if not BOOKINGS_DIR.exists():
        return []
    now = datetime.now(AR_TZ)
    out = []
    for path in sorted(BOOKINGS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            slot_key = data.get("slot_key", "")
            # slot_key formato YYYY-MM-DD_HHMM
            if "_" in slot_key:
                date_str, hhmm = slot_key.split("_")
                dt = datetime.strptime(f"{date_str} {hhmm[:2]}:{hhmm[2:]}", "%Y-%m-%d %H:%M")
                dt = dt.replace(tzinfo=AR_TZ)
                if dt >= now:
                    out.append(data)
        except Exception:  # pylint: disable=broad-except
            continue
    return out
