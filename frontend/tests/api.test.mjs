import assert from 'node:assert/strict'
import test from 'node:test'
import { ApiError, request } from '../src/lib/api.ts'
import {
  navigationRoutesForCreate,
  navigationRoutesForEdit,
  rolesAllowedForRoute,
  withSuperadminAccessFallback,
} from '../src/lib/navigation.ts'

test('request preserves credentials and parses successful responses', async () => {
  const originalFetch = globalThis.fetch
  let requestInit
  globalThis.fetch = async (_url, init) => {
    requestInit = init
    return new Response(JSON.stringify({ ok: true }), { status: 200 })
  }

  try {
    assert.deepEqual(await request('/sample'), { ok: true })
    assert.equal(requestInit.credentials, 'include')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('request reports HTTP errors with their status and server detail', async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'No autorizado.' }), { status: 403 })

  try {
    await assert.rejects(request('/restricted'), (error) => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.status, 403)
      assert.equal(error.kind, 'http')
      assert.equal(error.message, 'No autorizado.')
      return true
    })
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('request turns network failures into a user-facing API error', async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => { throw new TypeError('offline') }

  try {
    await assert.rejects(request('/offline'), (error) => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.status, 0)
      assert.equal(error.kind, 'network')
      assert.match(error.message, /conectar con el servidor/)
      return true
    })
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('request aborts a timed-out fetch and reports a timeout', async () => {
  const originalFetch = globalThis.fetch
  let signal
  globalThis.fetch = async (_url, init) => {
    signal = init.signal
    return new Promise((_resolve, reject) => {
      signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true })
    })
  }

  try {
    await assert.rejects(request('/slow', {}, 15), (error) => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.kind, 'timeout')
      assert.match(error.message, /tardó demasiado/)
      return true
    })
    assert.equal(signal.aborted, true)
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('request respects caller cancellation without reporting a timeout', async () => {
  const originalFetch = globalThis.fetch
  const controller = new AbortController()
  globalThis.fetch = async (_url, init) => new Promise((_resolve, reject) => {
    init.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true })
  })

  const pending = request('/cancelled', { signal: controller.signal }, 1_000)
  controller.abort()
  try {
    await assert.rejects(pending, (error) => !(error instanceof ApiError))
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('the protected RBAC menu entry is recovered only for the superadmin role', () => {
  const emptyMenu = []
  const rootMenu = withSuperadminAccessFallback(emptyMenu, 'superadmin')
  assert.deepEqual(rootMenu.map((item) => item.route_name), ['admin.access'])
  assert.equal(rootMenu[0].role_codes[0], 'superadmin')
  assert.strictEqual(withSuperadminAccessFallback(emptyMenu, 'admin'), emptyMenu)

  const configured = [{ ...rootMenu[0], id: 42, label: 'Configurado' }]
  assert.strictEqual(withSuperadminAccessFallback(configured, 'superadmin'), configured)
})

test('navigation selectors expose unconfigured routes and preserve the current edit route', () => {
  const routes = [
    { value: 'customer.orders', label: 'Mis pedidos', role_codes: ['customer'] },
    { value: 'admin.products', label: 'Productos', role_codes: ['admin', 'superadmin'] },
  ]
  const current = {
    id: 4, label: 'Mis pedidos', route_name: 'customer.orders', anchor: '', description: '',
    role_codes: ['customer'], permission_resource: null, permission_action: null, order: 10, active: true,
  }
  const configured = [{ ...current }]

  assert.deepEqual(navigationRoutesForCreate(routes, configured).map(({ value, configured: used }) => [value, used]), [
    ['customer.orders', true], ['admin.products', false],
  ])
  const editOptions = navigationRoutesForEdit(routes.slice(1), configured, current)
  assert.deepEqual(editOptions.map(({ value, configured: used }) => [value, used]), [
    ['customer.orders', false], ['admin.products', false],
  ])
  assert.deepEqual(editOptions[0].role_codes, ['customer'])
  assert.deepEqual(rolesAllowedForRoute(['customer', 'admin'], routes[0].role_codes), ['customer'])
})
