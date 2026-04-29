"""
precios.py
----------
Source of truth para los precios del presupuestador PMD.

Estrategia:
  1. Si Google Sheets está configurado (GOOGLE_SHEETS_ID + service account),
     lee la hoja "Precios" de la misma planilla donde se guardan los leads.
  2. Si Sheets no está configurado o falla, usa PRECIOS_DEFAULT (hardcoded).
  3. Cachea 60 segundos en memoria para no machacar la API.

Schema de la hoja "Precios" en Google Sheets (headers en fila 1):

    | categoria | item_id | label | sublabel | tipo | valor | texto_precio | tag |

Categorías válidas y tipos:
  - lineas       (tipo=base)   → línea de calidad PMD
  - pisos        (tipo=extra)  → pisos interiores USD/m²
  - aberturas    (tipo=extra)  → aberturas USD/m²
  - cocina       (tipo=fixed)  → cocina USD fijo
  - cubierta     (tipo=roof)   → cubierta USD/m²
  - revestimiento(tipo=fach)   → revestimiento USD/m² fachada
  - banos        (tipo=per_bano) → recargo USD por baño
  - clima        (tipo=extra)  → climatización USD/m²
  - agua         (tipo=fixed)  → agua caliente USD fijo
  - electrica    (tipo=fixed)  → eléctrica USD fijo
  - solar        (tipo=fixed)  → solar USD fijo
  - suelo        (tipo=extra)  → tipo de suelo USD/m²
  - extras       (tipo=fixed)  → extras toggle USD fijo
  - sistema      (tipo=mod)    → sistema constructivo (multiplicador)
  - plantas      (tipo=factor) → cantidad plantas (multiplicador)
  - ajuste_pmd   (tipo=factor) → ajuste final único (1.13)
  - linea_spread (tipo=spread) → item_id="<linea>_min" o "<linea>_max"
"""

from __future__ import annotations

import logging
import time
from typing import Any

import config

logger = logging.getLogger("lucas.precios")

# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK — Mismos valores que estaban hardcoded en presupuestador.html.
# Se usan si Google Sheets no está configurado o si la lectura falla.
# ─────────────────────────────────────────────────────────────────────────────

