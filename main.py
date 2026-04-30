"""
main.py
-------
Servidor FastAPI del MVP de Lucas.

Endpoints:
    GET  /                     → sirve static/index.html (demo)
    POST /api/session/new      → crea sesión y devuelve saludo inicial
    POST /api/chat             → recibe mensaje del cliente, devuelve respuesta de Lucas
    GET  /api/health           → health-check
    GET  /api/leads            → lista leads capturados (solo backup local)

Correr:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import config
from ai_provider import generate_response
from lead_capture import dispatch_lead, extract_contact
from excel_leads import append_lead, count_leads, excel_path_str
from agenda import next_available_slots, book_slot, upcoming_bookings
from precios import get_precios, invalidate_cache as invalidate_precios_cache, get_source as precios_source
import auth
import data_store
import email_service
from precios_override import get_lineas, save_lineas, get_precios_con_override
from notifications import notify_new_booking, reminder_loop, is_configured as notif_configured
from system_prompt import LUCAS_SYSTEM_PROMPT  # noqa: F401 (referenciado en logs)

# ---- Logging ----
logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(config.LOGS_DIR / "lucas.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("lucas.main")

app = FastAPI(title="Lucas — PMD Sales Agent", version="1.0.0")

# CORS abierto para que el widget funcione desde cualquier dominio donde lo embebas
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir estáticos (widget HTML)
if config.STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")
    # Mount específico para los assets de Mi Hogar (Vite buildea con base=/mi-hogar/
    # y referencia /mi-hogar/assets/index.js, etc — esto los sirve directo).
    mh_dir = config.STATIC_DIR / "mi-hogar"
    if mh_dir.exists():
        app.mount("/mi-hogar/assets", StaticFiles(directory=str(mh_dir / "assets")), name="mihogar-assets")


# ---- Almacenamiento de sesiones EN MEMORIA (para MVP) ----
# En producción esto iría a Redis o una DB. Para el MVP alcanza con un dict.
SESSIONS: dict[str, dict] = {}


# ---- Migración one-shot al startup ----
# Asegura que ciertos users del seed tengan el rol correcto, incluso si ya
# existían en data_store con un rol viejo (porque el seed solo corre la 1ra vez).
def _ensure_user_role(email: str, expected_role: str) -> None:
    try:
        u = data_store.get_user_by_email(email)
        if u and u.get("role") != expected_role:
            data_store.update_user(u["id"], role=expected_role)
            logger.info("Migración: %s actualizado a role=%s", email, expected_role)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("No se pudo migrar role de %s: %s", email, exc)


@app.on_event("startup")
async def _bootstrap_migrations():
    # Lucas y Augusto son ambos admin (full power). Marcos es architect.
    _ensure_user_role("augusto@pmdarquitectura.com", "admin")
    _ensure_user_role("lucas@pmdarquitectura.com", "admin")
    _ensure_user_role("marcos@pmdarquitectura.com", "architect")
    logger.info("Bootstrap migrations completadas")


# ---- Saludo inicial dinámico (hora del día) ----
# El saludo se calcula cuando se crea la sesión. Así Lucas dice "buen día",
# "buenas tardes" o "buenas noches" según corresponda en hora de Argentina.
# Además es corto y abierto — no pregunta cosas que el cliente quizás
# ya respondió en el presupuestador. Si el cliente llega con contexto
# (ej: "armé un presupuesto"), el bot lee ese mensaje y responde en
# consecuencia sin saludar dos veces.

def _saludo_hora_argentina() -> str:
    """Devuelve 'Buen día', 'Buenas tardes' o 'Buenas noches' según
    la hora local de Argentina (UTC-3)."""
    from datetime import datetime, timedelta, timezone as _tz
    ar = datetime.now(_tz(timedelta(hours=-3)))
    h = ar.hour
    if 5 <= h < 13:  return "Buen día"
    if 13 <= h < 20: return "Buenas tardes"
    return "Buenas noches"


def get_initial_greeting(context: str = "landing") -> str:
    """Saludo inicial que se muestra al abrir el chat, ajustado al contexto.

    - landing: presentación clásica + ¿en qué puedo ayudarle?
    - presupuestador: reconoce que ya armó cálculo, NO pregunta tipo de obra.
    - mi-hogar: tono de bienvenida a cliente existente, modo soporte.
    """
    saludo = _saludo_hora_argentina()

    if context == "presupuestador":
        return (
            f"{saludo}. Soy **Lucas**, del equipo de PMD. Vi que armaste "
            "tu cálculo en el presupuestador — buenísimo. Contame los "
            "detalles que tengas en mente y lo afinamos juntos."
        )

    if context == "mi-hogar":
        return (
            f"{saludo}. Soy **Lucas**, del equipo de PMD. Veo que ya sos "
            "cliente — bienvenido. ¿En qué te puedo dar una mano hoy?"
        )

    # landing (default)
    return (
        f"{saludo}. Soy **Lucas**, del equipo de PMD Servicios "
        "Arquitectónicos e Integrales. ¿En qué puedo ayudarle hoy?"
    )


# Mantenemos la constante por compatibilidad con imports existentes,
# pero el valor se recalcula cada vez que se crea una sesión (ver new_session).
INITIAL_GREETING = get_initial_greeting()


# ==== MODELOS ====

class ChatMessage(BaseModel):
    session_id: str = Field(..., description="ID de sesión devuelto por /session/new")
    message: str = Field(..., min_length=1, max_length=4000)


# Contextos válidos. Cualquier valor desconocido cae a "landing" en backend.
_VALID_CONTEXTS = {"landing", "presupuestador", "mi-hogar"}


class SessionRequest(BaseModel):
    context: str = Field(
        default="landing",
        description="De dónde viene el usuario: landing | presupuestador | mi-hogar",
    )

    def normalized_context(self) -> str:
        return self.context if self.context in _VALID_CONTEXTS else "landing"


class SessionResponse(BaseModel):
    session_id: str
    greeting: str
    context: str = "landing"


class ChatResponse(BaseModel):
    # `reply` queda por compatibilidad con clientes viejos (es el primer mensaje).
    reply: str
    # `replies` es la lista completa de mensajes a renderizar como burbujas
    # separadas. Lucas puede usar el delimitador [[SPLIT]] en su respuesta para
    # que el frontend la muestre como múltiples mensajes consecutivos.
    replies: list[str]
    provider: str
    lead_captured: bool = False
    lead_channels: dict | None = None


SPLIT_TOKEN = "[[SPLIT]]"


def split_reply(text: str) -> list[str]:
    """Divide la respuesta del LLM en una lista de mensajes usando [[SPLIT]].

    Tolera variaciones (espacios alrededor, salto de línea pegado).
    Filtra strings vacías. Como mucho devuelve 3 partes (límite de seguridad).
    """
    if not text:
        return [""]
    parts = [p.strip() for p in text.split(SPLIT_TOKEN)]
    parts = [p for p in parts if p][:3]
    return parts or [text.strip()]


# ==== HELPERS ====

def _get_session(session_id: str) -> dict:
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")
    return SESSIONS[session_id]


async def _simulate_typing_delay() -> None:
    """Espera un tiempo aleatorio para simular que Lucas está escribiendo."""
    delay = random.uniform(config.TYPING_DELAY_MIN, config.TYPING_DELAY_MAX)
    await asyncio.sleep(delay)


def _full_conversation_text(history: list[dict]) -> str:
    return "\n".join(f"{m['role']}: {m['content']}" for m in history)


# ==== ENDPOINTS ====

@app.get("/", include_in_schema=False)
async def root():
    """Sirve la landing principal con cache-busting agresivo — importante
    durante desarrollo porque editamos el HTML seguido."""
    index = config.STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(
            index,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return JSONResponse({"status": "ok", "message": "static/index.html no encontrado"})


@app.get("/mi-hogar", include_in_schema=False)
@app.get("/mi-hogar/", include_in_schema=False)
async def mi_hogar_index():
    """Sirve el dashboard React Mi Hogar (index.html del bundle de Vite).
    Los assets (JS, CSS) los sirve el mount /static/mi-hogar/ automáticamente
    porque Vite buildeó con base='/mi-hogar/' y el HTML referencia /mi-hogar/assets/*.
    Pero Vite escribe rutas absolutas /mi-hogar/assets/*, así que necesitamos
    también un mount específico en /mi-hogar/assets/. Lo agrego abajo del mount /static.
    """
    page = config.STATIC_DIR / "mi-hogar" / "index.html"
    if page.exists():
        return FileResponse(
            page,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
            },
        )
    return JSONResponse({"status": "error", "message": "mi-hogar build no encontrado"}, status_code=404)


@app.get("/admin", include_in_schema=False)
async def admin_panel():
    """Sirve el dashboard admin para ver leads y reuniones."""
    panel = config.STATIC_DIR / "admin.html"
    if panel.exists():
        return FileResponse(
            panel,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
            },
        )
    return JSONResponse({"error": "admin.html no encontrado"}, status_code=404)


@app.get("/admin/users", include_in_schema=False)
@app.get("/admin/users/", include_in_schema=False)
async def admin_users_panel():
    """Sirve la página de gestión de usuarios (clientes + equipo).
    Requiere login con rol admin (validado en frontend + backend en cada API call)."""
    panel = config.STATIC_DIR / "admin-users.html"
    if panel.exists():
        return FileResponse(
            panel,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
            },
        )
    return JSONResponse({"error": "admin-users.html no encontrado"}, status_code=404)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lead_channels": config.lead_channels_enabled(),
        "sessions_active": len(SESSIONS),
        "leads_excel": {
            "path": excel_path_str(),
            "count": count_leads(),
        },
    }


# ==== NUEVOS ENDPOINTS DE LEADS (presupuestador + form contacto) ====
#
# Estos endpoints escriben al Excel acumulativo (leads_pmd.xlsx).
# El bot de chat sigue usando dispatch_lead (email + sheets + webhook)
# Y además también va al Excel a través de la función append_lead
# (se enchufa en el flujo de chat en /api/chat).

@app.post("/api/lead/presupuesto")
async def lead_presupuesto(payload: dict):
    """Recibe el lead generado al completar el wizard del presupuestador."""
    payload.setdefault("origen", "presupuestador")
    ok = await asyncio.to_thread(append_lead, payload)
    logger.info(
        "Lead presupuestador: nombre=%s email=%s wsp=%s total=%s-%s USD",
        payload.get("nombre"), payload.get("email"), payload.get("whatsapp"),
        payload.get("total_min_usd"), payload.get("total_max_usd"),
    )
    return {"ok": ok, "total_leads": count_leads()}


@app.post("/api/lead/contacto")
async def lead_contacto(payload: dict):
    """Recibe el lead del formulario de contacto de la landing.

    El payload trae 'motivo_consulta' que puede ser:
      - Casa nueva / Reforma / Edificio  → origen=contacto-construccion
      - Inversión — ...                  → origen=contacto-inversion
      - Automatización — ...             → origen=contacto-automatizacion
    Así el dashboard los clasifica correctamente.
    """
    motivo = (payload.get("motivo_consulta") or "").lower()

    if "inversi" in motivo:
        payload.setdefault("origen", "contacto-inversion")
    elif "automat" in motivo:
        payload.setdefault("origen", "contacto-automatizacion")
    elif any(w in motivo for w in ("casa", "reforma", "edificio", "ampliaci")):
        payload.setdefault("origen", "contacto-construccion")
    else:
        payload.setdefault("origen", "contacto")

    # Mapeamos motivo_consulta a tipo_proyecto para que el dashboard lo muestre
    if not payload.get("tipo_proyecto") and payload.get("motivo_consulta"):
        payload["tipo_proyecto"] = payload["motivo_consulta"]

    ok = await asyncio.to_thread(append_lead, payload)
    logger.info(
        "Lead contacto: nombre=%s email=%s motivo=%s origen=%s",
        payload.get("nombre"), payload.get("email"),
        payload.get("motivo_consulta"), payload.get("origen"),
    )
    return {"ok": ok, "total_leads": count_leads()}


# ==== AGENDA DE REUNIONES ====
@app.get("/api/slots")
async def api_slots(n: int = 3):
    """Devuelve los próximos N slots disponibles (default 3).
    El bot Lucas usa esto cuando el cliente quiere agendar."""
    slots = await asyncio.to_thread(next_available_slots, n)
    return {"slots": slots, "timezone": "America/Argentina/Buenos_Aires"}


@app.post("/api/book")
async def api_book(payload: dict):
    """Reserva un slot. payload={slot_key, nombre, email, whatsapp, canal?, notas?, session_id?}.
    Dispara notificación inmediata por Telegram/webhook si están configurados."""
    result = await asyncio.to_thread(book_slot, payload)
    if not result.get("ok"):
        return result
    logger.info(
        "BOOKING: id=%s slot=%s por %s (%s, %s)",
        result.get("booking_id"), result.get("slot_key"),
        payload.get("nombre"), payload.get("email"), payload.get("whatsapp"),
    )
    # Notificación inmediata (en background, no bloquea la respuesta)
    booking_snapshot = {**payload, **result}
    asyncio.create_task(notify_new_booking(booking_snapshot))
    return result


# ==== ARRANQUE DEL REMINDER LOOP ====
# Al bootear la app, prendemos el loop que avisa 15 min antes de cada reunión.
@app.on_event("startup")
async def _startup_reminder():
    asyncio.create_task(reminder_loop())
    logger.info("Reminder loop arrancado. Canales notif: %s", notif_configured())


@app.get("/api/bookings")
async def api_bookings():
    """Lista las reservas futuras (dashboard del equipo PMD)."""
    return {"bookings": await asyncio.to_thread(upcoming_bookings)}


@app.get("/api/telegram/detect")
async def telegram_detect():
    """Helper ONE-SHOT para detectar el chat_id del bot de Telegram.

    Uso: después de mandarle cualquier mensaje al bot desde Telegram,
    abrís http://127.0.0.1:8000/api/telegram/detect  y te devuelve los
    chat_ids encontrados. Pegás el número en TELEGRAM_CHAT_ID del .env.
    """
    import os
    import httpx as _httpx
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return {
            "ok": False,
            "error": "Falta TELEGRAM_BOT_TOKEN en .env. Pegá el token del bot primero."
        }
    try:
        async with _httpx.AsyncClient(timeout=10) as cl:
            r = await cl.get(f"https://api.telegram.org/bot{token}/getUpdates")
            data = r.json()
        chats = {}
        for upd in data.get("result", []):
            msg = upd.get("message") or upd.get("edited_message") or {}
            chat = msg.get("chat") or {}
            if chat.get("id"):
                cid = str(chat["id"])
                chats[cid] = {
                    "chat_id": chat["id"],
                    "type": chat.get("type"),
                    "first_name": chat.get("first_name"),
                    "username": chat.get("username"),
                }
        if not chats:
            return {
                "ok": False,
                "hint": "No hay mensajes todavía. Abrí el bot en Telegram y mandale /start o cualquier mensaje. Después recargá esta URL.",
                "updates_count": 0,
            }
        return {
            "ok": True,
            "chats": list(chats.values()),
            "instrucciones": "Copiá el chat_id que queres usar y pegalo en TELEGRAM_CHAT_ID del archivo .env. Después reiniciá el bot.",
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# MI HOGAR — proxy a Anthropic. La React app del dashboard NO debe llamar
# a api.anthropic.com directo (no tiene la API key + CORS lo rebota). Estos
# endpoints usan la misma key del .env que ya usa Lucas.
# ─────────────────────────────────────────────────────────────────────────────

class MiHogarChatRequest(BaseModel):
    system: str = Field(default="", description="System prompt completo")
    messages: list[dict] = Field(default_factory=list, description="Mensajes en formato Anthropic")
    max_tokens: int = Field(default=400, ge=1, le=4000)


@app.post("/api/mi-hogar/chat")
async def mi_hogar_chat(payload: MiHogarChatRequest):
    """Proxy de chat para el dashboard Mi Hogar (Valentina IA).

    La React app manda system + history + max_tokens. Nosotros llamamos a
    Anthropic con la key del backend y devolvemos la respuesta tal cual.
    """
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        # Filtrar mensajes vacíos (Anthropic los rechaza)
        msgs = [
            {"role": m.get("role"), "content": m.get("content", "")}
            for m in payload.messages
            if (m.get("content") or "").strip() and m.get("role") in ("user", "assistant")
        ]
        if not msgs:
            return JSONResponse({"content": [{"type": "text", "text": "Hola, ¿en qué te puedo ayudar?"}]})

        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=min(payload.max_tokens, 1500),
            system=payload.system or "Sos Valentina, asistente IA del portal Mi Hogar de PMD Arquitectura.",
            messages=msgs,
        )
        # Reformatear a la estructura que espera la React app
        # (mismo formato que devuelve la API de Anthropic directo)
        content = [{"type": "text", "text": b.text} for b in response.content if hasattr(b, "text")]
        return JSONResponse({"content": content})
    except Exception as exc:
        logger.exception("Mi Hogar chat falló: %s", exc)
        return JSONResponse(
            {"content": [{"type": "text", "text": "Hubo un problema de conexión. Intentá de nuevo en un momento."}]},
            status_code=200,  # 200 para que la React app lo muestre como mensaje
        )


class MiHogarProcessUpdateRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=4000)
    pct: float = Field(default=0)
    photos_count: int = Field(default=0)


@app.post("/api/mi-hogar/process-update")
async def mi_hogar_process_update(payload: MiHogarProcessUpdateRequest):
    """Procesa la descripción de un avance del arquitecto y devuelve JSON estructurado.

    Usado por la pestaña 'Subir Avance' del panel del arquitecto. Le pide a
    Claude que arme título, resumen, items completados y próximos pasos.
    """
    try:
        import anthropic
        import json as _json
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

        prompt = (
            f"Sos el asistente de PMD Arquitectura (steel framing, Zona Norte GBA). "
            f"El arquitecto describió el avance de esta semana:\n\n"
            f"\"{payload.description}\"\n\n"
            f"Avance: {payload.pct}%\n"
            f"Fotos adjuntas: {payload.photos_count}\n\n"
            f"Generá un JSON con esta estructura EXACTA (solo JSON puro, sin markdown):\n"
            f'{{"title":"Título ejecutivo del avance (máx 55 chars, sin punto final)",'
            f'"summary":"Párrafo de 2-3 frases, tono técnico-profesional argentino",'
            f'"completed":["Tarea 1","Tarea 2","Tarea 3","Tarea 4"],'
            f'"next":["Próximo paso 1","Próximo paso 2","Próximo paso 3"]}}\n\n'
            f"Usá terminología técnica argentina de construcción (steel framing, PGC, OSB, DVH, H°A°, etc.). "
            f"Máximo 4 items en cada array."
        )

        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in response.content if hasattr(b, "text"))
        # Parsear el JSON aunque venga con markdown wrapper
        text = text.replace("```json", "").replace("```", "").strip()
        try:
            parsed = _json.loads(text)
        except _json.JSONDecodeError:
            parsed = {
                "title": "Actualización de avance de obra",
                "summary": payload.description[:300],
                "completed": ["Ver descripción adjunta del arquitecto"],
                "next": ["Confirmar próximos pasos en reunión"],
            }
        return JSONResponse(parsed)
    except Exception as exc:
        logger.exception("Mi Hogar process-update falló: %s", exc)
        return JSONResponse({
            "title": "Actualización de avance de obra",
            "summary": payload.description[:300],
            "completed": ["Ver descripción adjunta del arquitecto"],
            "next": ["Confirmar próximos pasos en reunión"],
        })


# ─────────────────────────────────────────────────────────────────────────────
# AUTH — login, password reset, magic-link
# ─────────────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)
    password: str = Field(..., min_length=1, max_length=200)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)


class SetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10)
    password: str = Field(..., min_length=4, max_length=200)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=4, max_length=200)


def _user_summary(user: dict) -> dict:
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "role": user.get("role"),
        "project_id": user.get("project_id"),
        "must_change_password": user.get("must_change_password", False),
    }


@app.post("/api/mi-hogar/login")
async def mi_hogar_login(payload: LoginRequest):
    user = data_store.get_user_by_email(payload.email)
    if not user or not user.get("password_hash"):
        return JSONResponse({"ok": False, "error": "Email o contrasena incorrectos"}, status_code=401)
    if not auth.verify_password(payload.password, user["password_hash"]):
        return JSONResponse({"ok": False, "error": "Email o contrasena incorrectos"}, status_code=401)
    token = auth.sign_session_token(user["id"])
    logger.info("Login OK: %s (%s)", user["email"], user["role"])
    return {"ok": True, "token": token, "user": _user_summary(user)}


@app.post("/api/mi-hogar/forgot-password")
async def mi_hogar_forgot_password(payload: ForgotPasswordRequest):
    user = data_store.get_user_by_email(payload.email)
    if user:
        token = auth.generate_random_token()
        data_store.add_token(token=token, user_id=user["id"], token_type="reset", ttl_seconds=auth.INVITE_TTL_SECONDS)
        email_service.send_password_reset(to_email=user["email"], name=user.get("name", "Hola"), reset_token=token)
        logger.info("Password reset solicitado para %s", user["email"])
    return {"ok": True, "message": "Si el email esta registrado, recibiras instrucciones."}


@app.post("/api/mi-hogar/set-password")
async def mi_hogar_set_password(payload: SetPasswordRequest):
    record = data_store.consume_token(payload.token, expected_type="reset")
    if not record:
        record = data_store.consume_token(payload.token, expected_type="invite")
    if not record:
        return JSONResponse({"ok": False, "error": "Token invalido o expirado"}, status_code=400)
    user = data_store.get_user_by_id(record["user_id"])
    if not user:
        return JSONResponse({"ok": False, "error": "Usuario no encontrado"}, status_code=404)
    new_hash = auth.hash_password(payload.password)
    data_store.update_user(user["id"], password_hash=new_hash, must_change_password=False)
    user = data_store.get_user_by_id(record["user_id"])
    session_token = auth.sign_session_token(user["id"])
    logger.info("Password seteada via %s para %s", record["type"], user["email"])
    return {"ok": True, "token": session_token, "user": _user_summary(user)}


@app.get("/api/mi-hogar/me")
async def mi_hogar_me(authorization: str | None = Header(default=None)):
    user_id = auth.authenticated_user_id(authorization)
    if not user_id:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)
    user = data_store.get_user_by_id(user_id)
    if not user:
        return JSONResponse({"ok": False, "error": "Usuario no encontrado"}, status_code=404)
    response: dict = {"ok": True, "user": _user_summary(user)}
    if user.get("project_id"):
        project = data_store.get_project(user["project_id"])
        if project:
            response["project"] = project
    role = user.get("role")
    if role == "admin":
        # admin ve TODOS los proyectos
        response["projects"] = data_store.list_projects()
    elif role == "asesor":
        # asesor ve solo los proyectos donde él es advisor_id
        all_projs = data_store.list_projects()
        response["projects"] = [p for p in all_projs if p.get("advisor_id") == user_id]
    elif role == "architect":
        # arquitecto ve solo los proyectos donde él es architect_id
        all_projs = data_store.list_projects()
        response["projects"] = [p for p in all_projs if p.get("architect_id") == user_id]
    return response


@app.post("/api/mi-hogar/change-password")
async def mi_hogar_change_password(payload: ChangePasswordRequest, authorization: str | None = Header(default=None)):
    user_id = auth.authenticated_user_id(authorization)
    if not user_id:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)
    user = data_store.get_user_by_id(user_id)
    if not user or not auth.verify_password(payload.current_password, user.get("password_hash") or ""):
        return JSONResponse({"ok": False, "error": "Password actual incorrecta"}, status_code=400)
    new_hash = auth.hash_password(payload.new_password)
    data_store.update_user(user_id, password_hash=new_hash, must_change_password=False)
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — gestion de users + projects
# ─────────────────────────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)
    name: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., pattern="^(admin|asesor|architect|client)$")
    project_id: str | None = None
    initial_password: str | None = None
    send_invite_email: bool = True


def _require_admin(authorization: str | None) -> dict | None:
    user_id = auth.authenticated_user_id(authorization)
    if not user_id:
        return None
    user = data_store.get_user_by_id(user_id)
    if not user or user.get("role") != "admin":
        return None
    return user


def _require_team(authorization: str | None) -> dict | None:
    """Devuelve el user si es admin/asesor/architect (equipo PMD), sino None."""
    user_id = auth.authenticated_user_id(authorization)
    if not user_id:
        return None
    user = data_store.get_user_by_id(user_id)
    if not user or user.get("role") not in ("admin", "asesor", "architect"):
        return None
    return user


@app.get("/api/admin/users")
async def admin_list_users(authorization: str | None = Header(default=None)):
    if not _require_admin(authorization):
        return JSONResponse({"ok": False, "error": "Solo admin"}, status_code=403)
    users = [_user_summary(u) for u in data_store.list_users()]
    return {"ok": True, "users": users}


@app.post("/api/admin/users")
async def admin_create_user(payload: CreateUserRequest, authorization: str | None = Header(default=None)):
    if not _require_admin(authorization):
        return JSONResponse({"ok": False, "error": "Solo admin"}, status_code=403)
    try:
        password_hash = None
        if payload.initial_password:
            password_hash = auth.hash_password(payload.initial_password)
        new_user = data_store.create_user(
            email=payload.email, name=payload.name, role=payload.role,
            project_id=payload.project_id, password_hash=password_hash,
            must_change_password=bool(payload.initial_password),
        )
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    invite_link = None
    if payload.send_invite_email and not payload.initial_password:
        token = auth.generate_random_token()
        data_store.add_token(token=token, user_id=new_user["id"], token_type="invite", ttl_seconds=auth.INVITE_TTL_SECONDS)
        sent = email_service.send_welcome_invite(to_email=new_user["email"], name=new_user["name"], invite_token=token, role=new_user["role"])
        invite_link = f"{email_service.PMD_BASE_URL}/mi-hogar?invite={token}"
        if not sent:
            logger.warning("Email de invite no se pudo mandar a %s", new_user["email"])
    return {"ok": True, "user": _user_summary(new_user), "invite_link": invite_link}


@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: str, authorization: str | None = Header(default=None)):
    admin_user = _require_admin(authorization)
    if not admin_user:
        return JSONResponse({"ok": False, "error": "Solo admin"}, status_code=403)
    if user_id == admin_user["id"]:
        return JSONResponse({"ok": False, "error": "No podes borrar tu propia cuenta admin"}, status_code=400)
    if data_store.delete_user(user_id):
        return {"ok": True}
    return JSONResponse({"ok": False, "error": "Usuario no encontrado"}, status_code=404)


@app.post("/api/admin/users/{user_id}/resend-invite")
async def admin_resend_invite(user_id: str, authorization: str | None = Header(default=None)):
    if not _require_admin(authorization):
        return JSONResponse({"ok": False, "error": "Solo admin"}, status_code=403)
    user = data_store.get_user_by_id(user_id)
    if not user:
        return JSONResponse({"ok": False, "error": "Usuario no encontrado"}, status_code=404)
    token = auth.generate_random_token()
    data_store.add_token(token=token, user_id=user["id"], token_type="invite", ttl_seconds=auth.INVITE_TTL_SECONDS)
    sent = email_service.send_welcome_invite(to_email=user["email"], name=user.get("name", ""), invite_token=token, role=user.get("role", "client"))
    return {"ok": True, "sent": sent, "invite_link": f"{email_service.PMD_BASE_URL}/mi-hogar?invite={token}"}


@app.get("/api/admin/projects")
async def admin_list_projects(authorization: str | None = Header(default=None)):
    if not _require_admin(authorization):
        return JSONResponse({"ok": False, "error": "Solo admin"}, status_code=403)
    return {"ok": True, "projects": data_store.list_projects()}


class UpsertProjectRequest(BaseModel):
    project: dict


@app.post("/api/admin/projects")
async def admin_upsert_project(payload: UpsertProjectRequest, authorization: str | None = Header(default=None)):
    # Permitimos a todo el equipo (admin/asesor/architect) editar proyectos
    # — el admin-users.html y el panel de equipo de Mi Hogar usan este endpoint.
    if not _require_team(authorization):
        return JSONResponse({"ok": False, "error": "Solo equipo PMD"}, status_code=403)
    try:
        result = data_store.upsert_project(payload.project)
        return {"ok": True, "project": result}
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@app.get("/api/precios")
async def api_precios():
    """Devuelve el catálogo de precios (líneas, pisos, aberturas, cocina, extras…).

    Los lee de Google Sheets si está configurado; si no, usa el fallback
    hardcoded de precios.py. Cachea 60s para no machacar la API de Sheets.
    Lo consume el presupuestador en static/presupuestador.html.
    """
    from precios_override import get_precios_con_override
    data = get_precios_con_override()
    return JSONResponse({
        "ok": True,
        "source": precios_source(),
        "precios": data,
    })


@app.post("/api/admin/precios/refresh")
async def api_precios_refresh():
    """Fuerza relectura de precios desde Sheets (limpia cache).

    Útil tras editar la planilla — los cambios se ven instantáneo en lugar de
    esperar el TTL de 60s. NO requiere auth por ahora; agregar antes del lanzamiento
    si se expone públicamente.
    """
    invalidate_precios_cache()
    data = get_precios(force_refresh=True)
    return JSONResponse({
        "ok": True,
        "source": precios_source(),
        "categorias": list(data.keys()),
    })


@app.post("/api/session/new", response_model=SessionResponse)
async def new_session(payload: SessionRequest | None = None):
    """Crea una sesión nueva y devuelve el saludo inicial de Lucas.

    Acepta opcionalmente un body JSON con {context: "landing"|"presupuestador"|"mi-hogar"}.
    El saludo y el system prompt se ajustan al contexto.
    Si no se manda body, default es "landing" (compatible con clientes viejos).
    """
    context = payload.normalized_context() if payload else "landing"
    session_id = uuid.uuid4().hex
    greeting = get_initial_greeting(context)
    SESSIONS[session_id] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "context": context,
        "history": [
            {"role": "assistant", "content": greeting},
        ],
        "lead_captured": False,
    }
    logger.info("Nueva sesión creada: %s — context=%s", session_id, context)
    return SessionResponse(session_id=session_id, greeting=greeting, context=context)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatMessage):
    """Recibe un mensaje del cliente y devuelve la respuesta de Lucas."""
    session = _get_session(payload.session_id)
    history: list[dict] = session["history"]

    # Agregar mensaje del usuario
    history.append({"role": "user", "content": payload.message})

    # Detectar contacto antes de llamar al LLM (por si hay que capturar lead)
    contact = extract_contact(payload.message)
    should_dispatch_lead = False

    if (contact["email"] or contact["phone"]) and not session["lead_captured"]:
        session["lead_captured"] = True
        should_dispatch_lead = True
        logger.info(
            "Contacto detectado en sesión %s — email=%s phone=%s",
            payload.session_id, contact["email"], contact["phone"],
        )

    # Arrancamos la llamada al LLM EN PARALELO al delay de "escribiendo".
    # Antes era secuencial: delay(1.5-4s) + claude(1-3s) = 2.5-7s total.
    # Ahora corren juntos: total = max(delay, claude_time) ≈ 1-3s.
    # Pasamos el context guardado en la sesión para que el system prompt
    # se ajuste (landing / presupuestador / mi-hogar).
    session_context = session.get("context", "landing")
    llm_task = asyncio.create_task(
        asyncio.to_thread(generate_response, history, session_context)
    )

    # Esperar el delay humano en paralelo con el LLM
    await _simulate_typing_delay()

    # Si el LLM todavía no terminó, esperamos lo que falte.
    # Si ya terminó, esto es instantáneo.
    raw_reply, provider = await llm_task

    # Dividir en múltiples mensajes si Lucas usó [[SPLIT]]
    replies = split_reply(raw_reply)

    # Guardamos en el historial el texto unido (sin el delimitador) para que
    # el LLM tenga contexto coherente de lo que ya dijo en próximas turnos.
    clean_reply = "\n\n".join(replies)
    history.append({"role": "assistant", "content": clean_reply})

    # Disparar lead EN BACKGROUND — no bloquea la respuesta al cliente.
    # El usuario ve la respuesta de Lucas al instante mientras los
    # canales (email, Sheets, webhook) corren en paralelo.
    if should_dispatch_lead:
        convo_text = _full_conversation_text(history)
        history_snapshot = list(history)

        # Escribir al Excel acumulativo (rápido, no bloquea)
        excel_payload = {
            "origen": "chat",
            "nombre": contact.get("name", ""),
            "email": contact.get("email", ""),
            "whatsapp": contact.get("phone", ""),
            "mensaje": convo_text[-800:],  # últimos 800 chars de la conversación
            "session_id": payload.session_id,
        }
        asyncio.create_task(asyncio.to_thread(append_lead, excel_payload))

        async def _dispatch_bg():
            try:
                channels = await asyncio.to_thread(
                    dispatch_lead,
                    session_id=payload.session_id,
                    contact=contact,
                    conversation_text=convo_text,
                    full_history=history_snapshot,
                )
                logger.info("Lead disparado en background: %s", channels)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Error en dispatch de lead: %s", exc)
        asyncio.create_task(_dispatch_bg())

    return ChatResponse(
        reply=replies[0],          # compat con clientes viejos
        replies=replies,           # lista completa para el widget actual
        provider=provider,
        lead_captured=should_dispatch_lead,
        lead_channels=None,        # el dispatch corre en background, el cliente no espera ese dato
    )


@app.get("/api/leads")
async def list_leads():
    """Lista los leads capturados (desde el backup local en logs/leads/)."""
    leads_dir = config.LOGS_DIR / "leads"
    if not leads_dir.exists():
        return {"total": 0, "leads": []}

    leads = []
    for path in sorted(leads_dir.glob("*.json"), reverse=True)[:100]:
        try:
            leads.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:  # pylint: disable=broad-except
            continue
    return {"total": len(leads), "leads": leads}


# ==== UPLOADER DE IMAGEN HERO ====
#
# Pagina /upload con drag-drop para subir la imagen del hero sin tocar
# Explorador de archivos. Guarda como static/hero.jpg directamente.

UPLOAD_PAGE_HTML = """<!DOCTYPE html>
<html lang="es-AR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Upload · PMD</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
  body{background:#F4F2EE;color:#1C1C1A;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
  .card{max-width:560px;width:100%;background:#fff;border:1px solid rgba(28,28,26,.09);border-radius:4px;padding:40px;box-shadow:0 30px 60px rgba(28,51,86,.12)}
  h1{font-family:'Cormorant Garamond',Georgia,serif;font-size:34px;font-weight:500;margin-bottom:8px;color:#1C3356}
  p.sub{color:#52524F;font-size:14.5px;margin-bottom:20px;line-height:1.6}
  .target-picker{display:flex;gap:10px;margin-bottom:20px}
  .target-picker label{flex:1;padding:14px 16px;border:1.5px solid rgba(28,28,26,.15);border-radius:4px;cursor:pointer;text-align:center;transition:all .2s;background:#F4F2EE}
  .target-picker label strong{display:block;font-size:14px;color:#1C3356;margin-bottom:4px}
  .target-picker label small{display:block;font-size:11.5px;color:#52524F}
  .target-picker input{display:none}
  .target-picker input:checked+*{background:#fff;border-color:#1C3356;box-shadow:0 0 0 3px rgba(91,163,201,.18)}
  .target-picker label:has(input:checked){background:#fff;border-color:#1C3356;box-shadow:0 0 0 3px rgba(91,163,201,.18)}
  .drop{border:2px dashed #3B6EA5;border-radius:4px;padding:48px 24px;text-align:center;cursor:pointer;transition:all .2s ease;background:#F4F2EE}
  .drop:hover,.drop.drag{background:#ECEAE5;border-color:#1C3356}
  .drop svg{width:44px;height:44px;stroke:#3B6EA5;margin-bottom:12px}
  .drop strong{display:block;font-size:15px;color:#1C3356;margin-bottom:4px}
  .drop span{color:#52524F;font-size:13px}
  input[type=file]{display:none}
  .status{margin-top:20px;padding:14px;border-radius:4px;font-size:14px;display:none}
  .status.ok{background:#E6F4EC;color:#1a6b3e;display:block}
  .status.err{background:#FDE8E8;color:#8a1e1e;display:block}
  .preview{margin-top:20px;display:none}
  .preview img{width:100%;border-radius:4px;max-height:240px;object-fit:cover}
  .back{margin-top:24px;text-align:center}
  .back a{color:#3B6EA5;text-decoration:none;font-size:13px;letter-spacing:.05em}
</style>
</head>
<body>
<div class="card">
  <h1>Subir imagen</h1>
  <p class="sub">Elegi a donde va esta imagen, despues arrastrala o haz click para seleccionarla. Se guarda al toque.</p>

  <div class="target-picker">
    <label>
      <input type="radio" name="target" value="hero" checked>
      <div>
        <strong>Hero (exterior)</strong>
        <small>La foto de la casa afuera</small>
      </div>
    </label>
    <label>
      <input type="radio" name="target" value="interior">
      <div>
        <strong>Interior</strong>
        <small>Lo que se ve cuando se abren las puertas</small>
      </div>
    </label>
  </div>

  <label class="drop" id="drop">
    <svg fill="none" stroke-width="1.5" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
      <polyline points="17 8 12 3 7 8"/>
      <line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
    <strong>Soltar imagen aqui</strong>
    <span>o hacer click para elegir archivo (JPG o PNG)</span>
    <input type="file" id="file" accept="image/*">
  </label>

  <div class="status" id="status"></div>
  <div class="preview" id="preview"><img id="img" alt=""></div>

  <div class="back">
    <a href="/">← Volver a la landing</a>
  </div>
</div>

<script>
const drop = document.getElementById('drop');
const file = document.getElementById('file');
const status = document.getElementById('status');
const preview = document.getElementById('preview');
const img = document.getElementById('img');

function currentTarget(){
  const checked = document.querySelector('input[name=target]:checked');
  return checked ? checked.value : 'hero';
}

['dragover','dragenter'].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.classList.add('drag');
}));
['dragleave','drop'].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.classList.remove('drag');
}));
drop.addEventListener('drop', ev => {
  if (ev.dataTransfer.files.length) upload(ev.dataTransfer.files[0]);
});
file.addEventListener('change', () => {
  if (file.files.length) upload(file.files[0]);
});

async function upload(f){
  if (!f.type.startsWith('image/')){
    status.textContent = 'Ese archivo no parece una imagen.';
    status.className = 'status err';
    return;
  }
  status.textContent = 'Subiendo...';
  status.className = 'status';
  const target = currentTarget();
  const fd = new FormData();
  fd.append('file', f);
  try{
    const r = await fetch('/api/upload-' + target, { method:'POST', body: fd });
    const data = await r.json();
    if (!r.ok || !data.ok) throw new Error(data.detail || 'upload failed');
    status.textContent = 'OK: ' + data.path;
    status.className = 'status ok';
    img.src = data.path + '?t=' + Date.now();
    preview.style.display = 'block';
  }catch(err){
    status.textContent = 'Error: ' + err.message;
    status.className = 'status err';
  }
}
</script>
</body>
</html>"""


@app.get("/upload", include_in_schema=False)
async def upload_page():
    """Página con drag-drop para subir imágenes del hero / interior."""
    return HTMLResponse(UPLOAD_PAGE_HTML)


async def _save_upload(file: UploadFile, dest_name: str) -> dict:
    """Helper: guarda el archivo subido como static/<dest_name>."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Archivo no es una imagen")
    dest = config.STA