"""
precios_override.py
-------------------
Gestiona los overrides de precios que el admin puede editar desde /admin.
Guarda un JSON con los valores actualizados de las 4 líneas PMD.
Si no existe el archivo, usa los valores de PRECIOS_DEFAULT.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path
from precios import PRECIOS_DEFAULT
 
logger = logging.getLogger("lucas.precios_override")
 
# Guarda el override en el mismo directorio que los logs
OVERRIDE_PATH = Path(__file__).parent / "logs" / "precios_lineas.json"
 
def get_lineas() -> list[dict]:
    """Devuelve las 4 líneas con sus precios actuales (override o default)."""
    if OVERRIDE_PATH.exists():
        try:
            data = json.loads(OVERRIDE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) == 4:
                return data
        except Exception as e:
            logger.warning("Error leyendo override de precios: %s — usando default", e)
    return PRECIOS_DEFAULT["lineas"]
 
def save_lineas(lineas: list[dict]) -> bool:
    """Guarda las 4 líneas actualizadas. Devuelve True si OK."""
    try:
        OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
        OVERRIDE_PATH.write_text(json.dumps(lineas, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Precios de líneas actualizados: %s", [l.get("base") for l in lineas])
        return True
    except Exception as e:
        logger.error("Error guardando override de precios: %s", e)
        return False
 
def get_precios_con_override() -> dict:
    """Devuelve el dict completo de precios con las líneas sobreescritas por el admin."""
    from precios import get_precios
    precios = dict(get_precios())
    precios["lineas"] = get_lineas()
    return precios
 
