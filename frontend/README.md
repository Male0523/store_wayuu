# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  # Wayuuwaa Frontend

  Tienda web en React, TypeScript y Vite conectada a la API de Django. La interfaz consume el catálogo real, sus fotografías, autenticación por sesión y operaciones de compra del backend.

  ## Requisitos

  - Node.js 22 o superior y npm.
  - Backend Django iniciado en `http://localhost:8000` y MySQL disponible.
  - Origen de Vite (`http://localhost:5173`) permitido en `CORS_ALLOWED_ORIGINS` y `CSRF_TRUSTED_ORIGINS` del backend.

  ## Iniciar

  Desde esta carpeta:

  ```powershell
  npm install
  Copy-Item .env.example .env.local
  npm run dev
  ```

  Abre `http://localhost:5173`. Si el backend usa otra dirección, cambia `VITE_API_BASE_URL` en `.env.local`. Usa el mismo host en ambas direcciones: `localhost` con `localhost`, o `127.0.0.1` con `127.0.0.1`, para compartir cookies.

  ## Funciones

  - Catálogo con búsqueda, categorías, filtro por color, ordenamiento y detalle de producto.
  - Registro e inicio de sesión con cookies, CSRF y solicitudes de acceso para tejedoras.
  - Carrito de sesión, cantidades, checkout con dirección, ciudad y método de pago.
  - Historial de pedidos para clientes y asignación/avance de pedidos para tejedoras.
  - Gestión admin de inventario, publicación de productos y estados de pedidos; administración avanzada en Django Admin.
  - Diseñador de mantas con patrones, colores, tallas, cantidades y precio estimado.

  ## Validación

  ```powershell
  npm run lint
  npm run build
  ```

  Contrato de endpoints y flujo CSRF: [`../docs/API.md`](../docs/API.md).
    extends: [
