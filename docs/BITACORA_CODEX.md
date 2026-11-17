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

## 2026-11-16 — Revisión correctiva del Pull Request #4

### Correcciones preparadas

- El filtro administrativo obtiene nombres e IDs reales del endpoint protegido `/api/v1/admin/orders/filters/`; la UI separa asignación (`all`, `assigned`, `unassigned`) de tejedora seleccionada. Cambiar cualquier filtro vuelve a página 1; las consultas siguen paginadas en servidor y el backend rechaza combinaciones incompatibles.
- `/api/v1/admin/orders/summary/` devuelve conteos agregados del conjunto completo de pedidos y los tres pedidos recientes. El tablero ya no deduce cifras de una página de 100 pedidos. “Activos” conserva el conjunto previo del tablero: accepted, weaving, preparing y shipped.
- `backend/store/order_workflow.py` contiene la única matriz de transiciones. API, rutas HTML, selector administrativo y panel de tejedora se basan en ella. El servidor valida cada cambio; la API devuelve `allowed_statuses` para que el frontend ofrezca solo acciones habilitadas.
- La ruta HTML conserva `orders.view`/`orders.change`, ownership exclusivo con consulta limitada a la tejedora activa, permiso `designs.change` solo para pedidos con diseños, bloqueos transaccionales y auditoría. El dashboard HTML ahora trata `designs.view` como permiso independiente, igual que la API.
- Se documentó la matriz y las reglas existentes en `docs/FLUJO_ESTADOS_PEDIDOS.md`, incluyendo las decisiones comerciales que no están especificadas por el código actual.

### Matriz y decisiones aún abiertas

- Los estados iniciales son `pending`; la aceptación asigna pedido y tejedora en una acción exclusiva.
- La tejedora puede accepted → weaving, weaving → accepted y weaving → completed. Administración conserva las transiciones documentadas, incluida la preparación desde estados anteriores y el pago desde completed.
- El código no establece pago obligatorio antes de preparar/enviar, cancelación por cliente/tejedora, ni semántica comercial del retorno weaving → accepted. No se inventaron dichas reglas; quedan señaladas en la matriz documentada.

### Verificación real

- Python 3.13 y las dependencias de `backend/requirements.txt` se instalaron en `backend/.venv`; Node 24.20 extraído en `work/` se usó con `npm ci`. Se retiró el runtime temporal `work/` al terminar. `backend/.venv` y `frontend/node_modules` están ignorados por Git.
- Suite backend completa `manage.py test store.tests --settings=config.test_settings`: 97 pruebas ejecutadas; 96 pasan y 1 falla en `test_seed_rbac_users_dry_run_create_profiles_and_remain_idempotent` porque Windows devuelve modo `438` (`0666`) donde la prueba exige `384` (`0600`). Es una comprobación de permisos POSIX incompatible con los modos de archivo de Windows; no afecta la DB de la aplicación ni las pruebas de pedidos.
- Suite dirigida de pedidos, permisos, filtros, paginación, conteos, matriz de estados, aislamiento y rutas API/HTML: 13 pruebas ejecutadas, todas pasan.
- `npm run build` (`tsc -b && vite build`): pasa, incluyendo TypeScript y compilación de producción.
- `npm run lint`: falla con 7 errores y 5 warnings de reglas React Hooks en `CustomerPanel.tsx` y `ShopApp.tsx` (efectos de perfil/sesión y navegación preexistentes, fuera de los efectos de consulta añadidos). No existe script de pruebas frontend en `frontend/package.json`.
- `npm ci` reportó 9 vulnerabilidades moderadas en el árbol de dependencias; no se ejecutó `npm audit fix` ni se cambiaron versiones.
- `git diff --check`: pasa. No se modificaron migraciones, `main`, imágenes ni el diseñador de mantas.

### Commits de revisión

- `9f8f760da11559cf8db807ce4829ed89150bb964` — `fix: align order workflows and admin filters`.
- `e1b4b51061767913f9d31f96ddc51cac4b2b774c` — `feat: use authorized order filters and summary`.
- `38251d0535c59b3398b17d968aa91e26ce6fe450` — `test: cover order workflow parity and summary`.
- Los commits publicados no se reescriben y no se hará force push.

### Estado del PR

