# Setup Google Sheets para precios + leads

Esta guía te lleva paso a paso a configurar la planilla donde vas a editar los precios del presupuestador (y donde se guardan los leads de Lucas) sin tocar código.

Tiempo total: ~25 minutos. Solo lo hacés una vez.

---

## Paso 1 — Crear la planilla en Google Sheets

1. Andá a https://sheets.new (te abre una planilla nueva).
2. Renombrala arriba a la izquierda: **`PMD — Precios y Leads`**.
3. Renombrá la pestaña de abajo de "Hoja 1" a **`Precios`** (doble clic en la pestaña).
4. Abrí el archivo `precios_template.csv` que está en la carpeta del proyecto (`lucas-chatbot-mvp/precios_template.csv`).
5. **Copiá todo el contenido** y pegalo en la celda A1 de la planilla. Google Sheets lo va a separar en columnas automáticamente.
6. Vas a tener algo así arriba:

   | A | B | C | D | E | F | G | H |
   |---|---|---|---|---|---|---|---|
   | categoria | item_id | label | sublabel | tipo | valor | texto_precio | tag |
   | lineas | confort | Línea Confort | Línea nacional 1ª marca | base | 1100 | USD 1.000–1.200/m² | |
   | lineas | premium | Línea Premium | ... | base | 1400 | USD 1.200–1.600/m² | Más elegido |
   | ... | | | | | | | |

7. **Copiá el ID de la planilla**: en la URL del navegador vas a ver algo como
   `docs.google.com/spreadsheets/d/AbCdEf123XYZ.../edit`. El **ID** es lo que está entre `/d/` y `/edit`. Guardalo, lo vas a necesitar.

---

## Paso 2 — Crear una Service Account en Google Cloud

Una "service account" es un usuario robot de Google que va a leer la planilla en nombre del backend.

1. Andá a https://console.cloud.google.com/
2. Arriba a la izquierda, clic en el selector de proyecto → **"Nuevo proyecto"** → llamalo `pmd-arquitectura` → crear.
3. En la barra de búsqueda de arriba, escribí **"Google Sheets API"** → entrá → clic **"Habilitar"**.
4. Hacé lo mismo con **"Google Drive API"** → habilitar.
5. Menú lateral → **"IAM y administración"** → **"Cuentas de servicio"** → **"+ Crear cuenta de servicio"**.
6. Nombre: `pmd-precios-reader`. Descripción: `Lee Google Sheets desde Railway`. → Crear.
7. En "Conceder acceso a este proyecto" — saltealo (clic continuar). → Listo.
8. Ahora vas a ver tu service account en la lista. Clic sobre ella → pestaña **"Claves"** → **"Agregar clave"** → **"Crear clave nueva"** → **JSON** → Crear.
9. Te descarga un archivo `.json` (algo como `pmd-arquitectura-abc123.json`). **Guardalo bien — es como una contraseña.**

---

## Paso 3 — Compartir la planilla con la service account

1. Abrí el archivo JSON que descargaste con un editor de texto.
2. Buscá el campo `"client_email"` — vas a ver algo como `pmd-precios-reader@pmd-arquitectura.iam.gserviceaccount.com`. **Copialo.**
3. Volvé a tu planilla de Google Sheets → botón verde **"Compartir"** arriba a la derecha.
4. Pegá ese email → seleccioná **"Editor"** (necesita escribir si querés guardar leads ahí también) → **Enviar**. Si te pregunta si querés notificar al destinatario, decí "No".

---

## Paso 4 — Subir el JSON al proyecto

Tenés 2 opciones:

### Opción A (recomendada para empezar): subir el JSON al repo

1. Renombrá el archivo JSON a `google-sa.json`.
2. Copialo a la carpeta `lucas-chatbot-mvp/credentials/` del proyecto. Si la carpeta no existe, creala.
3. **Importante**: el `.gitignore` ya tiene `credentials/` para que NO se suba a GitHub. Verificá que aparezca con:
   ```bash
   git status credentials/
   ```
   Si NO aparece `google-sa.json` como archivo a commitear, perfecto — está siendo ignorado.

   Pero entonces **¿cómo llega a Railway?** Lo subimos al volumen persistente o lo configuramos vía variable de entorno (Opción B abajo).

### Opción B (más segura para producción): variable de entorno en Railway

