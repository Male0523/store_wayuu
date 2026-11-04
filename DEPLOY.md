# Publicación de Wayuuwaa en Render

Este documento corresponde a los servicios existentes del proyecto. No aplicar el `render.yaml` actual como Blueprint sobre esta infraestructura: ese archivo define nombres y una base PostgreSQL diferentes, lo que podría crear recursos duplicados.

## 1. Backend existente

Servicio: `wayuu-store-backend`  
Repositorio: `Male0523/store_wayuu`  
Rama: `main`  
Root Directory: `backend`  
URL: https://wayuu-store-backend.onrender.com

Configuración:

- Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- Start Command: `python manage.py migrate --noinput && gunicorn config.wsgi --log-file - --bind 0.0.0.0:$PORT`
- Auto-Deploy: On Commit

Variables requeridas:

- `DJANGO_ENV=production`
- `DJANGO_DEBUG=False`
- `DJANGO_SECRET_KEY`: valor secreto configurado en Render.
- `DATABASE_URL`: conexión PostgreSQL de Render.
- `ALLOWED_HOSTS=wayuu-store-backend.onrender.com`
- `CORS_ALLOWED_ORIGINS=https://wayuu-store-frontend.onrender.com`
- `CSRF_TRUSTED_ORIGINS=https://wayuu-store-frontend.onrender.com`

El comando de inicio aplica las migraciones antes de iniciar Gunicorn. No ejecutes `migrate` contra otra base de datos por accidente.

## 2. Frontend React/Vite

Comprueba si ya existe el Static Site `wayuu-store-frontend`. Si no existe, créalo desde **New → Static Site** con:

- Repositorio: `Male0523/store_wayuu`
- Rama: `main`
- Root Directory: `frontend`
- Build Command: `npm ci && npm run build`
- Publish Directory: `dist`
- Auto-Deploy: On Commit

El archivo versionado `frontend/.env.production` define:

```env
VITE_API_BASE_URL=https://wayuu-store-backend.onrender.com/api/v1
```

Vite lo carga al ejecutar el build de producción. Si se define `VITE_API_BASE_URL` directamente en Render, ese valor prevalece y debe coincidir con la URL anterior.

El dominio público esperado para el Static Site es https://wayuu-store-frontend.onrender.com. Confirma la URL que Render asigne al crear el servicio y mantén el mismo origen en las variables CORS y CSRF del backend.

## 3. Importar los datos locales una sola vez

El respaldo final debe permanecer fuera del repositorio:

`/workspaces/wayuuwaa-data-final.json`

No subas este JSON ni una copia de SQLite a GitHub: contienen datos de usuarios y hashes de contraseñas.

El comando `import_render_demo_data`:

- Solo permite PostgreSQL con `DJANGO_ENV=production`.
- Rechaza archivos de fixture dentro del repositorio.
- Ejecuta las migraciones.
- Se niega a importar si ya hay datos de negocio en la base destino.
- Sustituye en una transacción los registros iniciales de roles, asignaciones, permisos y navegación.
- Verifica el respaldo final: 13 usuarios, 4 roles, 13 asignaciones, 6 tejedoras, 4 clientes, 1 categoría, 8 productos, 1 pedido, 3 detalles de pedido, 4 carritos, 31 permisos de rol, 16 elementos de navegación y 37 eventos de auditoría.

Antes de importar, confirma en Render que se está usando la base PostgreSQL correcta y que no hay usuarios, productos, pedidos u otros datos de negocio que deban conservarse. El comando está diseñado para una base destino vacía; no lo ejecutes sobre una base poblada.

Para importar desde Codespaces, abre una terminal:

```bash
cd /workspaces/store_wayuu/backend
source ../.venv/bin/activate

read -s -p "Pega la External Database URL de Render y pulsa Enter: " DATABASE_URL
echo
export DATABASE_URL
export DJANGO_ENV=production
export DJANGO_DEBUG=False

python manage.py import_render_demo_data --fixture /workspaces/wayuuwaa-data-final.json

unset DATABASE_URL DJANGO_ENV DJANGO_DEBUG
```

Usa la **External Database URL** del recurso PostgreSQL de Render desde Codespaces. No la compartas por chat, no la guardes en el repositorio y no la pegues en capturas. El entorno local debe tener una `DJANGO_SECRET_KEY` disponible para que Django cargue sus ajustes.

Si la importación informa que la base ya contiene datos, detente. No borres tablas ni recrees la base: primero revisa qué datos hay y decide cómo conservarlos.

## 4. Comprobaciones tras desplegar

API: abre https://wayuu-store-backend.onrender.com/api/v1/ y comprueba que responda con el estado de salud.

Frontend: abre https://wayuu-store-frontend.onrender.com y confirma que carga la aplicación.

Después prueba:

1. Inicio y cierre de sesión para superadministrador, administrador de tienda, tejedora y cliente.
2. Catálogo, detalle de producto y favoritos.
3. Persistencia del carrito al recargar.
4. Creación, consulta y estados de pedidos.
5. Productos y pedidos propios de las tejedoras.
6. Menú dinámico y protección real de permisos en el backend.
7. Ausencia de errores CORS y CSRF en la consola del navegador.

Si el backend gratuito está inactivo, la primera solicitud puede tardar en despertar. Un error HTTP 503 persistente requiere revisar Events y Logs del servicio en Render.

## 5. Persistencia y límites

Los servicios gratuitos pueden suspenderse por inactividad y el almacenamiento local del servicio web es efímero. No guardes allí archivos que deban persistir. La base PostgreSQL gratuita tiene límites y vencimiento; conserva el respaldo fuera del repositorio y verifica la política vigente de Render antes de usarla como almacén permanente.
