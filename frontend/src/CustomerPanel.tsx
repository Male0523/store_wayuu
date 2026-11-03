import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { ArrowLeft, Heart, Home, LogOut, Minus, Plus, Search, ShoppingBag, ShoppingCart, UserRound, X } from 'lucide-react'
import { api, ApiError } from './lib/api'
import { useUserSession } from './context/user-context'
import type { Cart, Category, Order, Product, UserProfile } from './types'
import './CustomerPanel.css'

type View = 'catalog' | 'favorites' | 'cart' | 'account' | 'detail'
const money = (value: string | number) => new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(Number(value || 0))
const messageOf = (error: unknown) => error instanceof ApiError ? error.message : 'No fue posible completar la operación. Comprueba que Django esté activo e inténtalo de nuevo.'

export default function CustomerPanel() {
  const { user, logout } = useUserSession()
  const [view, setView] = useState<View>('catalog')
  const [previousView, setPreviousView] = useState<View>('catalog')
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [cart, setCart] = useState<Cart>({ items: [], total: '0', count: 0 })
  const [orders, setOrders] = useState<Order[]>([])
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [selected, setSelected] = useState<Product | null>(null)
  const [favorites, setFavorites] = useState<number[]>([])
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('Todas')
  const [sort, setSort] = useState('default')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [checkoutOpen, setCheckoutOpen] = useState(false)
  const [address, setAddress] = useState('')
  const [city, setCity] = useState('')
  const [payment, setPayment] = useState('contact')
  const [notes, setNotes] = useState('')
  const [completed, setCompleted] = useState<Order | null>(null)
  const [profileEditing, setProfileEditing] = useState(false)

  useEffect(() => {
    let active = true
    const params = new URLSearchParams({ page_size: '100', ordering: 'name' })
    Promise.all([api.products(params), api.categories()]).then(([page, list]) => {
      if (!active) return
      setProducts(page.results)
      setCategories(list)
    }).catch((error) => { if (active) setNotice(messageOf(error)) })
    if (user?.role === 'customer') {
      api.cart().then((value) => { if (active) setCart(value) }).catch((error) => { if (active) setNotice(messageOf(error)) })
      api.profile().then((value) => {
        if (!active) return
        setProfile(value)
        setAddress(value.address ?? '')
        setCity(value.city ?? '')
      }).catch((error) => { if (active) setNotice(messageOf(error)) })
    }
    return () => { active = false }
  }, [user?.id, user?.role])

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(''), 4000)
    return () => window.clearTimeout(timer)
  }, [notice])

  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase()
    return products.filter((item) => {
      const matchesText = !needle || [item.name, item.description, item.region, item.craftswoman?.name].some((value) => value?.toLocaleLowerCase().includes(needle))
      const matchesCategory = category === 'Todas' || item.category?.name === category
      return matchesText && matchesCategory
    }).sort((a, b) => sort === 'low' ? Number(a.price) - Number(b.price) : sort === 'high' ? Number(b.price) - Number(a.price) : a.name.localeCompare(b.name))
  }, [products, query, category, sort])

  const favoriteProducts = products.filter((item) => favorites.includes(item.id))

  async function refreshCart() {
    const value = await api.cart()
    setCart(value)
  }

  async function addItem(product: Product, quantity = 1) {
    setBusy(true)
    try {
      await api.addToCart(product.id, quantity)
      await refreshCart()
      setNotice('Producto agregado al carrito.')
      setSelected(null)
    } catch (error) { setNotice(messageOf(error)) } finally { setBusy(false) }
  }

  async function changeQuantity(productId: number, quantity: number) {
    setBusy(true)
    try {
      if (quantity < 1) await api.removeFromCart(productId)
      else await api.setCartQuantity(productId, quantity)
      await refreshCart()
    } catch (error) { setNotice(messageOf(error)) } finally { setBusy(false) }
  }

  async function openAccount() {
    setBusy(true)
    try {
      const [page, data] = await Promise.all([api.orders(), api.profile()])
      setOrders(page.results)
      setProfile(data)
      setView('account')
    } catch (error) { setNotice(messageOf(error)) } finally { setBusy(false) }
  }

  async function submitCheckout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    try {
      const order = await api.checkout({ address, city, payment_method: payment, notes })
      setCompleted(order)
      await refreshCart()
      setCheckoutOpen(false)
      setNotes('')
    } catch (error) { setNotice(messageOf(error)) } finally { setBusy(false) }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!profile) return
    const form = new FormData(event.currentTarget)
    setBusy(true)
    try {
      const updated = await api.updateProfile({
        name: String(form.get('name') ?? ''),
        phone: String(form.get('phone') ?? ''),
        address: String(form.get('address') ?? ''),
        city: String(form.get('city') ?? ''),
      })
      setProfile(updated)
      setAddress(updated.address ?? '')
      setCity(updated.city ?? '')
      setProfileEditing(false)
      window.dispatchEvent(new Event('wayuu:session-change'))
      setNotice('Perfil actualizado correctamente.')
    } catch (error) { setNotice(messageOf(error)) } finally { setBusy(false) }
  }

  async function signOut() {
    setBusy(true)
    try {
      await logout()
      window.history.pushState(null, '', '/')
      window.dispatchEvent(new PopStateEvent('popstate'))
    } catch (error) { setNotice(messageOf(error)) } finally { setBusy(false) }
  }

  function navigate(next: View) {
    setView(next)
    setSelected(null)
  }

  const fullName = profile?.name || user?.name || user?.username || 'Cliente'

  return <div className="customer-shell">
    <aside className="customer-sidebar">
      <div className="customer-brand"><span className="customer-brand-mark">◇</span><div><strong>Wayúu</strong><small>Portal del Cliente</small></div></div>
      <div className="customer-nav-label">NAVEGACIÓN PRINCIPAL</div>
      <nav className="customer-nav">
        <button className={view === 'catalog' || view === 'detail' ? 'active' : ''} onClick={() => navigate('catalog')}><Home size={17}/>Inicio y catálogo</button>
        <button className={view === 'favorites' ? 'active' : ''} onClick={() => navigate('favorites')}><Heart size={17}/>Mis favoritos</button>
        <button className={view === 'cart' ? 'active' : ''} onClick={() => navigate('cart')}><ShoppingCart size={17}/>Mi carrito <span>{cart.count}</span></button>
        <button className={view === 'account' ? 'active' : ''} onClick={openAccount}><UserRound size={17}/>Mi cuenta y pedidos</button>
      </nav>
      <div className="customer-sidebar-bottom"><div className="customer-user"><span className="customer-avatar">{fullName.slice(0,1).toUpperCase()}</span><div><strong>{fullName}</strong><small>Cliente</small></div></div><button className="customer-logout" onClick={signOut} disabled={busy}><LogOut size={16}/>Cerrar sesión</button></div>
    </aside>

    <main className="customer-main">
      <header className="customer-topbar"><div><span className="customer-kicker">TIENDA ARTESANAL WAYÚU</span><h1>{view === 'catalog' ? 'Descubre nuestras piezas' : view === 'favorites' ? 'Mis favoritos' : view === 'cart' ? 'Mi carrito' : view === 'account' ? 'Mi cuenta y pedidos' : selected?.name}</h1></div><label className="customer-search"><Search size={17}/><input value={query} onChange={(event) => { setQuery(event.target.value); setView('catalog') }} placeholder="Buscar piezas..." /></label></header>
      {notice && <div className="customer-notice" role="status">{notice}<button onClick={() => setNotice('')} aria-label="Cerrar aviso"><X size={15}/></button></div>}

      {(view === 'catalog' || view === 'favorites') && <>
        <section className="customer-welcome"><div><span>HECHO A MANO, CON IDENTIDAD</span><h2>Tradición que se teje<br/>con cada hilo.</h2><p>Explora piezas artesanales elaboradas por manos Wayúu.</p><button onClick={() => navigate('catalog')}>Explorar colección <ArrowLeft size={15}/></button></div><div className="customer-welcome-art" aria-hidden="true"><span>✳</span><span>✳</span><span>◇</span></div></section>
        <section className="customer-products-section">
          <div className="customer-section-heading"><div><span className="customer-kicker">{view === 'favorites' ? 'TU SELECCIÓN' : 'COLECCIÓN DISPONIBLE'}</span><h2>{view === 'favorites' ? 'Piezas que guardaste' : 'Encuentra tu próxima pieza'}</h2></div><span>{(view === 'favorites' ? favoriteProducts : filtered).length} productos</span></div>
          {view === 'catalog' && <div className="customer-filters"><div className="customer-category-tabs"><button className={category === 'Todas' ? 'active' : ''} onClick={() => setCategory('Todas')}>Todas</button>{categories.map((item) => <button key={item.id} className={category === item.name ? 'active' : ''} onClick={() => setCategory(item.name)}>{item.name}</button>)}</div><select value={sort} onChange={(event) => setSort(event.target.value)} aria-label="Ordenar productos"><option value="default">Orden alfabético</option><option value="low">Menor precio</option><option value="high">Mayor precio</option></select></div>}
          {view === 'favorites' && <p className="customer-muted">Los favoritos se conservan durante esta sesión; todavía no existe sincronización de favoritos en Django.</p>}
          {view === 'catalog' && !products.length && <p className="customer-empty">No hay productos disponibles en el catálogo todavía.</p>}
          {view === 'favorites' && !favoriteProducts.length && <p className="customer-empty">Aún no has guardado favoritos en esta sesión.</p>}
          <div className="customer-product-grid">{(view === 'favorites' ? favoriteProducts : filtered).map((item) => <article className="customer-product-card" key={item.id}>
            <button className="customer-product-image" onClick={() => { setSelected(item); setPreviousView(view) }}><img src={item.image_url || ''} alt={item.name} onError={(event) => { event.currentTarget.style.display = 'none' }}/><span>{item.category?.name || 'Artesanía'}</span></button>
            <div className="customer-product-copy"><small>{item.region || 'La Guajira'}</small><h3>{item.name}</h3><p>{money(item.price)}</p><div><button onClick={() => { setSelected(item); setPreviousView(view) }}>Ver detalle</button><button aria-label="Agregar a favoritos" className={favorites.includes(item.id) ? 'saved' : ''} onClick={() => setFavorites((old) => old.includes(item.id) ? old.filter((id) => id !== item.id) : [...old, item.id])}><Heart size={17} fill={favorites.includes(item.id) ? 'currentColor' : 'none'}/></button></div></div>
          </article>)}</div>
        </section>
      </>}

      {view === 'detail' && selected && <section className="customer-detail"><button className="customer-back" onClick={() => setView(previousView)}><ArrowLeft size={16}/>Volver</button><div className="customer-detail-card"><div className="customer-detail-image"><img src={selected.image_url || ''} alt={selected.name}/></div><div className="customer-detail-copy"><span className="customer-kicker">{selected.category?.name || 'Artesanía Wayúu'}</span><h2>{selected.name}</h2><strong>{money(selected.price)}</strong><p>{selected.description || 'Pieza artesanal elaborada en La Guajira.'}</p><dl><div><dt>Origen</dt><dd>{selected.region || 'La Guajira'}</dd></div><div><dt>Color</dt><dd>{selected.color || 'Consultar disponibilidad'}</dd></div><div><dt>Talla</dt><dd>{selected.size || 'Consultar'}</dd></div><div><dt>Disponibles</dt><dd>{selected.stock}</dd></div></dl><button className="customer-primary" disabled={busy || selected.stock < 1} onClick={() => addItem(selected)}><ShoppingBag size={17}/>Agregar al carrito</button></div></div></section>}

      {view === 'cart' && <section className="customer-account-section"><div className="customer-section-heading"><div><span className="customer-kicker">RESUMEN DE COMPRA</span><h2>Tu carrito</h2></div><span>{cart.count} unidades</span></div>{!cart.items.length ? <p className="customer-empty">Tu carrito está vacío. Explora el catálogo para encontrar una pieza.</p> : <><div className="customer-cart-list">{cart.items.map((item) => <article className="customer-cart-row" key={item.product.id}><img src={item.product.image_url || ''} alt={item.product.name}/><div><h3>{item.product.name}</h3><p>{money(item.product.price)}</p><div className="customer-quantity"><button onClick={() => changeQuantity(item.product.id, item.quantity - 1)} disabled={busy}><Minus size={14}/></button><span>{item.quantity}</span><button onClick={() => changeQuantity(item.product.id, item.quantity + 1)} disabled={busy}><Plus size={14}/></button></div></div><strong>{money(item.subtotal)}</strong><button className="customer-remove" onClick={() => changeQuantity(item.product.id, 0)} aria-label="Retirar producto" disabled={busy}><X size={17}/></button></article>)}</div><div className="customer-cart-total"><span>Total de productos</span><strong>{money(cart.total)}</strong></div><button className="customer-primary" disabled={busy} onClick={() => setCheckoutOpen(true)}>Continuar con la compra</button></>}</section>}

      {view === 'account' && <section className="customer-account-section"><div className="customer-section-heading"><div><span className="customer-kicker">TU ACTIVIDAD</span><h2>Mis pedidos</h2></div><span>{orders.length} pedidos</span></div>{!orders.length ? <p className="customer-empty">Aún no tienes pedidos registrados.</p> : <div className="customer-order-list">{orders.map((order) => <article className="customer-order-card" key={order.id}><div><small>PEDIDO #{order.id} · {new Date(order.created_at).toLocaleDateString('es-CO')}</small><h3>{order.items.map((item) => item.product.name).join(', ')}</h3><p>{order.items.reduce((sum, item) => sum + item.quantity, 0)} unidades · {money(order.total)}</p></div><span className="customer-order-status">{order.status_label || order.status}</span></article>)}</div>}
        <div className="customer-profile-block"><div className="customer-section-heading"><div><span className="customer-kicker">DATOS PERSONALES</span><h2>Mi perfil</h2></div><button className="customer-text-button" onClick={() => setProfileEditing((value) => !value)}>{profileEditing ? 'Cancelar' : 'Editar datos'}</button></div>{profile && (profileEditing ? <form className="customer-profile-form" onSubmit={saveProfile}><label>Nombre completo<input name="name" defaultValue={profile.name}/></label><label>Teléfono<input name="phone" defaultValue={profile.phone || ''}/></label><label>Dirección<input name="address" defaultValue={profile.address || ''}/></label><label>Ciudad<input name="city" defaultValue={profile.city || ''}/></label><button className="customer-primary" disabled={busy}>Guardar cambios</button></form> : <div className="customer-profile-grid"><p><small>Nombre</small>{profile.name}</p><p><small>Correo</small>{profile.email}</p><p><small>Teléfono</small>{profile.phone || 'Sin registrar'}</p><p><small>Dirección</small>{profile.address || 'Sin registrar'}</p><p><small>Ciudad</small>{profile.city || 'Sin registrar'}</p></div>)}</div>
      </section>}

    </main>

    {checkoutOpen && <div className="customer-modal-backdrop"><form className="customer-modal" onSubmit={submitCheckout}><button type="button" className="customer-modal-close" onClick={() => setCheckoutOpen(false)}><X size={19}/></button><span className="customer-kicker">FINALIZAR COMPRA</span><h2>Datos de entrega</h2><label>Dirección<input required value={address} onChange={(event) => setAddress(event.target.value)}/></label><label>Ciudad<input required value={city} onChange={(event) => setCity(event.target.value)}/></label><label>Método de pago<select value={payment} onChange={(event) => setPayment(event.target.value)}><option value="contact">Coordinar con la tienda</option><option value="nequi">Nequi</option><option value="daviplata">Daviplata</option><option value="bancolombia">Bancolombia</option><option value="whatsapp">WhatsApp</option></select></label><label>Notas (opcional)<textarea value={notes} onChange={(event) => setNotes(event.target.value)}/></label><div className="customer-cart-total"><span>Total</span><strong>{money(cart.total)}</strong></div><button className="customer-primary" disabled={busy}>{busy ? 'Procesando…' : 'Confirmar pedido'}</button><p className="customer-small-note">El pedido se registra en Django. Este paso no procesa cobros bancarios automáticamente.</p></form></div>}

    {completed && <div className="customer-modal-backdrop"><div className="customer-modal customer-success"><span className="customer-success-mark">✓</span><span className="customer-kicker">PEDIDO REGISTRADO</span><h2>¡Gracias por tu compra!</h2><p>Tu pedido #{completed.id} fue registrado correctamente.</p><div className="customer-cart-total"><span>Total del pedido</span><strong>{money(completed.total)}</strong></div><button className="customer-primary" onClick={() => { setCompleted(null); void openAccount() }}>Ver mis pedidos</button><button className="customer-text-button" onClick={() => setCompleted(null)}>Seguir comprando</button></div></div>}

    {notice && <div className="customer-toast">{notice}<button onClick={() => setNotice('')}><X size={14}/></button></div>}
  </div>
}
