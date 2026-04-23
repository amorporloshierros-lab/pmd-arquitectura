# Compartir Lucas con un amigo — Cloudflare Tunnel

Esta guía te deja a Lucas con una URL pública para que cualquiera pruebe el chatbot, sin pisarse con tu túnel de n8n y sin pagar nada. Tu PC tiene que estar prendida.

---

## La forma más rápida: Quick Tunnel (2 comandos, sin cuenta)

### Paso 1 — Instalar cloudflared

Abrí **PowerShell**, copiá y pegá:

```powershell
winget install --id Cloudflare.cloudflared
```

(Si winget te tira que no existe el ID, alternativamente bajalo manual desde https://github.com/cloudflare/cloudflared/releases/latest — descargás el `.msi` para Windows y le hacés doble click.)

Verificá que quedó bien instalado:

```powershell
cloudflared --version
```

Tiene que mostrarte algo tipo `cloudflared version 2025.x.x`.

> **Si "cloudflared" no se reconoce:** cerrá y volvé a abrir PowerShell para que tome el PATH actualizado.

---

### Paso 2 — Asegurate de que Lucas esté corriendo

En una terminal, andá a la carpeta y arrancá el server:

```powershell
cd "C:\Users\amorp\OneDrive\Documentos\Claude\Projects\youtube automatic\lucas-chatbot-mvp"
python main.py
```

Vas a ver:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Dejá esa terminal abierta.** Lucas necesita seguir corriendo.

---

### Paso 3 — Levantar el túnel

Abrí **una segunda terminal de PowerShell** (no cierres la anterior) y corré:

```powershell
cloudflared tunnel --url http://localhost:8000
```

Después de unos segundos vas a ver algo así:

```
Your quick Tunnel has been created! Visit it at:
https://something-random-words.trycloudflare.com
```

**Esa es la URL pública de Lucas.** Copiala y mandásela a tu amigo por WhatsApp:

> *Probá esto: https://something-random-words.trycloudflare.com*

Tu amigo entra desde donde sea, ve la landing PMD, abre el widget y charla con Lucas en vivo.

---

## Detalles importantes del modo Quick Tunnel

✅ **Sin cuenta de Cloudflare.** Anónimo, gratis, instantáneo.
✅ **Sin límite de túneles abiertos.** Podés tener corriendo este, el del n8n, y los que sumes — todos a la vez.
✅ **HTTPS automático.** Cloudflare emite el certificado solo.
✅ **Sin cold starts.** Mientras tu PC esté prendida, Lucas responde al instante.

⚠️ **La URL es temporal.** Cada vez que cortás el túnel (Ctrl+C) y lo volvés a levantar, te genera una URL nueva.
⚠️ **Tu PC tiene que estar prendida** y con Lucas corriendo para que el chat funcione.

Si la URL temporal te molesta, en la próxima sección está cómo conseguir una URL fija con tu propio dominio.

---

## Para cortar el túnel y/o Lucas

- **Cortar el túnel:** `Ctrl+C` en la terminal donde corre `cloudflared`.
- **Cortar Lucas:** `Ctrl+C` en la terminal donde corre `python main.py`.

---

## (Opcional, para más adelante) URL fija con tu dominio

Si querés que la URL no cambie nunca y que sea algo como `chat.pmd-arquitectura.com`, necesitás:

1. Una cuenta de Cloudflare gratuita.
2. Tu dominio (`pmd-arquitectura.com` o el que sea) gestionado por Cloudflare.
   - Eso significa cambiar los **nameservers** del dominio en tu proveedor (NIC.ar, GoDaddy, etc.) a los que te da Cloudflare. Tarda unas horas en propagar.

Una vez que el dominio está en Cloudflare:

```powershell
# Login (abre el navegador)
cloudflared login

# Crear el túnel con nombre
cloudflared tunnel create lucas-pmd

# Asociarlo al subdominio
cloudflared tunnel route dns lucas-pmd chat.pmd-arquitectura.com

# Correrlo
cloudflared tunnel run lucas-pmd
```

A partir de ahí, `https://chat.pmd-arquitectura.com` apunta a Lucas. Para siempre.

Para que se levante **automáticamente cuando prendés la PC** (sin tener que abrir terminal cada vez):

```powershell
cloudflared service install
```

Eso lo registra como servicio de Windows. Lucas quedaría online cada vez que tu PC arranca, en background, sin tener que tocar nada.

---

## Resumen visual

```
┌─────────────────────────────────────────────────────────┐
│  TU PC (prendida)                                        │
│                                                          │
│  Terminal 1: python main.py        ← Lucas corre acá    │
│  Terminal 2: cloudflared tunnel    ← El túnel corre acá │
│                                                          │
└────────────────────────┬─────────────────────────────────┘
                         │
                  Túnel cifrado
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  CLOUDFLARE (su red mundial)                             │
│  https://random-words.trycloudflare.com                  │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
                  Tu amigo desde
                  cualquier parte del mundo
```

---

## Si algo falla

**`cloudflared` no se reconoce como comando** → cerrá y volvé a abrir PowerShell, o reiniciá la PC. Es el PATH que no se actualizó.

**El túnel se levanta pero la URL devuelve 502** → fijate que `python main.py` siga corriendo en la otra terminal. Si Lucas no está vivo, el túnel apunta al vacío.

**El túnel se cae solo cada cierto tiempo** → es normal en Quick Tunnel cuando hay inactividad larga. Volvelo a correr con `cloudflared tunnel --url http://localhost:8000`. Si te molesta, pasá al modo "Named Tunnel" con cuenta.

**Mi amigo dice que el chat no le responde** → abrí la consola del navegador en su pestaña (F12 → Console) y mirá si hay errores. Lo más probable es que el server local se haya frenado o que la API key de Claude haya expirado.