- El PR #4 continúa abierto hacia `integration/consolidacion-wayuu`. No se cerró ni fusionó. Las correcciones se publicarán como commits adicionales cuando queden registrados.

## 2026-11-17 — Cierre técnico del Sprint 1 / PR #4

### Cambios y decisiones

- Se revisó `docs/FLUJO_ESTADOS_PEDIDOS.md`. La matriz implementada y las decisiones comerciales pendientes siguen explícitas; no se agregaron reglas nuevas. Continúan pendientes la obligatoriedad del pago antes de preparar/enviar, la posibilidad de cancelación por cliente o tejedora, el sentido comercial de `weaving → accepted`, quién puede cancelar y la definición de pedido “activo”.
- `backend/store/tests.py`: la prueba de credenciales ahora comprueba modo `0600` en POSIX. En Windows invoca `icacls.exe` y rechaza ACL que incluyan Everyone, Authenticated Users o BUILTIN Users (incluidas sus variantes de SID/localización). El contenido e idempotencia del archivo siguen verificándose.
- No se modificó frontend: el `npm run lint` actual y el análisis de referencia muestran los mismos diagnósticos; ninguno corresponde a los filtros de pedidos añadidos por Sprint 1.

### Comandos y resultados exactos

- Desde `backend`: `$env:DJANGO_SECRET_KEY='test-only-wayuu-local-secret'; .\\.venv\\Scripts\\python.exe manage.py test` — **OK**, 97 pruebas, 0 fallos; comprobación del sistema sin incidencias. Django mostró el warning existente de que no hay directorio `backend/staticfiles/`.
- Desde `backend`: `$env:DJANGO_SECRET_KEY='test-only-wayuu-local-secret'; .\\.venv\\Scripts\\python.exe manage.py test store.tests.StoreAPITests.test_seed_rbac_users_dry_run_create_profiles_and_remain_idempotent` — **OK**, 1 prueba, 0 fallos.
- Desde `frontend`: `npm run build` — **OK**, `tsc -b` y `vite build` finalizaron; Vite transformó 1946 módulos.
- Desde `frontend`: `npm run lint` — **falló**, 7 errores y 5 warnings. `CustomerPanel.tsx`: 2 errores `react-hooks/set-state-in-effect` y 1 warning `react-hooks/exhaustive-deps`. `ShopApp.tsx`: 5 errores `react-hooks/set-state-in-effect` y 4 warnings `react-hooks/exhaustive-deps`.
- Referencia: se extrajo `integration/consolidacion-wayuu:frontend/src/ShopApp.tsx` a un archivo temporal ignorado y se ejecutó ESLint con formato JSON: 5 errores y 4 warnings, las mismas reglas. `CustomerPanel.tsx` coincide con la rama de integración (`git diff --quiet integration/consolidacion-wayuu -- frontend/src/CustomerPanel.tsx`, código 0). Por tanto, los 12 hallazgos del lint son preexistentes; no se atribuye ninguno al sprint. El archivo de comparación se eliminó.
- Desde la raíz del repositorio: `git diff --check` — **OK**, sin errores de whitespace.
- Una primera ejecución de la suite, antes de cambiar la verificación Windows a `icacls.exe`, falló porque `Get-Acl` no pudo cargar el módulo de seguridad PowerShell en este entorno. Se reemplazó esa vía, la prueba dirigida pasó y la suite completa se repitió con éxito.

### Alcance y estado

- No se tocaron `main`, migraciones, funcionalidades ajenas a pedidos, el diseñador de mantas, ni datos de aplicación. Las pruebas usaron la base temporal de Django.
- No se abordaron los diagnósticos heredados de lint para respetar el alcance de este cierre (sin refactor general). No hay script de pruebas frontend declarado en `frontend/package.json`.
- Pendiente de revisión humana: decidir las reglas comerciales listadas, resolver los hallazgos de lint preexistentes en un trabajo separado y revisar el PR.
- El PR #4 sigue abierto y sin fusionar; esta actualización no lo cerró ni lo integró.
- Commits locales en `feature/pedidos-trazabilidad`: `6febd5d2c8450d842469df0d9bc5ac2f710a20c4` (`test: check credential permissions across platforms`) y `45e143ccae0bad617fca6b5cab843f06b5836215` (`docs: record sprint 1 technical closeout`).
- Publicación pendiente: `git push origin feature/pedidos-trazabilidad` falló con `Could not resolve host: github.com`. GitHub confirma que el PR sigue abierto y sin fusionar, con head remoto `d76321d707c459635d6584cf714d0323320cba32`; los commits de cierre aún no aparecen en el PR. No se hizo force push.

