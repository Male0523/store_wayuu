# Arquitectura y hallazgos de Wayúu Store

**Fecha de corte:** 2026-11-16
**Referencia:** auditoría integral anterior de diez ramas; informe original no localizado. Este documento registra continuidad y cambios observados, no reemplaza la auditoría previa.

## Arquitectura y estructura comprobadas

El repositorio `Male0523/store_wayuu` contiene backend Django (`backend/manage.py`, Django REST Framework en `backend/requirements.txt`) y frontend React/TypeScript/Vite (`frontend/package.json`, `frontend/vite.config.ts`). El frontend usa React 19, TypeScript 6 y Vite 8 según el manifiesto. El backend declara Django 5.2 y DRF 3.18. La guía de frontend describe consumo de catálogo e imágenes del backend, sesión/CSRF, pedidos y diseñador de mantas.

Hay pruebas Django en `backend/store/tests.py`; `backend/config/test_settings.py` declara SQLite en memoria para pruebas. El manifiesto frontend solo define `dev`, `build`, `lint` y `preview`; no define un script de pruebas. `docs/API.md` es la única documentación encontrada antes de esta continuidad.

## Referencia Git y cambios posteriores

`main` permanece en el SHA documentado `6c120f70892170b97dd33006908ebca3ed30176e`. Los SHA de las nueve ramas alternas observados al clonar coinciden con las referencias que el usuario indicó como verificadas; por tanto, no se repitió su auditoría funcional. La lista actual es:

| Rama remota | SHA actual | Relación con auditoría anterior |
|---|---|---|
| `main` | `6c120f70892170b97dd33006908ebca3ed30176e` | Igual |
| `codex/estabilizacion-funcional-wayuu` | `2aa051025b8633de301cc856f9167c7603a7293d` | Igual |
| `codex/mejoras-pedidos-rbac-ux` | `52379ce719196ee3a52a2da528f326e106bc6487` | Igual |
| `codex/mejoras-pedidos-rbac-ux-e67` | `2224eb2c6ee8fdd80d1a89bb6aa6cd7150f3f12b` | Igual |
| `codex/pedidos-trazabilidad-y-pruebas` | `b66698b7c38df6ee987fdfc1fe048d6376d02681` | Igual |
| `codex/recuperacion-estable-wayuu` | `2aa051025b8633de301cc856f9167c7603a7293d` | Igual (misma punta que estabilización) |
| `codex/render-deploy-wayuuwaa` | `37240b2640dfdf87a97981a1474ef72432cb28fd` | Igual |
| `codex/revision-integracion-wayuu` | `bff547878e381b5f1e9fdc63f8838bdbd9ad328d` | Igual |
| `feature/menu-roles-configurables` | `8812be4664a15fb6dfb0e0d9ea7898ec042da941` | Igual |
| `feature/opencode-task` | `13cb234b216ce4a0a22393a9099afa5a02ac9ebe` | Igual |

El checkout se creó con `git clone --no-single-branch`; `git remote -v` confirmó `origin` exacto. Se creó la rama local `integration/consolidacion-wayuu` desde `main`. La rama local estaba limpia al preparar este documento y su HEAD inicial coincide con `main`. No hay evidencia en la lista remota consultada de una rama de integración previa.

## Matriz de continuidad

