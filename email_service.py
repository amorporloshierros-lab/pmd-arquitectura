"""
email_service.py
----------------
Servicio de email para Mi Hogar PMD via Resend HTTP API.

Manda dos tipos de email:
  - Welcome / invite (cuando admin crea un user nuevo)
  - Password reset

Por que Resend en vez de SMTP:
  Railway bloquea egress en puertos SMTP (25/465/587). Resend usa HTTPS,
  que sale sin restricciones. La cuenta free incluye 3.000 mails/mes.
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("lucas.email")

DEFAULT_BASE_URL = "https://pmd-arquitectura-production.up.railway.app"
PMD_BASE_URL = os.getenv("PMD_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

# Si el usuario no configura un from custom, usamos onboarding@resend.dev
# (el dominio default verificado de Resend, sirve para arrancar sin tocar DNS).
DEFAULT_FROM = "PMD Arquitectura <onboarding@resend.dev>"
PMD_FROM_EMAIL = os.getenv("PMD_FROM_EMAIL", "").strip() or DEFAULT_FROM

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_API_URL = "https://api.resend.com/emails"


def _resend_configured() -> bool:
    return bool(RESEND_API_KEY)


def _send(*, to_email: str, subject: str, html: str, plain: str) -> bool:
    if not _resend_configured():
        logger.warning("RESEND_API_KEY no configurado, no se manda email a %s", to_email)
        return False
    if not to_email:
        return False
    payload = {
        "from": PMD_FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": plain,
    }
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(RESEND_API_URL, json=payload, headers=headers)
        if r.status_code in (200, 201, 202):
            try:
                eid = r.json().get("id", "")
            except Exception:
                eid = ""
            logger.info("Email enviado a %s - '%s' [resend id=%s]", to_email, subject, eid)
            return True
        logger.error("Resend API rechazo el envio a %s (%s): %s", to_email, r.status_code, r.text[:300])
        return False
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Fallo envio de email a %s: %s", to_email, exc)
        return False


_BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>{title}</title></head>
<body style="margin:0;padding:0;background:#F0EDE8;font-family:-apple-system,Helvetica,Arial,sans-serif;color:#1E2A3A">
<table width="100%" cellspacing="0" cellpadding="0" style="background:#F0EDE8;padding:40px 20px"><tr><td align="center">
<table width="560" cellspacing="0" cellpadding="0" style="background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 4px 24px rgba(30,58,95,.08)">
<tr><td style="background:linear-gradient(135deg,#1E3A5F,#3A6EA5);padding:30px 36px">
<div style="display:inline-block"><span style="display:inline-block;width:13px;height:13px;background:#5B8EC2;border-radius:3px;margin-right:3px"></span><span style="display:inline-block;width:13px;height:13px;background:#3A6EA5;border-radius:3px;margin-right:3px"></span><span style="display:inline-block;width:13px;height:13px;background:#1E3A5F;border-radius:3px;margin-right:10px"></span><span style="font-size:18px;font-weight:900;color:#fff;letter-spacing:-.02em;vertical-align:1px">PMD</span> <span style="font-size:18px;font-weight:700;color:#fff;vertical-align:1px">arquitectura</span></div>
</td></tr>
<tr><td style="padding:36px">{body}</td></tr>
<tr><td style="background:#F0EDE8;padding:20px 36px;border-top:1px solid #E2DED8">
<p style="margin:0;font-size:12px;color:#94A0AE;line-height:1.6">PMD Soluciones Arquitectonicas e Integrales - Av. Agustin M. Garcia 10271, Benavidez, Buenos Aires<br>Email automatico desde el portal Mi Hogar.</p>
</td></tr></table></td></tr></table></body></html>"""


