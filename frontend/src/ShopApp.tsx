import { useCallback, useDeferredValue, useEffect, useRef, useState, type CSSProperties, type FormEvent } from 'react'
import {
  ArrowDown, ArrowLeft, ArrowRight, ArrowUpRight, Check, ChevronDown, Eye,
  Camera, CircleUserRound, Heart, LoaderCircle, LockKeyhole, Minus,
  Plus, Search, ShoppingBag, SlidersHorizontal, Trash2, X,
  LayoutDashboard, Boxes, Layers, LogOut, Sparkles, ShoppingCart,
} from 'lucide-react'
import { api, ApiError } from './lib/api'
import { useUserSession } from './context/user-context'
import type { AdminCategory, AdminProduct, AuditEvent, Cart, Category, CustomDesign, CraftswomanDashboard, Order, Product, RBACDelegation, RBACNavigationItem, RBACPermission, RBACRolePermissions, RBACUserPermissions, SessionUser, SuperadminUser, SuperadminUserInput, UserProfile } from './types'
import './ShopApp.css'

type Screen = 'shop' | 'orders' | 'craftswoman' | 'design' | 'admin'
type AuthMode = 'login' | 'register' | 'craftswoman'
type AccountSection = 'orders' | 'designs' | 'profile'

type ShopAppProps = {
  initialScreen?: Screen
}

export function ConnectedShop({ initialScreen = 'shop' }: ShopAppProps) {
  return <ShopApp initialScreen={initialScreen} />
}

export default ConnectedShop

const money = (value: string | number) => new Intl.NumberFormat('es-CO', {
  style: 'currency', currency: 'COP', maximumFractionDigits: 0,
}).format(Number(value))

const dateLabel = (value: string) => new Intl.DateTimeFormat('es-CO', {
  day: 'numeric', month: 'short', year: 'numeric',
}).format(new Date(value))

const orderStatusLabels: Record<string, string> = {
  pending: 'Pendiente', accepted: 'Aceptado', weaving: 'En tejido', completed: 'Tejido terminado',
  paid: 'Pagado', preparing: 'En preparación', shipped: 'Enviado', delivered: 'Entregado', cancelled: 'Cancelado',
}

const statusLabel = (status: string) => orderStatusLabels[status] ?? status

function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message
  return 'No pudimos conectar con la tienda. Revisa que el servidor esté activo e intenta otra vez.'
}

function hasEffectivePermission(user: SessionUser, permission: string) {
  return user.permissions?.includes(permission) ?? false
}

type SessionUserWithNames = SessionUser & {
  first_name?: string
  last_name?: string
}

function resolveUserDisplayName(user: SessionUser | null | undefined, profile: UserProfile | null | undefined = null) {
  const sessionUser = user as SessionUserWithNames | null | undefined
  const firstName = (sessionUser?.first_name ?? '').trim()
  const lastName = (sessionUser?.last_name ?? '').trim()
  const combinedName = [firstName, lastName].filter(Boolean).join(' ').trim()
  if (combinedName) return combinedName

  const sessionName = (user?.name ?? '').trim()
  if (sessionName) return sessionName

  const username = (user?.username ?? '').trim()
  if (username) return username

  const profileName = (profile?.name ?? '').trim() || (user?.profile?.name ?? '').trim()
  if (profileName) return profileName

  return 'Usuario'
}

