import { useEffect, useMemo, useState } from 'react'
import { api, ApiError } from './lib/api'
import { canAssignNavigationWithoutDataAccess, CRUD_ACTIONS, hasNavigationDraftChanges, permissionRequestPending, roleCodesWithVisibility, routePermissions } from './lib/navigationConfig'
import type { RBACAction, RBACCatalogEntry, RBACNavigationInput, RBACNavigationItem, RBACNavigationRoute, RBACPermission, RBACRole, RBACRolePermissions, SessionUser } from './types'
import './RBACNavigationConfigurator.css'

type Props = {
  currentUser: SessionUser
  roles: RBACRole[]
  items: RBACNavigationItem[]
  routes: RBACNavigationRoute[]
  resources: RBACCatalogEntry[]
  actions: RBACCatalogEntry[]
  loading: boolean
  rolesLoading: boolean
  error: string
  rolesError: string
  canAddNavigation: boolean
  canChangeNavigation: boolean
  canDeleteNavigation: boolean
  canViewPermissions: boolean
  canChangePermissions: boolean
  onItemsChanged: (items: RBACNavigationItem[]) => void
  onReload: () => void
}

type NavigationMetadata = {
  label: string
  description: string
  anchor: string
  order: number
  permission_resource: string | null
  permission_action: RBACAction | null
}

function permissionError(error: unknown) {
  if (error instanceof ApiError) return error.message
  return 'No se pudo guardar la configuración. Vuelve a consultar los datos e intenta otra vez.'
}

function effective(user: SessionUser, key: string) {
  return user.role === 'superadmin' || Boolean(user.permissions?.includes(key))
}

