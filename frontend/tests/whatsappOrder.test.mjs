import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { buildWhatsAppOrderMessage, buildWhatsAppOrderUrl } from '../src/lib/whatsappOrder.ts'

const customerPanelSource = await readFile(new URL('../src/CustomerPanel.tsx', import.meta.url), 'utf8')
const shopAppSource = await readFile(new URL('../src/ShopApp.tsx', import.meta.url), 'utf8')

const order = {
  id: 42,
  customer_id: 9,
  customer_name: 'María Alejandra Ñáñez',
  status: 'pending',
  status_label: 'Pendiente',
  payment_method: 'whatsapp',
  shipping_address: 'Dirección privada que no debe enviarse',
  notes: 'Nota privada que no debe enviarse',
  created_at: '2026-11-23T10:00:00Z',
  updated_at: '2026-11-23T10:00:00Z',
  items: [
    { id: 1, product: { id: 1, name: 'Manta ñandú & sol', image_url: '', price: '50000' }, quantity: 2, unit_price: '50000', subtotal: '100000', craftswoman: null, craftswoman_name: null, status: 'pending', status_label: 'Pendiente', allowed_statuses: [] },
    { id: 2, product: { id: 2, name: 'Mochila Wayúu', image_url: '', price: '75000' }, quantity: 1, unit_price: '75000', subtotal: '75000', craftswoman: null, craftswoman_name: null, status: 'pending', status_label: 'Pendiente', allowed_statuses: [] },
  ],
  total: '175000',
  craftswoman: null,
  allowed_statuses: [],
}

test('builds the summary from the confirmed order id, every line and server totals', () => {
  const message = buildWhatsAppOrderMessage(order)

  assert.match(message, /Pedido: #42/)
  assert.match(message, /Manta ñandú & sol x2/)
  assert.match(message, /Unitario: .*50\.000/)
  assert.match(message, /Subtotal: .*100\.000/)
  assert.match(message, /Mochila Wayúu x1/)
  assert.match(message, /Subtotal: .*75\.000/)
  assert.match(message, /TOTAL: .*175\.000/)
  assert.match(message, /Nombre: María Alejandra Ñáñez/)
  assert.doesNotMatch(message, /Dirección privada|Nota privada/)
})

test('uses the Colombian store destination and correctly encodes accents and line breaks', () => {
  const url = new URL(buildWhatsAppOrderUrl(order))

  assert.equal(url.origin + url.pathname, 'https://wa.me/573127768141')
  assert.equal(url.searchParams.get('text'), buildWhatsAppOrderMessage(order))
  assert.match(url.search, /%C3%B1|%C3%B1/i)
  assert.match(url.search, /%0A/)
})

test('only creates a WhatsApp URL for a pending order and never mutates its state', () => {
  assert.equal(buildWhatsAppOrderUrl({ ...order, status: 'preparing' }), null)
  assert.equal(order.status, 'pending')
})

test('adds WhatsApp only to successful React confirmations without replacing existing actions', () => {
  assert.match(customerPanelSource, /const order = await api\.checkout\([\s\S]*?setCompleted\(order\)/)
  assert.match(customerPanelSource, /completed\.status === 'pending'[\s\S]*?buildWhatsAppOrderUrl\(completed\)/)
  assert.match(customerPanelSource, /Ver mis pedidos/)
  assert.match(customerPanelSource, /Seguir comprando/)

  assert.match(shopAppSource, /const order = await api\.checkout\([\s\S]*?setCompletedOrder\(order\)/)
  assert.match(shopAppSource, /order\.status === 'pending'[\s\S]*?buildWhatsAppOrderUrl\(order\)/)
  assert.match(shopAppSource, /Seguir mi pedido/)
  assert.match(shopAppSource, /Volver a la tienda/)
  assert.doesNotMatch(shopAppSource, /buildWhatsAppOrderUrl\(order\)[^}]*api\.checkout/)
})
