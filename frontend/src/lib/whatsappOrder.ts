import type { Order } from '../types'

const WHATSAPP_ORDER_NUMBER = '573127768141'

const cop = (value: string | number) => new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
}).format(Number(value))

export function buildWhatsAppOrderMessage(order: Order): string {
  const products = order.items.map((item) =>
    `- ${item.product.name} x${item.quantity} — Unitario: ${cop(item.unit_price)} — Subtotal: ${cop(item.subtotal)}`,
  )

  return [
    '¡Hola! Quiero realizar un pedido en Tienda Wayúu.',
    '',
    'RESUMEN DEL PEDIDO',
    `Pedido: #${order.id}`,
    '',
    'PRODUCTOS:',
    ...products,
    '',
    `TOTAL: ${cop(order.total)}`,
    '',
    'DATOS DEL CLIENTE:',
    `Nombre: ${order.customer_name}`,
    '',
    'Quedo pendiente de la revisión y confirmación de mi pedido.',
  ].join('\n')
}

export function buildWhatsAppOrderUrl(order: Order): string | null {
  if (order.status !== 'pending') return null
  return `https://wa.me/${WHATSAPP_ORDER_NUMBER}?text=${encodeURIComponent(buildWhatsAppOrderMessage(order))}`
}
