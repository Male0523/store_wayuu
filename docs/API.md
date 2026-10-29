# API del backend

Base local: `http://127.0.0.1:8000/api/v1/`. La API usa JSON, sesiones Django y cookies; no usa tokens bearer. Las respuestas de precios son cadenas decimales en COP.

## Integración desde el frontend

Configura la URL base en el frontend. En desarrollo, agrega el origen del frontend a `CORS_ALLOWED_ORIGINS` y `CSRF_TRUSTED_ORIGINS` en `backend/.env`. Los valores iniciales permiten Vite (`5173`) y React (`3000`) en `localhost` o `127.0.0.1`.

Antes de enviar un `POST`, `PATCH` o `DELETE`, solicita `GET /csrf/`. Conserva las cookies y envía el valor de `csrftoken` en el encabezado `X-CSRFToken`:

```js
const API_URL = 'http://localhost:8000/api/v1';

await fetch(`${API_URL}/csrf/`, { credentials: 'include' });
const csrfToken = document.cookie
  .split('; ')
  .find((cookie) => cookie.startsWith('csrftoken='))
  ?.split('=')[1];

const response = await fetch(`${API_URL}/auth/login/`, {
  method: 'POST',
  credentials: 'include',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrfToken,
  },
  body: JSON.stringify({ username: 'usuario', password: 'contraseña' }),
});
```

Mantén `credentials: 'include'` en todas las llamadas para conservar sesión y carrito. Usa el mismo nombre de host en frontend y API (`localhost` en ambos o `127.0.0.1` en ambos); cambiar entre esos nombres puede bloquear cookies de sesión. En producción usa HTTPS y define explícitamente los dominios permitidos; no uses comodines de CORS con credenciales.

## Endpoints

| Método | Ruta | Acceso | Uso |
| --- | --- | --- | --- |
| GET | `/` | Público | Estado de la API |
| GET | `/csrf/` | Público | Emitir cookie CSRF |
| GET | `/categories/` | Público | Categorías con productos publicados |
| GET | `/products/` | Público | Catálogo paginado |
| GET | `/products/{id}/` | Público | Detalle de producto publicado |
| POST | `/auth/register/` | Público + CSRF | Crear cliente e iniciar sesión |
| POST | `/auth/register/craftswoman/` | Público + CSRF | Solicitar cuenta de tejedora inactiva |
| POST | `/auth/login/` | Público + CSRF | Iniciar sesión |
| POST | `/auth/logout/` | Sesión + CSRF | Cerrar sesión |
| GET | `/auth/me/` | Sesión | Usuario y rol actuales |
| GET, PATCH | `/profile/` | Cliente | Consultar o actualizar perfil |
| GET | `/cart/` | Cliente | Ver carrito, cantidades y total |
| POST | `/cart/items/` | Cliente | Agregar `{ "product_id": 1, "quantity": 2 }` |
| PATCH | `/cart/items/{product_id}/` | Cliente | Cambiar `{ "quantity": 3 }` |
| DELETE | `/cart/items/{product_id}/` | Cliente | Quitar un producto |
| POST | `/checkout/` | Cliente | Crear pedido desde el carrito |
| GET | `/orders/` | Sesión | Historial propio; pedidos asignados para tejedoras |
| GET | `/orders/{id}/` | Propietario, tejedora asignada o admin | Detalle del pedido |
| GET, POST | `/designs/` | Cliente | Listar o solicitar diseño personalizado |
| GET | `/craftswoman/dashboard/` | Tejedora | Pedidos disponibles, asignados y diseños |
| POST | `/craftswoman/orders/{id}/accept/` | Tejedora activa | Aceptar pedido disponible |
| PATCH | `/craftswoman/orders/{id}/status/` | Tejedora asignada | Actualizar estado del pedido |
| PATCH | `/craftswoman/designs/{id}/status/` | Tejedora asignada | Actualizar estado del diseño |
| GET, POST | `/admin/categories/` | Admin (`is_staff`) | Listar o crear categorías |
| PATCH | `/admin/categories/{id}/` | Admin (`is_staff`) | Activar o desactivar categorías |
| GET, POST | `/admin/products/` | Admin (`is_staff`) | Listar o crear productos |
| PATCH | `/admin/products/{id}/` | Admin (`is_staff`) | Editar precio, stock y publicación |
| PATCH | `/admin/orders/{id}/status/` | Admin (`is_staff`) | Actualizar estado de un pedido |

## Catálogo y paginación

`GET /products/?search=manta&category=2&color=rojo&size=M&available=true&ordering=price&page=1&page_size=20`

Filtros opcionales: `search`, `category`, `color`, `size` y `available=true`. Ordenamientos permitidos: `price`, `-price`, `name` y `-created_at`. `page_size` acepta hasta 100.

La respuesta paginada tiene `count`, `next`, `previous` y `results`. Cada producto incluye categoría y artesana como objetos, precio, existencias, imagen y tiempo de elaboración.

## Cuenta y roles

Registro de cliente:

```json
{
  "name": "Nombre completo",
  "username": "nombre.usuario",
  "email": "correo@example.com",
  "password": "una-clave-segura",
  "phone": "3001234567"
}
```

El registro de tejedora usa los mismos campos y admite además `community` y `region`; la cuenta queda pendiente de activación administrativa. `/auth/me/` devuelve `role` como `customer`, `craftswoman` o `admin`.

## Compra y diseños

Checkout acepta `address`, `city`, `payment_method` (`contact`, `nequi`, `daviplata`, `bancolombia`, `whatsapp`) y `notes`. El precio se toma del producto en el servidor, el stock se descuenta dentro de una transacción y el carrito se vacía solo si el pedido se crea correctamente.

Diseño personalizado acepta `pattern` (`rombos`, `olas`, `estrellas`, `caminos`), `base_color`, `accent_color_one`, `accent_color_two` en hexadecimal `#RRGGBB`, `size` (`S`, `M`, `L`, `XL`), `quantity` y `notes`. La API calcula el precio, crea el diseño y lo agrega al carrito.

Los estados de pedido son `pending`, `accepted`, `weaving`, `completed`, `paid`, `preparing`, `shipped`, `delivered` y `cancelled`. Las tejedoras solo pueden ejecutar las transiciones de tejido admitidas por el servidor.

## Administración

Las rutas administrativas requieren una cuenta autenticada con `is_staff`. Las categorías pueden listarse, crearse y activarse/desactivarse. Para crear productos, envía `sku`, `name`, `category` (id), `price` y `stock`; también acepta `size`, `region`, `image_url`, `active` y `made_to_order`. El listado incluye productos publicados y borradores. La edición parcial permite actualizar precio, existencias y publicación. La administración puede cambiar el estado de un pedido usando los estados listados arriba. Para gestionar usuarios, artesanas y formularios avanzados, continúa disponible `/admin/` de Django.

## Errores

La API usa códigos HTTP estándar: `400` para datos inválidos o falta de stock, `401/403` para autenticación/permisos, `404` para recursos inexistentes o ajenos y `405` para métodos no admitidos. Los detalles de validación se devuelven como JSON. `GET /api/v1/` debe responder `{"status":"ok","api_version":"1"}`.

## Arranque local

Desde `backend/`, instala `requirements.txt`, copia `.env.example` a `.env`, completa `DJANGO_SECRET_KEY` y las credenciales MySQL, y ejecuta:

```powershell
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

La configuración activa actualmente requiere MySQL. El administrador existente está disponible en `/admin/`.