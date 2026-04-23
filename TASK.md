# TASK: Lucas — Chatbot de ventas PMD

## Descripción
Chatbot web para atención al cliente y captura de leads en el sitio de PMD (Servicios Arquitectónicos e Integrales). Encarna a **Lucas**, asesor senior argentino con tono high-ticket, sigue un embudo de 3 fases (calificación → captura de contacto → precio+Calendly), y distribuye los leads capturados a email, Google Sheets y webhook en paralelo.

## Cuándo usar este script
- "Necesito un chatbot para mi web que atienda clientes"
- "Armame un agente de atención al cliente para PMD"
- "Quiero un widget de chat con captura de leads"

## Prerequisitos

**Variables de entorno** (en `.env`):
- `ANTHROPIC_API_KEY` (obligatorio)
- `GEMINI_API_KEY` (obligatorio — failover)
- `SMTP_USER`, `SMTP_PASSWORD` (opcional — email leads)
- `GOOGLE_SHEETS_ID` + `GOOGLE_SA_PATH` (opcional — Sheets)
- `LEAD_WEBHOOK_URL` (opcional — webhook n8n/Zapier)

**Dependencias**:
```bash
pip install -r requirements.txt
```

## Cómo ejecutar

```bash
# Desde la carpeta lucas-chatbot-mvp/
python main.py
# o también:
uvicorn main:app --reload --port 8000
```

Abrir `http://127.0.0.1:8000` para ver la landing con el widget integrado.

| Parámetro       | Tipo | Requerido | Default | Descripción |
|-----------------|------|-----------|---------|-------------|
| `HOST`          | str  | No        | 127.0.0.1 | IP donde bindea el server |
| `PORT`          | int  | No        | 8000    | Puerto HTTP |
| `TYPING_DELAY_MIN/MAX` | float | No | 1.5 / 4.0 | Rango de delay simulando escritura humana |

## Endpoints API

| Método | Ruta                | Descripción |
|--------|---------------------|-------------|
| GET    | `/`                 | Landing + widget |
| GET    | `/api/health`       | Health-check + estado de canales de lead |
| POST   | `/api/session/new`  | Crea sesión, devuelve saludo inicial |
| POST   | `/api/chat`         | `{session_id, message}` → respuesta de Lucas |
| GET    | `/api/leads`        | Lista leads capturados (backup local) |

## Output esperado
- Conversación fluida en español argentino con tono high-ticket.
- Bloqueo automático de precio hasta que el cliente deje WhatsApp o email.
- Lead dispatch a todos los canales configurados al detectar contacto.
- Backup local en `logs/leads/YYYYMMDD-HHMMSS_sessionid.json`.
- Failover transparente Claude → Gemini si Anthropic rate-limita.

## Errores comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `ANTHROPIC_API_KEY not found` | Falta en `.env` | Pegar la key en `.env` |
| `429 rate_limit_error` de Claude | Cuota agotada | El failover a Gemini debería activarse solo |
| `SMTPAuthenticationError` | Password común en lugar de "app password" | Crear contraseña de aplicación en Gmail |
| Lead no llega a Sheets | Service account no compartida con la planilla | Compartir la planilla con el email `xxx@xxx.iam.gserviceaccount.com` del JSON |

## Notas
- Sesiones viven en memoria (dict). Para producción, migrar a Redis.
- El widget asume mismo origen que el backend. Para embeber en otro dominio, cambiar `API_BASE` en `static/index.html`.
- `system_prompt.py` es intocable — cualquier cambio en el tono o en las reglas del embudo pasa por ahí.
