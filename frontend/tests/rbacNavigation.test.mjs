import assert from 'node:assert/strict'
import test from 'node:test'
import { adminNavigationTarget, canUseCustomerFeatures, canViewSharedCatalog, ensureSuperadminAccessEntry, firstAvailableNavigationRoute, isAdminPanelSection, navigationItemMatchesInput, rolesAllowedForRoute, updateNavigationRoleSelection } from '../src/lib/navigation.ts'
import { canAssignNavigationWithoutDataAccess, hasNavigationDraftChanges, permissionRequestPending, roleCodesWithVisibility, routePermissions, visibleRBACSections } from '../src/lib/navigationConfig.ts'

const role = (code, active = true) => ({
  code, name: code, description: '', priority: 10, active, system: false, assigned_users: 0,
})

test('route picker uses backend compatibility and includes active dynamic roles', () => {
  const roles = [role('customer'), role('orders_viewer'), role('inactive_viewer', false)]
  const route = { value: 'customer.orders', label: 'Mis pedidos', role_codes: ['customer', 'orders_viewer', 'inactive_viewer'] }
  assert.deepEqual(rolesAllowedForRoute(roles, route).map((entry) => entry.code), ['customer', 'orders_viewer'])
})

test('admin access and categories can be assigned to any active role without granting data permissions', () => {
  const roles = [role('superadmin'), role('craftswoman'), role('roles_auditor'), role('inactive_role', false)]
  const allRoles = ['superadmin', 'craftswoman', 'roles_auditor', 'inactive_role']
  for (const routeName of ['admin.access', 'admin.categories']) {
    const route = { value: routeName, label: routeName, role_codes: allRoles }
    assert.deepEqual(rolesAllowedForRoute(roles, route).map((entry) => entry.code), ['superadmin', 'craftswoman', 'roles_auditor'])
    assert.equal(canAssignNavigationWithoutDataAccess(routeName), true)
  }
  assert.equal(canAssignNavigationWithoutDataAccess('admin.products'), false)
})

test('role assignment adds and removes one role without losing other active assignments', () => {
  const assigned = ['admin', 'customer']
  assert.deepEqual(updateNavigationRoleSelection(assigned, 'orders_auditor', true), ['admin', 'customer', 'orders_auditor'])
  assert.deepEqual(updateNavigationRoleSelection(assigned, 'customer', false), ['admin'])
  assert.deepEqual(updateNavigationRoleSelection(['customer'], 'customer', false), [])
  assert.deepEqual(updateNavigationRoleSelection(['customer'], 'customer', true), ['customer'])
})

test('new route picker chooses a free route and returns empty when the catalog is exhausted', () => {
  const routes = [
    { value: 'customer.orders', label: 'Pedidos', role_codes: ['customer'] },
    { value: 'admin.inventory', label: 'Inventario', role_codes: ['superadmin', 'admin'] },
  ]
  const configured = [{ id: 1, label: 'Historial', route_name: 'customer.orders', role_codes: ['customer'] }]
  assert.equal(firstAvailableNavigationRoute(routes, configured, 'customer.orders'), 'admin.inventory')
  assert.equal(firstAvailableNavigationRoute(routes, configured, 'admin.inventory'), 'admin.inventory')
  assert.equal(firstAvailableNavigationRoute(routes, [...configured, { id: 2, label: 'Stock', route_name: 'admin.inventory' }]), '')
})

test('navigation write confirmation compares persisted fields and role assignments', () => {
  const input = {
    label: 'Mis pedidos', route_name: 'customer.orders', description: 'Historial', anchor: '',
    order: 20, active: true, role_codes: ['customer', 'orders_viewer'],
    permission_resource: null, permission_action: null,
  }
  const persisted = { id: 9, ...input, role_codes: ['orders_viewer', 'customer'] }
  assert.equal(navigationItemMatchesInput(persisted, input), true)
  assert.equal(navigationItemMatchesInput({ ...persisted, role_codes: ['customer'] }, input), false)
  assert.equal(navigationItemMatchesInput({ ...persisted, label: 'Viejo' }, input), false)
})

test('superadmin keeps an access entry if the navigation response omits it', () => {
  const configured = [{ id: 4, label: 'Pedidos', route_name: 'admin.orders' }]
  const result = ensureSuperadminAccessEntry(configured, 'superadmin')
  assert.equal(result[0], configured[0])
  assert.equal(result.filter((entry) => entry.route_name === 'admin.access').length, 1)
  assert.deepEqual(ensureSuperadminAccessEntry(configured, 'admin'), configured)
})

