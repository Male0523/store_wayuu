# Despliegue de Wayúwaa en Render

Esta rama (codex/render-deploy-wayuuwaa) prepara el frontend React/Vite, el backend Django y PostgreSQL en Render. El despliegue conserva la lógica de la tienda y no modifica el RBAC.

## 1. Recursos que crea el Blueprint

El archivo render.yaml define:

| Recurso | Nombre | Configuración |
|---|---|---|
| Frontend | wayuuwaa-frontend | Sitio estático React/Vite |
| Backend | wayuuwaa-backend | Django + Gunicorn |
| Base de datos | wayuuwaa-db | PostgreSQL |

Las URLs previstas son:

- Frontend: https://wayuuwaa-frontend.onrender.com
- API: https://wayuuwaa-backend.onrender.com/api/v1

Render asigna el subdominio .onrender.com a cada servicio. Si el nombre no está disponible y Render asigna otro, hay que actualizar CORS_ALLOWED_ORIGINS, CSRF_TRUSTED_ORIGINS y VITE_API_BASE_URL con las URLs reales antes de probar el inicio de sesión.

## 2. Crear los servicios desde Render

1. Abre https://dashboard.render.com/.
2. Selecciona **New → Blueprint**.
3. Conecta el repositorio Male0523/store_wayuu.
4. Selecciona la rama codex/render-deploy-wayuuwaa.
5. Comprueba que el archivo Blueprint sea render.yaml.
6. Revisa los tres recursos y sus planes antes de confirmar **Apply**.
7. Espera a que el backend y el frontend terminen su primer despliegue.

No selecciones ni conectes la rama de trabajo original para este despliegue. No introduzcas contraseñas ni claves dentro de este archivo.

### Variables configuradas por el Blueprint

Backend:

- DJANGO_SECRET_KEY: generada por Render.
- DJANGO_DEBUG=False.
- DJANGO_ENV=production.
- DATABASE_URL: conexión interna a PostgreSQL.
- CORS y CSRF: origen exacto del frontend de Render.

Frontend:

- VITE_API_BASE_URL: URL pública de la API.

El comando de inicio del backend ejecuta migrate --noinput antes de Gunicorn. Así se crean/actualizan las tablas antes de iniciar la API. No se cargan fixtures automáticamente en cada despliegue.

## 3. Importar los datos de demostración

El archivo exportado desde SQLite debe permanecer fuera del repositorio:

/workspaces/wayuuwaa-data-pre-render.json

No lo subas a GitHub: contiene cuentas y hashes de contraseñas. La copia SQLite y el JSON deben mantenerse privados.

### Por qué existe un comando de importación especial

Las migraciones de Django crean registros iniciales de roles, permisos y navegación. Cargar directamente el JSON encima de esos registros podría provocar duplicados. El comando import_render_demo_data:

- Solo funciona si DJANGO_ENV=production y la conexión es PostgreSQL.
- Comprueba que el fixture esté fuera del repositorio.
- Se niega a importar si encuentra datos de negocio preexistentes.
- Sustituye únicamente los registros iniciales de RBAC creados por las migraciones.
- Carga el fixture dentro de una transacción; si falla, revierte los cambios.
- Verifica los conteos del respaldo: 13 usuarios, 4 roles, 13 asignaciones, 6 tejedoras, 4 clientes, 8 productos, 1 pedido, 3 detalles, 2 carritos, 31 permisos, 16 elementos de navegación y 36 eventos de auditoría. Si algún conteo no coincide, revierte la importación.

### Ejecutar la importación desde Codespaces

Render Free no ofrece Shell/SSH para el servicio gratuito. Para importar una sola vez, se usa la conexión externa de PostgreSQL desde Codespaces.

1. En Render, abre el recurso PostgreSQL wayuuwaa-db.
2. Busca **Connect** y copia la **External Database URL**. No uses la URL interna en Codespaces.
3. En Codespaces, abre una terminal y ejecuta:

~~~bash
cd /workspaces/store_wayuu/backend
source ../.venv/bin/activate

read -s -p "Pega la External Database URL de Render y pulsa Enter: " DATABASE_URL
echo
export DATABASE_URL
export DJANGO_ENV=production
export DJANGO_DEBUG=False

python manage.py import_render_demo_data --fixture /workspaces/wayuuwaa-data-pre-render.json

unset DATABASE_URL DJANGO_ENV DJANGO_DEBUG
~~~

No pegues la URL en el chat, en un archivo del repositorio ni en una captura. El comando necesita que backend/.env tenga DJANGO_SECRET_KEY configurada para cargar los ajustes de Django; no muestres ese archivo.

Si el comando termina correctamente, informa los conteos y prueba el inicio de sesión con las cuentas de demostración. No ejecutes el comando una segunda vez sobre una base ya poblada: está diseñado para una importación inicial en una base vacía.

## 4. Verificaciones funcionales después de importar

Realiza estas pruebas en la URL pública:

1. Iniciar sesión como superadministrador y comprobar roles, permisos y menú dinámico.
2. Iniciar sesión como administrador de tienda y comprobar las funciones comerciales autorizadas.
3. Iniciar sesión como tejedora y comprobar que solo ve sus productos y pedidos relacionados.
4. Iniciar sesión como cliente y comprobar catálogo, favoritos, carrito, pedidos y cancelación permitida.
5. Comprobar que las peticiones de API no devuelvan errores CORS/CSRF.
6. Crear un registro de prueba y comprobar que queda guardado al recargar.

No cambies las reglas RBAC para solucionar un problema de despliegue: primero revisa logs, variables de entorno, cookies, CORS, CSRF y conexión a PostgreSQL.

## 5. Imágenes y archivos

La revisión previa no encontró archivos dentro de backend/media. Los archivos locales de un servicio web gratuito de Render son efímeros; no guardes allí imágenes que deban persistir. Las imágenes que estén referenciadas mediante URLs externas pueden seguir mostrándose si esas URLs continúan disponibles.

## 6. Límites del plan gratuito

Esta publicación es una demo, no una tienda de producción:

- Los servicios web gratuitos se duermen tras 15 minutos sin tráfico y pueden tardar alrededor de un minuto en despertar.
- El sistema de archivos del backend gratuito es efímero.
- PostgreSQL gratuito tiene límite de 1 GB y expira a los 30 días. Después hay un período de gracia de 14 días para actualizarlo antes de su eliminación.
- No hay copias de seguridad administradas para PostgreSQL gratuito.

Conserva la copia SQLite y el JSON fuera del repositorio. Antes de que venza PostgreSQL, exporta los datos o actualiza la base a un plan persistente.

Documentación oficial: https://render.com/docs/free
