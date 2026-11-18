import type { Cart } from './types'
import './LegacyCartNotice.css'

export default function LegacyCartNotice({
  items,
  busy,
  onRemove,
}: {
  items: Cart['legacy_items']
  busy: boolean
  onRemove: (key: string) => void
}) {
  if (!items?.length) return null

  return <div className="legacy-cart-notice" role="status">
    <p>Algunos elementos de un carrito anterior no se pudieron recuperar. Puedes retirarlos aquí; tus productos guardados no cambiarán.</p>
    <ul>{items.map((item) => <li key={item.key}>
      <span>{item.label}</span>
      <button type="button" onClick={() => onRemove(item.key)} disabled={busy}>Retirar</button>
    </li>)}</ul>
  </div>
}
