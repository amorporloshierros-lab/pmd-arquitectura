"""
config.py
---------
Carga y valida todas las variables de entorno del MVP de Lucas.
Falla explícitamente si falta algo crítico.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto
ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")


def get_env(key: str, default: str | None = None, required: bool = True) -> str:
    """Obtiene una variable de entorno con validación."""
    value = os.getenv(key, default)
    if required and (value is None or value == ""):
        print(f"[CONFIG] Variable requerida faltante en .env: {key}")
        sys.exit(1)
    return value  # type: ignore[return-value]


def get_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def get_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


# ---- IA Providers ----
ANTHROPIC_API_KEY = get_env("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = get_env("ANTHROPIC_MODEL", default="claude-sonnet-4-6", required=False)
GEMINI_API_KEY = get_env("GEMINI_API_KEY")
GEMINI_MODEL = get_env("GEMINI_MODEL", default="gemini-1.5-pro-latest", required=False)

# ---- Lead Capture: Email ----
SMTP_HOST = get_env("SMTP_HOST", default="smtp.gmail.com", required=False)
SMTP_PORT = get_int("SMTP_PORT", 587)
SMTP_USER = get_env("SMTP_USER", required=False)
SMTP_PASSWORD = get_env("SMTP_PASSWORD", required=False)
LEAD_RECIPIENT = get_env("LEAD_RECIPIENT", default="l.lanzalot@pmdarquitectura.com", required=False)

# ---- Lead Capture: Google Sheets ----
GOOGLE_SHEETS_ID = get_env("GOOGLE_SHEETS_ID", default="", required=False)
GOOGLE_SA_PATH = get_env("GOOGLE_SA_PATH", default="credentials/google-sa.json", required=False)
GOOGLE_SHEETS_TAB = get_env("GOOGLE_SHEETS_TAB", default="Leads", required=False)

# ---- Lead Capture: Webhook ----
LEAD_WEBHOOK_URL = get_env("LEAD_WEBHOOK_URL", default="", required=False)

# ---- Servidor ----
HOST = get_env("HOST", default="127.0.0.1", required=False)
PORT = get_int("PORT", 8000)
DEBUG = get_bool("DEBUG", False)
LOG_LEVEL = get_env("LOG_LEVEL", default="INFO", required=False)

# ---- Comportamiento ----
TYPING_DELAY_MIN = get_float("TYPING_DELAY_MIN", 1.5)
TYPING_DELAY_MAX = get_float("TYPING_DELAY_MAX", 4.0)
INACTIVITY_TIMEOUT = get_int("INACTIVITY_TIMEOUT", 600)

# ---- Rutas ----
STATIC_DIR = ROOT_DIR / "static"
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def lead_channels_enabled() -> dict[str, bool]:
    """Devuelve qué canales de captura de leads están configurados."""
    return {
        "email": bool(SMTP_USER and SMTP_PASSWORD and LEAD_RECIPIENT),
        "sheets": bool(GOOGLE_SHEETS_ID and (ROOT_DIR / GOOGLE_SA_PATH).exists()),
        "webhook": bool(LEAD_WEBHOOK_URL),
    }
