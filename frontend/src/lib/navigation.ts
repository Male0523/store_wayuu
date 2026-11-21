import type { RBACNavigationInput, RBACNavigationItem, RBACNavigationRoute, RBACRole } from '../types'

export function firstAvailableNavigationRoute(
  routes: RBACNavigationRoute[],
  items: RBACNavigationItem[],
  preferredValue = '',
): string {
  const configured = new Set(items.map((item) => item.route_name))
  const available = routes.filter((route) => route.role_codes.length > 0 && !configured.has(route.value))
  if (available.some((route) => route.value === preferredValue)) return preferredValue
  return available[0]?.value ?? ''
}

export function navigationItemMatchesInput(item: RBACNavigationItem, input: RBACNavigationInput): boolean {
  return item.label === input.label
    && item.route_name === input.route_name
    && item.description === input.description
    && item.anchor === input.anchor
    && item.order === input.order
    && item.active === input.active
    && item.permission_resource === (input.permission_resource ?? null)
    && item.permission_action === (input.permission_action ?? null)
    && [...item.role_codes].sort().join('\0') === [...input.role_codes].sort().join('\0')
}

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