| Hallazgo anterior | Estado actual | Evidencia nueva | Acción recomendada |
|---|---|---|---|
| Inventario y relaciones entre diez ramas | Puntas continúan sin cambios | Diez refs remotas y SHA coincidentes con los documentados por el usuario | Mantener como referencia; usar comparaciones desde `main` para selección |
| Mejoras aprovechables de pedidos | Sin cambios en ramas; comportamiento no revalidado | `backend/store/tests.py`; `codex/pedidos-trazabilidad-y-pruebas` sin cambios de SHA | Recuperar selectivamente tras poder ejecutar pruebas |
| Trazabilidad de pedidos | Sin cambios en ramas; comportamiento no revalidado | Rama de pedidos/trazabilidad disponible con SHA documentado | Evaluar contrato API, modelos y pruebas antes de aplicar |
| RBAC configurable parcial | Sin cambios en ramas; cobertura efectiva pendiente | Código Django incluye `rbac.py`, `permissions.py`, `navigation.py`; hay rama `feature/menu-roles-configurables` | Confirmar permisos por endpoint y configuración observable |
| Problemas de delegación administrativa | Sin cambios en ramas; comportamiento pendiente | `backend/store` incluye lógica y migración `0011_userpermissiongrant_delegation.py` | Comprobar alcance, expiración, permisos subyacentes y pruebas existentes |
| Roles/rutas estáticas | Sin cambios en ramas; cobertura pendiente | Código de navegación/RBAC y migraciones de menú están presentes | Contrastar rutas, permisos y API, incluidos endpoints no visibles en UI |
| Regresiones o diseñador de mantas desactivado en ramas alternativas | Hallazgo previo conservado; no repetido | `backend/store/migrations/0006_product_custom_design.py`; README frontend documenta diseñador; punta de ramas sin cambios | Proteger flujo y comparar cambios solo al preparar una recuperación |
| Sustitución de imágenes reales por imágenes genéricas | Hallazgo previo conservado; asociación no comprobada | La guía de frontend indica consumo de fotografías del backend; DB/catalogo no inspeccionado | Verificar referencias reales en datos de prueba autorizados; no incorporar sustitución fija |
| Riesgos de integración de migraciones | Requiere verificación dinámica; estructura muestra convergencia explícita | Dos migraciones `0012_*` dependen de `0011`; `0013` depende de la rama de carrito; `0014_merge_20261104_0528.py` une `0012_seed_supported_navigation_routes` y `0013` | Ejecutar comprobación de grafo/estado solo con runtime y base de prueba; no inferir estado aplicado |
| Implementaciones React y Django | Arquitectura confirmada como frontend React y API Django | `frontend/package.json`, `vite.config.ts`, `backend/manage.py`, `requirements.txt`, guía de frontend | Conservar separación UI/API y comprobar responsabilidades duplicadas en el código |
| Persistencia de carrito y favoritos | Migración de carrito persistente presente; comportamiento real pendiente | `0012_persistent_customer_cart.py`; base de datos no consultada; favoritos no confirmados en runtime | Verificar contrato, persistencia tras sesión/recarga y pruebas, sin datos reales |
| Identidad visual fragmentada | Hallazgo previo conservado; estado visual no reevaluado | No se hizo inspección general de estilos en esta fase | Abordar en etapa visual después de consolidar arquitectura y flujos |
| Contenido y estado de DB | No comprobado | `backend/db.sqlite3` está rastreado; su contenido no fue abierto ni consultado | Usar copia/prueba autorizada; verificar existencia de datos, esquema y migraciones aplicadas |
| Correspondencia imágenes-productos | Pendiente | No se consultaron filas, archivos ni URLs de imágenes | Comprobar en entorno de prueba autorizado |
| Perfiles reales de tejedoras | Pendiente | No se consultaron datos | Verificar existencia y relación producto-perfil sin exponer datos personales |
| Persistencia real carrito/favoritos | Pendiente | Código/migración visible, sin ejecución ni DB | Verificar con suite o datos sintéticos en base efímera |
| Funcionamiento completo del diseñador | Pendiente | Componentes documentados, no ejecutados | Recorrido funcional con test existente o entorno de prueba |
| Efectividad de delegaciones | Pendiente | Código/migraciones presentes; sin pruebas ejecutadas | Validar permisos delegados y límites por endpoint |
| Estado de migraciones en entorno actual | Pendiente | Grafo tiene merge; no se consultó DB ni runtime | Confirmar contra base de prueba sin tocar datos reales |
| Instalación de dependencias, compilación y pruebas | No ejecutable en este entorno | Node `v24.22.1`; npm no disponible; Python shim inaccesible; `node_modules` ausente | Repetir con runtimes disponibles y registrar salida real |
| Rama de integración | Preparada localmente desde `main` | `integration/consolidacion-wayuu` creada; ausencia remota antes de crear | Mantener esta rama como base de Fase 1 tras revisión |

## Línea base ejecutada y límites

| Comprobación/comando | Resultado real |
|---|---|
| `git remote -v` | `origin` fetch/push: `https://github.com/Male0523/store_wayuu.git` |
| `git status --short --branch` tras clonar | `main...origin/main`, limpio |
| `git rev-parse HEAD` inicial | `6c120f70892170b97dd33006908ebca3ed30176e` |
| `git branch --all --verbose --no-abbrev` | Diez ramas remotas más `main` local; SHA enumerados arriba |
| `git switch -c integration/consolidacion-wayuu` | Correcto; rama nueva desde `main` |
| `node --version` | `v24.22.1` |
| `npm --version` | No ejecutable: `npm` no reconocido por PowerShell |
| `python --version` | No ejecutable: shim `WindowsApps\python.exe` inaccesible |
| `git ls-remote --heads origin` en sandbox | No ejecutable por DNS (`Could not resolve host: github.com`); el clon previo sí recuperó ramas. La conexión GitHub se había confirmado y no se sustituyó el repo. |
| `frontend/node_modules` | Ausente |
| `npm run lint`, `npm run build` | No ejecutados por falta de npm/dependencias |
| Pruebas Django (`backend/store/tests.py`) | No ejecutadas por falta de Python/Django disponibles |
| Pruebas frontend | No hay script de pruebas en `package.json` |
| Migraciones/DB | No se ejecutaron comandos de base de datos ni migraciones; archivo SQLite versionado no se inspeccionó |

No se instalaron dependencias. No se modificó código funcional. La línea base dinámica queda pendiente, no fallida.

## Hallazgos que permanecen vigentes, cambiaron o siguen pendientes

- **Conservados como hallazgos previos:** RBAC parcial, problemas de delegación, restricciones estáticas, regresiones del diseñador, sustitución de imágenes, duplicidad de responsabilidades, persistencia incompleta de carrito/favoritos e identidad visual fragmentada.
- **Verificación nueva:** la punta de `main` y las nueve ramas alternas coincide con los SHA documentados; no hay commits posteriores que requieran una nueva inspección de esas ramas.
- **Cambio de estado de preparación:** existe checkout correcto y rama local de integración; no había rama remota equivalente al momento de inspección.
- **Evidencia estructural nueva:** hay una migración de carrito persistente y el grafo de migraciones incluye una migración merge. Esto no confirma migración aplicada ni comportamiento correcto.
- **Pendiente:** línea base ejecutable, estado de datos, imágenes y perfiles, comportamiento de carrito/favoritos, diseñador, delegaciones y cobertura de permisos.

## Riesgos pendientes

1. Runtime Python y npm faltantes impiden validar código y pruebas en esta máquina.
2. Estado real de migraciones y DB desconocido; el archivo SQLite está versionado pero no fue consultado.
3. Ausencia del informe original limita trazabilidad del método y evidencia detallada previa; el resumen del usuario se mantiene sin descartarlo.
4. La igualdad de SHA evita repetir auditorías de rama, pero no reemplaza las verificaciones funcionales pendientes ni la revisión de integración.
