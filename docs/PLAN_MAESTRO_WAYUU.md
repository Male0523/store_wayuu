# Plan maestro Wayúu Store

**Fase:** 0 — preparación y continuidad
**Fecha de corte:** 2026-11-16
**Checkout:** `C:\Users\oscar\Documents\Codex\2026-11-16\wayuu-store-fase0`
**Estado:** línea base documental preparada; verificaciones dinámicas pendientes por herramientas de entorno no disponibles. No iniciar Fase 1 hasta revisar este informe.

## Propósito y fuente de continuidad

La auditoría integral anterior de diez ramas es la línea base técnica obligatoria. El informe original no está incluido en el repositorio ni fue localizado en los archivos de trabajo disponibles. Se conserva el resumen de hallazgos aportado por el usuario y la tabla de SHA que el usuario indicó que ya había cotejado. En esta Fase 0 se verificó que los SHA observados tras clonar coinciden con esa referencia; no se repitió el análisis de contenido de las ramas sin cambios.

## Estado Git confirmado

- Repositorio: [`Male0523/store_wayuu`](https://github.com/Male0523/store_wayuu)
- `origin`: `https://github.com/Male0523/store_wayuu.git` para fetch y push.
- `main`: `6c120f70892170b97dd33006908ebca3ed30176e`.
- Checkout inicial: `main`, limpio y en el SHA esperado.
- Rama local preparada: `integration/consolidacion-wayuu`, creada desde el `main` verificado. En el momento de crearla su HEAD era el mismo SHA de `main`.
- La consulta remota del clon no mostró una rama `origin/integration/consolidacion-wayuu` antes de crear la local.
- Diez ramas remotas auditadas están disponibles; sus nombres y SHA actuales figuran en [Arquitectura y hallazgos](ARQUITECTURA_Y_HALLAZGOS.md).

## Secuencia definitiva de trabajo

1. Revisar y aceptar el presente diagnóstico de continuidad.
2. Ejecutar las verificaciones dinámicas pendientes en un entorno con Python/Django y Node/npm disponibles, preservando base de datos y datos reales. Registrar límites y comandos exactos.
3. Comprobar los puntos de comportamiento pendientes: RBAC/delegación y permisos por endpoint; carrito/favoritos; diseñador de mantas; catálogo, imágenes y perfiles de tejedoras. Usar pruebas existentes o consultas no destructivas autorizadas, sin expandir a una auditoría general.
4. Verificar el estado real de migraciones solo en una base de prueba o mediante comprobaciones seguras, tras recuperar el runtime. La Fase 0 actual no ejecutó comandos de base de datos.
5. Priorizar cambios por dependencia: compatibilidad del modelo y migraciones; backend/API, pedidos, trazabilidad y permisos; frontend conectado a la API; persistencia de carrito/favoritos y diseñador; identidad visual.
6. Recuperar mejoras de ramas selectivamente, en cambios revisables y probados; proteger el diseñador y las imágenes reales frente a regresiones.
7. Mantener el trabajo de consolidación en `integration/consolidacion-wayuu`; no modificar `main` ni integrar ramas sin evaluación.
8. Detenerse y esperar revisión antes de empezar Fase 1.

## Decisiones de consolidación

- La arquitectura objetivo verificada es Django + Django REST Framework y React + TypeScript + Vite.
- Conservar como referencias los hallazgos de auditoría anteriores. La igualdad de SHA indica que las puntas de las ramas no cambiaron respecto de la referencia entregada; no reabrir su análisis histórico.
- Recuperar selectivamente pedidos y trazabilidad, RBAC configurable y delegaciones después de comprobar compatibilidad con `main` y migraciones.
- No aceptar desactivación del diseñador ni reemplazos de imágenes reales por contenido genérico.
- No asumir que una migración está aplicada en una base porque aparezca en el árbol Git; ese estado queda pendiente.
- La duplicidad React/Django se interpreta en contexto de front/API: verificar coexistencia y dependencias antes de retirar o duplicar funcionalidad.

## Limitaciones de la línea base

El checkout no tiene dependencias instaladas en `frontend/node_modules`. `node --version` respondió `v24.22.1`; `npm` no está disponible. El shim de `python` de Windows no pudo ejecutarse, así que no se pudo verificar Python, Django ni pytest. No se ejecutaron `npm run lint`, `npm run build` ni las pruebas de Django. El paquete frontend no declara script de pruebas.

No se leyó ni conectó `backend/db.sqlite3`, aunque es un archivo rastreado del repositorio. No se ejecutaron migraciones ni consultas de base de datos. El estado aplicado de migraciones, contenido real, perfiles, imágenes y persistencia efectiva requieren una comprobación posterior autorizada en entorno adecuado.
