import assert from 'node:assert/strict'
import test from 'node:test'
import { ensureSuperadminAccessEntry, rolesAllowedForRoute } from '../src/lib/navigation.ts'

const role = (code, active = true) => ({
  code, name: code, description: '', priority: 10, active, system: false, assigned_users: 0,
})

test('route picker uses backend compatibility and includes active dynamic roles', () => {
  const roles = [role('customer'), role('orders_viewer'), role('inactive_viewer', false)]
  const route = { value: 'customer.orders', label: 'Mis pedidos', role_codes: ['customer', 'orders_viewer', 'inactive_viewer'] }
  assert.deepEqual(rolesAllowedForRoute(roles, route).map((entry) => entry.code), ['customer', 'orders_viewer'])
})

test('superadmin keeps an access entry if the navigation response omits it', () => {
  const configured = [{ id: 4, label: 'Pedidos', route_name: 'admin.orders' }]
  const result = ensureSuperadminAccessEntry(configured, 'superadmin')
  assert.equal(result[0], configured[0])
  assert.equal(result.filter((entry) => entry.route_name === 'admin.access').length, 1)
  assert.deepEqual(ensureSuperadminAccessEntry(configured, 'admin'), configured)
})

test('does not duplicate a configured superadmin access entry', () => {
  const configured = [{ id: 8, label: 'Roles y permisos', route_name: 'admin.access' }]
  assert.equal(ensureSuperadminAccessEntry(configured, 'superadmin'), configured)
})