export function RBACNavigationConfigurator({ currentUser, roles, items, routes, resources, actions, loading, rolesLoading, error, rolesError, canAddNavigation, canChangeNavigation, canDeleteNavigation, canViewPermissions, canChangePermissions, onItemsChanged, onReload }: Props) {
  const [roleCode, setRoleCode] = useState('')
  const [routeName, setRouteName] = useState('')
  const [rolePermissions, setRolePermissions] = useState<RBACRolePermissions | null>(null)
  const [permissionsLoadedFor, setPermissionsLoadedFor] = useState<string | null>(null)
  const [visibleDraft, setVisibleDraft] = useState<boolean | null>(null)
  const [metadataDraft, setMetadataDraft] = useState<NavigationMetadata | null>(null)
  const [initialEffects, setInitialEffects] = useState<Record<string, string>>({})
  const [effects, setEffects] = useState<Record<string, string>>({})
  const [loadingPermissions, setLoadingPermissions] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [failure, setFailure] = useState('')
  const [permissionLoadError, setPermissionLoadError] = useState('')
  const [search, setSearch] = useState('')
  const [permissionReloadVersion, setPermissionReloadVersion] = useState(0)

  const activeRoles = useMemo(() => roles.filter((role) => role.active), [roles])
  const selectedRoleCode = activeRoles.some((role) => role.code === roleCode) ? roleCode : activeRoles[0]?.code ?? ''
  const selectedRouteName = routes.some((route) => route.value === routeName) ? routeName : routes[0]?.value ?? ''
  const selectedRole = activeRoles.find((role) => role.code === selectedRoleCode)
  const selectedRoute = routes.find((route) => route.value === selectedRouteName)
  const item = items.find((entry) => entry.route_name === selectedRouteName) ?? null
  const serverMetadata: NavigationMetadata = item ? {
    label: item.label,
    description: item.description,
    anchor: item.anchor,
    order: item.order,
    permission_resource: item.permission_resource,
    permission_action: item.permission_action,
  } : {
    label: selectedRoute?.label ?? '',
    description: '',
    anchor: '',
    order: 10,
    permission_resource: null,
    permission_action: null,
  }
  const metadata = metadataDraft ?? serverMetadata
  const serverVisible = Boolean(item?.active && item.role_codes.includes(selectedRoleCode))
  const visible = visibleDraft ?? serverVisible
  const visiblePermissions = selectedRoute && rolePermissions?.role === selectedRoleCode
    ? routePermissions(selectedRoute, rolePermissions.permissions, metadata.permission_resource)
    : []
  const permissionBaselines = Object.fromEntries(visiblePermissions.map((permission) => {
    const key = `${permission.resource}.${permission.action}`
    return [key, Object.prototype.hasOwnProperty.call(initialEffects, key) ? initialEffects[key] : permission.effect ?? 'inherit']
  }))
  const rolePermissionsAvailable = Boolean(rolePermissions?.role === selectedRoleCode && permissionsLoadedFor === selectedRoleCode)
  const metadataDirty = Object.keys(serverMetadata).some((key) => serverMetadata[key as keyof typeof serverMetadata] !== metadata[key as keyof typeof metadata])
  const dirty = hasNavigationDraftChanges(serverVisible, visible, permissionBaselines, effects) || metadataDirty
  const sharedInactiveAssignment = Boolean(item && !item.active && item.role_codes.some((code) => code !== selectedRoleCode))
  const isLoadingPermissions = loadingPermissions || permissionRequestPending(canViewPermissions, selectedRoleCode, Boolean(selectedRoute), permissionsLoadedFor)
  const missingRequirements = selectedRoute && selectedRole ? selectedRoute.required_permissions.filter((requirement) => {
    const key = `${requirement.resource}.${requirement.action}`
    const draft = effects[key] ?? permissionBaselines[key]
    if (draft === 'allow') return false
    if (draft === 'deny') return true
    return (selectedRoute.missing_permissions[selectedRole.code] ?? []).some((missing) => missing.resource === requirement.resource && missing.action === requirement.action)
  }) : []
  const missingScopes = selectedRoute && selectedRole ? selectedRoute.missing_scopes[selectedRole.code] ?? [] : []
  const optionalPermissionKey = metadata.permission_resource && metadata.permission_action
    ? `${metadata.permission_resource}.${metadata.permission_action}`
    : ''
  const optionalPermission = optionalPermissionKey
    ? rolePermissions?.permissions.find((permission) => `${permission.resource}.${permission.action}` === optionalPermissionKey)
    : undefined
  const optionalPermissionEffect = optionalPermissionKey ? effects[optionalPermissionKey] ?? permissionBaselines[optionalPermissionKey] : undefined
  const missingOptionalPermission = Boolean(canViewPermissions && optionalPermissionKey && !selectedRoute?.required_permissions.some((entry) => `${entry.resource}.${entry.action}` === optionalPermissionKey)
    && (optionalPermissionEffect === 'deny' || (optionalPermissionEffect !== 'allow' && !optionalPermission?.allowed)))
  const visibleBlocked = missingRequirements.length > 0 || missingScopes.length > 0 || missingOptionalPermission
  const visibilityIndependent = canAssignNavigationWithoutDataAccess(selectedRouteName)
  const canSaveVisibility = (visible === serverVisible || (item ? canChangeNavigation : canAddNavigation)) && (!visible || !visibleBlocked || visibilityIndependent)
  const navigationDirty = metadataDirty || visible !== serverVisible
  const canSaveNavigation = !navigationDirty || (item ? canChangeNavigation : canAddNavigation)
  const metadataValid = Boolean(metadata.label.trim())
    && metadata.order >= 0 && metadata.order <= 32767
    && Boolean(metadata.permission_resource) === Boolean(metadata.permission_action)
  const canSavePermissions = !Object.keys(effects).some((key) => permissionBaselines[key] !== effects[key]) || canChangePermissions
  const canSave = dirty && canSaveVisibility && canSaveNavigation && canSavePermissions && (!metadataDirty || metadataValid) && !saving && !isLoadingPermissions && Boolean(selectedRoute && selectedRole)
  const selectedAssignedItems = items.filter((entry) => entry.role_codes.includes(selectedRoleCode))
  const query = search.trim().toLocaleLowerCase('es')
  const filteredRows = selectedAssignedItems.filter((entry) => {
    const route = routes.find((candidate) => candidate.value === entry.route_name)
    return !query || `${entry.label} ${route?.label ?? ''} ${entry.route_name}`.toLocaleLowerCase('es').includes(query)
  })

  function confirmDiscard() {
    return !dirty || window.confirm('Hay cambios sin guardar. ¿Descartarlos y cambiar la selección?')
  }

  function selectRole(next: string) {
    if (next === selectedRoleCode || !confirmDiscard()) return
    setLoadingPermissions(canViewPermissions && Boolean(selectedRoute))
    setRoleCode(next)
    setVisibleDraft(null)
    setMetadataDraft(null)
    setInitialEffects({})
    setEffects({})
    setFailure('')
    setPermissionLoadError('')
    setMessage('')
  }

  function selectRoute(next: string) {
    if (next === selectedRouteName || !confirmDiscard()) return
    setLoadingPermissions(canViewPermissions)
    setRouteName(next)
    setVisibleDraft(null)
    setMetadataDraft(null)
    setEffects({})
    setFailure('')
    setPermissionLoadError('')
    setMessage('')
  }

  useEffect(() => {
    if (!selectedRole || !selectedRoute) return
    if (!canViewPermissions) return
    let current = true
    api.rolePermissions(selectedRole.code).then((result) => {
      if (!current) return
      setRolePermissions(result)
      setPermissionsLoadedFor(selectedRole.code)
      setPermissionLoadError('')
      const next = Object.fromEntries(routePermissions(selectedRoute, result.permissions).map((entry) => [`${entry.resource}.${entry.action}`, entry.effect ?? 'inherit']))
      setInitialEffects(next)
      setEffects(next)
    }).catch((loadError: unknown) => {
      if (current) {
        setPermissionsLoadedFor(selectedRole.code)
        setRolePermissions((previous) => previous?.role === selectedRole.code ? null : previous)
        setInitialEffects({})
        setEffects({})
        const message = `No se pudieron consultar los permisos de ${selectedRole.name}: ${permissionError(loadError)}`
        setPermissionLoadError(message)
        setFailure(message)
      }
    }).finally(() => { if (current) setLoadingPermissions(false) })
    return () => { current = false }
  }, [selectedRole, selectedRoute, canViewPermissions, permissionReloadVersion])

  function retryPermissionLoad() {
    setFailure('')
    setPermissionLoadError('')
    setPermissionsLoadedFor(null)
    setLoadingPermissions(true)
    setPermissionReloadVersion((version) => version + 1)
  }

  function cancelChanges() {
    if (!confirmDiscard()) return
    setVisibleDraft(null)
    setMetadataDraft(null)
    setEffects(permissionBaselines)
    setFailure('')
    setMessage('Cambios descartados. Se conserva la configuración guardada.')
  }

  async function saveChanges() {
    if (!selectedRoute || !selectedRole || !canSave) return
    setSaving(true)
    setFailure('')
    setPermissionLoadError('')
    setMessage('')
    let permissionsSaved = false
    let navigationSaved = false
    try {
      const changed = visiblePermissions.filter((permission) => {
        const key = `${permission.resource}.${permission.action}`
        return permissionBaselines[key] !== effects[key]
      }).map((permission) => ({
        resource: permission.resource,
        action: permission.action,
        effect: effects[`${permission.resource}.${permission.action}`] === 'inherit' ? null : effects[`${permission.resource}.${permission.action}`] as 'allow' | 'deny',
      }))
      if (changed.length) {
        const updatedPermissions = await api.updateRolePermissions(selectedRole.code, changed)
        setRolePermissions(updatedPermissions)
        const savedEffects = Object.fromEntries(routePermissions(selectedRoute, updatedPermissions.permissions, metadata.permission_resource).map((entry) => [`${entry.resource}.${entry.action}`, entry.effect ?? 'inherit']))
        setInitialEffects(savedEffects)
        setEffects(savedEffects)
        permissionsSaved = true
      }

      const nextRoleCodes = roleCodesWithVisibility(item, selectedRole.code, visible)
      const visibilityChanged = serverVisible !== visible
      if (navigationDirty) {
        if (item) {
          const values: Partial<RBACNavigationInput> = { ...metadata }
          if (visibilityChanged) values.role_codes = nextRoleCodes
          if (visible && !item.active) values.active = true
          await api.updateNavigationItem(item.id, values)
        } else {
          await api.createNavigationItem({
            ...metadata,
            route_name: selectedRoute.value,
            role_codes: visible ? nextRoleCodes : [],
            active: true,
          })
        }
        navigationSaved = true
      }

      if (navigationDirty) {
        const refreshed = await api.navigationItems()
        onItemsChanged(refreshed)
      }
      if (changed.length) {
        const freshPermissions = await api.rolePermissions(selectedRole.code)
        setRolePermissions(freshPermissions)
        const next = Object.fromEntries(routePermissions(selectedRoute, freshPermissions.permissions, metadata.permission_resource).map((entry) => [`${entry.resource}.${entry.action}`, entry.effect ?? 'inherit']))
        setInitialEffects(next)
        setEffects(next)
      }
      setVisibleDraft(null)
      setMetadataDraft(null)
      setMessage('Cambios guardados y confirmados con el servidor.')
    } catch (saveError) {
      const detail = permissionError(saveError)
      setFailure(permissionsSaved && navigationDirty && !navigationSaved
        ? `Los permisos se guardaron, pero la actualización de la pantalla falló. La operación quedó parcialmente aplicada; vuelve a cargar para ver el estado real. ${detail}`
        : permissionsSaved || navigationSaved
          ? `El servidor guardó parte o todos los cambios, pero no se pudo confirmar la respuesta. Vuelve a cargar para consultar el estado real. ${detail}`
          : detail)
      onReload()
    } finally { setSaving(false) }
  }

  async function deleteSoleAssignment(row: RBACNavigationItem) {
    if (!canDeleteNavigation || row.route_name === 'admin.access' || row.role_codes.length !== 1 || row.role_codes[0] !== selectedRoleCode) return
    if (!window.confirm(`¿Eliminar la configuración de «${row.label}»?`)) return
    setSaving(true)
    setFailure('')
    setMessage('')
    try {
      await api.deleteNavigationItem(row.id)
      onItemsChanged(await api.navigationItems())
      setMessage('Configuración eliminada y confirmada con el servidor.')
      if (row.route_name === selectedRouteName) setVisibleDraft(false)
    } catch (deleteError) {
      setFailure(permissionError(deleteError))
      onReload()
    } finally { setSaving(false) }
  }

  async function removeRoleAssignment(row: RBACNavigationItem) {
    if (!canChangeNavigation || row.route_name === 'admin.access' && selectedRoleCode === 'superadmin') return
    if (!window.confirm(`¿Quitar «${selectedRole?.name ?? selectedRoleCode}» de la pantalla «${row.label}»?`)) return
    setSaving(true)
    setFailure('')
    setMessage('')
    try {
      await api.updateNavigationItem(row.id, { role_codes: row.role_codes.filter((code) => code !== selectedRoleCode) })
      onItemsChanged(await api.navigationItems())
      if (row.route_name === selectedRouteName) {
        setVisibleDraft(null)
        setMetadataDraft(null)
      }
      setMessage(`La pantalla «${row.label}» se quitó del menú de ${selectedRole?.name ?? selectedRoleCode}.`)
    } catch (removeError) {
      setFailure(permissionError(removeError))
      onReload()
    } finally { setSaving(false) }
  }

  const routeWarnings = [
    ...missingRequirements.map((entry) => `Falta ${entry.resource_name} · consultar.`),
    ...missingScopes.map((resource) => `El alcance de ${resource} debe permitir los registros requeridos.`),
    ...(missingOptionalPermission ? [`Falta el permiso ${metadata.permission_action} sobre ${metadata.permission_resource} que exige esta opción de menú.`] : []),
  ]

  function permissionValue(permission: RBACPermission) {
    const key = `${permission.resource}.${permission.action}`
    if (Object.prototype.hasOwnProperty.call(effects, key)) return effects[key]
    return rolePermissions?.role === selectedRoleCode
      ? rolePermissions.permissions.find((entry) => entry.resource === permission.resource && entry.action === permission.action)?.effect ?? 'inherit'
      : 'inherit'
  }

  return <section className="rbac-block rbac-vistas" aria-labelledby="rbac-vistas-title">
    <header className="rbac-vistas-heading"><span className="rbac-vistas-icon" aria-hidden="true">▣</span><div><h3 id="rbac-vistas-title">Vistas y menú</h3><p>Configura qué pantallas aparecen en el menú de cada rol. La visibilidad no concede permisos de operación.</p></div></header>
    {(error || rolesError) && <p className="rbac-warning" role="alert">{[error && `Vistas: ${error}`, rolesError && `Roles: ${rolesError}`].filter(Boolean).join(' ')} <button type="button" onClick={onReload}>Volver a cargar</button></p>}
    {(loading || rolesLoading) && <p className="muted-copy" role="status">Cargando configuración real del servidor…</p>}
    {!loading && !rolesLoading && !error && !rolesError && !activeRoles.length && <p className="rbac-info">No hay roles activos disponibles para configurar.</p>}
    {!loading && !rolesLoading && !error && !rolesError && !routes.length && <p className="rbac-info">El backend no devolvió pantallas disponibles en el catálogo.</p>}
    {failure && <p className="rbac-error" role="alert">{failure}{permissionLoadError && <button type="button" disabled={loadingPermissions || saving} onClick={retryPermissionLoad}>Reintentar consulta de permisos</button>}</p>}
    {message && <p className="rbac-feedback" role="status">{message}</p>}
    {!loading && !rolesLoading && !error && !rolesError && <>
      <div className="rbac-vistas-steps" aria-label="Pasos de configuración">
        <strong><span>1</span> Seleccionar rol</strong><i /><strong><span>2</span> Seleccionar pantalla</strong><i /><strong><span>3</span> Configurar visibilidad y permisos</strong>
      </div>
      <div className="rbac-vistas-form">
        <label className="form-label">Rol *<select aria-label="Rol para configurar la vista" value={selectedRoleCode} onChange={(event) => selectRole(event.target.value)} disabled={!activeRoles.length || saving}>
          {activeRoles.map((role) => <option key={role.code} value={role.code}>{role.name}</option>)}
        </select></label>
        <label className="form-label">Pantalla *<select aria-label="Pantalla para configurar" value={selectedRouteName} onChange={(event) => selectRoute(event.target.value)} disabled={!routes.length || saving}>
          {routes.map((route) => <option key={route.value} value={route.value}>{route.label}</option>)}
        </select></label>
        <label className="rbac-vistas-toggle"><strong>Visible en el menú</strong><span><input type="checkbox" aria-label="Visible en el menú para el rol seleccionado" checked={visible} disabled={saving || isLoadingPermissions || (selectedRouteName === 'admin.access' && selectedRoleCode === 'superadmin') || sharedInactiveAssignment || (!visible && visibleBlocked && !visibilityIndependent)} onChange={(event) => setVisibleDraft(event.target.checked)} /> Sí, mostrar en el menú</span>{selectedRouteName === 'admin.access' && selectedRoleCode === 'superadmin' && <small>La entrada del superadministrador permanece protegida.</small>}</label>
        <label className="form-label">Nombre visible<input maxLength={80} value={metadata.label} disabled={saving || !(item ? canChangeNavigation : canAddNavigation)} onChange={(event) => setMetadataDraft((current) => ({ ...serverMetadata, ...current, label: event.target.value }))} /></label>
        <label className="form-label">Orden del menú<input type="number" min="0" max="32767" value={metadata.order} disabled={saving || !(item ? canChangeNavigation : canAddNavigation)} onChange={(event) => setMetadataDraft((current) => ({ ...serverMetadata, ...current, order: Number(event.target.value) }))} /></label>
        <label className="form-label">Descripción<input maxLength={220} value={metadata.description} disabled={saving || !(item ? canChangeNavigation : canAddNavigation)} onChange={(event) => setMetadataDraft((current) => ({ ...serverMetadata, ...current, description: event.target.value }))} /></label>
        <label className="form-label">Sección auxiliar<input maxLength={80} value={metadata.anchor} disabled={saving || !(item ? canChangeNavigation : canAddNavigation)} onChange={(event) => setMetadataDraft((current) => ({ ...serverMetadata, ...current, anchor: event.target.value }))} /></label>
        {resources.length > 0 && <><label className="form-label">Requisito adicional de recurso (opcional)<select value={metadata.permission_resource ?? ''} disabled={saving || !(item ? canChangeNavigation : canAddNavigation)} onChange={(event) => setMetadataDraft((current) => ({ ...serverMetadata, ...current, permission_resource: event.target.value || null, permission_action: event.target.value ? current?.permission_action ?? metadata.permission_action : null }))}><option value="">Sin requisito adicional</option>{resources.map((resource) => <option key={resource.code} value={resource.code}>{resource.name}</option>)}</select></label><label className="form-label">Acción requerida<select value={metadata.permission_action ?? ''} disabled={saving || !(item ? canChangeNavigation : canAddNavigation) || !metadata.permission_resource} onChange={(event) => setMetadataDraft((current) => ({ ...serverMetadata, ...current, permission_action: (event.target.value || null) as RBACAction | null }))}><option value="">Selecciona una acción</option>{actions.map((action) => <option key={action.code} value={action.code}>{action.name}</option>)}</select></label></>}
        <section className="rbac-vistas-crud" aria-label="Permisos de pantalla">
          <div><strong>Permisos de la pantalla (CRUD)</strong><small>Son grants reales por recurso. El RBAC vigente los aplica en todo el recurso, no solo en esta ruta.</small></div>
          {canViewPermissions ? isLoadingPermissions ? <p className="muted-copy" role="status">Consultando permisos del rol…</p> : <div className="rbac-vistas-actions">{visiblePermissions.filter((permission) => CRUD_ACTIONS.includes(permission.action as typeof CRUD_ACTIONS[number])).map((permission) => {
            const key = `${permission.resource}.${permission.action}`
            const value = permissionValue(permission)
            const allowDisabled = value !== 'allow' && !effective(currentUser, key)
            return <label key={key}><span>{permission.action === 'view' ? 'Consultar / Ver' : permission.action === 'create' ? 'Crear' : permission.action === 'edit' ? 'Editar' : 'Eliminar'}</span><select value={value} disabled={saving || isLoadingPermissions || !canChangePermissions} onChange={(event) => setEffects((current) => ({ ...current, [key]: event.target.value }))}><option value="inherit">Sin grant</option><option value="allow" disabled={allowDisabled}>Permitir</option><option value="deny">Denegar</option></select></label>
          })}</div> : <p className="rbac-info">La consulta de permisos requiere el permiso efectivo permissions.view.</p>}
          {canViewPermissions && rolePermissionsAvailable && !visiblePermissions.some((permission) => CRUD_ACTIONS.includes(permission.action as typeof CRUD_ACTIONS[number])) && <p className="muted-copy">Esta pantalla no tiene capacidades CRUD configuradas en el catálogo.</p>}
        </section>
        {canViewPermissions && !isLoadingPermissions && visiblePermissions.some((permission) => !CRUD_ACTIONS.includes(permission.action as typeof CRUD_ACTIONS[number])) && <details className="rbac-vistas-extra"><summary>Acciones adicionales del recurso</summary><div className="rbac-vistas-actions">{visiblePermissions.filter((permission) => !CRUD_ACTIONS.includes(permission.action as typeof CRUD_ACTIONS[number])).map((permission) => {
          const key = `${permission.resource}.${permission.action}`
          const value = permissionValue(permission)
          return <label key={key}><span>{permission.action_name ?? permission.action} · {permission.resource_name ?? permission.resource}</span><select value={value} disabled={saving || isLoadingPermissions || !canChangePermissions} onChange={(event) => setEffects((current) => ({ ...current, [key]: event.target.value }))}><option value="inherit">Sin grant</option><option value="allow" disabled={value !== 'allow' && !effective(currentUser, key)}>Permitir</option><option value="deny">Denegar</option></select></label>
        })}</div></details>}
        {routeWarnings.map((warning) => <p className="rbac-warning" role="status" key={warning}>{warning} La visibilidad no sustituye este requisito.</p>)}
        {visibilityIndependent && visibleBlocked && <p className="rbac-info" role="status">La asignación se guardará sin grants. La pantalla solo aparecerá cuando el rol tenga los permisos y alcances requeridos; las operaciones siguen protegidas por el servidor.</p>}
        {sharedInactiveAssignment && <p className="rbac-warning" role="status">Esta pantalla está desactivada globalmente y asignada a otros roles. No se activará desde aquí para evitar cambiar su visibilidad compartida.</p>}
        {metadataDirty && !metadataValid && <p className="rbac-warning" role="alert">Completa un nombre visible y selecciona recurso y acción requeridos juntos, o deja ambos sin requisito adicional.</p>}
        {!canChangePermissions && canViewPermissions && <p className="rbac-info">Consulta habilitada. Para modificar capacidades necesitas permissions.change; los cambios se rechazan también en el servidor.</p>}
        <p className="rbac-vistas-notice">ⓘ La visibilidad del menú y los permisos CRUD son independientes. Mostrar una pantalla no concede permisos de operación. Cada acción se valida en el servidor.</p>
        <div className="rbac-vistas-footer"><span>{dirty ? 'Hay cambios sin guardar.' : 'Configuración sincronizada con el servidor.'}</span><div><button type="button" className="button button-outline" disabled={saving || !dirty} onClick={cancelChanges}>Cancelar</button><button type="button" className="button button-dark" disabled={!canSave} onClick={() => void saveChanges()}>{saving ? 'Guardando…' : 'Guardar cambios'}</button></div></div>
      </div>
      <section className="rbac-vistas-table-wrap"><div className="rbac-vistas-table-title"><div><h4>Vistas configuradas</h4><p>Asignaciones existentes para el rol seleccionado.</p></div><input type="search" aria-label="Buscar vistas configuradas" placeholder="Buscar pantalla" value={search} onChange={(event) => setSearch(event.target.value)} /></div>
        {filteredRows.length ? <div className="rbac-vistas-table-scroll"><table className="rbac-vistas-table"><thead><tr><th>Pantalla</th><th>Ruta</th><th>Rol</th><th>Visible en menú</th><th>Permisos CRUD</th><th>Acciones</th></tr></thead><tbody>{filteredRows.map((row) => {
          const rowRoute = routes.find((route) => route.value === row.route_name)
          const isVisible = row.active
          const crud = rowRoute && rolePermissionsAvailable && rolePermissions?.role === selectedRoleCode ? routePermissions(rowRoute, rolePermissions.permissions, row.permission_resource).filter((permission) => CRUD_ACTIONS.includes(permission.action as typeof CRUD_ACTIONS[number]) && permission.effect === 'allow') : []
          return <tr key={`${row.id}-${selectedRoleCode}`}><td><strong>{rowRoute?.label ?? row.label}</strong></td><td>{row.route_name}</td><td>{selectedRole?.name ?? selectedRoleCode}</td><td><span className={isVisible ? 'rbac-vistas-badge is-visible' : 'rbac-vistas-badge'}>{isVisible ? 'Visible' : 'Oculto'}</span></td><td>{crud.map((permission) => permission.action === 'view' ? 'Ver' : permission.action === 'create' ? 'Crear' : permission.action === 'edit' ? 'Editar' : 'Eliminar').join(' · ') || 'Sin grants CRUD'}</td><td><button type="button" className="button button-outline" disabled={saving} onClick={() => selectRoute(row.route_name)}>Editar</button>{canChangeNavigation && !(row.route_name === 'admin.access' && selectedRoleCode === 'superadmin') && <button type="button" className="button button-outline" disabled={saving} onClick={() => void removeRoleAssignment(row)}>Quitar rol</button>}{canDeleteNavigation && row.route_name !== 'admin.access' && row.role_codes.length === 1 && <button type="button" className="button button-outline" disabled={saving} onClick={() => void deleteSoleAssignment(row)}>Eliminar pantalla</button>}</td></tr>
        })}</tbody></table></div> : <p className="muted-copy">No hay vistas configuradas para este rol o la búsqueda no encontró coincidencias.</p>}
      </section>
    </>}
  </section>
}