## 2026-11-17 — Sprint 2: RBAC dinámico configurable

### Preparación y cambios

- Se verificó `Male0523/store_wayuu`, remote `origin https://github.com/Male0523/store_wayuu.git` y la rama base local `feature/pedidos-trazabilidad`. El árbol estaba limpio antes de crear `feature/rbac-configurable`; no se cambió de rama con modificaciones pendientes.
- `AccessRole.code` acepta códigos persistentes dinámicos. Los roles se pueden crear, editar, activar y desactivar; sus asignaciones y grants históricos se conservan al desactivarlos. El rol raíz y los roles base no se eliminan.
- Se añadieron las migraciones `store.0015_rbacaction_rbacresource_alter_accessrole_code_and_more` y `store.0016_rbacrecordscopegrant`: catálogos independientes de recursos/acciones/capacidades, grants `ALLOW`/`DENY` por rol/usuario y ámbitos de registros separados por rol/usuario. Las migraciones agregan tablas/catálogos y amplían el campo del código de rol; no borran roles, usuarios ni grants anteriores, que se mantienen como fallback compatible.
- La matriz inicial incluye CRUD expresado como `view/create/edit/delete` y operaciones especializadas solo donde existen operaciones reales. Las pantallas se asignan a roles por navegación, sin grants de datos. Los endpoints administrativos nuevos permiten administrar roles, recursos, acciones y capacidades; el panel superadmin incluye formularios y matrices dinámicas.
- El backend conserva la autoridad: API y vistas HTML validan permisos. Los pedidos/diseños de cliente y tejedora conservan sus filtros de propietario/asignación. Las concesiones históricas de consulta de pedidos no abren las listas administrativas. Se revocan también los grants individuales que un administrador delegado hubiera emitido al perder su rol.
- La interfaz genera controles desde las capacidades efectivas; publicación, cancelación, aprobación y asignación ya no se presentan como si fueran el permiso genérico `edit` cuando existe una acción especializada.
- Se documentó precedencia, compatibilidad, límites y decisiones pendientes en `docs/FLUJO_RBAC.md`.
- No se tocó `main`, no se publicó ni fusionó ningún cambio, no se modificó el diseñador de mantas ni se ejecutaron migraciones contra la base SQLite del proyecto.

### Decisiones y límites de seguridad

- Precedencia implementada: cualquier `DENY` dinámico del usuario o rol prevalece; si no hay denegación, un `ALLOW` individual prevalece sobre el rol; después se considera el `ALLOW` del rol y, por último, la compatibilidad histórica. Está probado, pero requiere aprobación del responsable de seguridad.
- El superadministrador es raíz global, no recibe grants individuales y no puede ser limitado por la matriz ordinaria. No puede desactivarse el rol raíz ni retirar al último superadministrador activo.
- Los ámbitos de registros son independientes de las acciones y configurables por rol/usuario: `none` o `all`; el valor ausente hereda. Para colecciones administrativas privadas (`orders`, `designs`, `products`, `customers`, `users`, `craftswomen`) se requieren permiso de acción y ámbito efectivo `all`. Los roles personalizados parten sin ámbito; clientes y tejedoras conservan los filtros existentes de registros propios/asignados.
- Aún no se ofrecen ámbitos personalizados `own`/`assigned`; para agregarlos hay que definir y probar las relaciones específicas de cada modelo. La asignación `all` para roles personalizados requiere aprobación del responsable de seguridad.
- Se mantiene un fallback temporal: permisos históricos `edit` pueden habilitar `approve`, `publish`, `unpublish`, `assign` y `cancel` si la capacidad dinámica especializada no tiene grant explícito. `reject` y `export` están en catálogo pero no se vincularon a endpoints que hoy no existen. Ambos puntos requieren decisión/aprobación y están explicados en el flujo RBAC.
- Roles cliente/tejedora conservan restricciones de perfil para operaciones de persona. No se implementan delegaciones administrativas avanzadas; la delegación heredada sigue limitada a los controles ya existentes.

