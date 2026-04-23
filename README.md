# PMD Arquitectura — Landing + Chatbot Lucas + Presupuestador

Landing web de PMD Servicios Arquitectónicos con:

- **Chatbot Lucas** (Claude API + Gemini fallback) — agente comercial 24/7 que cierra reuniones.
- **Presupuestador interactivo** — wizard de 8 pasos con las 4 líneas de calidad PMD y ajuste +13%.
- **Formulario de contacto** con captura a Excel.
- **Agenda de reuniones** sin superposición (slots L–V 10:00 / 11:30 / 15:00 / 16:30).
- **Dashboard admin** en `/admin` con tabla de leads y reuniones agendadas.
- **Sección "Mi Hogar"** oculta por default con PMD Arquitectura / Capital / Autonomic.

## Stack

- Python 3.11 + FastAPI
- Anthropic Claude (`claude-sonnet-4-6`) + Google Gemini como fallback
- HTML/CSS/JS vanilla (sin build, sin frameworks)
- openpyxl para Excel de leads
- Cloudflared para el túnel público de desarrollo
- Deploy: Railway / Render

## Requisitos

- Python 3.11 o superior
- API key de Anthropic (obligatoria) — `ANTHROPIC_API_KEY`
- API key de Google Gemini (opcional, fallback) — `GEMINI_API_KEY`

## Quick start (local)

```bash
git clone <tu-repo>
cd lucas-chatbot-mvp

# Crear venv e instalar dependencias
python -m venv .venv
.venv\Scripts\Activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus keys

python main.py
```

Se levanta en `http://127.0.0.1:8000`.

## Endpoints principales

| Endpoint | Método | Qué hace |
|---|---|---|
| `/` | GET | Landing principal |
| `/admin` | GET | Dashboard admin (leads + reuniones) |
| `/api/session/new` | POST | Crea sesión de chat + saludo dinámico con hora del día |
| `/api/chat` | POST | Mensaje al bot Lucas |
| `/api/lead/presupuesto` | POST | Captura lead del presupuestador |
| `/api/lead/contacto` | POST | Captura lead del form de contacto |
| `/api/leads` | GET | Lista los últimos 100 leads (para el admin) |
| `/api/slots?n=3` | GET | Próximos N horarios libres de agenda |
| `/api/book` | POST | Reserva un slot |
| `/api/bookings` | GET | Reuniones agendadas futuras |
| `/api/health` | GET | Health check + count de leads |

## Dónde se guardan los leads

- **Excel acumulativo**: `logs/leads_pmd.xlsx` (una fila por lead, se crea solo).
- **JSONs individuales**: `logs/leads/*.json` (con historial completo del chat).
- **Reservas**: `logs/bookings/*.json`.
- **Canales extras opcionales** (configurables en `.env`):
  - Email SMTP (`SMTP_USER` + `SMTP_PASSWORD`).
  - Google Sheets (`GOOGLE_SHEETS_ID` + `credentials/google-sa.json`).
  - Webhook (n8n / Zapier / Make) → `LEAD_WEBHOOK_URL`.

## Deploy

Ver [DEPLOY.md](DEPLOY.md) para instrucciones completas.

Opciones:

1. **Railway** (recomendado) — conectás el repo, auto-detecta Python, deploy en 3 minutos.
2. **Render** — mismo concepto, free tier disponible.
3. **VPS** (DigitalOcean, Hetzner) — `Dockerfile` listo.

## Estructura de carpetas

```
lucas-chatbot-mvp/
├── main.py                 # FastAPI app (endpoints + chat logic)
├── system_prompt.py        # Prompt maestro de Lucas (intocable)
├── ai_provider.py          # Claude + Gemini con failover
├── lead_capture.py         # Email + Sheets + Webhook + JSON backup
├── excel_leads.py          # Leads a Excel acumulativo
├── agenda.py               # Slots + reservas sin superposición
├── config.py               # Paths + env config
├── requirements.txt        # Dependencias Python
├── railway.toml            # Config de deploy a Railway
├── Dockerfile              # Para deploy en contenedor
├── .env.example            # Template de variables
├── .gitignore
├── static/
│   ├── index.html          # Landing principal
│   ├── presupuestador.html # Wizard de 8 pasos (iframe embebido)
│   ├── admin.html          # Panel admin en /admin
│   └── index.backup-v2-good.html
├── credentials/            # Service accounts Google (gitignored)
├── logs/                   # Leads capturados (gitignored)
└── README.md
```

## Los 5 intocables

Estos componentes son parte de la identidad de la marca PMD y **no se reemplazan**:

1. **Logo 3 cuadrados** con `sqWave` + `sqShimmer` + rotación planetaria al scroll.
2. **Paleta PMD**: `--b1:#5BA3C9 --b2:#3B6EA5 --b3:#2B4E7A --b4:#1C3356`.
3. **Chatbot Lucas** completo (FAB + ventana + multi-burbuja `[[SPLIT]]` + typing).
4. **Presupuestador wizard** de 8 pasos (iframe standalone).
5. **Scroll reveals** con IntersectionObserver bidireccional.

## Licencia

Propietario · PMD Global Corporate Automation®
