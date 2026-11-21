import type { RBACNavigationItem, RBACNavigationRoute, RBACPermission } from '../types'

export const CRUD_ACTIONS = ['view', 'create', 'edit', 'delete'] as const

export function routePermissions(route: RBACNavigationRoute, permissions: RBACPermission[]) {
  const resources = [...new Set(route.required_permissions.map((entry) => entry.resource))]
  return permissions.filter((permission) => resources.includes(permission.resource))
}

export function roleCodesWithVisibility(item: RBACNavigationItem | null, roleCode: string, visible: boolean) {
  const current = item?.role_codes ?? []
  return visible
    ? [...new Set([...current, roleCode])]
    : current.filter((code) => code !== roleCode)
}

export function hasNavigationDraftChanges(
  initialVisible: boolean,
  visible: boolean,
  initialEffects: Record<string, string>,
  effects: Record<string, string>,
) {
  return initialVisible !== visible || Object.keys({ ...initialEffects, ...effects }).some((key) => initialEffects[key] !== effects[key])
}