### Verificaciones ejecutadas

- Desde `backend`: `$env:DJANGO_SECRET_KEY='test-only-wayuu-local-secret'; .\\.venv\\Scripts\\python.exe manage.py test` — **OK**, 100 pruebas, 0 fallos; comprobación de sistema sin incidencias. Django emitió el warning preexistente de directorio `backend/staticfiles/` ausente.
- Pruebas dirigidas de creación/edición/desactivación de roles, catálogo extensible, precedencia, separación de vista/datos, aislamiento por perfil y delegaciones — **OK**, 4 pruebas en la última ejecución dirigida.
- Desde `backend`: `$env:DJANGO_SECRET_KEY='test-only-wayuu-local-secret'; .\\.venv\\Scripts\\python.exe manage.py makemigrations --check --dry-run` — **OK**, `No changes detected`.
- Desde `frontend`: `npm run build` — **OK**, `tsc -b` y Vite; 1946 módulos transformados.
- Desde `frontend`: `npm run lint` — **falló**, 7 errores y 5 warnings de `react-hooks/set-state-in-effect` y `react-hooks/exhaustive-deps`. Coinciden con los hallazgos preexistentes registrados en el cierre del Sprint 1; el warning adicional que apareció durante la implementación se corrigió y no permanece en el resultado final. No se amplió el alcance con un refactor de lint ajeno al RBAC.
- Desde `frontend`: `npm run` confirmó que no hay script de pruebas frontend (`dev`, `build`, `lint`, `preview`).
- Desde la raíz: `git diff --check` — **OK**, sin errores de whitespace.

### Commits y estado

- `0bb0934ef97acd0e3f82b1f3e7bce4b20fa46d76` — `feat: add configurable RBAC grants and catalogs`.
- `e2fc58529270c0a29c3844d648fd4e2f759423d1` — `feat: enforce dynamic RBAC in APIs and navigation`.
- `b08d5c1ecd343f5c1200da28895d61cc19de971c` — `feat: add dynamic RBAC administration controls`.
- `7e8207cfdc4a286e9931aafe83a0de914753292e` — `test: cover configurable RBAC and access boundaries`.
- `ce5e4216b71e2300f13e5a1bca767c8608f73c01` — `docs: record dynamic RBAC policy and sprint results`.
- `9a11bd90a733a3387b6660bbc04a41d4014f8b58` — `feat: add configurable record scopes to RBAC`.
- `2da355a6593cdfc3b76adf1e55253c14b08c9297` — `feat: manage RBAC record scopes in the admin panel`.
- `e964f1c88cd399c4c757cfdc057782f4a6bf31bb` — `test: verify record scope and privilege boundaries`.
- `ae056318926a84037c6ab37afbeb648b2e1770d9` — `docs: record configurable record scope policy`.
- Rama local: `feature/rbac-configurable`. No se hizo push, merge, despliegue ni modificación de ramas remotas.

## 2026-11-17 — Sprint 3: carrito, favoritos y checkout

### Preparación y cambios

- Se verificó el checkout local del repositorio `Male0523/store_wayuu`, remoto `origin https://github.com/Male0523/store_wayuu.git`, rama limpia `feature/rbac-configurable` en el estado `1af0d8ffba339d1219eaf9b22d809f34edf788c9`; se creó `feature/carrito-favoritos-checkout` desde esa base. No se cambió `main` ni se publicaron ramas.
- Se añadió `CustomerFavorite` con unicidad por cliente/producto y la migración aditiva `store.0017_customerfavorite`. La migración registra el recurso RBAC `favorites` y concede al rol cliente acciones de consulta, alta y retiro sin borrar ni reescribir datos existentes.
- El carrito autenticado usa `CustomerCartItem` como fuente persistente para API y vistas HTML. El merge de carritos de sesión agrega cantidades una sola vez, no trunca cantidades según el stock y retiene en sesión entradas no migrables para evitar perderlas silenciosamente. Las líneas disponibles y el estado de disponibilidad se calculan con el inventario actual.
- Altas y cambios de cantidad comprueban producto activo, límites y stock. Los diseños personalizados continúan restringidos a su cliente propietario y a cantidad uno. El diseñador no se modificó; su producto ahora se guarda en el mismo carrito persistente.
- El checkout API y HTML bloquean el cliente/carrito/productos, validan propietario, estado y stock, crean pedido e ítems, descuentan inventario y limpian el carrito dentro de una transacción. Un reenvío secuencial encuentra el carrito vacío y no crea un segundo pedido. Los errores de disponibilidad conservan el carrito.
- Se agregaron endpoints de favoritos con acceso por cliente, alta idempotente y aislamiento entre clientes. El frontend lee y modifica favoritos en backend; los favoritos heredados de `localStorage` se importan al iniciar sesión. Catálogo, detalle y favoritos usan un único estado de cuenta. El carrito informa y bloquea continuar cuando una línea ya no está disponible.
- Los estados, cobro, descuentos y reservas no se alteraron. No se ejecutaron migraciones sobre la base de datos local/de producción; `makemigrations --check` solo comparó el estado del modelo.

