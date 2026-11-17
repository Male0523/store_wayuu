# Flujo de autorización RBAC

## Componentes

- `AccessRole` contiene roles persistentes. Sus códigos no cambian después de crearlos; los roles pueden activarse y desactivarse. La desactivación conserva asignaciones y grants para permitir su recuperación y mantener trazabilidad.
- `NavigationItem` representa vistas existentes y su asignación por rol. Mostrar una vista en el menú no concede acceso a los datos ni a las operaciones.
- `RBACResource`, `RBACAction` y `RBACCapability` forman catálogos independientes. Una capacidad existe solo cuando se vincula explícitamente un recurso con una acción.
- `RBACGrant` representa grants `allow` o `deny` por rol o por usuario. Los grants individuales prevalecen únicamente cuando no hay un `deny` aplicable.
- `RolePermission`, `UserPermissionGrant` y los permisos Django siguen leyéndose como compatibilidad con las asignaciones históricas. Las tablas históricas no se eliminan ni se vacían.
- La navegación, los endpoints API y las vistas HTML aplican controles en servidor. Las listas y detalles conservan los filtros de propiedad/asignación existentes.

## Precedencia provisional

Para una cuenta distinta del superadministrador, la evaluación se realiza en este orden:

1. Una denegación explícita del usuario o de su rol deniega la capacidad.
2. Si no existe denegación, un `allow` individual concede la capacidad.
3. Si no existe grant individual, un `allow` del rol concede la capacidad.
4. Si no hay grant dinámico para esa capacidad, se consulta la concesión heredada de Django/Wayuu.
5. En ausencia de una concesión aplicable, se deniega.

El superadministrador es una raíz global: los grants ordinarios no pueden limitarlo, no se le pueden asignar grants individuales y su rol no se puede desactivar. Solo el superadministrador administra el catálogo y los grants de rol. Una cuenta sin rol superadministrador no puede elevarse por sí misma; los cambios de rol requieren una operación del superadministrador.

Esta precedencia está implementada y probada, pero es una **política de seguridad provisional pendiente de aprobación del responsable del sistema**. Debe aprobarse explícitamente si una denegación de rol debe prevalecer sobre un `allow` individual.

## Acciones y compatibilidad

El catálogo inicial contiene `view`, `create`, `edit`, `delete`, `approve`, `reject`, `publish`, `unpublish`, `assign`, `cancel`, `export` y `manage`. Se crean capacidades especializadas solo donde hay una operación del proyecto identificada. Las acciones sin endpoint u operación asociada no conceden por sí mismas acceso.

Durante la transición, las capacidades `approve`, `publish`, `unpublish`, `assign` y `cancel` pueden heredar el permiso Django `edit` de un rol histórico cuando no exista un grant dinámico específico. Un grant dinámico explícito sobre la capacidad especializada reemplaza esa compatibilidad. Este puente puede mantener permisos más amplios que la matriz nueva y requiere aprobación o un plan de retiro antes de eliminarlo.

Los nombres `add`/`change` se aceptan como alias de `create`/`edit` para conservar clientes y grants existentes.

## Alcance de registros

Los perfiles de cliente y tejedora conservan los límites existentes: pedidos y diseños propios para clientes, pedidos asignados y datos de taller para tejedoras. Las concesiones históricas `orders.view` no se interpretan como autorización para los listados administrativos. Los endpoints administrativos de recursos con registros privados (`orders`, `designs`, `customers`, `users` y `craftswomen`) quedan reservados a los roles administrativos existentes; un rol personalizado falla cerrado allí hasta que exista una política de alcance por registro aprobada y configurable.

La versión actual no incluye un catálogo configurable de ámbitos (`propios`, `asignados`, `globales` u otros) ni filtros de alcance para cada modelo. Por tanto, **no deben otorgarse capacidades de datos sensibles a roles personalizados esperando que eso defina su alcance**. Definir y administrar esos ámbitos es un pendiente de seguridad para el siguiente incremento, no una regla inferida en este sprint.

## Decisiones que requieren aprobación

- Aprobar la precedencia `DENY` sobre grants `ALLOW` del rol y del usuario.
- Aprobar al superadministrador como raíz sin posibilidad de auto-denegación ordinaria y la protección del último superadministrador activo.
- Definir si los administradores pueden acceder a registros ajenos y qué roles pueden recibir alcance `global`, `propio` o `asignado` por recurso.
- Definir las relaciones de propiedad/asignación para recursos personalizados antes de habilitar roles personalizados sobre esos registros.
- Decidir cómo retirar el fallback histórico que permite acciones especializadas a partir de `edit`.
- Asociar `reject` y `export` a operaciones reales antes de concederlas; se mantienen en el catálogo general, pero no hay capacidades iniciales para endpoints que no existen.

No se modificaron las reglas comerciales de pedidos ni los permisos de diseño de mantas.
