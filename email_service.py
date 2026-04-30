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