### Decisiones comerciales pendientes

- El sistema sigue descontando inventario al confirmar el pedido, como ya hacía el flujo existente. No hay reserva de stock durante la navegación/carrito. El negocio debe definir si requiere reservas y su vencimiento.
- `payment_method` continúa registrándose como dato del pedido; no se realizan cobros. Falta definir y aprobar integración, confirmación de pago, reembolsos y reglas de cambio de estado asociadas al pago.
- No se implementaron descuentos ni promociones, ni reglas de precio distintas a guardar el precio actual del producto al crear el ítem del pedido.
- Las entradas de carrito de sesión con ID malformado, producto eliminado o diseño ajeno se conservan en la sesión, pero el catálogo del carrito no tiene una interfaz para resolver esas entradas heredadas. Requiere una decisión sobre limpieza/manual review si se presentan en producción.

### Verificaciones ejecutadas

- Desde `backend`: `$env:DJANGO_SECRET_KEY='sprint3-test-only-local-key'; $env:DB_ENGINE='sqlite'; .\\.venv\\Scripts\\python.exe manage.py test` — **OK**, 106 pruebas, 0 fallos, 0 errores; Django reportó `System check identified no issues`. Se emitió el warning preexistente de `backend/staticfiles/` ausente y la salida informativa de la prueba de auditoría de roles (`role-audit-candidate`).
- Desde `backend`: `manage.py makemigrations --check --dry-run` con la misma clave temporal — **OK**, `No changes detected`.
- Pruebas dirigidas — **OK**, 9 pruebas: compra y descuento de stock, rechazo tras cambio de inventario, reenvío duplicado, merge único del carrito de sesión, conservación de entradas heredadas no migrables, persistencia/aislamiento de favoritos, rechazo de producto inactivo/inexistente, matriz RBAC y checkout HTML con perfil autenticado.
- Desde `frontend`: `npm run build` — **OK**, TypeScript y Vite, 1946 módulos transformados.
- Desde `frontend`: `npm run lint` — **falló**, 6 errores y 5 warnings. La referencia previa era 7 errores y 5 warnings. Los diagnósticos actuales permanecen en `CustomerPanel.tsx` y `ShopApp.tsx`, en reglas de estado síncrono dentro de efectos y dependencias de hooks; el cambio de favoritos eliminó uno de los errores previos. No aparecieron errores nuevos en la lógica de API o componentes de Sprint 3.
- Desde `frontend`: `npm run` confirmó que no hay script de pruebas frontend (`dev`, `build`, `lint`, `preview`).
- `git diff --check` — **OK**, sin problemas de whitespace.

### Commits y estado

- `97fa0ca0e9af384919307db95ba1839f6c6a94d9` — `feat: persist customer carts and favorites`.
- `c96a6307ee452e95515883940a74937d89798a25` — `feat: sync account favorites and cart availability`.
- No se integraron ramas ni se realizó push, PR o despliegue. La rama de trabajo es `feature/carrito-favoritos-checkout`.

## 2026-11-17 — Sprint 4: catálogo, productos y categorías

### Preparación y cambios