1. Abrí el archivo JSON con un editor.
2. Copiá TODO el contenido (es JSON con ~10 campos).
3. En Railway → tu servicio → pestaña **Variables** → agregá una variable nueva llamada `GOOGLE_SA_JSON` con todo el JSON pegado como valor.
4. Después necesitás un pequeño cambio en `precios.py` para que en lugar de leer del archivo, lea de la variable de entorno. Decímelo y lo hago en 2 minutos.

**Para el lanzamiento de mañana, usá la Opción A.** Es más rápida.

---

## Paso 5 — Configurar variables en Railway

En el panel de Railway → servicio PMD-arquitectura → **Variables** → agregá (o actualizá):

```
GOOGLE_SHEETS_ID=<el ID que copiaste en el Paso 1, punto 7>
GOOGLE_SA_PATH=credentials/google-sa.json
GOOGLE_SHEETS_TAB=Leads
```

(`GOOGLE_SHEETS_TAB` es la pestaña donde se guardan los leads. Para los precios, el código busca específicamente la pestaña "Precios" que ya creaste.)

---

## Paso 6 — Probar que ande

1. Hacé `git push` con el código nuevo (precios.py + endpoint + presupuestador con fetch).
2. Cuando Railway termine el redeploy, abrí en el navegador:
   ```
   https://pmd-arquitectura-production.up.railway.app/api/precios
   ```
3. Vas a ver un JSON. Mirá el campo `"source"`:
   - `"source": "sheets"` → ✅ está leyendo de tu planilla
   - `"source": "default"` → ❌ algo no está bien, está usando los defaults hardcoded

4. Si dice `"sheets"`: cambiá un valor en tu Google Sheets (por ejemplo, `Línea Confort` de 1100 a 1200), guardá, y en máximo 60 segundos vas a ver el cambio reflejado en el presupuestador. (También podés llamar `POST /api/admin/precios/refresh` para forzar refresh inmediato.)

---

## Cómo cambiar precios en el día a día

Una vez configurado:

1. Abrís Google Sheets → pestaña Precios → encontrás la fila del item que querés cambiar
2. Editás la columna **F (valor)** y opcionalmente la columna **D (sublabel)** y **G (texto_precio)** para que coincida con el nuevo número
3. Guardás (Cmd/Ctrl+S — Sheets guarda solo)
4. En 60s aparece en el sitio. Si tenés apuro: `POST https://pmd-arquitectura-production.up.railway.app/api/admin/precios/refresh` (con curl o Postman)

**No necesitás pushear código nunca más para cambiar precios.**

---

## Estructura de la planilla — referencia rápida

Cada fila representa un precio en el presupuestador. La columna `categoria` define a qué grupo pertenece:

| categoria | qué es | tipo | dónde aparece |
|---|---|---|---|
| `lineas` | Líneas de calidad PMD | base | Step Terminaciones — primera grilla |
| `pisos` | Pisos interiores | extra | Step Terminaciones — pisos |
| `aberturas` | Aberturas | extra | Step Terminaciones — aberturas |
| `cocina` | Tipo de cocina | fixed | Step Terminaciones — cocina |
| `cubierta` | Techo | roof | Step Terminaciones — cubierta |
| `revestimiento` | Fachada | fach | Step Terminaciones — revestimiento |
| `banos` | Recargo por baño | per_bano | Step Terminaciones — baños |
| `clima` | Climatización | extra | Step Instalaciones — clima |
| `agua` | Agua caliente | fixed | Step Instalaciones — agua |
| `electrica` | Eléctrica | fixed | Step Instalaciones — eléctrica |
| `solar` | Energía solar | fixed | Step Instalaciones — solar |
| `suelo` | Tipo de suelo | extra | Step Datos — suelo |
| `extras` | Extras opcionales | fixed | Step Extras |
| `sistema` | Multiplicador sistema | mod | Step Datos — sistema constructivo |
| `plantas` | Multiplicador plantas | factor | Step Datos — slider plantas |
| `ajuste_pmd` | Ajuste % final | factor | Aplicado al total |
| `linea_spread` | Spread min/max por línea | spread | Determina rango USD por línea |

**¡No borres filas ni cambies los `item_id`!** El código matchea por `label` para los items de lista y por `item_id` para sistema/plantas/spread. Si cambiás un label, el override no funciona y se queda con el default del HTML.

Si tenés dudas o algo no funciona, escribime el resultado de `GET /api/precios` y vemos.