test('route CRUD capabilities use route resources and an optional item-specific resource', () => {
  const route = { required_permissions: [{ resource: 'orders', action: 'view', resource_name: 'Pedidos' }] }
  const permissions = [
    { resource: 'orders', action: 'view' },
    { resource: 'orders', action: 'assign' },
    { resource: 'products', action: 'edit' },
    { resource: 'designs', action: 'view' },
  ]
  assert.deepEqual(routePermissions(route, permissions), permissions.slice(0, 2))
  assert.deepEqual(routePermissions(route, permissions, 'designs'), [permissions[0], permissions[1], permissions[3]])
})

test('visibility assignment changes only the selected role and avoids duplicates', () => {
  const item = { role_codes: ['admin', 'customer'] }
  assert.deepEqual(roleCodesWithVisibility(item, 'admin', true), ['admin', 'customer'])
  assert.deepEqual(roleCodesWithVisibility(item, 'admin', false), ['customer'])
  assert.deepEqual(roleCodesWithVisibility(null, 'craftswoman', true), ['craftswoman'])
})

test('navigation draft detects permission and visibility changes', () => {
  assert.equal(hasNavigationDraftChanges(false, false, { 'orders.view': 'inherit' }, { 'orders.view': 'inherit' }), false)
  assert.equal(hasNavigationDraftChanges(false, true, {}, {}), true)
  assert.equal(hasNavigationDraftChanges(false, false, { 'orders.view': 'inherit' }, { 'orders.view': 'allow' }), true)
})

test('permission loading ends when a role request completes, including a failed request', () => {
  assert.equal(permissionRequestPending(true, 'admin', true, null), true)
  assert.equal(permissionRequestPending(true, 'admin', true, 'admin'), false)
  assert.equal(permissionRequestPending(true, 'craftswoman', true, 'admin'), true)
  assert.equal(permissionRequestPending(true, 'admin', false, null), false)
})

test('admin navigation recognizes the colon-delimited storefront route', () => {
  assert.equal(adminNavigationTarget({ panel: 'shared', section: 'catalog' }), 'storefront')
  assert.equal(adminNavigationTarget({ panel: 'admin', section: 'access' }), 'access')
  assert.equal(adminNavigationTarget({ panel: 'admin', section: 'unknown' }), null)
  assert.equal(adminNavigationTarget({ panel: 'craftswoman', section: 'orders' }), null)
  assert.equal(isAdminPanelSection('storefront'), false)
  assert.equal(isAdminPanelSection('access'), true)
})

test('shared customer catalog requires effective product view for each non-superadmin role', () => {
  assert.equal(canViewSharedCatalog({ role: 'admin', permissions: ['products.view'] }), true)
  assert.equal(canViewSharedCatalog({ role: 'superadmin', permissions: [] }), true)
  assert.equal(canViewSharedCatalog({ role: 'craftswoman', permissions: ['orders.view'] }), false)
  assert.equal(canViewSharedCatalog({ role: 'admin', permissions: ['products.edit'] }), false)
  assert.equal(canViewSharedCatalog(null), false)
})

test('favorites, cart, and account features are restricted to the full customer panel', () => {
  assert.equal(canUseCustomerFeatures({ role: 'customer', permissions: [] }, false), true)
  assert.equal(canUseCustomerFeatures({ role: 'customer', permissions: [] }, true), false)
  assert.equal(canUseCustomerFeatures({ role: 'admin', permissions: ['products.view'] }, false), false)
})

test('RBAC tabs use independent view grants while superadmin remains global', () => {
  const adminRead = ['roles.view', 'users.view', 'navigation.view', 'permissions.view', 'audit.view']
  assert.deepEqual(visibleRBACSections('admin', adminRead), ['roles', 'users', 'navigation', 'catalog', 'audit'])
  assert.deepEqual(visibleRBACSections('admin', ['roles.view']), ['roles'])
  assert.deepEqual(visibleRBACSections('craftswoman', ['roles.view', 'audit.view']), ['roles', 'audit'])
  assert.deepEqual(visibleRBACSections('superadmin', []), ['roles', 'users', 'navigation', 'catalog', 'audit'])
})

test('does not duplicate a configured superadmin access entry', () => {
  const configured = [{ id: 8, label: 'Roles y permisos', route_name: 'admin.access' }]
  assert.equal(ensureSuperadminAccessEntry(configured, 'superadmin'), configured)
})