- Se verificó que `feature/carrito-favoritos-checkout` estaba limpia en `d6f402c05ba5c61ce6b6472cc765c99c2abf5649`, con `origin https://github.com/Male0523/store_wayuu.git`; se creó `feature/catalogo-productos` desde ese commit. Se conservaron los commits previos.
- Se añadió `Category.is_internal` mediante migración aditiva `store.0018_category_internal`. Los registros existentes reciben `False`; la categoría generada por el diseñador con nombre exacto `Diseños personalizados` se clasifica como interna. No se elimina ni renombra ninguna categoría o producto.
- El endpoint público de categorías devuelve todas las categorías comerciales activas, aunque no tengan productos, y omite las inactivas e internas. Listado, búsqueda, filtros, paginación y detalle del catálogo público excluyen productos personalizados/internos y productos de categorías inactivas. Las vistas HTML tradicionales aplican el mismo aislamiento.
- Las categorías internas son de solo lectura en la administración y no aparecen en selectores comerciales. Los serializers de productos de administración y tejedora rechazan categorías internas/inactivas al elegir categoría. Los endpoints administrativos continúan protegidos por RBAC; se añadió `/api/v1/admin/products/options/` para cargar categorías comerciales y perfiles reales de tejedoras bajo permiso de consulta de productos.
- El panel permite editar datos de categoría y crear/editar productos con opciones de categorías comerciales y perfiles existentes. El detalle de producto muestra nombre, comunidad, región y biografía de la tejedora solo cuando existe una relación real. El manejador de imagen del catálogo muestra un fallback visual si la referencia de una imagen falla, sin sustituirla por otra fotografía.
- Inspección de solo lectura de la base SQLite local: 8 productos públicos, 0 referencias vacías, 8 referencias `data:image`, 0 referencias repetidas y 0 productos vinculados a tejedora. No se asignaron perfiles ficticios.
- `Product.image_url` conserva referencias HTTP(S) o datos de imagen embebidos, que el API transmite sin reescribir. No se encontró `MEDIA_ROOT`, `MEDIA_URL` ni endpoint de carga de archivos para este flujo; las ocho imágenes locales usan datos embebidos. La implementación no incorpora almacenamiento de archivos nuevo.
- Se conservó el diseñador: la categoría técnica creada por sus dos flujos se marca interna para que no aparezca en el catálogo comercial; el flujo y los productos/diseños no se eliminaron ni reconstruyeron.

### Verificaciones ejecutadas

- Pruebas dirigidas — **OK**, 7 pruebas en la última ejecución: categorías comerciales vacías/internas, búsqueda/filtros/paginación, perfiles e imagen en listado/detalle, CRUD y permisos RBAC de categorías, CRUD de productos y opciones reales de tejedoras, visibilidad HTML/API y continuidad del diseñador.
- Desde `backend`: `$env:DJANGO_SECRET_KEY='sprint4-test-only-local'; $env:DB_ENGINE='sqlite'; .\\.venv\\Scripts\\python.exe manage.py test` — **OK**, 111 pruebas, 0 fallos, 0 errores; `System check identified no issues`. Django emitió el warning preexistente por falta del directorio `backend/staticfiles/` y la salida informativa de la prueba de auditoría de roles.
- Desde `backend`: `manage.py makemigrations --check --dry-run` con clave temporal — **OK**, `No changes detected`. No se aplicó la migración a la base de datos local/de producción; la suite usó su base de prueba efímera.
- Desde `frontend`: `npm run build` — **OK**, TypeScript y Vite; 1946 módulos transformados.
- Desde `frontend`: `npm run lint` — **falló**, 6 errores y 5 warnings, igual que el cierre Sprint 3 (referencia previa a Sprint 3: 7 errores y 5 warnings). Siguen siendo diagnósticos de hooks React en `CustomerPanel.tsx` y `ShopApp.tsx`; el Sprint 4 no añadió ni aumentó errores de lint.
- Desde `frontend`: `npm run` confirma que no existe script de pruebas frontend.
- `git diff --check` — **OK**, sin errores de whitespace.

### Commits y estado

- `814cd46a2fffd8dc0b05b44272c8dd5631cbdb79` — `feat: separate commercial and internal catalog categories`.
- `36b4bd1f65821211a29411d5f31e4871a8faff26` — `feat: manage catalog profiles and category edits`.
- No hubo push, merge, despliegue ni cambios en `main`. Rama local: `feature/catalogo-productos`.

