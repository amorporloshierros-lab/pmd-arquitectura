# Guía de Deploy

Cómo subir el bot a producción con URL fija (sin depender de cloudflared temporal).

## Opción A: Railway (RECOMENDADA)

**Pros:** deploy automático al hacer `git push`, URL HTTPS gratis, free tier de 500hs/mes.

### Pasos

1. Subir el repo a GitHub (ver sección final de este documento).

2. Ir a [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**.

3. Seleccionar el repo → Railway detecta Python automáticamente.

4. **Variables de entorno** — en la pestaña "Variables", agregar:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ANTHROPIC_MODEL=claude-sonnet-4-6
   GEMINI_API_KEY=AIzaSy...
   GEMINI_MODEL=gemini-1.5-pro-latest
   HOST=0.0.0.0
   PORT=8000
   DEBUG=false
   LOG_LEVEL=INFO
   TYPING_DELAY_MIN=1.0
   TYPING_DELAY_MAX=2.2
   LEAD_RECIPIENT=tu@email.com
   ```

5. **Generar dominio público** — pestaña "Settings" → "Networking" → "Generate Domain". Te da una URL tipo `https://pmd-arquitectura-production.up.railway.app`.

6. **Listo.** Cada `git push` que hagas va a redeploy automático.

### Costo

- Free tier: 500 horas/mes + 1GB RAM. Suficiente para beta.
- Después: ~$5 USD/mes para uptime 24/7.

---

## Opción B: Render

Similar a Railway, tiene free tier permanente pero el servicio "duerme" tras 15 min de inactividad (tarda ~30s en despertar).

1. [render.com](https://render.com) → **New Web Service**.
2. Conectar repo de GitHub.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Variables: mismas que en Railway.

---

## Opción C: VPS (DigitalOcean, Hetzner)

Para quien quiera control total. El `Dockerfile` ya está incluido.

```bash
docker build -t pmd-lucas .
docker run -d -p 80:8000 --env-file .env pmd-lucas
```

Requiere apuntar tu dominio al servidor + configurar nginx con SSL.

---

## Subir a GitHub

Desde la carpeta `lucas-chatbot-mvp/` en PowerShell:

```powershell
# Primera vez
git init
git add .
git commit -m "Initial: landing PMD + chatbot Lucas + presupuestador + admin"

# Vincular con repo remoto (crear antes en github.com/new)
git branch -M main
git remote add origin https://github.com/TU-USUARIO/pmd-arquitectura.git
git push -u origin main
```

Después de la primera vez, para guardar cambios:

```powershell
git add .
git commit -m "descripción de los cambios"
git push
```

---

## Después del deploy

### Chequeos post-deploy

1. Abrí `https://TU-DOMINIO/api/health` — debe devolver `{"status":"ok",...}`.
2. Abrí `https://TU-DOMINIO/` — la landing carga.
3. Abrí `https://TU-DOMINIO/admin` — el dashboard funciona.
4. Probá el chat de Lucas y el presupuestador end-to-end.

### Backups de leads

Los leads se guardan dentro del contenedor. Para que no se pierdan:

- **Railway con persistent volume**: agregar un volume en Settings → Variables → Volumes, y apuntar a `/app/logs/`.
- **Alternativa robusta**: configurar `GOOGLE_SHEETS_ID` en las variables para que cada lead vaya también a una Google Sheet. Así tenés backup externo garantizado.

### Dominio propio

Si querés usar un dominio propio (ej: `chat.pmdarquitectura.com`):

1. En Railway: Settings → Networking → "Custom Domain" → escribí tu subdominio.
2. Railway te da un CNAME a configurar en tu DNS.
3. En el panel de tu proveedor de dominio, agregá ese CNAME.
4. Esperás unos minutos (propagación DNS) y ya está.