def send_welcome_invite(*, to_email: str, name: str, invite_token: str, role: str) -> bool:
    invite_url = f"{PMD_BASE_URL}/mi-hogar?invite={invite_token}"
    role_label = {"admin": "Administrador", "asesor": "Asesor", "architect": "Arquitecto", "client": "Cliente"}.get(role, role.title())

    if role == "client":
        intro = (f"<p style=\"font-size:16px;line-height:1.6;margin:0 0 20px\">Hola <strong>{name}</strong>,</p>"
                 f"<p style=\"font-size:15px;line-height:1.65;color:#5C6A7A;margin:0 0 20px\">"
                 "Bienvenido a tu portal privado <strong>Mi Hogar</strong>. Desde aca vas a poder seguir tu obra "
                 "en tiempo real: avance, fotos semanales, presupuesto, certificados de pago, planos y mucho mas.</p>")
    else:
        intro = (f"<p style=\"font-size:16px;line-height:1.6;margin:0 0 20px\">Hola <strong>{name}</strong>,</p>"
                 f"<p style=\"font-size:15px;line-height:1.65;color:#5C6A7A;margin:0 0 20px\">"
                 f"Tu cuenta de <strong>{role_label}</strong> en el portal Mi Hogar de PMD ya esta creada. "
                 "Para activarla, hace clic en el boton de abajo y elegi tu contrasena.</p>")

    body = intro + (
        f"<table cellspacing=\"0\" cellpadding=\"0\" style=\"margin:24px 0\"><tr><td style=\"background:#3A6EA5;border-radius:10px\">"
        f"<a href=\"{invite_url}\" style=\"display:inline-block;padding:14px 28px;color:#fff;text-decoration:none;font-weight:700;font-size:15px\">Activar mi cuenta</a>"
        "</td></tr></table>"
        "<p style=\"font-size:13px;color:#94A0AE;margin:24px 0 8px\">Si el boton no funciona, copia este link:</p>"
        f"<p style=\"font-size:12px;color:#3A6EA5;word-break:break-all;margin:0 0 24px\">{invite_url}</p>"
        "<p style=\"font-size:13px;color:#94A0AE;margin:24px 0 0;border-top:1px solid #E2DED8;padding-top:18px\">"
        "<strong>Importante:</strong> este link expira en 24 horas.</p>"
    )

    subject = "Bienvenido a Mi Hogar - Activa tu cuenta"
    html = _BASE_TEMPLATE.format(title=subject, body=body)
    plain = (f"Hola {name},\n\nTu cuenta de {role_label} en Mi Hogar PMD ya esta creada.\n"
             f"Activala con este link (expira en 24hs):\n\n{invite_url}\n\n- Equipo PMD")
    return _send(to_email=to_email, subject=subject, html=html, plain=plain)


def send_password_reset(*, to_email: str, name: str, reset_token: str) -> bool:
    reset_url = f"{PMD_BASE_URL}/mi-hogar?reset={reset_token}"
    body = (
        f"<p style=\"font-size:16px;line-height:1.6;margin:0 0 20px\">Hola <strong>{name}</strong>,</p>"
        "<p style=\"font-size:15px;line-height:1.65;color:#5C6A7A;margin:0 0 20px\">"
        "Recibimos una solicitud para restablecer tu contrasena en el portal Mi Hogar. "
        "Hace clic en el boton para elegir una nueva.</p>"
        f"<table cellspacing=\"0\" cellpadding=\"0\" style=\"margin:24px 0\"><tr><td style=\"background:#3A6EA5;border-radius:10px\">"
        f"<a href=\"{reset_url}\" style=\"display:inline-block;padding:14px 28px;color:#fff;text-decoration:none;font-weight:700;font-size:15px\">Restablecer contrasena</a>"
        "</td></tr></table>"
        f"<p style=\"font-size:12px;color:#3A6EA5;word-break:break-all;margin:0 0 24px\">{reset_url}</p>"
        "<p style=\"font-size:13px;color:#94A0AE;margin:24px 0 0;border-top:1px solid #E2DED8;padding-top:18px\">"
        "<strong>Si no pediste este reset</strong>, ignora este email - tu contrasena sigue intacta. Link valido 24hs.</p>"
    )
    subject = "Restablecer tu contrasena - Mi Hogar PMD"
    html = _BASE_TEMPLATE.format(title=subject, body=body)
    plain = (f"Hola {name},\n\nRecibimos una solicitud para restablecer tu contrasena.\n"
             f"Restablecela con este link (expira en 24hs):\n\n{reset_url}\n\n"
             "Si no pediste este reset, ignora este email.\n\n- Equipo PMD")
    return _send(to_email=to_email, subject=subject, html=html, plain=plain)


def _fila(label: str, valor) -> str:
    """Genera una fila de la tabla del presupuesto."""
    if not valor:
        return ""
    return (
        f"<tr>"
        f"<td style='padding:8px 12px;font-size:13px;color:#5C6A7A;border-bottom:1px solid #EEE;width:40%'>{label}</td>"
        f"<td style='padding:8px 12px;font-size:13px;color:#1E2A3A;font-weight:600;border-bottom:1px solid #EEE'>{valor}</td>"
        f"</tr>"
    )


def _seccion(titulo: str, filas: str) -> str:
    """Genera una sección con título y tabla de filas."""
    if not filas:
        return ""
    return (
        f"<p style='font-size:13px;font-weight:700;color:#1E3A5F;letter-spacing:.06em;text-transform:uppercase;"
        f"margin:24px 0 8px;padding-bottom:6px;border-bottom:2px solid #3A6EA5'>{titulo}</p>"
        f"<table width='100%' cellspacing='0' cellpadding='0' style='border:1px solid #EEE;border-radius:8px;overflow:hidden;margin-bottom:8px'>"
        f"{filas}</table>"
    )


