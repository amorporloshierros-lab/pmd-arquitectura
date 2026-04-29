"""
precios_override.py
-------------------
Gestiona los overrides de precios que el admin puede editar desde /admin.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path
from precios import PRECIOS_DEFAULT

logger = logging.getLogger("lucas.precios_override")

OVERRIDE_PATH = Path(__file__).parent / "logs" / "precios_lineas.json"
FULL_OVERRIDE_PATH = Path(__file__).parent / "logs" / "precios_full.json"

def get_lineas() -> list[dict]:
    """Devuelve las 4 lineas con sus precios actuales."""
    full = _load_full()
    if full and "lineas" in full:
        return full["lineas"]
    if OVERRIDE_PATH.exists():
        try:
            data = json.loads(OVERRIDE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) == 4:
                return data
        except Exception as e:
            logger.warning("Error leyendo override: %s", e)
    return PRECIOS_DEFAULT["lineas"]

def save_lineas(lineas: list[dict]) -> bool:
    """Guarda las 4 lineas. Compatibilidad hacia atras."""
    try:
        OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
        OVERRIDE_PATH.write_text(json.dumps(lineas, ensure_ascii=False, indent=2), encoding="utf-8")
        # Tambien actualizar en el full si existe
        full = _load_full() or {}
        full["lineas"] = lineas
        _save_full(full)
        return True
    except Exception as e:
        logger.error("Error guardando lineas: %s", e)
        return False

def _load_full() -> dict | None:
    if FULL_OVERRIDE_PATH.exists():
        try:
            return json.loads(FULL_OVERRIDE_PATH.read_text(encoding="utf-8"))
        except:
            return None
    return None

def _save_full(data: dict) -> bool:
    try:
        FULL_OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FULL_OVERRIDE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        logger.error("Error guardando full: %s", e)
        return False

def save_precios_full(data: dict) -> bool:
    """Guarda todos los precios del presupuestador."""
    ok = _save_full(data)
    # Sync lineas override para compatibilidad
    if ok and "lineas" in data:
        try:
            OVERRIDE_PATH.write_text(json.dumps(data["lineas"], ensure_ascii=False, indent=2), encoding="utf-8")
        except:
            pass
    return ok

def get_precios_con_override() -> dict:
    """Devuelve el dict completo con overrides aplicados."""
    from precios import get_precios
    base = dict(get_precios())
    full = _load_full()
    if full:
        for key, val in full.items():
            if key in base:
                base[key] = val
    return base
