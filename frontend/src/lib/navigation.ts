import type { RBACNavigationItem, RBACNavigationRoute, RBACRole } from '../types'

export function rolesAllowedForRoute(roles: RBACRole[], route?: RBACNavigationRoute): RBACRole[] {
  if (!route) return []
  return roles.filter((role) => role.active && route.role_codes.includes(role.code))
}

export function ensureSuperadminAccessEntry(
  items: RBACNavigationItem[],
  roleCode: string | null | undefined,
): RBACNavigationItem[] {
  if (roleCode !== 'superadmin' || items.some((item) => item.route_name === 'admin.access')) return items
  return [...items, {
    id: -1,
    label: 'Roles y permisos',
    route_name: 'admin.access',
    anchor: '',
    description: 'Administración de roles, permisos y navegación.',
    role_codes: ['superadmin'],
    permission_resource: null,
    permission_action: null,
    order: 0,
    active: true,
  }]
}