function ShopApp({ initialScreen = 'shop' }: ShopAppProps) {
  const { user, login: loginUser, register: registerUser, logout: logoutUser } = useUserSession()
  const [screen, setScreen] = useState<Screen>(initialScreen)
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [cart, setCart] = useState<Cart | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [adminProducts, setAdminProducts] = useState<AdminProduct[]>([])
  const [adminCategories, setAdminCategories] = useState<AdminCategory[]>([])
  const [designs, setDesigns] = useState<CustomDesign[]>([])
  const [profileDraft, setProfileDraft] = useState<UserProfile | null>(null)
  const [accountSection, setAccountSection] = useState<AccountSection>('orders')
  const [dashboard, setDashboard] = useState<CraftswomanDashboard | null>(null)
  const [craftswomanProducts, setCraftswomanProducts] = useState<Product[]>([])
  const [roleNavigation, setRoleNavigation] = useState<RBACNavigationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [catalogError, setCatalogError] = useState('')
  const [notice, setNotice] = useState('')
  const [query, setQuery] = useState('')
  const deferredQuery = useDeferredValue(query)
  const [categoryId, setCategoryId] = useState('all')
  const [colorFilter, setColorFilter] = useState('')
  const [sort, setSort] = useState('name')
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
  const [cartOpen, setCartOpen] = useState(false)
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState<AuthMode>('login')
  const [pendingProduct, setPendingProduct] = useState<number | null>(null)
  const [checkoutOpen, setCheckoutOpen] = useState(false)
  const [checkoutAddress, setCheckoutAddress] = useState('')
  const [checkoutCity, setCheckoutCity] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('contact')
  const [checkoutNotes, setCheckoutNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const cartMutations = useRef<Promise<void>>(Promise.resolve())
  const [completedOrder, setCompletedOrder] = useState<Order | null>(null)
  const [designPattern, setDesignPattern] = useState('rombos')
  const [designSize, setDesignSize] = useState('M')
  const [designQuantity, setDesignQuantity] = useState(1)
  const [designColors, setDesignColors] = useState(['#b77f86', '#d4b9a2', '#87978c'])
  const [designNotes, setDesignNotes] = useState('')
  const featuredProduct = products.find((product) => product.image_url) ?? products[0]
  const customPrice = ({ S: 100000, M: 120000, L: 145000, XL: 175000 }[designSize] ?? 120000) * designQuantity
  const canRequestDesign = !user || hasEffectivePermission(user, 'designs.add')

  useEffect(() => {
    setProfileDraft(null)
  }, [user?.id, user?.email, user?.username, user?.role])

  useEffect(() => {
    let active = true
    if (!user) { setRoleNavigation([]); return }
    api.roleNavigation().then((items) => { if (active) setRoleNavigation(items) }).catch(() => { if (active) setRoleNavigation([]) })
    return () => { active = false }
  }, [user?.id, user?.role, user?.permissions?.join('|')])

  const loadAdminData = useCallback(async () => {
    if (!user || (user.role !== 'admin' && user.role !== 'superadmin')) return

    const emptyOrderPage: { count: number; next: string | null; previous: string | null; results: Order[] } = {
      count: 0,
      next: null,
      previous: null,
      results: [],
    }
    const requests: [
      Promise<{ count: number; next: string | null; previous: string | null; results: Order[] }>,
      Promise<AdminProduct[]>,
      Promise<AdminCategory[]>,
    ] = [
      hasEffectivePermission(user, 'orders.view') ? api.orders() : Promise.resolve(emptyOrderPage),
      hasEffectivePermission(user, 'products.view') ? api.adminProducts() : Promise.resolve([]),
      hasEffectivePermission(user, 'categories.view') ? api.adminCategories() : Promise.resolve([]),
    ]

    try {
      const [orderPage, productsPage, categoryList] = await Promise.all(requests)
      const nextOrders = Array.isArray(orderPage?.results) ? orderPage.results : []
      setOrders(nextOrders)
      setAdminProducts(Array.isArray(productsPage) ? productsPage : [])
      setAdminCategories(Array.isArray(categoryList) ? categoryList : [])
    } catch (error) {
      setNotice(errorMessage(error))
    }
  }, [user])

  useEffect(() => {
    let active = true
    api.categories().then((data) => { if (active) setCategories(data) }).catch(() => undefined)
    return () => { active = false }
  }, [])

  useEffect(() => {
    let active = true
    if (user?.role !== 'customer') {
      return () => { active = false }
    }
    api.profile().then((profile) => {
      if (!active) return
      setCheckoutAddress(profile.address ?? '')
      setCheckoutCity(profile.city ?? '')
    }).catch(() => undefined)
    api.cart().then((nextCart) => { if (active) setCart(nextCart) }).catch(() => { if (active) setCart(null) })
    return () => { active = false }
  }, [user])

  useEffect(() => {
    if (initialScreen !== 'craftswoman' || user?.role !== 'craftswoman') return

    let cancelled = false
    const loadDashboard = async () => {
      try {
        const [data, ownProducts] = await Promise.all([
          api.craftswomanDashboard(),
          api.craftswomanProducts(),
        ])
        if (cancelled) return
        setDashboard(data)
        setCraftswomanProducts(ownProducts)
        setScreen('craftswoman')
      } catch (error) {
        if (!cancelled) setNotice(errorMessage(error))
      }
    }

    void loadDashboard()
    return () => { cancelled = true }
  }, [initialScreen, user])

  useEffect(() => {
    if (initialScreen !== 'admin' || !user || (user.role !== 'admin' && user.role !== 'superadmin')) return

    let cancelled = false
    const run = async () => {
      try {
        await loadAdminData()
      } catch (error) {
        if (!cancelled) setNotice(errorMessage(error))
      }
    }

    void run()
    return () => { cancelled = true }
  }, [initialScreen, loadAdminData, user])

  useEffect(() => {
    let active = true
    const params = new URLSearchParams({ page_size: '100', ordering: sort })
    if (deferredQuery.trim()) params.set('search', deferredQuery.trim())
    if (categoryId !== 'all') params.set('category', categoryId)
    if (colorFilter) params.set('color', colorFilter)
    api.products(params).then((page) => {
      if (!active) return
      setProducts(page.results)
      setCatalogError('')
      setLoading(false)
    }).catch((error: unknown) => {
      if (!active) return
      setCatalogError(errorMessage(error))
      setLoading(false)
    })
    return () => { active = false }
  }, [deferredQuery, categoryId, colorFilter, sort])

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(''), 3400)
    return () => window.clearTimeout(timer)
  }, [notice])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSelectedProduct(null)
        setAuthOpen(false)
        setCartOpen(false)
        setCompletedOrder(null)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  async function refreshCart() {
    const nextCart = await api.cart()
    setCart(nextCart)
    return nextCart
  }

  async function addToCart(productId: number) {
    if (!user || user.role !== 'customer') {
      setPendingProduct(productId)
      setAuthMode('login')
      setAuthOpen(true)
      setNotice('Inicia sesión como cliente para agregar una pieza al carrito.')
      return
    }
    setBusy(true)
    try {
      await api.addToCart(productId)
      await refreshCart()
      setNotice('La pieza quedó en tu carrito.')
      setSelectedProduct(null)
    } catch (error) {
      setNotice(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  async function changeQuantity(productId: number, quantity: number) {
    const mutation = cartMutations.current.then(async () => {
      if (quantity < 1) await api.removeFromCart(productId)
      else await api.setCartQuantity(productId, quantity)
      await refreshCart()
    })
    cartMutations.current = mutation.catch(() => undefined)
    try {
      await mutation
    } catch (error) {
      setNotice(errorMessage(error))
    }
  }

  async function openCart() {
    if (!user || user.role !== 'customer') {
      setAuthMode('login')
      setAuthOpen(true)
      setNotice('Inicia sesión para consultar tu carrito y tus pedidos.')
      return
    }
    try { await refreshCart() } catch (error) { setNotice(errorMessage(error)) }
    setCheckoutOpen(false)
    setCartOpen(true)
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    const values = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<string, string>
    try {
      const account = authMode === 'login'
        ? await loginUser(values.username, values.password)
        : await registerUser(values, authMode === 'craftswoman')
      setProfileDraft(null)
      setAuthOpen(false)
      setNotice(authMode === 'craftswoman' ? 'Solicitud enviada. La cuenta debe ser activada por administración.' : 'Sesión iniciada.')
      if (account.role === 'customer') {
        setCheckoutAddress(account.profile?.address ?? '')
        setCheckoutCity(account.profile?.city ?? '')
        try { await refreshCart() } catch { setCart(null) }
        if (pendingProduct !== null) {
          const productId = pendingProduct
          setPendingProduct(null)
          await api.addToCart(productId)
          await refreshCart()
          setCartOpen(true)
        }
      } else {
        setCart(null)
      }
    } catch (error) { setNotice(errorMessage(error)) } finally { setBusy(false) }
  }

  async function signOut() {
    try { await logoutUser() } catch (error) {
      setNotice(errorMessage(error))
      return
    }
    setCart(null)
    setOrders([])
    setDesigns([])
    setProfileDraft(null)
    setDashboard(null)
    setScreen('shop')
    setNotice('Sesión cerrada.')
  }

  async function openAccount() {
    if (!user) {
      setAuthMode('login')
      setAuthOpen(true)
      return
    }
    setProfileDraft(null)
    setBusy(true)
    try {
      const configuredNavigation = await api.roleNavigation()
      setRoleNavigation(configuredNavigation)
      if (user.role === 'admin' || user.role === 'superadmin') {
        await loadAdminData()
        setScreen('admin')
      } else if (user.role === 'craftswoman') {
        const visibleRoutes = configuredNavigation.map((item) => item.route_name)
        const [craftswomanDashboard, ownProducts] = await Promise.all([
          visibleRoutes.includes('craftswoman.dashboard') || visibleRoutes.includes('craftswoman.orders') ? api.craftswomanDashboard() : Promise.resolve(null),
          visibleRoutes.some((route) => ['craftswoman.dashboard', 'craftswoman.products', 'craftswoman.inventory'].includes(route)) ? api.craftswomanProducts() : Promise.resolve([]),
        ])
        setDashboard(craftswomanDashboard)
        setCraftswomanProducts(ownProducts)
        setScreen('craftswoman')
      } else {
        const visibleRoutes = roleNavigation.map((item) => item.route_name)
        const requests = await Promise.all([
          visibleRoutes.includes('customer.orders') ? api.orders() : Promise.resolve({ results: [] as Order[] }),
          visibleRoutes.includes('customer.designs') ? api.designs() : Promise.resolve([] as CustomDesign[]),
          visibleRoutes.includes('customer.profile') ? api.profile() : Promise.resolve(null),
        ])
        const [orderPage, customerDesigns, customerProfile] = requests
        setOrders(orderPage.results)
        setDesigns(customerDesigns)
        setProfileDraft(customerProfile)
        const firstSection = configuredNavigation.find((item) => item.route_name.startsWith('customer.'))?.route_name.split('.')[1] as AccountSection | undefined
        setAccountSection(firstSection ?? 'orders')
        setScreen('orders')
      }
    } catch (error) { setNotice(errorMessage(error)) } finally { setBusy(false) }
  }

  async function submitCheckout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    try {
      const order = await api.checkout({ address: checkoutAddress, city: checkoutCity, payment_method: paymentMethod, notes: checkoutNotes })
      setCart({ items: [], total: '0', count: 0 })
      setCompletedOrder(order)
      setCartOpen(false)
      setCheckoutOpen(false)
      setCheckoutNotes('')
    } catch (error) { setNotice(errorMessage(error)) } finally { setBusy(false) }
  }

  async function createDesign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!user || user.role !== 'customer') {
      setAuthMode('login')
      setAuthOpen(true)
      setNotice('Inicia sesión como cliente para solicitar un diseño.')
      return
    }
    setBusy(true)
    try {
      await api.createDesign({
        pattern: designPattern,
        base_color: designColors[0],
        accent_color_one: designColors[1],
        accent_color_two: designColors[2],
        size: designSize,
        quantity: designQuantity,
        notes: designNotes,
      })
      await refreshCart()
      setCartOpen(true)
      setScreen('shop')
      setNotice('Diseño creado y agregado al carrito.')
    } catch (error) { setNotice(errorMessage(error)) } finally { setBusy(false) }
  }

  async function createCraftswomanProduct(values: {
    sku: string; name: string; category: number; description?: string; region?: string;
    color?: string; size?: string; production_time?: string; price: string | number;
    stock: number; image_url?: string; made_to_order?: boolean;
  }) {
    setBusy(true)
    try {
      const created = await api.createCraftswomanProduct(values)
      setCraftswomanProducts((current) => [created, ...current])
      setNotice('Producto enviado a revisión. El administrador debe aprobar su publicación.')
    } catch (error) {
      setNotice(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  async function acceptOrder(orderId: number) {
    try {
      await api.acceptOrder(orderId)
      setDashboard(await api.craftswomanDashboard())
      setNotice(`Pedido #${orderId} asignado a tu taller.`)
    } catch (error) { setNotice(errorMessage(error)) }
  }

  async function updateOrder(orderId: number, status: string) {
    try {
      await api.updateOrderStatus(orderId, status)
      setDashboard(await api.craftswomanDashboard())
      setNotice('Estado del pedido actualizado.')
    } catch (error) { setNotice(errorMessage(error)) }
  }

  async function updateDesignStatus(designId: number, status: string) {
    try {
      await api.updateDesignStatus(designId, status)
      setDashboard(await api.craftswomanDashboard())
      setNotice('Estado del diseño actualizado.')
    } catch (error) { setNotice(errorMessage(error)) }
  }

  async function saveAdminProduct(productId: number, values: Partial<AdminProduct>) {
    setBusy(true)
    try {
      const updated = await api.updateAdminProduct(productId, values)
      setAdminProducts((current) => current.map((product) => product.id === productId ? updated : product))
      setNotice('Producto actualizado.')
    } catch (error) { setNotice(errorMessage(error)) } finally { setBusy(false) }
  }

  async function createAdminProduct(values: Partial<AdminProduct>) {
    setBusy(true)
    try {
      const created = await api.createAdminProduct(values)
      setAdminProducts((current) => [created, ...current])
      setNotice('Producto agregado al catálogo.')
    } catch (error) { setNotice(errorMessage(error)) } finally { setBusy(false) }
  }

  async function createAdminCategory(values: Pick<AdminCategory, 'name' | 'description' | 'active'>) {
    setBusy(true)
    try {
      const created = await api.createAdminCategory(values)
      setAdminCategories((current) => [...current, created].sort((first, second) => first.name.localeCompare(second.name)))
      setCategories((current) => [...current, created].sort((first, second) => first.name.localeCompare(second.name)))
      setNotice('Categoría creada.')
    } catch (error) { setNotice(errorMessage(error)) } finally { setBusy(false) }
  }

  async function updateAdminCategory(categoryId: number, active: boolean) {
    setBusy(true)
    try {
      const updated = await api.updateAdminCategory(categoryId, { active })
      setAdminCategories((current) => current.map((category) => category.id === categoryId ? updated : category))
      setCategories((current) => active ? [...current.filter((category) => category.id !== categoryId), updated] : current.filter((category) => category.id !== categoryId))
      setNotice(`Categoría ${active ? 'activada' : 'desactivada'}.`)
    } catch (error) { setNotice(errorMessage(error)) } finally { setBusy(false) }
  }

  async function saveAdminOrderStatus(orderId: number, status: string) {
    setBusy(true)
    try {
      const updated = await api.updateAdminOrderStatus(orderId, status)
      setOrders((current) => current.map((order) => order.id === orderId ? updated : order))
      setNotice(`Pedido #${orderId} actualizado.`)
    } catch (error) { setNotice(errorMessage(error)) } finally { setBusy(false) }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!profileDraft) return
    setBusy(true)
    try {
      const values = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<string, string>
      const updated = await api.updateProfile(values)
      setProfileDraft(updated)
      window.dispatchEvent(new Event('wayuu:session-change'))
      setCheckoutAddress(updated.address ?? '')
      setCheckoutCity(updated.city ?? '')
      setNotice('Tus datos quedaron actualizados.')
    } catch (error) { setNotice(errorMessage(error)) } finally { setBusy(false) }
  }

  return <div className="app-shell">
    {screen !== 'craftswoman' && screen !== 'admin' && <header className="site-header">
      <button className="wordmark" onClick={() => setScreen('shop')} aria-label="Ir al inicio"><span className="wordmark-symbol" aria-hidden="true"><span /><span /><span /></span><span>wayuuwaa<small>TEJIDO CON ORIGEN</small></span></button>
      <nav className="main-nav" aria-label="Navegación principal"><button className={screen === 'shop' ? 'active' : ''} onClick={() => setScreen('shop')}>Colección</button>{canRequestDesign && <button className={screen === 'design' ? 'active' : ''} onClick={() => setScreen('design')}>Diseña tu manta</button>}<button className="nav-story" onClick={() => document.getElementById('origen')?.scrollIntoView({ behavior: 'smooth' })}>Nuestro origen</button></nav>
      <div className="header-actions"><label className="header-search" aria-label="Buscar en la colección"><Search size={17} /><input value={query} onChange={(event) => { setQuery(event.target.value); setScreen('shop') }} placeholder="Buscar" /></label><button className="icon-action account-action" onClick={openAccount} title={user ? `Cuenta de ${resolveUserDisplayName(user, profileDraft)}` : 'Iniciar sesión'} aria-label={user ? 'Abrir mi cuenta' : 'Iniciar sesión'}><CircleUserRound size={20} strokeWidth={1.6} /></button><button className="icon-action bag-action" onClick={openCart} title="Abrir carrito" aria-label="Abrir carrito"><ShoppingBag size={20} strokeWidth={1.6} /><span className="bag-count">{cart?.count ?? 0}</span></button></div>
    </header>}

    {screen === 'shop' && <>
      <main>
        <section className="hero" aria-label="Colección Wayuu"><div className="hero-copy"><p className="eyebrow"><span className="eyebrow-line" /> COLECCIÓN DE LA GUAJIRA</p><h1>El color también<br />cuenta <em>historias.</em></h1><p className="hero-description">Mantas tejidas a mano por mujeres Wayuu. Cada trama guarda una forma distinta de mirar el territorio.</p><button className="button button-dark" onClick={() => document.getElementById('coleccion')?.scrollIntoView({ behavior: 'smooth' })}>Explorar mantas <ArrowDown size={15} /></button></div><div className="hero-art">{featuredProduct?.image_url ? <img src={featuredProduct.image_url} alt={featuredProduct.name} /> : <div className="image-placeholder"><LoaderCircle className="spin" size={24} /></div>}<div className="hero-art-caption"><span>PIEZA DESTACADA</span><span>{featuredProduct?.name ?? 'Colección Wayuu'}</span></div></div></section>
        <section className="collection section-shell" id="coleccion"><div className="section-heading"><div><p className="eyebrow"><span className="eyebrow-line" /> LA COLECCIÓN</p><h2>Piezas para <em>habitar.</em></h2></div><p className="collection-intro">Cada manta nace del tiempo, la memoria y las manos que la tejen.</p></div>
          <div className="collection-toolbar"><div className="category-tabs" aria-label="Filtrar por categoría"><button className={categoryId === 'all' ? 'selected' : ''} onClick={() => setCategoryId('all')}>Todas</button>{categories.map((category) => <button key={category.id} className={categoryId === String(category.id) ? 'selected' : ''} onClick={() => setCategoryId(String(category.id))}>{category.name}</button>)}</div><div className="toolbar-controls"><label className="filter-select"><SlidersHorizontal size={15} /><select aria-label="Filtrar por color" value={colorFilter} onChange={(event) => setColorFilter(event.target.value)}><option value="">Color</option><option value="rojo">Rojo</option><option value="azul">Azul</option><option value="verde">Verde</option><option value="dorado">Dorado</option><option value="multicolor">Multicolor</option></select><ChevronDown size={13} /></label><label className="sort-select"><span>Ordenar</span><select aria-label="Ordenar productos" value={sort} onChange={(event) => setSort(event.target.value)}><option value="name">Nombre</option><option value="price">Menor precio</option><option value="-price">Mayor precio</option><option value="-created_at">Recientes</option></select><ChevronDown size={13} /></label></div></div>
          <p className="product-count" aria-live="polite">{loading ? 'Cargando piezas…' : `${products.length} ${products.length === 1 ? 'pieza' : 'piezas'}`}</p>
          {catalogError ? <div className="catalog-error"><p>{catalogError}</p><button className="button button-outline" onClick={() => window.location.reload()}>Volver a intentar <ArrowRight size={15} /></button></div> : <div className="product-grid">{loading && products.length === 0 ? Array.from({ length: 4 }, (_, index) => <div className="product-skeleton" key={index}><div /><span /><i /></div>) : products.map((product, index) => <article className="product-card" key={product.id} style={{ animationDelay: `${index * 70}ms` }}><button className="product-image-button" onClick={() => setSelectedProduct(product)} aria-label={`Ver ${product.name}`}><ProductPhoto src={product.image_url} alt={product.name} className="product-card-photo" loading={index > 3 ? 'lazy' : 'eager'} />{product.stock === 0 && <span className="product-label">AGOTADA</span>}<span className="quick-view">Ver pieza <ArrowUpRight size={15} /></span></button><div className="product-info"><div><p className="product-origin">{product.region || product.category.name}</p><h3>{product.name}</h3></div><p className="product-price">{money(product.price)}</p></div><div className="product-meta"><span>Talla {product.size}</span><span>{product.production_time || 'Tejido artesanal'}</span></div></article>)}{!loading && !catalogError && products.length === 0 && <div className="empty-results"><Search size={24} /><h3>No encontramos esa pieza</h3><p>Prueba con otra búsqueda o categoría.</p><button className="text-button" onClick={() => { setQuery(''); setCategoryId('all'); setColorFilter('') }}>Limpiar filtros <ArrowRight size={15} /></button></div>}</div>}
        </section>
        <section className="origin-band" id="origen"><div className="origin-copy"><p className="eyebrow">NUESTRO ORIGEN</p><h2>Tejido con <em>memoria.</em></h2></div><p className="origin-text">Cada manta nace del tiempo, el conocimiento y las manos de una tejedora Wayuu.</p>{canRequestDesign && <button className="origin-link" onClick={() => setScreen('design')}>Diseña tu pieza <ArrowUpRight size={17} /></button>}</section>
      </main>
    </>}

    {screen === 'design' && <main className="inner-page design-page"><button className="back-link" onClick={() => setScreen('shop')}><ArrowLeft size={15} /> Volver a la colección</button><div className="inner-page-heading"><p className="eyebrow"><span className="eyebrow-line" /> HECHA A TU MANERA</p><h1>Imagina tu <em>manta.</em></h1><p>Elige una combinación de color, un patrón y una talla. La tejedora recibirá tus indicaciones junto con el pedido.</p></div><form className="designer-layout" onSubmit={createDesign}><div className="designer-preview"><div className={`weave-preview pattern-${designPattern}`} style={{ '--base': designColors[0], '--accent-one': designColors[1], '--accent-two': designColors[2] } as CSSProperties}><span /><span /><span /><span /></div><div className="preview-caption"><span>VISTA DE COLOR</span><span>{designPattern.toUpperCase()} · TALLA {designSize}</span></div></div><div className="designer-controls"><fieldset><legend>01 / Elige un patrón</legend><div className="pattern-options">{[['rombos', 'Rombos'], ['olas', 'Olas'], ['estrellas', 'Estrellas'], ['caminos', 'Caminos']].map(([value, label]) => <button type="button" key={value} className={designPattern === value ? 'pattern-choice active' : 'pattern-choice'} onClick={() => setDesignPattern(value)}><span className={`pattern-swatch pattern-${value}`} /><span>{label}</span>{designPattern === value && <Check size={14} />}</button>)}</div></fieldset><fieldset><legend>02 / Combina tus colores</legend><div className="color-pickers">{designColors.map((color, index) => <label key={index}><input type="color" value={color} onChange={(event) => setDesignColors((current) => current.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} /><span>{['Base', 'Acento 1', 'Acento 2'][index]}</span></label>)}</div></fieldset><fieldset><legend>03 / Escoge la talla</legend><div className="size-options">{['S', 'M', 'L', 'XL'].map((size) => <button type="button" key={size} className={designSize === size ? 'size-option selected' : 'size-option'} onClick={() => setDesignSize(size)}>{size}</button>)}</div></fieldset><label className="form-label">Cantidad<div className="stepper"><button type="button" onClick={() => setDesignQuantity((value) => Math.max(1, value - 1))} aria-label="Disminuir cantidad"><Minus size={14} /></button><span>{designQuantity}</span><button type="button" onClick={() => setDesignQuantity((value) => Math.min(20, value + 1))} aria-label="Aumentar cantidad"><Plus size={14} /></button></div></label><label className="form-label">Indicaciones para la tejedora<textarea value={designNotes} onChange={(event) => setDesignNotes(event.target.value)} placeholder="Cuéntanos qué te gustaría tener en cuenta…" rows={3} /></label><div className="design-total"><span>Precio estimado</span><strong>{money(customPrice)}</strong><small>El precio final se confirma con la tejedora.</small></div><button className="button button-dark full-button" disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : <ShoppingBag size={16} />} Agregar diseño al carrito</button></div></form></main>}

    {screen === 'orders' && user && <CustomerAccountView user={user} navigationItems={roleNavigation} orders={orders} designs={designs} profile={profileDraft} section={accountSection} busy={busy} onSection={setAccountSection} onProfileSubmit={saveProfile} onSignOut={signOut} onShop={() => setScreen('shop')} />}

    {screen === 'craftswoman' && dashboard && <CraftswomanAccountView user={user} navigationItems={roleNavigation} dashboard={dashboard} products={craftswomanProducts} categories={categories} busy={busy} onCreateProduct={createCraftswomanProduct} onSignOut={signOut} onAcceptOrder={acceptOrder} onOrderStatus={updateOrder} onDesignStatus={updateDesignStatus} />}

    {screen === 'admin' && user && (user.role === 'admin' || user.role === 'superadmin') && <AdminAccountView user={user} isSuperadmin={user.role === 'superadmin'} navigationItems={roleNavigation} orders={orders} products={adminProducts} categories={adminCategories} busy={busy} onSignOut={signOut} onSaveProduct={saveAdminProduct} onCreateProduct={createAdminProduct} onCreateCategory={createAdminCategory} onCategoryActive={updateAdminCategory} onOrderStatus={saveAdminOrderStatus} />}

    {screen !== 'shop' && screen !== 'admin' && <Footer onInstagram={() => setNotice('Pronto encontrarás nuestras novedades en Instagram.')} />}
    {selectedProduct && <ProductDialog product={selectedProduct} busy={busy} onClose={() => setSelectedProduct(null)} onAdd={() => addToCart(selectedProduct.id)} />}
    {cartOpen && <CartDrawer cart={cart} checkoutOpen={checkoutOpen} busy={busy} address={checkoutAddress} city={checkoutCity} paymentMethod={paymentMethod} notes={checkoutNotes} onClose={() => { setCartOpen(false); setCheckoutOpen(false) }} onCheckout={() => setCheckoutOpen(true)} onBack={() => setCheckoutOpen(false)} onQuantity={changeQuantity} onAddress={setCheckoutAddress} onCity={setCheckoutCity} onPayment={setPaymentMethod} onNotes={setCheckoutNotes} onSubmit={submitCheckout} />}
    {authOpen && <AuthDialog mode={authMode} busy={busy} onMode={setAuthMode} onClose={() => { setAuthOpen(false); setPendingProduct(null) }} onSubmit={submitAuth} />}
    {completedOrder && <OrderSuccess order={completedOrder} onClose={() => setCompletedOrder(null)} onOrders={() => { setCompletedOrder(null); void openAccount() }} />}
    {notice && <div className="toast" role="status"><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Cerrar aviso"><X size={16} /></button></div>}
  </div>
}

function ProductPhoto({ src, alt, className, loading = 'lazy' }: { src: string; alt: string; className: string; loading?: 'eager' | 'lazy' }) {
  return src
    ? <img src={src} alt={alt} className={className} loading={loading} />
    : <span className={`product-photo-fallback ${className}`} role="img" aria-label={alt}><ShoppingBag size={22} strokeWidth={1.4} /></span>
}

function ProductDialog({ product, busy, onClose, onAdd }: { product: Product; busy: boolean; onClose: () => void; onAdd: () => void }) {
  return <div className="overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="product-dialog" role="dialog" aria-modal="true" aria-labelledby="product-title"><button className="close-button" onClick={onClose} aria-label="Cerrar"><X size={19} /></button><div className="dialog-image"><ProductPhoto src={product.image_url} alt={product.name} className="dialog-product-photo" /></div><div className="dialog-product-copy"><p className="eyebrow">{product.region || product.category.name}</p><h2 id="product-title">{product.name}</h2><p className="dialog-price">{money(product.price)}</p><p className="dialog-description">{product.description || 'Una pieza tejida a mano con el cuidado de quien conoce cada hilo.'}</p><dl className="product-details"><div><dt>Talla</dt><dd>{product.size}</dd></div><div><dt>Elaboración</dt><dd>{product.production_time || 'Artesanal'}</dd></div><div><dt>Disponibilidad</dt><dd>{product.stock > 0 ? `${product.stock} unidades` : 'Por pedido'}</dd></div>{product.craftswoman && <div><dt>Tejedora</dt><dd>{product.craftswoman.name}</dd></div>}</dl><button className="button button-dark full-button" onClick={onAdd} disabled={busy || product.stock < 1}>{busy ? <LoaderCircle className="spin" size={16} /> : <ShoppingBag size={16} />}{product.stock < 1 ? 'Sin existencias' : 'Agregar al carrito'}</button><p className="dialog-note"><Heart size={14} /> Una pieza hecha para acompañarte.</p></div></section></div>
}

function CartDrawer({ cart, checkoutOpen, busy, address, city, paymentMethod, notes, onClose, onCheckout, onBack, onQuantity, onAddress, onCity, onPayment, onNotes, onSubmit }: {
  cart: Cart | null; checkoutOpen: boolean; busy: boolean; address: string; city: string; paymentMethod: string; notes: string
  onClose: () => void; onCheckout: () => void; onBack: () => void; onQuantity: (id: number, quantity: number) => void
  onAddress: (value: string) => void; onCity: (value: string) => void; onPayment: (value: string) => void
  onNotes: (value: string) => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><aside className="cart-drawer" role="dialog" aria-modal="true" aria-labelledby="cart-title"><div className="drawer-header"><div><p className="eyebrow">WAYUUWAA · TU ELECCIÓN</p><h2 id="cart-title">{checkoutOpen ? 'Datos de entrega' : 'Tu carrito'} <span>({cart?.count ?? 0})</span></h2></div><button className="close-button" onClick={onClose} aria-label="Cerrar carrito"><X size={19} /></button></div>{checkoutOpen ? <form className="checkout-form" onSubmit={onSubmit}><button type="button" className="back-link" onClick={onBack}><ArrowLeft size={15} /> Volver al carrito</button><p className="checkout-help">Cuéntanos dónde quieres recibir tu pieza. El pago se coordina contigo.</p><label className="form-label">Dirección de entrega<input required value={address} onChange={(event) => onAddress(event.target.value)} autoComplete="street-address" placeholder="Calle, número, barrio" /></label><label className="form-label">Ciudad<input required value={city} onChange={(event) => onCity(event.target.value)} autoComplete="address-level2" placeholder="Ciudad" /></label><label className="form-label">Forma de pago<select value={paymentMethod} onChange={(event) => onPayment(event.target.value)}><option value="contact">Acordar con la tejedora</option><option value="nequi">Nequi</option><option value="daviplata">Daviplata</option><option value="bancolombia">Bancolombia</option><option value="whatsapp">WhatsApp</option></select></label><label className="form-label">Nota para el pedido<textarea value={notes} onChange={(event) => onNotes(event.target.value)} rows={3} placeholder="Indicaciones de entrega (opcional)" /></label><div className="checkout-total"><span>Total</span><strong>{money(cart?.total ?? 0)}</strong></div><button className="button button-dark full-button" disabled={busy || !cart?.count}>{busy ? <LoaderCircle className="spin" size={16} /> : <LockKeyhole size={16} />} Confirmar pedido</button></form> : <><div className="cart-content">{cart?.items.length ? cart.items.map((item) => <div className="cart-line" key={item.product.id}><ProductPhoto src={item.product.image_url} alt={item.product.name} className="cart-product-photo" /><div className="cart-line-copy"><p className="product-origin">PIEZA WAYUU</p><h3>{item.product.name}</h3><strong>{money(item.product.price)}</strong><div className="cart-stepper"><button onClick={() => onQuantity(item.product.id, item.quantity - 1)} aria-label="Disminuir cantidad"><Minus size={13} /></button><span>{item.quantity}</span><button onClick={() => onQuantity(item.product.id, item.quantity + 1)} aria-label="Aumentar cantidad"><Plus size={13} /></button></div></div><button className="remove-item" onClick={() => onQuantity(item.product.id, 0)} title="Eliminar del carrito" aria-label={`Quitar ${item.product.name}`}><Trash2 size={15} /></button></div>) : <div className="empty-cart"><ShoppingBag size={29} strokeWidth={1.4} /><h3>Tu carrito está esperando.</h3><p>Cuando encuentres tu pieza, estará aquí.</p><button className="text-button" onClick={onClose}>Seguir explorando <ArrowRight size={15} /></button></div>}</div>{cart?.items.length ? <div className="drawer-footer"><div className="subtotal-row"><span>Subtotal</span><strong>{money(cart.total)}</strong></div><p className="drawer-shipping">El costo de envío se confirma al coordinar la entrega.</p><button className="button button-dark full-button" onClick={onCheckout}>Continuar al pedido <ArrowRight size={16} /></button><div className="secure-note"><LockKeyhole size={13} /> Compra acompañada por la tejedora</div></div> : <div className="drawer-footer drawer-footer-empty"><button className="button button-outline full-button" onClick={onClose}>Seguir explorando <ArrowRight size={15} /></button></div>}</>}</aside></div>
}

function AuthDialog({ mode, busy, onMode, onClose, onSubmit }: { mode: AuthMode; busy: boolean; onMode: (mode: AuthMode) => void; onClose: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  const registering = mode !== 'login'
  return <div className="overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title"><button className="close-button" onClick={onClose} aria-label="Cerrar"><X size={19} /></button><div className="auth-mark"><span className="wordmark-symbol"><span /><span /><span /></span></div><p className="eyebrow">WAYUUWAA · MI CUENTA</p><h2 id="auth-title">{mode === 'login' ? 'Qué bueno verte.' : mode === 'craftswoman' ? 'Tejamos juntas.' : 'Comienza por aquí.'}</h2><p className="auth-intro">{mode === 'craftswoman' ? 'Envía tu solicitud para vincular tu taller a la tienda.' : 'Inicia sesión para guardar tus piezas y seguir tus pedidos.'}</p><div className="auth-tabs"><button className={mode === 'login' ? 'active' : ''} onClick={() => onMode('login')}>Iniciar sesión</button><button className={mode === 'register' ? 'active' : ''} onClick={() => onMode('register')}>Crear cuenta</button></div><form className="auth-form" onSubmit={onSubmit}>{registering && <label className="form-label">Nombre completo<input name="name" required autoComplete="name" placeholder="Tu nombre" /></label>}<label className="form-label">Usuario<input name="username" required autoComplete="username" placeholder="Tu usuario" /></label>{registering && <label className="form-label">Correo electrónico<input name="email" type="email" required autoComplete="email" placeholder="tu@correo.com" /></label>}<label className="form-label">Contraseña<input name="password" type="password" required minLength={8} autoComplete={registering ? 'new-password' : 'current-password'} placeholder="Mínimo 8 caracteres" /></label>{registering && <label className="form-label">Teléfono <span className="optional">OPCIONAL</span><input name="phone" autoComplete="tel" placeholder="300 000 0000" /></label>}{mode === 'craftswoman' && <><label className="form-label">Comunidad<input name="community" placeholder="Tu comunidad" /></label><label className="form-label">Región<input name="region" placeholder="La Guajira" /></label></>}<button className="button button-dark full-button" disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : registering ? <ArrowRight size={16} /> : <LockKeyhole size={16} />}{mode === 'login' ? 'Entrar a mi cuenta' : mode === 'craftswoman' ? 'Enviar solicitud' : 'Crear cuenta'}</button></form>{mode !== 'craftswoman' && <button className="craftswoman-link" onClick={() => onMode('craftswoman')}>¿Eres tejedora? Solicita acceso <ArrowUpRight size={14} /></button>}</section></div>
}

function CustomerAccountView({ user, navigationItems, orders, designs, profile, section, busy, onSection, onProfileSubmit, onSignOut, onShop }: {
  user: SessionUser
  navigationItems: RBACNavigationItem[]
  orders: Order[]
  designs: CustomDesign[]
  profile: UserProfile | null
  section: AccountSection
  busy: boolean
  onSection: (section: AccountSection) => void
  onProfileSubmit: (event: FormEvent<HTMLFormElement>) => void
  onSignOut: () => void
  onShop: () => void
}) {
  const accountName = resolveUserDisplayName(user, profile)
  return <main className="inner-page account-page">
    <div className="account-heading"><div><p className="eyebrow"><span className="eyebrow-line" /> MI CUENTA</p><h1>Hola, <em>{accountName}.</em></h1><p>Pedidos, diseños y datos de entrega en un mismo lugar.</p></div><button className="text-button" onClick={onSignOut}>Cerrar sesión <ArrowUpRight size={15} /></button></div>
    <div className="account-tabs"><div className="account-tab-buttons">{navigationItems.filter((item) => item.route_name.startsWith('customer.')).map((item) => { const target = item.route_name.split('.')[1] as AccountSection; return <button key={item.id} className={section === target ? 'active' : ''} onClick={() => onSection(target)}>{item.label}{target === 'orders' && <span>{orders.length}</span>}{target === 'designs' && <span>{designs.length}</span>}</button> })}</div><span>{user.email}</span></div>
    {section === 'orders' && (orders.length ? <div className="orders-list">{orders.map((order) => <OrderCard key={order.id} order={order} />)}</div> : <div className="empty-account"><ShoppingBag size={30} strokeWidth={1.4} /><h2>Aún no tienes pedidos.</h2><p>Cuando encuentres la pieza indicada, la guardaremos aquí.</p><button className="button button-dark" onClick={onShop}>Explorar la colección <ArrowRight size={15} /></button></div>)}
    {section === 'designs' && (designs.length ? <div className="design-list">{designs.map((design) => <DesignSummary key={design.id} design={design} />)}</div> : <div className="empty-account"><Heart size={29} strokeWidth={1.4} /><h2>Aún no has creado diseños.</h2><p>Combina patrón y colores para imaginar una manta propia.</p><button className="button button-dark" onClick={onShop}>Diseñar una manta <ArrowRight size={15} /></button></div>)}
    {navigationItems.filter((item) => item.route_name.startsWith('customer.')).length === 0 && <div className="empty-account"><LockKeyhole size={28} /><h2>No tienes secciones habilitadas</h2><p>El superadministrador debe asignarte las opciones y permisos correspondientes.</p></div>}
    {section === 'profile' && <form className="profile-form" onSubmit={onProfileSubmit}><div className="profile-form-heading"><div><p className="eyebrow">DATOS DE ENTREGA</p><h2>Tu información</h2></div><p>La usaremos para preparar tus pedidos.</p></div><label className="form-label">Nombre completo<input name="name" required maxLength={150} defaultValue={resolveUserDisplayName(user, profile)} autoComplete="name" /></label><label className="form-label">Correo electrónico<input value={user.email} readOnly /></label><label className="form-label">Teléfono<input name="phone" maxLength={30} defaultValue={profile?.phone ?? ''} autoComplete="tel" /></label><div className="profile-address-row"><label className="form-label">Dirección<input name="address" defaultValue={profile?.address ?? ''} autoComplete="street-address" /></label><label className="form-label">Ciudad<input name="city" maxLength={100} defaultValue={profile?.city ?? ''} autoComplete="address-level2" /></label></div><button className="button button-dark" disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : <Check size={15} />} Guardar datos</button></form>}
  </main>
}

function CraftswomanAccountView({ user, navigationItems, dashboard, products, categories, busy, onCreateProduct, onSignOut, onAcceptOrder, onOrderStatus, onDesignStatus }: {
  user: SessionUser | null
  navigationItems: RBACNavigationItem[]
  dashboard: CraftswomanDashboard | null
  products: Product[]
  categories: Category[]
  busy: boolean
  onCreateProduct: (values: {
    sku: string; name: string; category: number; description?: string; region?: string;
    color?: string; size?: string; production_time?: string; price: string | number;
    stock: number; image_url?: string; made_to_order?: boolean;
  }) => void
  onSignOut: () => void
  onAcceptOrder: (orderId: number) => void
  onOrderStatus: (orderId: number, status: string) => void
  onDesignStatus: (designId: number, status: string) => void
}) {
  const [activeSection, setActiveSection] = useState<'dashboard' | 'products' | 'inventory' | 'orders'>('dashboard')
  const [showProductForm, setShowProductForm] = useState(false)
  const canChangeOrders = Boolean(user && hasEffectivePermission(user, 'orders.change'))
  const canChangeDesigns = Boolean(user && hasEffectivePermission(user, 'designs.change'))
  const accountName = resolveUserDisplayName(user)
  const published = products.filter((product) => product.active).length
  const pending = products.length - published
  const stock = products.reduce((total, product) => total + product.stock, 0)
  const initials = accountName.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
  const navItems = navigationItems.filter((item) => item.route_name.startsWith('craftswoman.')).map((item) => {
    const id = item.route_name.split('.')[1] as 'dashboard' | 'products' | 'inventory' | 'orders'
    const icon = id === 'dashboard' ? <LayoutDashboard size={17} /> : id === 'products' ? <ShoppingBag size={17} /> : id === 'inventory' ? <Boxes size={17} /> : <ShoppingCart size={17} />
    return { id, label: item.label, icon }
  })
  const canOpenSection = (section: string) => navItems.some((item) => item.id === section)
  useEffect(() => {
    if (!canOpenSection(activeSection) && navItems[0]) setActiveSection(navItems[0].id)
  }, [navigationItems, activeSection])
  function submitProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const values = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<string, string>
    onCreateProduct({
      sku: values.sku.trim(), name: values.name.trim(), category: Number(values.category),
      price: values.price, stock: Number(values.stock), size: values.size || 'M',
      region: values.region.trim(), color: values.color.trim(),
      production_time: values.production_time.trim(), description: values.description.trim(),
      image_url: values.image_url.trim(), made_to_order: values.made_to_order === 'on',
    })
    event.currentTarget.reset()
    setShowProductForm(false)
  }
  return <div className="craftswoman-workspace">
    <aside className="craftswoman-sidebar">
      <div className="craftswoman-brand"><span className="craftswoman-brand-mark"><Layers size={22} /></span><span><strong>Wayúu</strong><small>PORTAL DE TEJEDORA</small></span></div>
      <nav className="craftswoman-nav" aria-label="Menú de tejedora">
        <p>MENÚ PRINCIPAL</p>
        {navItems.map((item) => <button key={item.id} className={activeSection === item.id ? 'active' : ''} onClick={() => setActiveSection(item.id)}>{item.icon}<span>{item.label}</span></button>)}
      </nav>
      <div className="craftswoman-sidebar-profile"><span className="craftswoman-avatar">{initials || 'TW'}</span><div><strong>{accountName}</strong><small>Tejedora Wayúu</small></div><button onClick={onSignOut} aria-label="Cerrar sesión" title="Cerrar sesión"><LogOut size={16} /></button></div>
      <div className="craftswoman-sidebar-foot">SÜCHIKI KANAAS · LEGADO CULTURAL</div>
    </aside>
    <section className="craftswoman-main">
      <header className="craftswoman-topbar"><div><span>ROL: TEJEDORA</span><b>/</b><strong>{navItems.find((item) => item.id === activeSection)?.label}</strong></div><div className="craftswoman-top-user"><span className="craftswoman-avatar">{initials || 'TW'}</span><span><strong>{accountName}</strong><small>Espacio de trabajo</small></span></div></header>
      <main className="craftswoman-content">
        {navItems.length === 0 ? <div className="craftswoman-empty"><LockKeyhole size={30} /><h2>No tienes secciones habilitadas</h2><p>El superadministrador debe asignarte las opciones y permisos correspondientes.</p></div> : !dashboard?.active && (canOpenSection('dashboard') || canOpenSection('orders')) ? <div className="craftswoman-empty"><LockKeyhole size={30} /><h2>Cuenta pendiente de activación</h2><p>La administración debe activar tu perfil antes de asignarte pedidos.</p></div> : <>
          {canOpenSection('dashboard') && activeSection === 'dashboard' && <div className="craftswoman-dashboard">
            <section className="craftswoman-welcome"><div><span><Sparkles size={14} /> SÜCHIKI KANAAS · LEGADO CULTURAL</span><h1>Jamaya, {accountName}!</h1><p>Tu trabajo conserva historias. Aquí puedes organizar tus tejidos, revisar tus pedidos y compartir nuevas piezas con la tienda.</p></div><div className="craftswoman-welcome-actions"><button onClick={() => { setActiveSection('products'); setShowProductForm(true) }}><Plus size={16} /> Registrar nuevo tejido</button><button className="secondary" onClick={() => setActiveSection('orders')}><ShoppingCart size={16} /> Ver mis pedidos</button></div></section>
            <section className="craftswoman-stats">
              <article><span>Total de tejidos</span><strong>{products.length}</strong><small>Registrados por ti</small></article>
              <article><span>Publicados</span><strong>{published}</strong><small>Visibles en la tienda</small></article>
              <article><span>En revisión</span><strong>{pending}</strong><small>Esperando aprobación</small></article>
              <article><span>En inventario</span><strong>{stock} <small>unid.</small></strong><small>Piezas registradas</small></article>
              <article><span>Pedidos asignados</span><strong>{(dashboard?.orders ?? []).length}</strong><small>De tu taller</small></article>
            </section>
            <div className="craftswoman-columns">
              <section className="craftswoman-panel"><div className="craftswoman-panel-heading"><div><small>ACTIVIDAD</small><h2>Pedidos por aceptar</h2></div><span>{(dashboard?.available_orders ?? []).length}</span></div>{(dashboard?.available_orders ?? []).length ? (dashboard?.available_orders ?? []).slice(0,3).map((order) => <div className="artisan-order" key={order.id}><OrderCard order={order} />{canChangeOrders && canChangeDesigns && <button className="button button-dark" onClick={() => onAcceptOrder(order.id)}>Aceptar pedido <ArrowRight size={15} /></button>}</div>) : <p className="muted-copy">No hay pedidos disponibles en este momento.</p>}</section>
              <section className="craftswoman-panel"><div className="craftswoman-panel-heading"><div><small>TU TALLER</small><h2>Mis productos recientes</h2></div><button onClick={() => setActiveSection('products')}>Ver todos <ArrowRight size={14} /></button></div>{products.slice(0,4).map((product) => <div className="craftswoman-product-mini" key={product.id}><span><strong>{product.name}</strong><small>{product.category.name} · Stock {product.stock}</small></span><em className={product.active ? 'published' : ''}>{product.active ? 'Publicado' : 'En revisión'}</em></div>)}{!products.length && <p className="muted-copy">Registra tu primera pieza para comenzar.</p>}</section>
            </div>
          </div>}
        {canOpenSection('products') && activeSection === 'products' && <section className="craftswoman-panel craftswoman-products-section"><div className="craftswoman-panel-heading"><div><small>CATÁLOGO DE TU TALLER</small><h1>Mis tejidos y productos</h1><p>Registra tus piezas. Antes de aparecer en la tienda, cada producto debe ser aprobado por administración.</p></div><button className="craftswoman-primary-action" onClick={() => setShowProductForm((value) => !value)}><Plus size={16} /> {showProductForm ? 'Cerrar formulario' : 'Registrar tejido'}</button></div>
            {showProductForm && <form className="craftswoman-product-form" onSubmit={submitProduct}>
              <label className="form-label">Referencia<input name="sku" required maxLength={50} placeholder="Ej. WAY-TEJ-001" /></label><label className="form-label">Nombre de la pieza<input name="name" required maxLength={180} /></label><label className="form-label">Categoría<select name="category" required defaultValue=""><option value="" disabled>Selecciona una categoría</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label><label className="form-label">Precio sugerido (COP)<input name="price" type="number" min="0" step="1" required /></label><label className="form-label">Stock inicial<input name="stock" type="number" min="0" step="1" defaultValue="1" required /></label><label className="form-label">Talla *<input name="size" maxLength={30} defaultValue="M" required /></label><label className="form-label">Región de elaboración *<input name="region" maxLength={100} placeholder="La Guajira" required /></label><label className="form-label">Colores principales *<input name="color" maxLength={150} placeholder="Ej. vino tinto, beige y negro" required /></label><label className="form-label">Tiempo de elaboración *<input name="production_time" maxLength={100} placeholder="Ej. 10 a 15 días" required /></label><label className="form-label">Imagen del tejido (URL) *<input name="image_url" type="url" placeholder="https://..." required /></label><label className="form-label craftswoman-description-field">Descripción del tejido *<textarea name="description" rows={2} minLength={10} maxLength={2000} placeholder="Describe el diseño, la técnica y los detalles de la pieza..." required /></label><label className="admin-check"><input name="made_to_order" type="checkbox" /> Elaborar por pedido</label><button className="button button-dark craftswoman-submit-review" disabled={busy || !categories.length}>{busy ? <LoaderCircle className="spin" size={15} /> : <Plus size={15} />} Enviar a revisión</button>
            </form>}
            <div className="craftswoman-product-list">{products.map((product) => <article key={product.id}><div><strong>{product.name}</strong><small>{product.sku} · {product.category.name} · Talla {product.size}</small></div><span>{money(product.price)}</span><span>Stock {product.stock}</span><em className={product.active ? 'published' : ''}>{product.active ? 'Publicado' : 'Pendiente de revisión'}</em></article>)}{!products.length && <p className="muted-copy">Todavía no has registrado productos en tu taller.</p>}</div>
          </section>}
          {canOpenSection('inventory') && activeSection === 'inventory' && <section className="craftswoman-panel"><div className="craftswoman-panel-heading"><div><small>CONTROL DE EXISTENCIAS</small><h1>Mi inventario</h1><p>Consulta las piezas y las unidades registradas en tu taller.</p></div><span className="craftswoman-total-stock">{stock} unidades</span></div><div className="craftswoman-product-list">{products.map((product) => <article key={product.id}><div><strong>{product.name}</strong><small>{product.sku} · {product.category.name}</small></div><span>{money(product.price)}</span><span>Disponibles: {product.stock}</span><em className={product.stock > 0 ? 'published' : ''}>{product.stock > 0 ? 'Con existencias' : 'Agotado'}</em></article>)}{!products.length && <p className="muted-copy">Tu inventario aparecerá aquí cuando registres productos.</p>}</div></section>}
          {canOpenSection('orders') && activeSection === 'orders' && <div className="craftswoman-orders"><section className="craftswoman-panel"><div className="craftswoman-panel-heading"><div><small>OPORTUNIDADES DE TRABAJO</small><h1>Pedidos por aceptar</h1></div><span>{(dashboard?.available_orders ?? []).length}</span></div>{(dashboard?.available_orders ?? []).length ? (dashboard?.available_orders ?? []).map((order) => <div className="artisan-order" key={order.id}><OrderCard order={order} />{canChangeOrders && canChangeDesigns && <button className="button button-dark" onClick={() => onAcceptOrder(order.id)}>Aceptar pedido <ArrowRight size={15} /></button>}</div>) : <p className="muted-copy">No hay pedidos disponibles.</p>}</section>
            <section className="craftswoman-panel"><div className="craftswoman-panel-heading"><div><small>PRODUCCIÓN</small><h1>Pedidos de mi taller</h1></div><span>{(dashboard?.orders ?? []).length}</span></div>{(dashboard?.orders ?? []).length ? (dashboard?.orders ?? []).map((order) => <div className="artisan-order" key={order.id}><OrderCard order={order} />{canChangeOrders && canChangeDesigns && order.status === 'accepted' && <button className="button button-outline" onClick={() => onOrderStatus(order.id, 'weaving')}>Iniciar tejido <ArrowRight size={15} /></button>}{canChangeOrders && canChangeDesigns && order.status === 'weaving' && <button className="button button-outline" onClick={() => onOrderStatus(order.id, 'completed')}>Marcar como terminado <Check size={15} /></button>}</div>) : <p className="muted-copy">Tus pedidos aceptados aparecerán aquí.</p>}</section></div>}
          {activeSection !== 'orders' && activeSection !== 'dashboard' && (dashboard?.designs.length ?? 0) > 0 && <section className="craftswoman-panel craftswoman-designs"><div className="craftswoman-panel-heading"><div><small>DISEÑOS PERSONALIZADOS</small><h2>Diseños de mi taller</h2></div><span>{dashboard?.designs.length ?? 0}</span></div><div className="design-list">{(dashboard?.designs ?? []).map((design) => <article className="artisan-design" key={design.id}><DesignSummary design={design} /><div className="design-actions">{canChangeDesigns && design.status === 'accepted' && <button className="button button-outline" onClick={() => onDesignStatus(design.id, 'weaving')}>Iniciar tejido <ArrowRight size={15} /></button>}{canChangeDesigns && design.status === 'weaving' && <button className="button button-outline" onClick={() => onDesignStatus(design.id, 'completed')}>Marcar terminado <Check size={15} /></button>}</div></article>)}</div></section>}
        </>}
      </main>
    </section>
  </div>
}

function AdminAccountView({ user, isSuperadmin, navigationItems, orders, products, categories, busy, onSignOut, onSaveProduct, onCreateProduct, onCreateCategory, onCategoryActive, onOrderStatus }: {
  user: SessionUser
  navigationItems: RBACNavigationItem[]
  isSuperadmin: boolean
  orders: Order[]
  products: AdminProduct[]
  categories: AdminCategory[]
  busy: boolean
  onSignOut: () => void
  onSaveProduct: (productId: number, values: Partial<AdminProduct>) => void
  onCreateProduct: (values: Partial<AdminProduct>) => void
  onCreateCategory: (values: Pick<AdminCategory, 'name' | 'description' | 'active'>) => void
  onCategoryActive: (categoryId: number, active: boolean) => void
  onOrderStatus: (orderId: number, status: string) => void
}) {
  const [activeSection, setActiveSection] = useState<'dashboard' | 'products' | 'orders' | 'categories' | 'access'>('dashboard')
  const [showCreateForm, setShowCreateForm] = useState(false)
  function submitNewCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const values = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<string, string>
    onCreateCategory({ name: values.name.trim(), description: values.description.trim(), active: true })
    event.currentTarget.reset()
  }
  function submitNewProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const values = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<string, string>
    onCreateProduct({
      sku: values.sku.trim(), name: values.name.trim(), category: Number(values.category),
      price: values.price, stock: Number(values.stock), size: values.size || 'M',
      region: values.region.trim(), image_url: values.image_url.trim(),
      active: values.active === 'on', made_to_order: values.made_to_order === 'on',
    })
    event.currentTarget.reset()
    setShowCreateForm(false)
  }
  const pendingProducts = products.filter((product) => !product.active)
  const publishedProducts = products.filter((product) => product.active)
  const pendingOrders = orders.filter((order) => order.status === 'pending').length
  const activeOrders = orders.filter((order) => ['accepted', 'weaving', 'preparing', 'shipped'].includes(order.status)).length
  const canViewOrders = hasEffectivePermission(user, 'orders.view')
  const canChangeOrders = hasEffectivePermission(user, 'orders.change')
  const canViewProducts = hasEffectivePermission(user, 'products.view')
  const canAddProducts = hasEffectivePermission(user, 'products.add')
  const canChangeProducts = hasEffectivePermission(user, 'products.change')
  const canViewCategories = hasEffectivePermission(user, 'categories.view')
  const canAddCategories = hasEffectivePermission(user, 'categories.add')
  const canChangeCategories = hasEffectivePermission(user, 'categories.change')
  const accountName = resolveUserDisplayName(user)
  const navItems = [
    ...navigationItems.filter((item) => item.route_name.startsWith('admin.') && item.route_name !== 'admin.access').map((item) => {
      const id = item.route_name.split('.')[1] as 'dashboard' | 'products' | 'orders' | 'categories'
      const icon = id === 'dashboard' ? <LayoutDashboard size={17} /> : id === 'products' ? <ShoppingBag size={17} /> : id === 'orders' ? <ShoppingCart size={17} /> : <Boxes size={17} />
      return { id, label: item.label, icon }
    }),
    ...(isSuperadmin ? [{ id: 'access' as const, label: 'Roles y permisos', icon: <LockKeyhole size={17} /> }] : []),
  ]
  const canOpenSection = (section: string) => navItems.some((item) => item.id === section)
  useEffect(() => {
    if (!canOpenSection(activeSection) && navItems[0]) setActiveSection(navItems[0].id)
  }, [navigationItems, activeSection])
  return <div className="craftswoman-workspace admin-workspace">
    <aside className="craftswoman-sidebar">
      <div className="craftswoman-brand"><span className="craftswoman-brand-mark"><Layers size={22} /></span><span><strong>Wayúu</strong><small>{isSuperadmin ? 'CONTROL GENERAL DEL SISTEMA' : 'ADMINISTRACIÓN DE TIENDA'}</small></span></div>
      <nav className="craftswoman-nav" aria-label="Menú de administración">
        <p>MENÚ PRINCIPAL</p>
        {navItems.map((item) => <button key={item.id} className={activeSection === item.id ? 'active' : ''} onClick={() => setActiveSection(item.id)}>{item.icon}<span>{item.label}</span></button>)}
      </nav>
      <div className="craftswoman-sidebar-profile"><span className="craftswoman-avatar">{accountName.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'AD'}</span><div><strong>{accountName}</strong><small>{isSuperadmin ? 'Superadministrador' : 'Administrador de tienda'}</small></div><button onClick={onSignOut} aria-label="Cerrar sesión" title="Cerrar sesión"><LogOut size={16} /></button></div>
      <div className="craftswoman-sidebar-foot">SÜCHIKI KANAAS · LEGADO CULTURAL</div>
    </aside>
    <section className="craftswoman-main">
      <header className="craftswoman-topbar"><div><span>ROL: {isSuperadmin ? 'SUPERADMINISTRADOR' : 'ADMINISTRADOR'}</span><b>/</b><strong>{navItems.find((item) => item.id === activeSection)?.label}</strong></div><div className="craftswoman-top-user"><span className="craftswoman-avatar">{accountName.slice(0, 1).toUpperCase()}</span><span><strong>{accountName}</strong><small>Gestión comercial</small></span></div></header>
      <main className="craftswoman-content admin-content">
        {!isSuperadmin && navItems.length === 0 && <div className="craftswoman-empty"><LockKeyhole size={30} /><h2>No tienes secciones habilitadas</h2><p>El superadministrador debe asignarte las opciones y permisos correspondientes.</p></div>}
        {canOpenSection('dashboard') && activeSection === 'dashboard' && <div className="craftswoman-dashboard">
          <section className="craftswoman-welcome"><div><span><Sparkles size={14} /> SÜCHIKI KANAAS · GESTIÓN DE LA TIENDA</span><h1>Jamaya, {accountName}!</h1><p>Desde aquí puedes acompañar el trabajo de las tejedoras, revisar nuevas piezas y mantener organizada la tienda.</p></div><div className="craftswoman-welcome-actions"><button onClick={() => setActiveSection('products')}><Eye size={16} /> Revisar tejidos</button><button className="secondary" onClick={() => setActiveSection('orders')}><ShoppingCart size={16} /> Ver pedidos</button></div></section>
          <section className="craftswoman-stats admin-stats">
            <article><span>Productos registrados</span><strong>{products.length}</strong><small>En el catálogo de tienda</small></article>
            <article><span>Por revisar</span><strong>{pendingProducts.length}</strong><small>Esperando aprobación</small></article>
            <article><span>Publicados</span><strong>{publishedProducts.length}</strong><small>Visibles para clientes</small></article>
            <article><span>Pedidos pendientes</span><strong>{pendingOrders}</strong><small>Requieren seguimiento</small></article>
            <article><span>Pedidos activos</span><strong>{activeOrders}</strong><small>En preparación o envío</small></article>
          </section>
          <div className="craftswoman-columns">
            <section className="craftswoman-panel"><div className="craftswoman-panel-heading"><div><small>REVISIÓN DE CATÁLOGO</small><h2>Tejidos por aprobar</h2></div><span>{pendingProducts.length}</span></div>{pendingProducts.slice(0,4).map((product) => <div className="admin-review-mini" key={product.id}><div><strong>{product.name}</strong><small>{product.sku} · Taller #{product.craftswoman ?? 'sin asignar'}</small></div><button disabled={busy || !canChangeProducts} onClick={() => onSaveProduct(product.id, { active: true })}>Aprobar</button></div>)}{!pendingProducts.length && <p className="muted-copy">No hay tejidos pendientes de revisión.</p>}<button className="admin-text-link" onClick={() => setActiveSection('products')}>Ir a productos <ArrowRight size={14} /></button></section>
            <section className="craftswoman-panel"><div className="craftswoman-panel-heading"><div><small>OPERACIÓN</small><h2>Pedidos recientes</h2></div><span>{orders.length}</span></div>{orders.slice(0,3).map((order) => <div className="admin-review-mini" key={order.id}><div><strong>Pedido #{order.id}</strong><small>{dateLabel(order.created_at)} · {money(order.total)}</small></div><em>{statusLabel(order.status)}</em></div>)}{!orders.length && <p className="muted-copy">Los pedidos aparecerán aquí cuando los clientes compren.</p>}<button className="admin-text-link" onClick={() => setActiveSection('orders')}>Consultar pedidos <ArrowRight size={14} /></button></section>
          </div>
          
        </div>}
        {canOpenSection('products') && activeSection === 'products' && <section className="craftswoman-panel craftswoman-products-section">
          <div className="craftswoman-panel-heading"><div><small>CATÁLOGO Y CONTROL DE PUBLICACIÓN</small><h1>Productos y tejidos</h1><p>Los tejidos enviados por las artesanas llegan aquí como pendientes. Aprueba su publicación cuando la información esté completa.</p></div>{canAddProducts && <button className="craftswoman-primary-action" onClick={() => setShowCreateForm((visible) => !visible)}><Plus size={16} /> {showCreateForm ? 'Cerrar formulario' : 'Agregar producto'}</button>}</div>
          {showCreateForm && <form className="craftswoman-product-form" onSubmit={submitNewProduct}><label className="form-label">Referencia *<input name="sku" required maxLength={50} /></label><label className="form-label">Nombre de la pieza *<input name="name" required maxLength={180} /></label><label className="form-label">Categoría *<select name="category" required defaultValue=""><option value="" disabled>Selecciona una categoría</option>{categories.filter((category) => category.active).map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label><label className="form-label">Precio COP *<input name="price" type="number" min="0" step="1" required /></label><label className="form-label">Stock inicial *<input name="stock" type="number" min="0" step="1" defaultValue="0" required /></label><label className="form-label">Talla<input name="size" maxLength={30} defaultValue="M" /></label><label className="form-label">Región<input name="region" maxLength={100} /></label><label className="form-label">Imagen (URL)<input name="image_url" type="url" placeholder="https://…" /></label><label className="admin-check"><input name="active" type="checkbox" /> Publicar directamente</label><label className="admin-check"><input name="made_to_order" type="checkbox" /> Elaborar por pedido</label><button className="button button-dark craftswoman-submit-review" disabled={busy || !categories.some((category) => category.active)}>{busy ? <LoaderCircle className="spin" size={15} /> : <Plus size={15} />} Guardar producto</button></form>}
          {canViewProducts && <><div className="admin-section-subheading"><h2>Pendientes de aprobación</h2><span>{pendingProducts.length}</span></div>{pendingProducts.length ? <div className="admin-review-list">{pendingProducts.map((product) => <article className="admin-review-card" key={product.id}><div className="admin-review-card-main">{product.image_url ? <img src={product.image_url} alt={product.name} /> : <span className="admin-review-placeholder"><ShoppingBag size={22} /></span>}<div><strong>{product.name}</strong><small>{product.sku} · {categories.find((category) => category.id === product.category)?.name ?? 'Categoría'}</small><small>Taller vinculado: {product.craftswoman_name || (product.craftswoman ? `Taller #${product.craftswoman}` : 'No asignado')} · Stock: {product.stock}</small><p>{product.description || 'Sin descripción registrada.'}</p></div></div><div className="admin-review-actions"><span className="admin-review-pending">Pendiente de revisión</span>{canChangeProducts && <button className="craftswoman-submit-review" disabled={busy} onClick={() => onSaveProduct(product.id, { active: true })}><Check size={15} /> Aprobar y publicar</button>}</div></article>)}</div> : <p className="muted-copy">No hay tejidos pendientes. Cuando una tejedora envíe una pieza, aparecerá en esta sección.</p>}</>}
          {canViewProducts && <><div className="admin-section-subheading"><h2>Productos publicados y catálogo</h2><span>{publishedProducts.length}</span></div><div className="admin-product-list">{publishedProducts.map((product) => <AdminProductRow key={product.id} product={product} busy={busy} canChange={canChangeProducts} onSave={onSaveProduct} />)}</div></>}
        </section>}
        {canOpenSection('orders') && activeSection === 'orders' && <section className="craftswoman-panel"><div className="craftswoman-panel-heading"><div><small>SEGUIMIENTO COMERCIAL</small><h1>Pedidos de clientes</h1><p>Consulta las compras registradas y actualiza su estado según el avance real.</p></div><span>{orders.length} pedidos</span></div>{canViewOrders ? orders.length ? <div className="orders-list">{orders.map((order) => <AdminOrderRow key={order.id} order={order} busy={busy} canChange={canChangeOrders} onStatus={onOrderStatus} />)}</div> : <p className="muted-copy">Todavía no hay pedidos registrados.</p> : <p className="muted-copy">Tu rol no tiene permiso para consultar pedidos.</p>}</section>}
        {canOpenSection('categories') && activeSection === 'categories' && <section className="craftswoman-panel"><div className="craftswoman-panel-heading"><div><small>ORGANIZACIÓN DEL CATÁLOGO</small><h1>Categorías</h1><p>Mantén las categorías disponibles para ordenar las piezas de la tienda.</p></div></div>{canAddCategories && <form className="admin-category-form" onSubmit={submitNewCategory}><label className="form-label">Nombre de categoría *<input name="name" required maxLength={100} placeholder="Ej. Mantas Wayúu" /></label><label className="form-label">Descripción<input name="description" maxLength={500} placeholder="Descripción breve" /></label><button className="button button-dark" disabled={busy}>{busy ? <LoaderCircle className="spin" size={15} /> : <Plus size={15} />} Crear categoría</button></form>}{canViewCategories && <div className="admin-category-list">{categories.map((category) => <div className="admin-category-row" key={category.id}><div><strong>{category.name}</strong><small>{category.description || 'Sin descripción'}</small></div><span className={category.active ? 'category-state active' : 'category-state'}>{category.active ? 'Activa' : 'Inactiva'}</span>{canChangeCategories && <button className="text-button" disabled={busy} onClick={() => onCategoryActive(category.id, !category.active)}>{category.active ? 'Desactivar' : 'Activar'}</button>}</div>)}</div>}</section>}
        {canOpenSection('access') && activeSection === 'access' && isSuperadmin && <SuperadminRBACPanel currentUser={user} />}
      </main>
    </section>
  </div>
}

const rbacRoleLabels: Record<SessionUser['role'], string> = {
  superadmin: 'Superadministrador', admin: 'Administrador de tienda',
  craftswoman: 'Tejedora', customer: 'Cliente',
}
const rbacActionLabels: Record<RBACPermission['action'], string> = {
  view: 'Consultar', add: 'Crear', change: 'Editar', delete: 'Eliminar',
}
const rbacResourceLabels: Record<string, string> = {
  cart: 'Carrito de compras', products: 'Productos', categories: 'Categorías',
  orders: 'Pedidos', designs: 'Diseños de mantas', craftswomen: 'Tejedoras',
  customers: 'Clientes', users: 'Cuentas de usuario', roles: 'Roles',
  role_assignments: 'Asignación de roles', permissions: 'Permisos',
  delegations: 'Delegaciones', navigation: 'Menú y navegación', audit: 'Registro de actividad',
}
const navigationRouteOptions = [
  { value: 'customer.orders', label: 'Cliente · Mis pedidos', roles: ['customer'] },
  { value: 'customer.designs', label: 'Cliente · Mis diseños', roles: ['customer'] },
  { value: 'customer.profile', label: 'Cliente · Mis datos', roles: ['customer'] },
  { value: 'craftswoman.dashboard', label: 'Tejedora · Panel principal', roles: ['craftswoman'] },
  { value: 'craftswoman.products', label: 'Tejedora · Mis tejidos', roles: ['craftswoman'] },
  { value: 'craftswoman.inventory', label: 'Tejedora · Mi inventario', roles: ['craftswoman'] },
  { value: 'craftswoman.orders', label: 'Tejedora · Mis pedidos', roles: ['craftswoman'] },
  { value: 'admin.dashboard', label: 'Administrador · Panel principal', roles: ['admin', 'superadmin'] },
  { value: 'admin.products', label: 'Administrador · Productos', roles: ['admin', 'superadmin'] },
  { value: 'admin.orders', label: 'Administrador · Pedidos', roles: ['admin', 'superadmin'] },
  { value: 'admin.categories', label: 'Administrador · Categorías', roles: ['admin', 'superadmin'] },
  { value: 'admin.access', label: 'Superadministrador · Roles y permisos', roles: ['superadmin'] },
] as const
type RBACSection = 'roles' | 'users' | 'delegations' | 'audit' | 'navigation'

function SuperadminRBACPanel({ currentUser }: { currentUser: SessionUser }) {
  const [catalog, setCatalog] = useState<RBACPermission[]>([])
  const [users, setUsers] = useState<SuperadminUser[]>([])
  const [delegations, setDelegations] = useState<RBACDelegation[]>([])
  const [navigationItems, setNavigationItems] = useState<RBACNavigationItem[]>([])
  const [audit, setAudit] = useState<AuditEvent[]>([])
  const [selectedRole, setSelectedRole] = useState<SessionUser['role']>('admin')
  const [rolePermissions, setRolePermissions] = useState<RBACRolePermissions | null>(null)
  const [selectedUserId, setSelectedUserId] = useState('')
  const [userPermissions, setUserPermissions] = useState<RBACUserPermissions | null>(null)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const [saving, setSaving] = useState(false)
  const [showCreateUser, setShowCreateUser] = useState(false)
  const [activeSection, setActiveSection] = useState<RBACSection>('roles')
  const [permissionSearch, setPermissionSearch] = useState('')
  const [createUserRole, setCreateUserRole] = useState<SessionUser['role']>('customer')
  const [newNavigationRoute, setNewNavigationRoute] = useState('customer.orders')
  const [newNavigationRoles, setNewNavigationRoles] = useState<SessionUser['role'][]>(['customer'])
  const canViewCatalog = hasEffectivePermission(currentUser, 'permissions.view')
  const canChangePermissions = hasEffectivePermission(currentUser, 'permissions.change')
  const canViewUsers = hasEffectivePermission(currentUser, 'users.view')
  const canAddUsers = hasEffectivePermission(currentUser, 'users.add')
  const canChangeUsers = hasEffectivePermission(currentUser, 'users.change')
  const canAssignRoles = hasEffectivePermission(currentUser, 'role_assignments.change')
  const canViewRoles = hasEffectivePermission(currentUser, 'roles.view')
  const canChangeRoles = hasEffectivePermission(currentUser, 'roles.change')
  const canViewDelegations = hasEffectivePermission(currentUser, 'delegations.view')
  const canAddDelegations = hasEffectivePermission(currentUser, 'delegations.add')
  const canViewAudit = hasEffectivePermission(currentUser, 'audit.view')
  const canViewNavigation = hasEffectivePermission(currentUser, 'navigation.view')
  const canAddNavigation = hasEffectivePermission(currentUser, 'navigation.add')
  const canChangeNavigation = hasEffectivePermission(currentUser, 'navigation.change')
  const canDeleteNavigation = hasEffectivePermission(currentUser, 'navigation.delete')
  const selectedUser = users.find((candidate) => String(candidate.id) === selectedUserId)
  const visibleRolePermissions = (rolePermissions?.permissions ?? []).filter((permission) => {
    const search = permissionSearch.trim().toLocaleLowerCase('es')
    return !search || (rbacResourceLabels[permission.resource] ?? permission.resource).toLocaleLowerCase('es').includes(search) || rbacActionLabels[permission.action].toLocaleLowerCase('es').includes(search) || permission.name.toLocaleLowerCase('es').includes(search)
  })
  const permissionGroups = visibleRolePermissions.reduce<Record<string, RBACPermission[]>>((groups, permission) => {
    if (!groups[permission.resource]) groups[permission.resource] = []
    groups[permission.resource].push(permission)
    return groups
  }, {})

  useEffect(() => {
    Promise.all([
      canViewCatalog ? api.rbacCatalog() : Promise.resolve({ permissions: [] }),
      canViewUsers ? api.superadminUsers(new URLSearchParams({ page_size: '100' })) : Promise.resolve([]),
      canViewDelegations ? api.permissionDelegations() : Promise.resolve([]),
      canViewAudit ? api.auditEvents() : Promise.resolve([]),
    ]).then(([catalogResponse, userRows, delegationRows, auditRows]) => {
      setCatalog(catalogResponse.permissions)
      setUsers(userRows)
      setDelegations(delegationRows)
      setAudit(auditRows)
      const firstManageable = userRows.find((candidate) => candidate.role !== 'superadmin')
      setSelectedUserId(String(firstManageable?.id ?? userRows[0]?.id ?? ''))
    }).catch((loadError: unknown) => setError(errorMessage(loadError)))
  }, [currentUser.id, canViewCatalog, canViewUsers, canViewDelegations, canViewAudit])

  useEffect(() => {
    if (!canViewNavigation) return
    api.navigationItems().then(setNavigationItems).catch((loadError: unknown) => setError(errorMessage(loadError)))
  }, [canViewNavigation])

  useEffect(() => {
    if (!canViewRoles) return
    api.rolePermissions(selectedRole)
      .then(setRolePermissions)
      .catch((loadError: unknown) => setError(errorMessage(loadError)))
  }, [selectedRole, canViewRoles])

  useEffect(() => {
    if (!selectedUserId || !canViewUsers || !canViewCatalog) return
    api.userPermissions(Number(selectedUserId))
      .then(setUserPermissions)
      .catch((loadError: unknown) => setError(errorMessage(loadError)))
  }, [selectedUserId, canViewUsers, canViewCatalog])

  async function reloadUsers(selectedId?: number) {
    const refreshedUsers = await api.superadminUsers(new URLSearchParams({ page_size: '100' }))
    setUsers(refreshedUsers)
    const nextSelectedId = selectedId ?? Number(selectedUserId)
    if (selectedId) setSelectedUserId(String(selectedId))
    if (nextSelectedId && canViewUsers && canViewCatalog) {
      setUserPermissions(await api.userPermissions(nextSelectedId))
    }
  }

  async function createManagedUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setFeedback('')
    const values = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<string, string>
    const payload: SuperadminUserInput = {
      username: values.username.trim(),
      email: values.email.trim(),
      first_name: values.first_name.trim(),
      last_name: values.last_name.trim(),
      role: values.role as SessionUser['role'],
      password: values.password,
      is_active: values.is_active === 'on',
      phone: values.phone.trim(),
    }
    if (payload.role === 'customer') {
      payload.address = values.address.trim()
      payload.city = values.city.trim()
    }
    if (payload.role === 'craftswoman') {
      payload.community = values.community.trim()
      payload.region = values.region.trim()
      payload.craftswoman_active = values.craftswoman_active === 'on'
    }
    try {
      const created = await api.createSuperadminUser(payload)
      await reloadUsers(created.id)
      setShowCreateUser(false)
      setFeedback(`Cuenta ${created.username} creada.`)
    } catch (saveError) { setError(errorMessage(saveError)) } finally { setSaving(false) }
  }

  async function updateManagedUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedUser || !canChangeUsers) return
    setSaving(true)
    setError('')
    setFeedback('')
    const values = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<string, string>
    const payload: Partial<SuperadminUserInput> = {
      username: values.username.trim(),
      email: values.email.trim(),
      first_name: values.first_name.trim(),
      last_name: values.last_name.trim(),
      role: values.role as SessionUser['role'],
      is_active: values.is_active === 'on',
      phone: values.phone.trim(),
    }
    if (values.password) payload.password = values.password
    if (payload.role === 'customer') {
      payload.address = values.address.trim()
      payload.city = values.city.trim()
    }
    if (payload.role === 'craftswoman') {
      payload.community = values.community.trim()
      payload.region = values.region.trim()
      payload.craftswoman_active = values.craftswoman_active === 'on'
    }
    try {
      const updated = await api.updateSuperadminUser(selectedUser.id, payload)
      if (updated.id === currentUser.id) {
        window.location.reload()
        return
      }
      await reloadUsers(updated.id)
      setFeedback(`Cuenta ${updated.username} actualizada.`)
    } catch (saveError) { setError(errorMessage(saveError)) } finally { setSaving(false) }
  }

  async function createNavigationItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canAddNavigation) return
    const form = event.currentTarget
    const values = new FormData(form)
    const roleCodes = values.getAll('role_codes').map(String) as SessionUser['role'][]
    setSaving(true)
    setError('')
    try {
      const created = await api.createNavigationItem({
        label: String(values.get('label') ?? '').trim(),
        route_name: String(values.get('route_name') ?? '').trim(),
        description: String(values.get('description') ?? '').trim(),
        anchor: String(values.get('anchor') ?? '').trim(),
        role_codes: roleCodes,
        permission_resource: String(values.get('permission_resource') ?? '') || null,
        permission_action: String(values.get('permission_action') ?? '') as RBACPermission['action'] || null,
        order: Number(values.get('order') ?? 10),
        active: true,
      })
      setNavigationItems((current) => [...current, created].sort((a, b) => a.order - b.order))
      form.reset()
      setFeedback('Elemento de menú creado y guardado.')
    } catch (saveError) { setError(errorMessage(saveError)) } finally { setSaving(false) }
  }

  async function toggleNavigationItem(item: RBACNavigationItem, active: boolean) {
    if (!canChangeNavigation) return
    setSaving(true)
    setError('')
    try {
      const updated = await api.updateNavigationItem(item.id, { active })
      setNavigationItems((current) => current.map((entry) => entry.id === item.id ? updated : entry))
      setFeedback('Visibilidad del menú actualizada.')
    } catch (saveError) { setError(errorMessage(saveError)) } finally { setSaving(false) }
  }

  async function removeNavigationItem(item: RBACNavigationItem) {
    if (!canDeleteNavigation || !window.confirm(`¿Eliminar la opción "${item.label}" del menú?`)) return
    setSaving(true)
    setError('')
    try {
      await api.deleteNavigationItem(item.id)
      setNavigationItems((current) => current.filter((entry) => entry.id !== item.id))
      setFeedback('Opción de menú eliminada.')
    } catch (saveError) { setError(errorMessage(saveError)) } finally { setSaving(false) }
  }

  async function changeRolePermission(permission: RBACPermission, allowed: boolean) {
    if (!rolePermissions || !canChangeRoles) return
    setSaving(true)
    setError('')
    try {
      setRolePermissions(await api.updateRolePermissions(selectedRole, [{
        resource: permission.resource,
        action: permission.action,
        allowed,
      }]))
      if (canViewAudit) setAudit(await api.auditEvents())
    } catch (saveError) { setError(errorMessage(saveError)) } finally { setSaving(false) }
  }

  async function changeRoleActive(active: boolean) {
    if (!canChangeRoles) return
    setSaving(true)
    setError('')
    try {
      await api.setRoleActive(selectedRole, active)
      setRolePermissions((current) => current ? { ...current, active } : current)
      if (canViewAudit) setAudit(await api.auditEvents())
    } catch (saveError) { setError(errorMessage(saveError)) } finally { setSaving(false) }
  }

  async function changeUserPermission(permission: RBACPermission, effect: 'allow' | 'deny' | null) {
    if (!canChangePermissions) return
    setSaving(true)
    setError('')
    try {
      setUserPermissions(await api.updateUserPermissions(Number(selectedUserId), [{
        resource: permission.resource,
        action: permission.action,
        effect,
      }]))
      if (canViewAudit) setAudit(await api.auditEvents())
    } catch (saveError) { setError(errorMessage(saveError)) } finally { setSaving(false) }
  }

  async function changeDelegation(permission: RBACPermission, allowed: boolean) {
    if (!selectedUser || !canAddDelegations) return
    setSaving(true)
    setError('')
    try {
      await api.setPermissionDelegation({
        admin_user_id: selectedUser.id,
        resource: permission.resource,
        action: permission.action,
        allowed,
      })
      if (canViewDelegations) setDelegations(await api.permissionDelegations())
      if (String(selectedUser.id) === selectedUserId && canViewUsers && canViewCatalog) {
        setUserPermissions(await api.userPermissions(selectedUser.id))
      }
      if (canViewAudit) setAudit(await api.auditEvents())
    } catch (saveError) { setError(errorMessage(saveError)) } finally { setSaving(false) }
  }

  return <section className="rbac-panel" aria-labelledby="rbac-heading">
    <div className="rbac-hero"><div><p className="eyebrow">SEGURIDAD DE LA TIENDA</p><h2 id="rbac-heading">Roles y permisos</h2><p>Administra qué puede consultar y modificar cada tipo de cuenta.</p></div><div className="rbac-total"><strong>{catalog.length}</strong><span>permisos disponibles</span></div></div>
    <nav className="rbac-tabs" aria-label="Secciones de administración de acceso">
      {([['roles', 'Permisos por rol'], ['users', 'Cuentas'], ['delegations', 'Delegaciones'], ['navigation', 'Menú dinámico'], ['audit', 'Auditoría']] as [RBACSection, string][]).map(([section, label]) => <button type="button" key={section} className={activeSection === section ? 'active' : ''} onClick={() => setActiveSection(section)}>{label}</button>)}
    </nav>
    {error && <p className="rbac-error" role="alert">{error}</p>}
    {feedback && <p className="rbac-feedback" role="status">{feedback}</p>}
    {activeSection === "users" && canAddUsers && canAssignRoles && <section className="rbac-block rbac-user-create">
      <div className="rbac-block-heading"><h3>Crear cuenta</h3><button className="button button-outline" type="button" onClick={() => setShowCreateUser((visible) => !visible)}>{showCreateUser ? 'Cerrar' : 'Nueva cuenta'}</button></div>
      {showCreateUser && <form className="rbac-user-form" onSubmit={createManagedUser}>
        <label className="form-label">Usuario<input name="username" required maxLength={150} /></label>
        <label className="form-label">Correo<input name="email" type="email" required maxLength={254} /></label>
        <label className="form-label">Nombre<input name="first_name" maxLength={150} /></label>
        <label className="form-label">Apellido<input name="last_name" maxLength={150} /></label>
        <label className="form-label">Rol<select name="role" value={createUserRole} onChange={(event) => setCreateUserRole(event.target.value as SessionUser['role'])}>{(['customer', 'craftswoman', 'admin', 'superadmin'] as const).map((role) => <option key={role} value={role}>{role}</option>)}</select></label>
        <label className="form-label">Contraseña inicial<input name="password" type="password" required minLength={8} autoComplete="new-password" /></label>
        <label className="form-label">Teléfono<input name="phone" maxLength={30} /></label>
        {createUserRole === 'customer' && <><label className="form-label">Dirección<input name="address" maxLength={500} /></label><label className="form-label">Ciudad<input name="city" maxLength={100} /></label></>}
        {createUserRole === 'craftswoman' && <><label className="form-label">Comunidad<input name="community" maxLength={150} /></label><label className="form-label">Región<input name="region" maxLength={100} /></label><label className="admin-check"><input name="craftswoman_active" type="checkbox" /> Perfil artesana activo</label></>}
        <label className="admin-check"><input name="is_active" type="checkbox" defaultChecked /> Cuenta activa</label>
        <button className="button button-dark" disabled={saving}>{saving ? <LoaderCircle className="spin" size={15} /> : <Plus size={15} />} Crear cuenta</button>
      </form>}
    </section>}
    <div className="rbac-layout">
      {activeSection === 'roles' && canViewRoles && <section className="rbac-block rbac-main-block"><div className="rbac-block-heading"><div><h3>Configurar permisos por rol</h3><p>Selecciona un rol y activa únicamente las acciones que necesita.</p></div><div className="rbac-role-heading-actions">{canAddNavigation && <button type="button" className="button button-outline" onClick={() => setActiveSection('navigation')}><Plus size={15} /> Añadir al menú</button>}<select aria-label="Rol a configurar" value={selectedRole} onChange={(event) => { setSelectedRole(event.target.value as SessionUser['role']); setPermissionSearch('') }}>{(['superadmin', 'admin', 'craftswoman', 'customer'] as const).map((role) => <option key={role} value={role}>{rbacRoleLabels[role]}</option>)}</select></div></div>
        {rolePermissions && <div className="rbac-role-status"><label className="admin-check rbac-active"><input type="checkbox" checked={rolePermissions.active} disabled={saving || !canChangeRoles || selectedRole === 'superadmin'} onChange={(event) => void changeRoleActive(event.target.checked)} /> Rol activo</label><span>{rolePermissions.active ? 'Este rol puede acceder al sistema.' : 'Este rol está desactivado y no puede acceder al sistema.'}</span></div>}
        {selectedRole === 'superadmin' && <p className="rbac-info">El superadministrador conserva acceso global. Esta matriz es solo informativa y no se puede modificar.</p>}
        <label className="rbac-search"><Search size={16} /><input value={permissionSearch} onChange={(event) => setPermissionSearch(event.target.value)} placeholder="Buscar recurso o acción..." /></label>
        <div className="rbac-groups">{Object.entries(permissionGroups).map(([resource, permissions]) => <section className="rbac-resource-card" key={resource}><div className="rbac-resource-heading"><strong>{rbacResourceLabels[resource] ?? resource}</strong><span>{permissions.filter((permission) => permission.allowed).length} de {permissions.length} acciones activas</span></div><div className="rbac-actions-grid">{permissions.map((permission) => <label className="rbac-action-option" key={permission.resource + '.' + permission.action}><input type="checkbox" checked={Boolean(permission.allowed)} disabled={saving || !canChangeRoles || !rolePermissions?.active || selectedRole === 'superadmin'} onChange={(event) => void changeRolePermission(permission, event.target.checked)} /><span>{rbacActionLabels[permission.action]}</span></label>)}</div></section>)}</div>
        {Object.keys(permissionGroups).length === 0 && <p className="muted-copy">No hay permisos que coincidan con la búsqueda.</p>}
      </section>}
      {activeSection === "users" && canViewUsers && canViewCatalog && <section className="rbac-block"><div className="rbac-block-heading"><div><h3>Cuenta y permisos individuales</h3><p>Administra los datos y excepciones de una cuenta específica.</p></div><select aria-label="Usuario a gestionar" value={selectedUserId} onChange={(event) => setSelectedUserId(event.target.value)}><option value="">Selecciona una cuenta</option>{users.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.username} · {candidate.role}</option>)}</select></div>
        {selectedUser && <form className="rbac-user-form" key={`${selectedUser.id}-${selectedUser.username}-${selectedUser.email}-${selectedUser.role}`} onSubmit={updateManagedUser}>
          <label className="form-label">Usuario<input name="username" required maxLength={150} defaultValue={selectedUser.username} disabled={!canChangeUsers} /></label>
          <label className="form-label">Correo<input name="email" type="email" required maxLength={254} defaultValue={selectedUser.email} disabled={!canChangeUsers} /></label>
          <label className="form-label">Nombre<input name="first_name" maxLength={150} defaultValue={selectedUser.first_name} disabled={!canChangeUsers} /></label>
          <label className="form-label">Apellido<input name="last_name" maxLength={150} defaultValue={selectedUser.last_name} disabled={!canChangeUsers} /></label>
          <label className="form-label">Rol<select name="role" defaultValue={selectedUser.role === 'unassigned' ? 'customer' : selectedUser.role} disabled={!canChangeUsers || !canAssignRoles}>{(['customer', 'craftswoman', 'admin', 'superadmin'] as const).map((role) => <option key={role} value={role}>{role}</option>)}</select></label>
          <label className="form-label">Nueva contraseña<input name="password" type="password" minLength={8} autoComplete="new-password" disabled={!canChangeUsers} /></label>
          <label className="admin-check"><input name="is_active" type="checkbox" defaultChecked={selectedUser.is_active} disabled={!canChangeUsers || selectedUser.role === 'superadmin'} /> Cuenta activa</label>
          {selectedUser.role === 'customer' && <><label className="form-label">Teléfono<input name="phone" maxLength={30} defaultValue={selectedUser.profile?.phone ?? ''} disabled={!canChangeUsers} /></label><label className="form-label">Dirección<input name="address" maxLength={500} defaultValue={selectedUser.profile?.address ?? ''} disabled={!canChangeUsers} /></label><label className="form-label">Ciudad<input name="city" maxLength={100} defaultValue={selectedUser.profile?.city ?? ''} disabled={!canChangeUsers} /></label></>}
          {selectedUser.role === 'craftswoman' && <><label className="form-label">Teléfono<input name="phone" maxLength={30} defaultValue={selectedUser.profile?.phone ?? ''} disabled={!canChangeUsers} /></label><label className="form-label">Comunidad<input name="community" maxLength={150} defaultValue={selectedUser.profile?.community ?? ''} disabled={!canChangeUsers} /></label><label className="form-label">Región<input name="region" maxLength={100} defaultValue={selectedUser.profile?.region ?? ''} disabled={!canChangeUsers} /></label><label className="admin-check"><input name="craftswoman_active" type="checkbox" defaultChecked={selectedUser.profile?.active ?? false} disabled={!canChangeUsers} /> Perfil artesana activo</label></>}
          {canChangeUsers && <button className="button button-outline" disabled={saving}>{saving ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />} Guardar cuenta</button>}
        </form>}
        <div className="rbac-permission-list">{userPermissions?.permissions.map((permission) => <label className="rbac-permission" key={`${permission.resource}.${permission.action}`}><span><strong>{rbacResourceLabels[permission.resource] ?? permission.resource}</strong><small>{rbacActionLabels[permission.action]} · {permission.name}</small></span><select aria-label={`${permission.resource} ${permission.action} para ${userPermissions.username}`} value={permission.effect ?? ''} disabled={saving || !canChangePermissions} onChange={(event) => void changeUserPermission(permission, event.target.value ? event.target.value as 'allow' | 'deny' : null)}><option value="">Heredado</option><option value="allow">Permitir</option><option value="deny">Denegar</option></select></label>)}</div>
      </section>}
      {activeSection === "delegations" && canViewDelegations && <section className="rbac-block"><div className="rbac-block-heading"><h3>Delegaciones para admin</h3><span>{selectedUser?.role === 'admin' ? selectedUser.username : 'Selecciona un admin'}</span></div>
        {selectedUser?.role === 'admin' ? <div className="rbac-permission-list">{catalog.map((permission) => {
          const delegated = delegations.some((item) => item.admin_user_id === selectedUser.id && item.resource === permission.resource && item.action === permission.action)
          return <label className="rbac-permission" key={`${permission.resource}.${permission.action}`}><input type="checkbox" checked={delegated} disabled={saving || !canAddDelegations} onChange={(event) => void changeDelegation(permission, event.target.checked)} /><span><strong>{permission.resource}</strong><small>{permission.action} · {permission.name}</small></span></label>
        })}</div> : <p className="muted-copy">Las delegaciones solo se pueden asignar a cuentas con rol admin.</p>}
      </section>}
      {activeSection === 'navigation' && canViewNavigation && <section className="rbac-block">
        <div className="rbac-block-heading"><div><h3>Menú y vistas por rol</h3><p>Registra opciones de navegación, define a qué roles se muestran y cuál permiso deben tener.</p></div><span>{navigationItems.length} opciones</span></div>
        {canAddNavigation && <form className="rbac-user-form" onSubmit={createNavigationItem}>
          <label className="form-label">Nombre visible<input name="label" required maxLength={80} placeholder="Ej. Mis pedidos" /></label>
          <label className="form-label">Pantalla permitida<select name="route_name" required value={newNavigationRoute} onChange={(event) => { const next = event.target.value; setNewNavigationRoute(next); const option = navigationRouteOptions.find((item) => item.value === next); setNewNavigationRoles(option ? [...option.roles] as SessionUser['role'][] : []) }}>{navigationRouteOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          <label className="form-label">Sección (opcional)<input name="anchor" maxLength={80} placeholder="Ej. pedidos" /></label>
          <label className="form-label">Descripción<input name="description" maxLength={220} placeholder="Describe qué encontrará el usuario" /></label>
          <label className="form-label">Orden<input name="order" type="number" min="0" max="32767" defaultValue="10" /></label>
          <label className="form-label">Permiso requerido · recurso<select name="permission_resource" defaultValue=""><option value="">Sin requisito adicional</option>{Object.entries(rbacResourceLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label>
          <label className="form-label">Permiso requerido · acción<select name="permission_action" defaultValue=""><option value="">Sin acción</option>{Object.entries(rbacActionLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label>
          <fieldset className="rbac-role-picker"><legend>Mostrar a estos roles</legend>{(['superadmin', 'admin', 'craftswoman', 'customer'] as const).filter((role) => navigationRouteOptions.find((option) => option.value === newNavigationRoute)?.roles.some((allowedRole) => allowedRole === role)).map((role) => <label key={role}><input type="checkbox" name="role_codes" value={role} checked={newNavigationRoles.includes(role)} onChange={(event) => setNewNavigationRoles((current) => event.target.checked ? [...current, role] : current.filter((item) => item !== role))} /> {rbacRoleLabels[role]}</label>)}</fieldset>
          <button className="button button-dark" disabled={saving}>{saving ? 'Guardando…' : 'Añadir opción al menú'}</button>
        </form>}
        <div className="rbac-nav-list">{navigationItems.map((item) => <article className="rbac-nav-row" key={item.id}><div><strong>{item.label}</strong><small>{item.route_name} · Orden {item.order}</small><small>{item.role_codes.map((role) => rbacRoleLabels[role]).join(', ')}</small><small>{item.permission_resource ? (rbacResourceLabels[item.permission_resource] ?? item.permission_resource) + ' · ' + rbacActionLabels[item.permission_action ?? 'view'] : 'Sin permiso adicional configurado'}</small></div><div className="rbac-nav-actions"><label><input type="checkbox" checked={item.active} disabled={saving || !canChangeNavigation} onChange={(event) => void toggleNavigationItem(item, event.target.checked)} /> Visible</label>{canDeleteNavigation && <button type="button" className="button button-outline" disabled={saving} onClick={() => void removeNavigationItem(item)}>Eliminar</button>}</div></article>)}</div>
        {navigationItems.length === 0 && <p className="muted-copy">Todavía no hay opciones de menú configuradas.</p>}
      </section>}
      {activeSection === "audit" && canViewAudit && <section className="rbac-block"><div className="rbac-block-heading"><h3>Actividad sensible</h3><span>{audit.length} eventos recientes</span></div>
        <div className="rbac-audit-list">{audit.slice(0, 12).map((event) => <article className="rbac-audit-row" key={event.id}><time>{new Date(event.created_at).toLocaleString('es-CO')}</time><strong>{event.action}</strong><span>{event.actor ?? 'Sistema'} · {event.affected_user ?? event.resource}</span><small>{event.result === 'denied' ? 'Denegado' : 'Correcto'}</small></article>)}</div>
      </section>}
    </div>
  </section>
}

function AdminProductRow({ product, busy, canChange, onSave }: { product: AdminProduct; busy: boolean; canChange: boolean; onSave: (id: number, values: Partial<AdminProduct>) => void }) {
  const [price, setPrice] = useState(product.price)
  const [stock, setStock] = useState(String(product.stock))
  const [active, setActive] = useState(product.active)
  return <div className="admin-product-row"><div className="admin-product-name"><span className="product-origin">{product.sku}</span><strong>{product.name}</strong><small>{product.size} · {product.region || 'Sin región'}</small></div>{canChange ? <><label className="admin-inline-field">Precio<input aria-label={`Precio de ${product.name}`} type="number" min="0" step="1" value={price} onChange={(event) => setPrice(event.target.value)} /></label><label className="admin-inline-field">Stock<input aria-label={`Stock de ${product.name}`} type="number" min="0" step="1" value={stock} onChange={(event) => setStock(event.target.value)} /></label><label className="admin-check"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} /> Publicado</label><button className="button button-outline" disabled={busy} onClick={() => onSave(product.id, { price, stock: Number(stock), active })}>Guardar</button></> : <><span>{money(product.price)}</span><span>Stock {product.stock}</span><span>{product.active ? 'Publicado' : 'Oculto'}</span></>}</div>
}

function AdminOrderRow({ order, busy, canChange, onStatus }: { order: Order; busy: boolean; canChange: boolean; onStatus: (id: number, status: string) => void }) {
  return <div className="admin-order-row"><OrderCard order={order} />{canChange && <label className="admin-inline-field">Estado<select aria-label={`Estado del pedido ${order.id}`} disabled={busy} value={order.status} onChange={(event) => onStatus(order.id, event.target.value)}>{Object.entries(orderStatusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>}</div>
}

function DesignSummary({ design }: { design: CustomDesign }) {
  return <article className="design-summary"><div className="design-summary-heading"><div><p className="product-origin">DISEÑO #{String(design.id).padStart(4, '0')}</p><h3>{design.pattern.charAt(0).toUpperCase() + design.pattern.slice(1)} · Talla {design.size}</h3></div><span className={`status-pill status-${design.status}`}>{statusLabel(design.status)}</span></div><div className="design-summary-details"><div className="design-colors" aria-label="Colores del diseño"><span style={{ backgroundColor: design.base_color }} /><span style={{ backgroundColor: design.accent_color_one }} /><span style={{ backgroundColor: design.accent_color_two }} /></div><span>{design.quantity} {design.quantity === 1 ? 'pieza' : 'piezas'}</span><strong>{money(design.estimated_price)}</strong><time>{dateLabel(design.created_at)}</time></div>{design.notes && <p className="design-notes">{design.notes}</p>}{design.craftswoman_name && <p className="design-assignee">Tejido por {design.craftswoman_name}</p>}</article>
}

function OrderCard({ order }: { order: Order }) {
  return <article className="order-card"><div className="order-topline"><div><p className="product-origin">PEDIDO #{String(order.id).padStart(4, '0')}</p><h3>{dateLabel(order.created_at)}</h3></div><span className={`status-pill status-${order.status}`}>{order.status_label}</span></div><div className="order-products">{order.items.map((item) => <div className="order-product" key={item.id}><ProductPhoto src={item.product.image_url} alt={item.product.name} className="order-product-photo" /><span>{item.product.name}<small>Cantidad: {item.quantity}</small></span><strong>{money(item.subtotal)}</strong></div>)}</div><div className="order-total"><span>{order.craftswoman ? `Tejido por ${order.craftswoman.name}` : order.payment_method === 'contact' ? 'Pago por coordinar' : `Pago: ${order.payment_method}`}</span><strong>Total {money(order.total)}</strong></div></article>
}

function OrderSuccess({ order, onClose, onOrders }: { order: Order; onClose: () => void; onOrders: () => void }) {
  return <div className="overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="success-dialog" role="dialog" aria-modal="true" aria-labelledby="success-title"><div className="success-icon"><Check size={24} /></div><p className="eyebrow">PEDIDO #{String(order.id).padStart(4, '0')}</p><h2 id="success-title">Tu elección ya<br /><em>está en camino.</em></h2><p>Guardamos tu pedido. El pago y la entrega se coordinan contigo.</p><div className="success-total"><span>Total del pedido</span><strong>{money(order.total)}</strong></div><button className="button button-dark full-button" onClick={onOrders}>Seguir mi pedido <ArrowRight size={15} /></button><button className="text-button success-close" onClick={onClose}>Volver a la tienda</button></section></div>
}

function Footer({ onInstagram }: { onInstagram: () => void }) {
  return <footer className="site-footer"><div className="footer-main"><div className="footer-brand"><span className="wordmark-symbol" aria-hidden="true"><span /><span /><span /></span><div><strong>wayuuwaa</strong><p>Tejido con origen.</p></div></div><p className="footer-note">Cada pieza lleva consigo el tiempo y la mirada de quien la teje.</p><button className="social-button" onClick={onInstagram} aria-label="Instagram"><Camera size={18} /></button></div><div className="footer-bottom"><span>© WAYUUWAA · LA GUAJIRA, COLOMBIA</span><span>HECHO A MANO, CON RESPETO</span><a href="#coleccion">VOLVER ARRIBA <ArrowUpRight size={12} /></a></div></footer>
}