# Despliegue público para internet

La app ya está preparada para funcionar sin depender de tu PC local en un servidor público.

## 1) Backend en Render

1. Crear cuenta en https://render.com
2. Crear un servicio Web con el repositorio del proyecto.
3. Elegir el directorio `backend`.
4. Usar estas variables de entorno:

```
DJANGO_SECRET_KEY=tu-clave-super-secreta
DJANGO_DEBUG=False
ALLOWED_HOSTS=wayuuwaa-backend.onrender.com
CORS_ALLOWED_ORIGINS=https://tu-frontend.vercel.app
CSRF_TRUSTED_ORIGINS=https://tu-frontend.vercel.app
DATABASE_URL=postgres://usuario:password@host:5432/dbname
```

5. Comando de build:

```
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

6. Comando de inicio:

```
gunicorn config.wsgi --bind 0.0.0.0:$PORT
```

## 2) Frontend en Vercel

1. Crear cuenta en https://vercel.com
2. Importar el repositorio.
3. Seleccionar carpeta `frontend`.
4. Variables de entorno:

```
VITE_API_BASE_URL=https://tu-backend.onrender.com/api/v1
```

5. Hacer deploy.

## 3) Dominio opcional

Con Cloudflare o el DNS del proveedor, apunta un dominio personalizado a la URL pública del frontend y del backend si lo necesitas.

## 4) Resultado

Con esto la app queda accesible desde internet aunque tu PC esté apagada, siempre que el servicio desplegado siga activo en la nube.
