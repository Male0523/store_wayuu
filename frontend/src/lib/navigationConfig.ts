import type { RBACNavigationItem, RBACNavigationRoute, RBACPermission } from '../types'

export const CRUD_ACTIONS = ['view', 'create', 'edit', 'delete'] as const
export const VISIBILITY_INDEPENDENT_ROUTES = ['admin.access', 'admin.categories'] as const

export function canAssignNavigationWithoutDataAccess(routeName: string): boolean {
  return VISIBILITY_INDEPENDENT_ROUTES.includes(routeName as typeof VISIBILITY_INDEPENDENT_ROUTES[number])
}

export const RBAC_SECTIONS = ['roles', 'users', 'navigation', 'catalog', 'audit'] as const
export type RBACSection = typeof RBAC_SECTIONS[number]

export function visibleRBACSections(roleCode: string, permissionKeys: string[]): RBACSection[] {
  if (roleCode === 'superadmin') return [...RBAC_SECTIONS]
  const effective = new Set(permissionKeys)
  return RBAC_SECTIONS.filter((section) => effective.has(`${({ roles: 'roles', users: 'users', navigation: 'navigation', catalog: 'permissions', audit: 'audit' } as const)[section]}.view`))
}

export function permissionRequestPending(canViewPermissions: boolean, roleCode: string, hasSelectedRoute: boolean, completedRoleCode: string | null) {
  return canViewPermissions && Boolean(roleCode && hasSelectedRoute && completedRoleCode !== roleCode)
}

export function routePermissions(route: RBACNavigationRoute, permissions: RBACPermission[], additionalResource?: string | null) {
  const resources = [...new Set([...route.required_permissions.map((entry) => entry.resource), ...(additionalResource ? [additionalResource] : [])])]
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
