"""
data_store.py
-------------
Persistencia JSON para Mi Hogar PMD.

Guarda users, projects, tokens (invites/resets) y precios en un único JSON
ubicado en el volumen persistente de Railway (/data/pmd-data.json).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import config

logger = logging.getLogger("lucas.data_store")


def _resolve_data_path() -> Path:
    env_path = os.getenv("PMD_DATA_PATH")
    if env_path:
        p = Path(env_path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
        except OSError as exc:
            logger.warning("PMD_DATA_PATH=%s no es escribible (%s) - fallback a local", env_path, exc)
    fallback = config.ROOT_DIR / "data" / "pmd-data.json"
    fallback.parent.mkdir(parents=True, exist_ok=True)
    return fallback


DATA_PATH = _resolve_data_path()
logger.info("data_store: usando archivo %s", DATA_PATH)
_lock = threading.RLock()


def _seed_data() -> dict[str, Any]:
    """Datos iniciales si el archivo no existe."""
    from auth import hash_password
    bootstrap_password = "pmd-admin-2026"

    users = [
        {"id": "user_augusto", "email": "augusto@pmdarquitectura.com",
         "password_hash": hash_password(bootstrap_password), "role": "admin",
         "name": "Augusto", "project_id": None, "advisor_for": [],
         "created_at": "2026-04-29T00:00:00Z", "must_change_password": True},
        {"id": "user_lucas", "email": "lucas@pmdarquitectura.com",
         "password_hash": hash_password(bootstrap_password), "role": "admin",
         "name": "Lucas", "project_id": None, "advisor_for": [],
         "created_at": "2026-04-29T00:00:00Z", "must_change_password": True},
        {"id": "user_marcos", "email": "marcos@pmdarquitectura.com",
         "password_hash": hash_password(bootstrap_password), "role": "architect",
         "name": "Arq. Marcos Delgado", "project_id": None, "advisor_for": [],
         "created_at": "2026-04-29T00:00:00Z", "must_change_password": True},
        {"id": "user_garcia", "email": "garcia@mail.com",
         "password_hash": hash_password("1234"), "role": "client",
         "name": "Familia Garcia", "project_id": "NDT-45", "advisor_for": [],
         "created_at": "2026-04-29T00:00:00Z", "must_change_password": False},
    ]

    project_garcia = {
        "id": "NDT-45", "name": "Casa Nordelta - Lote 45",
        "client_id": "user_garcia", "advisor_id": "user_lucas",
        "architect_id": "user_marcos", "system": "Steel Framing",
        "location": "Nordelta, Tigre - GBA Norte",
        "startDate": "01 Nov 2025", "estimatedEnd": "01 Ago 2026",
        "totalM2": 180, "overallProgress": 62,
        "phases": [
            {"name": "Platea HoAo", "pct": 100},
            {"name": "Estructura SF", "pct": 85},
            {"name": "Cerramiento", "pct": 60},
            {"name": "Instalaciones", "pct": 30},
            {"name": "Terminaciones", "pct": 0},
        ],
        "milestones": [
            {"id": 1, "name": "Firma de contrato", "pct": 15, "usd": 22275, "status": "paid", "paidDate": "03 Nov 2025", "certRef": "PMD-CERT-001"},
            {"id": 2, "name": "Inicio de obra / Platea", "pct": 20, "usd": 29700, "status": "paid", "paidDate": "20 Nov 2025", "certRef": "PMD-CERT-002"},
            {"id": 3, "name": "Estructura SF completa", "pct": 20, "usd": 29700, "status": "paid", "paidDate": "12 Feb 2026", "certRef": "PMD-CERT-003"},
            {"id": 4, "name": "Cerramiento completo", "pct": 20, "usd": 29700, "status": "pending", "paidDate": None, "certRef": None},
            {"id": 5, "name": "Instalaciones completas", "pct": 15, "usd": 22275, "status": "pending", "paidDate": None, "certRef": None},
            {"id": 6, "name": "Terminaciones completas", "pct": 7, "usd": 10395, "status": "pending", "paidDate": None, "certRef": None},
            {"id": 7, "name": "Entrega y llaves", "pct": 3, "usd": 4455, "status": "pending", "paidDate": None, "certRef": None},
        ],
        "cac": {
            "base": {"value": 847.3, "date": "Nov 2025"},
            "current": {"value": 976.4, "date": "Abr 2026"},
            "history": [
                {"m": "Nov", "v": 847}, {"m": "Dic", "v": 865}, {"m": "Ene", "v": 888},
                {"m": "Feb", "v": 913}, {"m": "Mar", "v": 945}, {"m": "Abr", "v": 976},
            ],
        },
        "budget": [],
        "updates": [
            {"id": 1, "date": "18 Abr 2026", "week": "Sem. 24",
             "title": "Estructura completada sector norte", "progress": 62,
             "summary": "Se completaron los perfiles PGC 100/40 en toda la fachada norte y oeste.",
             "completed": ["Perfiles PGC fachada norte", "Marcos DVH PB", "OSB sector norte"],
             "next": ["Completar cubierta sector sur", "Inicio chapas galvanizadas"],
             "photos": ["https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=700&h=460&fit=crop"]},
        ],
        "mods": [],
        "documents": [
            {"id": 1, "cat": "planos", "icon": "P", "name": "Planta baja - Arquitectura", "date": "Oct 2025", "size": "2.4 MB", "status": "vigente"},
            {"id": 7, "cat": "legal", "icon": "L", "name": "Contrato de obra PMD", "date": "01 Nov 2025", "size": "890 KB", "status": "vigente"},
            {"id": 10, "cat": "cert", "icon": "C", "name": "Certificado de Avance N1", "date": "03 Nov 2025", "size": "180 KB", "ref": "PMD-CERT-001", "status": "emitido"},
        ],
    }

    return {
        "version": 1, "users": users, "projects": [project_garcia],
        "tokens": [], "precios": {},
        "metadata": {"created_at": "2026-04-29T00:00:00Z",
                     "bootstrap_password_note": f"Password inicial admins: {bootstrap_password}"},
    }


def load() -> dict[str, Any]:
    with _lock:
        if not DATA_PATH.exists():
            logger.info("Creando %s con seed", DATA_PATH)
            data = _seed_data()
            _write_atomic(data)
            return data
        try:
            with DATA_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.exception("Error leyendo %s: %s", DATA_PATH, exc)
            raise


def save(data: dict[str, Any]) -> None:
    with _lock:
        _write_atomic(data)


def _write_atomic(data: dict[str, Any]) -> None:
    tmp = DATA_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(DATA_PATH)


def list_users() -> list[dict]:
    return list(load().get("users", []))


def get_user_by_email(email: str) -> dict | None:
    if not email:
        return None
    email_norm = email.strip().lower()
    for u in load().get("users", []):
        if u.get("email", "").lower() == email_norm:
            return u
    return None


def get_user_by_id(user_id: str) -> dict | None:
    if not user_id:
        return None
    for u in load().get("users", []):
        if u.get("id") == user_id:
            return u
    return None


def create_user(*, email: str, name: str, role: str, project_id: str | None = None,
                password_hash: str | None = None, must_change_password: bool = True) -> dict:
    if role not in ("admin", "asesor", "architect", "client"):
        raise ValueError(f"Role invalido: {role}")
    with _lock:
        data = load()
        email_norm = email.strip().lower()
        for u in data["users"]:
            if u.get("email", "").lower() == email_norm:
                raise ValueError(f"Email ya registrado: {email}")
        new_user = {
            "id": f"user_{uuid.uuid4().hex[:12]}", "email": email_norm,
            "password_hash": password_hash, "role": role, "name": name,
            "project_id": project_id, "advisor_for": [],
            "created_at": _now_iso(), "must_change_password": must_change_password,
        }
        data["users"].append(new_user)
        save(data)
        logger.info("Usuario creado: %s (%s)", email_norm, role)
        return new_user


def update_user(user_id: str, **fields) -> dict | None:
    allowed = {"name", "role", "project_id", "password_hash", "must_change_password", "advisor_for", "email"}
    with _lock:
        data = load()
        for u in data["users"]:
            if u.get("id") == user_id:
                for k, v in fields.items():
                    if k in allowed:
                        u[k] = v
                save(data)
                return u
        return None


def delete_user(user_id: str) -> bool:
    with _lock:
        data = load()
        before = len(data["users"])
        data["users"] = [u for u in data["users"] if u.get("id") != user_id]
        if len(data["users"]) == before:
            return False
        save(data)
        return True


def list_projects() -> list[dict]:
    return list(load().get("projects", []))


def get_project(project_id: str) -> dict | None:
    if not project_id:
        return None
    for p in load().get("projects", []):
        if p.get("id") == project_id:
            return p
    return None


def upsert_project(project: dict) -> dict:
    if not project.get("id"):
        raise ValueError("project debe tener 'id'")
    with _lock:
        data = load()
        existing = next((p for p in data["projects"] if p.get("id") == project["id"]), None)
        if existing:
            existing.update(project)
            result = existing
        else:
            data["projects"].append(project)
            result = project
        save(data)
        return result


def delete_project(project_id: str) -> bool:
    with _lock:
        data = load()
        before = len(data["projects"])
        data["projects"] = [p for p in data["projects"] if p.get("id") != project_id]
        if len(data["projects"]) == before:
            return False
        save(data)
        return True


def add_token(*, token: str, user_id: str, token_type: str, ttl_seconds: int) -> dict:
    if token_type not in ("invite", "reset"):
        raise ValueError(f"token_type invalido: {token_type}")
    record = {
        "token": token, "user_id": user_id, "type": token_type,
        "expires_at": int(time.time()) + ttl_seconds, "created_at": _now_iso(),
    }
    with _lock:
        data = load()
        data["tokens"].append(record)
        save(data)
    return record


def consume_token(token: str, expected_type: str | None = None) -> dict | None:
    """Busca y consume un token. Solo lo borra si las validaciones pasan
    (o si esta expirado, para cleanup). Si el tipo no coincide, devuelve None
    pero deja el token intacto -- esto permite a un endpoint intentar varios
    tipos en cascada (reset / invite) sin perderlo.
    """
    if not token:
        return None
    with _lock:
        data = load()
        for i, t in enumerate(data["tokens"]):
            if t.get("token") != token:
                continue
            if expected_type and t.get("type") != expected_type:
                return None
            if t.get("expires_at", 0) < time.time():
                data["tokens"].pop(i)
                save(data)
                return None
            data["tokens"].pop(i)
            save(data)
            return t
        return None


def cleanup_expired_tokens() -> int:
    now = time.time()
    with _lock:
        data = load()
        before = len(data["tokens"])
        data["tokens"] = [t for t in data["tokens"] if t.get("expires_at", 0) >= now]
        removed = before - len(data["tokens"])
        if removed > 0:
            save(data)
        return removed


def get_precios() -> dict:
    return load().get("precios", {}) or {}


def set_precios(precios: dict) -> None:
    with _lock:
        data = load()
        data["precios"] = precios
        save(data)


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