PRECIOS_DEFAULT: dict[str, Any] = {
    "lineas": [
        {"id": "confort",  "label": "Línea Confort",        "sublabel": "Línea nacional 1ª marca",     "base": 1100, "texto_precio": "USD 1.000–1.200/m²", "tag": ""},
        {"id": "premium",  "label": "Línea Premium",        "sublabel": "Primeras marcas · DVH",       "base": 1400, "texto_precio": "USD 1.200–1.600/m²", "tag": "Más elegido"},
        {"id": "alta",     "label": "Línea Alta Gama",      "sublabel": "Importados seleccionados",    "base": 2250, "texto_precio": "USD 2.000–2.500/m²", "tag": "Alta gama"},
        {"id": "lujo",     "label": "Línea Lujo Importado", "sublabel": "Schüco, Leicht, mármol",      "base": 3800, "texto_precio": "USD 2.600–5.000/m²", "tag": "Lujo"},
    ],
    "pisos": [
        {"id": "cemento",     "label": "Cemento alisado / microcemento", "sublabel": "USD 18/m²",                      "extra": 18},
        {"id": "ceramico",    "label": "Cerámico 60x60 nacional 1a",     "sublabel": "Nacional 1ª marca · USD 28/m²",  "extra": 28},
        {"id": "porcelanato", "label": "Porcelanato 80x80 premium",      "sublabel": "Importado o premium · USD 45/m²", "extra": 45},
        {"id": "madera",      "label": "Piso de madera",                 "sublabel": "Flotante o parquet · USD 55/m²",  "extra": 55},
    ],
    "aberturas": [
        {"id": "aluminio", "label": "Aluminio simple sin DVH",       "sublabel": "Sin DVH · USD 100/m²",            "extra": 100},
        {"id": "modena",   "label": "Negro DVH Modena + mosquitero", "sublabel": "+ mosquitero · USD 195/m²",       "extra": 195},
        {"id": "rpt",      "label": "RPT importado",                 "sublabel": "Rotura puente térmico · USD 350/m²", "extra": 350},
        {"id": "schuco",   "label": "Schüco europeo",                "sublabel": "Sistema europeo · USD 600/m²",    "extra": 600},
    ],
    "cocina": [
        {"id": "basica",    "label": "Básica · melamina + granito",          "sublabel": "Melamina + granito · USD 4.000",        "fixed": 4000,  "tag": ""},
        {"id": "isla",      "label": "Con isla · Silestone (Naudir)",         "sublabel": "Silestone · USD 8.000",                 "fixed": 8000,  "tag": "Más elegido"},
        {"id": "diseno",    "label": "De diseño · lacada + Silestone premium","sublabel": "Lacada + Silestone premium · USD 15.000","fixed": 15000, "tag": ""},
        {"id": "importada", "label": "Importada · Leicht / SieMatic",         "sublabel": "Leicht / SieMatic · USD 35.000+",       "fixed": 35000, "tag": ""},
    ],
    "cubierta": [
        {"id": "chapa_galv", "label": "Chapa galvanizada C25",         "sublabel": "Estándar SF · USD 9,5/m²",  "roof": 9.5},
        {"id": "chapa_pre",  "label": "Chapa prepintada",              "sublabel": "Color a elección · USD 12/m²", "roof": 12},
        {"id": "plana",      "label": "Cubierta plana losa+membrana",  "sublabel": "Losa + membrana · USD 18/m²", "roof": 18},
    ],
    "revestimiento": [
        {"id": "eifs",        "label": "EIFS / revoque estándar PMD", "sublabel": "Estándar PMD · incluido",                  "fach": 0},
        {"id": "porcelanato", "label": "Porcelanato exterior",        "sublabel": "60x60 o 90x90 · +USD 45/m² fach.",         "fach": 45},
        {"id": "ipe",         "label": "Listones madera IPE",         "sublabel": "Estilo Punta del Este · +USD 60/m² fach.", "fach": 60},
        {"id": "corten",      "label": "Chapa / cortén",              "sublabel": "Elemento de diseño · +USD 100/m² fach.",   "fach": 100},
    ],
    "banos": [
        {"id": "ceramico",  "label": "Cerámico 30x60 nacional",  "sublabel": "30x60 · incluido",          "per_bano": 0},
        {"id": "marmol",    "label": "Porcelanato mármol",       "sublabel": "+USD 800/baño",             "per_bano": 800},
        {"id": "travertino","label": "Mármol / travertino importado", "sublabel": "Importado · +USD 2.500/baño", "per_bano": 2500},
    ],
    "clima": [
        {"id": "split",    "label": "Split / AC frío-calor",   "sublabel": "Sin gas · USD 8/m²",        "extra": 8},
        {"id": "caldera",  "label": "Caldera + radiadores gas","sublabel": "Gas natural · USD 12/m²",   "extra": 12},
        {"id": "losa",     "label": "Losa radiante",           "sublabel": "Caldera + circuitos · USD 22/m²", "extra": 22},
        {"id": "sin",      "label": "Sin calefacción",         "sublabel": "Cotizar aparte · USD 0",    "extra": 0},
    ],
    "agua": [
        {"id": "termo_gas",   "label": "Termotanque gas",   "sublabel": "Estándar",        "fixed": 0},
        {"id": "caldera",     "label": "Caldera mural",     "sublabel": "+USD 2.200",      "fixed": 2200},
        {"id": "termo_solar", "label": "Termotanque solar", "sublabel": "+USD 3.600",      "fixed": 3600},
    ],
    "electrica": [
        {"id": "estandar", "label": "Estándar", "sublabel": "Reglamentaria",  "fixed": 0},
        {"id": "domotica", "label": "Domótica", "sublabel": "+USD 5.400",     "fixed": 5400},
    ],
    "solar": [
        {"id": "no",      "label": "No incluir",                "sublabel": "Conexión red estándar", "fixed": 0},
        {"id": "paneles", "label": "Paneles 3kW + batería",     "sublabel": "+USD 7.200",            "fixed": 7200},
    ],
    "suelo": [
        {"id": "normal",  "label": "Normal / tosca", "sublabel": "Estándar",        "extra": 0},
        {"id": "relleno", "label": "Relleno",        "sublabel": "Tierra vegetal", "extra": 15},
    ],
    "extras": [
        {"id": "piscina",         "label": "Piscina",                "sublabel": "Precio fijo · MO incluida · USD 16.265", "fixed": 16265},
        {"id": "garage",          "label": "Garage cubierto",        "sublabel": "Estructura SF · 1 auto · USD 8.000",     "fixed": 8000},
        {"id": "deck",            "label": "Terraza / deck",         "sublabel": "Madera o porcelanato · USD 5.000",       "fixed": 5000},
        {"id": "quincho",         "label": "Quincho / parrilla",     "sublabel": "+USD 4.200",                              "fixed": 4200},
        {"id": "placares",        "label": "Placares a medida",      "sublabel": "+USD 3.500",                              "fixed": 3500},
        {"id": "vestidor",        "label": "Vestidor",               "sublabel": "+USD 4.800",                              "fixed": 4800},
        {"id": "office",          "label": "Home office",            "sublabel": "+USD 2.200",                              "fixed": 2200},
        {"id": "theater",         "label": "Home theater",           "sublabel": "+USD 5.500",                              "fixed": 5500},
        {"id": "parque",          "label": "Parquerización",         "sublabel": "Se evalúa según proyecto · lo anotamos",  "fixed": 0,  "note": True},
        {"id": "riego",           "label": "Sistema de riego",       "sublabel": "Se evalúa según proyecto · lo anotamos",  "fixed": 0,  "note": True},
    ],
    "sistema": {
        "Steel framing":     1.00,
        "Mampostería":       0.95,
        "Hormigón elaborado":1.08,
    },
    "plantas": {
        "1": 1.00,
        "2": 1.04,
        "3": 1.09,
        "4": 1.15,
    },
    "ajuste_pmd": 1.13,
    "linea_spread": {
        "Línea Confort":         {"min": 0.91, "max": 1.09},
        "Línea Premium":         {"min": 0.87, "max": 1.13},
        "Línea Alta Gama":       {"min": 0.90, "max": 1.11},
        "Línea Lujo Importado":  {"min": 0.72, "max": 1.30},
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# CACHÉ EN MEMORIA
# ─────────────────────────────────────────────────────────────────────────────

CACHE_TTL_SECONDS = 60  # corto, así los cambios en Sheets se ven en ~1 min

_cache: dict[str, Any] = {"data": None, "ts": 0.0, "source": "default"}


# ─────────────────────────────────────────────────────────────────────────────
# LECTOR DE GOOGLE SHEETS
# ─────────────────────────────────────────────────────────────────────────────

# Categorías que son listas de items (mismo schema con id/label/sublabel + valor)
LIST_CATEGORIES = {
    "lineas", "pisos", "aberturas", "cocina", "cubierta", "revestimiento",
    "banos", "clima", "agua", "electrica", "solar", "suelo", "extras",
}

# Mapeo de categoría → nombre del campo numérico
TYPE_FIELD = {
    "base": "base",
    "extra": "extra",
    "fixed": "fixed",
    "roof": "roof",
    "fach": "fach",
    "per_bano": "per_bano",
}


def _read_from_sheets() -> dict[str, Any] | None:
    """Lee la hoja 'Precios' de Google Sheets y devuelve el dict completo.

    Si Sheets no está configurado o algo falla → None (caller usa fallback).
    """
    if not config.GOOGLE_SHEETS_ID:
        return None
    sa_path = config.ROOT_DIR / config.GOOGLE_SA_PATH
    if not sa_path.exists():
        return None

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(str(sa_path), scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(config.GOOGLE_SHEETS_ID)

        try:
            ws = sh.worksheet("Precios")
        except gspread.WorksheetNotFound:
            logger.warning("Hoja 'Precios' no existe en la planilla — usando defaults")
            return None

        rows = ws.get_all_records()  # cada fila = dict con headers como keys
        if not rows:
            logger.warning("Hoja 'Precios' vacía — usando defaults")
            return None

        # Resultado vacío con la misma estructura
        result: dict[str, Any] = {cat: [] for cat in LIST_CATEGORIES}
        result["sistema"] = {}
        result["plantas"] = {}
        result["ajuste_pmd"] = PRECIOS_DEFAULT["ajuste_pmd"]
        result["linea_spread"] = {}

        for row in rows:
            cat = str(row.get("categoria", "")).strip()
            item_id = str(row.get("item_id", "")).strip()
            label = str(row.get("label", "")).strip()
            sublabel = str(row.get("sublabel", "")).strip()
            tipo = str(row.get("tipo", "")).strip()
            valor_raw = row.get("valor", "")
            texto_precio = str(row.get("texto_precio", "")).strip()
            tag = str(row.get("tag", "")).strip()

            # Convertir valor a número (si vino como string con coma decimal, normalizar)
            try:
                if isinstance(valor_raw, str):
                    valor_raw = valor_raw.replace(",", ".").strip()
                valor = float(valor_raw) if valor_raw not in ("", None) else 0
            except (ValueError, TypeError):
                logger.warning("Valor no numérico en fila %s — saltando", row)
                continue

            if cat in LIST_CATEGORIES:
                if not item_id or not label:
                    continue
                field = TYPE_FIELD.get(tipo, "extra")
                item: dict[str, Any] = {
                    "id": item_id,
                    "label": label,
                    "sublabel": sublabel,
                    field: valor,
                }
                if texto_precio:
                    item["texto_precio"] = texto_precio
                if tag:
                    item["tag"] = tag
                result[cat].append(item)

            elif cat == "sistema":
                # item_id = "Steel framing" / "Mampostería" / "Hormigón elaborado"
                if item_id:
                    result["sistema"][item_id] = valor

            elif cat == "plantas":
                # item_id = "1" / "2" / "3" / "4"
                if item_id:
                    result["plantas"][str(item_id)] = valor

            elif cat == "ajuste_pmd":
                result["ajuste_pmd"] = valor

            elif cat == "linea_spread":
                # item_id = "Línea Confort_min" o "Línea Confort_max"
                if "_" in item_id:
                    linea, side = item_id.rsplit("_", 1)
                    if side in ("min", "max"):
                        result["linea_spread"].setdefault(linea, {})
                        result["linea_spread"][linea][side] = valor

        # Para cada categoría de lista que quedó vacía → usar el default
        # (así si el usuario no completó algo, no se rompe el presupuestador)
        for cat in LIST_CATEGORIES:
            if not result[cat]:
                result[cat] = PRECIOS_DEFAULT[cat]
        if not result["sistema"]:
            result["sistema"] = PRECIOS_DEFAULT["sistema"]
        if not result["plantas"]:
            result["plantas"] = PRECIOS_DEFAULT["plantas"]
        if not result["linea_spread"]:
            result["linea_spread"] = PRECIOS_DEFAULT["linea_spread"]

        logger.info(
            "Precios cargados desde Google Sheets — %d filas procesadas", len(rows)
        )
        return result

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Error leyendo precios desde Sheets: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# API PÚBLICA
# ─────────────────────────────────────────────────────────────────────────────

def get_precios(force_refresh: bool = False) -> dict[str, Any]:
    """Devuelve el dict completo de precios.

    Cachea 60s. Si force_refresh=True, ignora el cache y vuelve a leer.
    Prioridad: Google Sheets → fallback PRECIOS_DEFAULT.
    """
    now = time.time()
    if not force_refresh and _cache["data"] and (now - _cache["ts"]) < CACHE_TTL_SECONDS:
        return _cache["data"]

    data = _read_from_sheets()
    if data is not None:
        _cache["source"] = "sheets"
    else:
        data = PRECIOS_DEFAULT
        _cache["source"] = "default"

    _cache["data"] = data
    _cache["ts"] = now
    return data


def invalidate_cache() -> None:
    """Forzar relectura en la próxima llamada a get_precios()."""
    _cache["data"] = None
    _cache["ts"] = 0.0


def get_source() -> str:
    """Devuelve 'sheets' o 'default' según de dónde salió el último read."""
    return _cache.get("source", "default")