def send_lead_presupuesto(*, lead: dict, to_email: str) -> bool:
    """Envía email completo con TODO el proyecto del presupuestador a PMD."""
    nombre = lead.get("nombre") or "Sin nombre"
    from_label = f"Nuevo presupuesto — {nombre}"

    # ---- CONTACTO ----
    filas_contacto = (
        _fila("Nombre", nombre) +
        _fila("Email", lead.get("email")) +
        _fila("WhatsApp", lead.get("whatsapp")) +
        _fila("Zona", lead.get("zona")) +
        _fila("Urgencia", lead.get("urgencia")) +
        _fila("Comentarios", lead.get("comentarios"))
    )

    # ---- PROYECTO ----
    filas_proyecto = (
        _fila("Tipo de obra", lead.get("tipo")) +
        _fila("M² cubiertos", f"{lead.get('cubiertos_m2')} m²" if lead.get("cubiertos_m2") else "") +
        _fila("M² semicubiertos", f"{lead.get('semicubiertos_m2')} m²" if lead.get("semicubiertos_m2") else "") +
        _fila("Plantas", lead.get("plantas")) +
        _fila("Sistema constructivo", lead.get("sistema")) +
        _fila("Tipo de obra", lead.get("obra")) +
        _fila("Tipo de suelo", lead.get("suelo")) +
        _fila("Etapa", lead.get("etapa")) +
        _fila("Modo presupuestador", lead.get("modo"))
    )

    # ---- TERMINACIONES ----
    extras_list = lead.get("extras", [])
    extras_str = ", ".join(extras_list) if isinstance(extras_list, list) else str(extras_list or "")
    filas_term = (
        _fila("Nivel/Calidad", lead.get("nivel")) +
        _fila("Pisos interiores", lead.get("pisos")) +
        _fila("Aberturas", lead.get("aberturas")) +
        _fila("Cocina", lead.get("cocina")) +
        _fila("Climatización", lead.get("clima")) +
        _fila("Agua caliente", lead.get("agua")) +
        _fila("Instalación eléctrica", lead.get("electrica")) +
        _fila("Solar/Paneles", lead.get("solar")) +
        _fila("Cubierta", lead.get("cubierta")) +
        _fila("Revestimiento exterior", lead.get("revestimiento")) +
        _fila("Baños", lead.get("banos")) +
        _fila("Cantidad baños", lead.get("banos_cantidad")) +
        _fila("Extras adicionales", extras_str)
    )

    # ---- PRESUPUESTO ----
    total_min = lead.get("total_min_usd") or lead.get("presupuesto_min_usd") or 0
    total_max = lead.get("total_max_usd") or lead.get("presupuesto_max_usd") or 0
    from locale import format_string
    try:
        min_fmt = f"USD {int(total_min):,}".replace(",", ".")
        max_fmt = f"USD {int(total_max):,}".replace(",", ".")
    except Exception:
        min_fmt = str(total_min)
        max_fmt = str(total_max)

    filas_presu = (
        _fila("Rango estimado", f"{min_fmt} – {max_fmt}") +
        _fila("Ajuste PMD", f"{lead.get('ajuste_pmd_pct', 13)}%") +
        _fila("Fecha", lead.get("timestamp", ""))
    )

    body = (
        f"<p style='font-size:16px;font-weight:700;color:#1E2A3A;margin:0 0 6px'>Nuevo presupuesto completado</p>"
        f"<p style='font-size:14px;color:#5C6A7A;margin:0 0 24px'>Un cliente completó el wizard del presupuestador PMD.</p>"
        + _seccion("Datos de contacto", filas_contacto)
        + _seccion("Proyecto", filas_proyecto)
        + _seccion("Terminaciones y equipamiento", filas_term)
        + _seccion("Presupuesto estimado", filas_presu)
        + "<p style='font-size:12px;color:#94A0AE;margin:24px 0 0;border-top:1px solid #E2DED8;padding-top:16px'>"
          "Este lead fue generado automáticamente desde el presupuestador web de PMD Arquitectura.</p>"
    )

    subject = f"[PMD] Nuevo presupuesto — {nombre} · {min_fmt}–{max_fmt}"
    html = _BASE_TEMPLATE.format(title=subject, body=body)
    plain = (
        f"NUEVO PRESUPUESTO PMD\n{'='*40}\n"
        f"Nombre: {nombre}\n"
        f"Email: {lead.get('email')}\nWhatsApp: {lead.get('whatsapp')}\n"
        f"Zona: {lead.get('zona')}\n\n"
        f"PROYECTO\n{'-'*20}\n"
        f"Tipo: {lead.get('tipo')}\nM²: {lead.get('cubiertos_m2')}\n"
        f"Sistema: {lead.get('sistema')}\nNivel: {lead.get('nivel')}\n\n"
        f"PRESUPUESTO ESTIMADO\n{'-'*20}\n"
        f"Rango: {min_fmt} – {max_fmt}\n"
    )
    return _send(to_email=to_email, subject=subject, html=html, plain=plain)
