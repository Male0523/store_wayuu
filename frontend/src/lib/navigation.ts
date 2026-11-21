import type { RBACNavigationItem, RBACNavigationRoute } from '../types'

export type NavigationRouteOption = RBACNavigationRoute & { configured: boolean }

export function rolesAllowedForRoute(roleCodes: string[], routeRoleCodes: string[]): string[] {
  return roleCodes.filter((code) => routeRoleCodes.includes(code))
}

export function navigationRoutesForCreate(
  routes: RBACNavigationRoute[],
  items: RBACNavigationItem[],
): NavigationRouteOption[] {
  return routes.map((route) => ({
    ...route,
    configured: items.some((item) => item.route_name === route.value),
  }))
}

export function navigationRoutesForEdit(
  routes: RBACNavigationRoute[],
  items: RBACNavigationItem[],
  item: RBACNavigationItem,
): NavigationRouteOption[] {
  const options = routes.some((route) => route.value === item.route_name)
    ? routes
    : [{ value: item.route_name, label: item.route_name, role_codes: item.role_codes }, ...routes]
  return options.map((route) => ({
    ...route,
    configured: route.value !== item.route_name && items.some((entry) => entry.route_name === route.value),
  }))
}

const SUPERADMIN_ACCESS_FALLBACK: RBACNavigationItem = {
  id: -1,
  label: 'Roles y permisos',
  route_name: 'admin.access',
  anchor: '',
  description: 'Administra roles, permisos y vistas del sistema.',
  role_codes: ['superadmin'],
  permission_resource: null,
  permission_action: null,
  order: 90,
  active: true,
}

/** Keep the protected root-management entry reachable if menu loading fails. */
export function withSuperadminAccessFallback(
  items: RBACNavigationItem[],
  role: string | null | undefined,
): RBACNavigationItem[] {
  if (role !== 'superadmin' || items.some((item) => item.route_name === 'admin.access')) return items
  return [...items, SUPERADMIN_ACCESS_FALLBACK]
}
