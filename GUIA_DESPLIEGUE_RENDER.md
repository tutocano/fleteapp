# Guía de despliegue en Render (capa gratuita)

Esta guía lleva `fleteapp` de tu Mac a una URL pública en internet, sin costo,
usando [Render](https://render.com). El archivo `render.yaml` en la raíz del
proyecto ya define los 3 recursos necesarios (backend, frontend, base de
datos) para que Render los cree automáticamente con un solo "Blueprint".

Nadie más que tú puede crear tus cuentas ni subir tu código — los pasos
marcados con 👉 los ejecutas tú en tu Mac o en el navegador.

## Antes de empezar: qué esperar de la capa gratuita

- **Backend (Cloud Run... digo, Render Web Service, plan free):** "duerme"
  tras 15 minutos sin tráfico. La primera petición después de dormir tarda
  hasta ~50 segundos en responder (arranque en frío); las siguientes son
  normales. Perfecto para pruebas y demos, no para un uso constante 24/7.
- **Frontend (Render Static Site):** nunca duerme, siempre responde rápido.
- **Base de datos (Render Postgres, plan free):** **expira 30 días después de
  creada**, con 14 días de gracia para subirla a un plan pago antes de que se
  borre para siempre. Si al día 44 no has actualizado el plan, pierdes los
  datos. Para un ambiente de prueba esto suele ser aceptable — simplemente
  vuelve a correr el `seed.py` si se te vence y quieres seguir probando. Si
  necesitas que los datos persistan indefinidamente sin pagar, la alternativa
  es usar una base de datos externa gratuita que no expira (por ejemplo Neon)
  en vez de la Postgres de Render — avísame si quieres que preparemos esa
  variante.
- Ninguno de estos servicios te pedirá tarjeta de crédito para el plan
  gratuito.

## Paso 1 — Limpiar y preparar git en tu Mac

👉 En tu Terminal:

```bash
cd "/Users/TCano/Claude/Projects/CalculoCostosFleteProgramadoejecutado"
rm -f .git/*.lock .git/objects/*.lock 2>/dev/null
git status
```

Deberías ver `On branch master` y una lista de archivos modificados/nuevos
(son todos los cambios de v2 que hemos ido construyendo). Si `git status` da
error, dime exactamente qué dice.

Guarda todo en un commit nuevo (la v1.0 protegida sigue intacta como tag, no
se toca):

```bash
git add -A
git commit -m "v2: zonas con poligono, POR_KILOMETRO, tarifas por tipo de camion, listo para Render"
```

## Paso 2 — Crear el repositorio en GitHub

👉 Ve a [github.com/new](https://github.com/new), crea un repositorio (puede
ser privado), **sin** marcar "Initialize with README" (ya tienes uno). Copia
la URL que te da GitHub (algo como
`https://github.com/tutocano/fleteapp.git`).

👉 De vuelta en tu Terminal:

```bash
git remote add origin https://github.com/TU-USUARIO/TU-REPO.git
git push -u origin master
git push --tags
```

Si GitHub te pide iniciar sesión, sigue las instrucciones en pantalla (puede
abrir el navegador para autenticarte).

## Paso 3 — Crear cuenta en Render y desplegar el Blueprint

👉 Ve a [dashboard.render.com/register](https://dashboard.render.com/register)
y crea una cuenta (puedes usar tu cuenta de GitHub para entrar más rápido).

👉 En el dashboard: **New +** → **Blueprint**. Conecta tu cuenta de GitHub si
te lo pide, y selecciona el repositorio que acabas de crear.

👉 Render va a leer `render.yaml` automáticamente y te va a mostrar una vista
previa con 3 recursos: `fleteapp-backend`, `fleteapp-frontend` y
`fleteapp-db`. Revisa que los 3 digan plan **Free**, y dale **Apply**.

👉 Te va a pedir el valor de `GOOGLE_MAPS_API_KEY` (lo dejamos fuera del
código a propósito, por seguridad). Pega tu API key ahí.

Render va a construir y desplegar los 3 recursos. La primera vez tarda varios
minutos (construye la imagen Docker del backend y el build de Vite del
frontend).

## Paso 4 — Verificar las URLs y cargar los datos de ejemplo

Cuando termine, Render te muestra las URLs de cada servicio. Deberían ser:

- Backend: `https://fleteapp-backend.onrender.com`
- Frontend: `https://fleteapp-frontend.onrender.com`

**Si Render usó un nombre distinto** (porque "fleteapp-backend" o
"fleteapp-frontend" ya estaban tomados por otro usuario — los subdominios
`.onrender.com` son globales, no por cuenta), tienes que corregir 2 variables
de entorno manualmente:

1. En el servicio **fleteapp-frontend** → Environment → edita `VITE_API_URL`
   para que apunte a la URL real de tu backend + `/api` (ej.
   `https://fleteapp-backend-ab12.onrender.com/api`) → guarda y espera a que
   redespliegue.
2. En el servicio **fleteapp-backend** → Environment → edita
   `FRONTEND_ORIGINS` para que apunte a la URL real de tu frontend (ej.
   `https://fleteapp-frontend-xy34.onrender.com`, sin `/` al final) → guarda.

Con las URLs correctas, carga los datos de ejemplo:

👉 En el dashboard de Render, entra al servicio **fleteapp-backend** → pestaña
**Shell** → escribe:

```bash
python seed.py
```

Espera a que termine ("SEED COMPLETADO EXITOSAMENTE"). Como el backend "duerme"
en el plan gratis, si el Shell se desconecta por inactividad simplemente
vuelve a abrirlo.

## Paso 5 — Probar

Abre `https://fleteapp-frontend.onrender.com` (o la URL real que te dio
Render) en el navegador. La primera carga puede tardar ~30-50 segundos si el
backend estaba dormido — es normal, espera y recarga si hace falta.

## Actualizar la app despues de hacer cambios

Cada vez que quieras subir cambios nuevos (por ejemplo si seguimos
trabajando en el proyecto conmigo):

```bash
cd "/Users/TCano/Claude/Projects/CalculoCostosFleteProgramadoejecutado"
git add -A
git commit -m "descripcion del cambio"
git push
```

Render tiene `autoDeploy: true`, así que redespliega solo apenas detecta el
push — no hace falta hacer nada más en el dashboard.

## Si algo falla

Copia el mensaje de error exacto (del build log en Render, o del navegador) y
lo revisamos juntos.