## 2026-11-17 — Sprint 5: estabilización del diseñador de mantas

### Preparación, hallazgos y cambios

- Se verificó el checkout local en `feature/catalogo-productos`, limpio y basado en el historial previo; se creó `feature/estabilizacion-disenador-mantas`. El remote se mantiene en `https://github.com/Male0523/store_wayuu.git`.
- Se revisaron solamente el modelo `CustomDesign`, sus endpoints y vista HTML, serializers, componentes de diseño, permisos de diseños y asociaciones con pedidos. El modelo ya conserva cliente, patrón, colores, talla, cantidad, indicaciones, precio, estado y tejedora; el producto privado del diseño sirve como relación con líneas de pedido. La API y la vista HTML permiten crear y consultar el diseño; la edición de sus parámetros por cliente no está implementada. No se creó un endpoint de edición porque el código/documentación no define cuándo deja de ser editable un diseño ya agregado al carrito o vinculado a un pedido.
- Se detectó que ambos flujos de creación persistían diseño/producto y después escribían el carrito fuera de la transacción. Se movió el `update_or_create` del carrito dentro de la misma transacción en API y HTML.
- La vista HTML ahora valida patrón, colores hexadecimales, talla, cantidad entre 1 y 20 e indicaciones hasta 2000 caracteres, conforme a las opciones ya admitidas por la API; se evita la excepción al recibir una cantidad malformada. No se alteró la lista de patrones ni la experiencia visual.
- Se encontró que la actualización administrativa de estado de un pedido no sincronizaba los diseños enlazados y no requería `designs.change`. Ahora la ruta API exige ese permiso cuando hay diseños y sincroniza sus estados en la misma transacción que el pedido y la auditoría. Se conserva la matriz existente; no se crean transiciones comerciales.
- No se modificaron modelos, migraciones, diseñador visual, carrito fuera del guardado del diseño, checkout ni trazabilidad de tejedoras. La administración de Django y el panel de tejedora conservan los caminos existentes de consulta filtrados por sus permisos/relaciones; no se añadieron superficies nuevas de consulta.

### Verificaciones ejecutadas

- Pruebas dirigidas — **OK**, 4 pruebas: flujo de creación/listado API y carrito, validación/guardado HTML, permiso `designs.change` y sincronización de estado admin/diseño, y matriz compartida de transiciones.
- Desde `backend`: `$env:DJANGO_SECRET_KEY='sprint5-test-only-local'; $env:DB_ENGINE='sqlite'; .\\.venv\\Scripts\\python.exe manage.py test` — **OK**, 113 pruebas, 0 fallos, 0 errores; Django informó `System check identified no issues`. Se conservó el warning ya visto de `backend/staticfiles/` ausente y la salida informativa de la prueba de auditoría de roles.
- Desde `backend`: `manage.py makemigrations --check --dry-run` con la clave temporal — **OK**, `No changes detected`. No se modificaron migraciones ni se aplicó operación a la base de datos local/de producción.
- Desde `frontend`: `npm run build` — **OK**, TypeScript/Vite y 1946 módulos transformados.
- Desde `frontend`: `npm run lint` — **falló** con 6 errores y 5 warnings en `CustomerPanel.tsx` y `ShopApp.tsx`, igual a la referencia registrada al cierre del Sprint 4; no se modificó frontend en este sprint. No existe script de pruebas frontend (`npm run` lista `dev`, `build`, `lint`, `preview`).
- `git diff --check` — **OK**, sin errores de whitespace.

### Commits y pendientes

- `1375a5501c37eef93962fd76fac4ae44371c9e9d` — `fix: preserve custom designs through order updates` (código funcional y pruebas).
- Commit documental: se creará después de registrar este hash y las verificaciones finales.
- Este registro describe lo verificado en la rama `feature/estabilizacion-disenador-mantas`. No hubo push, merge, despliegue ni cambios en `main`.
- Pendiente funcional: definir y aprobar el ciclo de vida de edición de un diseño (quién puede editar y hasta qué estado/relación); implementar edición cliente únicamente tras esa definición. La ruta de pedido y cambios de estado mantienen aislamiento RBAC; no se cambió la matriz comercial.
