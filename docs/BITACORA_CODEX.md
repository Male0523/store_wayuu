# Bitácora Codex — Wayúu Store

## 2026-11-16 — Fase 0, checkout y continuidad

### Identificación y clonación

- Repositorio confirmado: `https://github.com/Male0523/store_wayuu` (`Male0523/store_wayuu`).
- Ruta nueva exclusiva: `C:\Users\oscar\Documents\Codex\2026-11-16\wayuu-store-fase0`.
- El primer intento dentro del sandbox falló con `Could not resolve host: github.com`. La clonación autorizada se completó al habilitar ejecución de red.
- Comando: `git clone --no-single-branch https://github.com/Male0523/store_wayuu.git C:\Users\oscar\Documents\Codex\2026-11-16\wayuu-store-fase0`.
- `git remote -v` confirmó `origin` para fetch y push en `https://github.com/Male0523/store_wayuu.git`.
- Checkout inicial: `main` en `6c120f70892170b97dd33006908ebca3ed30176e`, limpio.
- Se verificaron las diez ramas remotas y sus SHA; coinciden con la referencia anterior suministrada. `integration/consolidacion-wayuu` no existía como rama local ni remota en la revisión previa a crearla.
- Se creó `integration/consolidacion-wayuu` desde el `main` verificado. No se crearon ramas funcionales.

### Línea base

- Estructura identificada: `backend/` Django/DRF y `frontend/` React/TypeScript/Vite.
- Backend declara Django 5.2.17 y DRF 3.18.0; `backend/store/tests.py` contiene la suite Django. Las pruebas usan SQLite en memoria según `backend/config/test_settings.py`.
- Frontend declara React 19, TypeScript 6 y Vite 8; scripts disponibles: `dev`, `build`, `lint`, `preview`; no hay script de pruebas.
- `node --version` → `v24.22.1`. `npm` no se encontró. `frontend/node_modules` está ausente.
- `python --version` no pudo ejecutarse: el shim de WindowsApps no tiene acceso al ejecutable. No se pudo comprobar Django ni pytest.
- No se ejecutaron lint, compilación ni pruebas porque sus runtimes/dependencias no están disponibles. No se instalaron dependencias.
- Inspección estática limitada del grafo de migraciones: hay dos migraciones `0012` con dependencias paralelas desde `0011`; `0013` depende de `0012_persistent_customer_cart`; `0014_merge_20261104_0528` une la rama `0012_seed_supported_navigation_routes` y `0013`. No se ejecutó el cargador de migraciones ni se comprobó estado aplicado.
- `backend/db.sqlite3` está rastreado por Git. No se abrió ni se consultó. No se ejecutó ningún comando de DB ni migración.
- La configuración de ejemplo está presente (`backend/.env.example`, `frontend/.env.example`). No hay `.env` versionado.

### Hallazgos y límites

- El informe original de la auditoría anterior no se localizó. Se preserva el resumen de hallazgos proporcionado por el usuario.
- Los SHA de las diez ramas se mantienen iguales a la auditoría según la referencia del usuario y el cotejo del clon; no se repitió su análisis.
- Las pruebas de comportamiento sobre DB, imágenes, perfiles, carrito/favoritos, diseñador, delegaciones y cobertura por endpoint siguen pendientes.
- La consulta `git ls-remote --heads origin` desde el sandbox falló por DNS después del clon. Se usaron las refs remotas ya traídas en el clon. No se cambió remote ni repositorio.

### Cambios documentales preparados

- `docs/PLAN_MAESTRO_WAYUU.md`
- `docs/ARQUITECTURA_Y_HALLAZGOS.md`
- `docs/BITACORA_CODEX.md`

No se modificó código funcional, `main`, datos, migraciones ni configuración. Se revisó el contenido y el diff documental antes del commit.

### Commits

El hash del commit documental se informa en la entrega de Fase 0 y queda en el historial local de esta rama.

## 2026-11-16 — Sprint 1, recuperación de pedidos y trazabilidad

### Alcance y comparación

- Checkout: `C:\Users\oscar\Documents\Codex\2026-11-16\wayuu-store-fase0`; remote `origin`: `https://github.com/Male0523/store_wayuu.git`.
- Rama de trabajo `feature/pedidos-trazabilidad`, basada en `integration/consolidacion-wayuu` (`3727e0b375557c2aaf033bcac2111b87895dfe0f`). `main` permanece en `6c120f70892170b97dd33006908ebca3ed30176e`.
- Se comparó la rama histórica `codex/pedidos-trazabilidad-y-pruebas` (`b66698b7c38df6ee987fdfc1fe048d6376d02681`) con integration. Se recuperaron de forma selectiva los patrones de pedidos, pruebas y filtros útiles; no se fusionó la rama completa ni se incorporaron sus cambios ajenos al sprint.
- Se mantuvieron intactos el diseñador de mantas, fotografías, migraciones y modelos. No se ejecutaron operaciones de base de datos.

### Cambios

- Endpoint administrativo paginado `/api/v1/admin/orders/` con búsqueda por pedido, cliente, correo, producto y tejedora; filtros por estado, cliente y asignación/tejedora; acceso limitado a admin y superadmin.
- El frontend consulta el endpoint con parámetros de servidor y usa paginación remota; eliminó el filtrado exclusivo en memoria para la lista administrativa.
- Las transiciones administrativas se validan en servidor y bajo bloqueo transaccional. Se preserva el endpoint de aceptación de la tejedora para la asignación.
- La asignación y los cambios de estado registran actor, estado y/o tejedora en auditoría.
- La tejedora solo puede ver y actualizar pedidos asignados a su perfil. La gestión del permiso de diseños personalizados se exige únicamente cuando el pedido contiene un diseño personalizado; se preserva el aislamiento existente de diseños.
- Se añadieron pruebas para búsqueda, filtros, paginación, roles, transiciones, asignación/auditoría y permisos para pedidos con diseños personalizados. Las pruebas existentes de aislamiento de pedidos y diseños se mantienen.

### Verificación y límites

- `git diff --check integration/consolidacion-wayuu...HEAD`: correcto; el árbol quedó limpio después de cada commit previo a esta actualización.
- Las pruebas Django no pudieron ejecutarse: `python.exe` de WindowsApps falla al iniciar con «El sistema no tiene acceso al archivo».
- No se pudo ejecutar build/lint del frontend: `npm` no está instalado/disponible, Node es `v24.22.1` y falta `frontend/node_modules`.
- La suite de pruebas modificada está pendiente de ejecución en un entorno con Python/Django y dependencias del frontend. No se afirma que haya pasado.
- No se hicieron cambios en el código de migraciones ni se alteró `main`.

### Commits de implementación y pruebas

- `06a770acd9552ced788e5db83a8a6d278cfbdd8c` — `feat: add server-side administrative order tracking`.
- `083085f86da16b1e381a4353c87d57d1191cab25` — `test: cover order access and tracking boundaries`.
- El commit de esta actualización documental queda identificado por su SHA en el historial local y en el informe final.

### Revisión

- Se publicaron en `origin` `integration/consolidacion-wayuu` (`3727e0b375557c2aaf033bcac2111b87895dfe0f`) y `feature/pedidos-trazabilidad` para revisión.
- Pull Request abierto: `https://github.com/Male0523/store_wayuu/pull/4`, base `integration/consolidacion-wayuu`. GitHub reporta que se puede integrar; permanece abierto y sin fusionar.
