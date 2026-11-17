# Flujo de estados de pedidos

La matriz operativa está implementada en `backend/store/order_workflow.py`. API, vistas HTML y clientes reciben o aplican esa misma regla; el servidor valida toda transición.

| Estado actual | Aceptación/asignación | Tejedora | Administración |
|---|---|---|---|
| Pendiente | Aceptado | — | En preparación, Cancelado |
| Aceptado | — | En tejido | En preparación, Cancelado |
| En tejido | — | Aceptado, Tejido terminado | En preparación, Cancelado |
| Tejido terminado | — | — | Pagado, En preparación, Cancelado |
| Pagado | — | — | En preparación, Cancelado |
| En preparación | — | — | Enviado, Cancelado |
| Enviado | — | — | Entregado, Cancelado |
| Entregado | — | — | — |
| Cancelado | — | — | — |

## Reglas verificadas en el código existente

- Los pedidos nacen en `pending`.
- La aceptación por una tejedora es una acción de asignación separada, disponible solo para pedidos pendientes y sin asignar. Asigna simultáneamente la tejedora y el estado `accepted`.
- Las tejedoras pueden mover `accepted → weaving`, `weaving → accepted` y `weaving → completed`; la vuelta a `accepted` se conservó porque ya estaba disponible como “Regresar a pendiente” en el flujo anterior, aunque el estado resultante es “Aceptado”.
- Administración ya tenía una ruta para actualizar el estado desde el Sprint 1. Se conserva su matriz publicada: preparación/cancelación desde estados previos; pago desde tejido terminado; envío desde preparación; entrega desde enviado.
- `paid` no es condición previa a `preparing` en la matriz existente. `completed → preparing` también se conserva.
- La cancelación solo está permitida a administración en la matriz. No se introduce una vía de cancelación por cliente o tejedora.
- Los diseños vinculados siguen las transiciones de producción de la tejedora. Su consulta/cambio requiere el permiso de diseños; pedidos normales solo requieren permiso de pedidos.

## Decisiones comerciales pendientes

El código previo no define si `paid` debe ser requisito antes de preparar/enviar, si la tejedora puede cancelar un pedido, si el retroceso de `weaving` debe volver a `accepted`, ni quién puede cancelar. Tampoco define si `completed` o `paid` deben contarse como “activos”. No se inventaron reglas para resolver estas preguntas: se mantuvieron los permisos y transiciones ya usados. El contador “activos” conserva la definición que ya tenía el tablero: aceptados, en tejido, preparación y envío.
