# Base de conocimiento de Lucas — Sistema Híbrido

Este directorio contiene la **memoria externa** de Lucas. Como Claude no aprende
entre conversaciones, usamos archivos que se leen al inicio de cada sesión para
que Lucas sea progresivamente mejor vendedor.

## Estructura

```
conocimiento/
├── clientes/        AUTO         Una ficha .md por cada lead capturado
├── staging/         AUTO         Preguntas y objeciones detectadas (sin revisar)
└── aprobado/        MANUAL       Lo que Lucas "sabe" — se inyecta en su prompt
```

## El flujo híbrido

### Parte automática (sin intervención tuya)

Cada vez que una conversación termina (cliente deja contacto, o cierra el
widget, o pasa tiempo de inactividad), el backend llama a Claude con un
"prompt de extracción" que analiza la charla completa y extrae:

1. **Ficha del cliente** → `conocimiento/clientes/YYYY-MM-DD_sessionid.md`
   - Datos duros (contacto, obra, m², nivel, zona)
   - Extras que eligió o descartó
   - Objeciones que puso
   - Preguntas que hizo
   - Outcome (agendó / dejó contacto / se fue sin nada)
   - Notas cualitativas

2. **Preguntas detectadas** → `conocimiento/staging/preguntas_nuevas.md`
   - Toda pregunta "nueva" que no esté ya en el FAQ aprobado se anexa acá.

3. **Objeciones detectadas** → `conocimiento/staging/objeciones_nuevas.md`
   - Lo mismo para objeciones ("me parece caro", "no tengo apuro", etc.).

### Parte manual (tu intervención — idealmente 1 vez por semana)

Abrís los archivos de `staging/` y para cada entrada decidís:

- **Aprobar con respuesta modelo** → movés la pregunta/objeción a
  `aprobado/preguntas_frecuentes.md` (o `aprendizajes.md` si es algo más
  estratégico), agregándole una respuesta/táctica.

- **Descartar** → la borrás del staging. Claude a veces inventa o duplica.

- **Agrupar** → si 5 clientes hicieron variantes de la misma pregunta
  ("¿cuánto tarda una obra?" / "¿en cuánto tiempo entregan?" / "¿cuál es el
  plazo de obra?"), las consolidás en una sola entrada.

Una vez aprobado, ese conocimiento **automáticamente aparece en el system
prompt de Lucas** en la próxima conversación. Sin redeploys, sin reinicios.

## Archivos clave y qué poner en ellos

### `aprobado/preguntas_frecuentes.md`

Formato por entrada:

```markdown
## ¿Cuánto tarda una obra desde cero?

**Frecuencia:** 23 clientes lo preguntaron (a 2026-04-20)

**Respuesta modelo:**
> "Muy buena pregunta. Para una casa de 150m² en steel framing, hablamos
> de 5-6 meses calendario desde el inicio de obra. En mampostería
> tradicional, 9-12 meses. Ese plazo está incluido en el contrato y lo
> seguís viernes a viernes en Mi Hogar."

**Notas internas:** lo que más convence es mencionar que el plazo es
contractual y que el avance se ve online.
```

### `aprobado/aprendizajes.md`

Formato más libre. Tus notas después de cada semana.

```markdown
## 2026-04-21 — Los clientes de Escobar son más sensibles al precio

He notado que el 70% de los leads de Escobar eligen Eco Confort o
Estándar. Los de Nordelta van directo a Premium/Élite.

**Acción:** cuando detecto zona = Escobar, sugerir primero Eco/Estándar
y mencionar el Entorno Mi Hogar como diferenciador (no competimos por
precio bajo, competimos por transparencia).
```

## Qué se inyecta al prompt de Lucas

Al inicio de cada conversación, el backend toma los últimos N items de:

- `aprobado/preguntas_frecuentes.md` (todo, hasta cierto tamaño)
- `aprobado/aprendizajes.md` (las últimas 10 entradas)

y los suma al final del system prompt como una sección llamada
"CONOCIMIENTO ACUMULADO". Lucas los usa como contexto pero no los
menciona explícitamente al cliente.

## Privacidad

- Los archivos `.md` quedan en el filesystem del servidor. No se suben a
  ningún lado.
- Si deployás a Railway/VPS, estos archivos viven en el contenedor —
  considerar backup periódico si son críticos.
- Los teléfonos y emails de los clientes SÍ se guardan (para hacer
  seguimiento). Si te incomoda, podés anonimizarlos con un hash.

## Comandos útiles

```bash
# Ver leads del mes
ls conocimiento/clientes/2026-04-*

# Contar preguntas pendientes de revisar
wc -l conocimiento/staging/preguntas_nuevas.md

# Ver el último lead capturado
ls -t conocimiento/clientes/ | head -1
```
