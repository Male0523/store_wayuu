import type {
  AdminCategory,
  AdminProduct,
  Cart,
  Category,
  CustomDesign,
  CraftswomanDashboard,
  Order,
  Page,
  Product,
  SessionUser,
  UserProfile,
} from '../types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1').replace(/\/$/, '')

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function csrfCookie(): string | undefined {
  const entry = document.cookie.split('; ').find((cookie) => cookie.startsWith('csrftoken='))
  return entry ? decodeURIComponent(entry.slice('csrftoken='.length)) : undefined
}

async function ensureCsrf(): Promise<string> {
  let token = csrfCookie()
  if (!token) {
    await fetch(`${API_BASE}/csrf/`, { credentials: 'include' })
    token = csrfCookie()
  }
  if (!token) throw new ApiError('No fue posible iniciar una sesión segura. Intenta de nuevo.', 0)
  return token
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) headers.set('X-CSRFToken', await ensureCsrf())

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    method,
    headers,
    credentials: 'include',
  })

  if (response.status === 204) return undefined as T
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = payload?.detail
      ?? Object.values(payload ?? {}).flat().find((value) => typeof value === 'string')
      ?? `No se pudo completar la solicitud (${response.status}).`
    throw new ApiError(String(detail), response.status)
  }
  return payload as T
}

const json = (value: unknown): string => JSON.stringify(value)

export const api = {
  health: () => request<{ status: string }>('/'),
  categories: () => request<Category[]>('/categories/'),
  products: (params: URLSearchParams) => request<Page<Product>>(`/products/?${params}`),
  product: (id: number) => request<Product>(`/products/${id}/`),
  me: () => request<{ user: SessionUser }>('/auth/me/'),
  profile: () => request<UserProfile>('/profile/'),
  updateProfile: (values: Partial<UserProfile>) =>
    request<UserProfile>('/profile/', { method: 'PATCH', body: json(values) }),
  login: (username: string, password: string) =>
    request<{ user: SessionUser }>('/auth/login/', { method: 'POST', body: json({ username, password }) }),
  register: (values: Record<string, string>, craftswoman = false) =>
    request<{ user: SessionUser }>(
      craftswoman ? '/auth/register/craftswoman/' : '/auth/register/',
      { method: 'POST', body: json(values) },
    ),
  logout: () => request<void>('/auth/logout/', { method: 'POST' }),
  cart: () => request<Cart>('/cart/'),
  addToCart: (productId: number, quantity = 1) =>
    request('/cart/items/', { method: 'POST', body: json({ product_id: productId, quantity }) }),
  setCartQuantity: (productId: number, quantity: number) =>
    request(`/cart/items/${productId}/`, { method: 'PATCH', body: json({ quantity }) }),
  removeFromCart: (productId: number) =>
    request<void>(`/cart/items/${productId}/`, { method: 'DELETE' }),
  checkout: (values: { address: string; city: string; payment_method: string; notes: string }) =>
    request<Order>('/checkout/', { method: 'POST', body: json(values) }),
  orders: () => request<Page<Order>>('/orders/'),
  designs: () => request<CustomDesign[]>('/designs/'),
  createDesign: (values: Record<string, string | number>) =>
    request('/designs/', { method: 'POST', body: json(values) }),
  craftswomanDashboard: () => request<CraftswomanDashboard>('/craftswoman/dashboard/'),
  acceptOrder: (id: number) => request<Order>(`/craftswoman/orders/${id}/accept/`, { method: 'POST' }),
  updateOrderStatus: (id: number, value: string) =>
    request<Order>(`/craftswoman/orders/${id}/status/`, { method: 'PATCH', body: json({ status: value }) }),
  updateDesignStatus: (id: number, value: string) =>
    request<Pick<CustomDesign, 'id' | 'status'>>(`/craftswoman/designs/${id}/status/`, { method: 'PATCH', body: json({ status: value }) }),
  adminProducts: () => request<AdminProduct[]>('/admin/products/'),
  adminCategories: () => request<AdminCategory[]>('/admin/categories/'),
  createAdminCategory: (values: Pick<AdminCategory, 'name' | 'description' | 'active'>) =>
    request<AdminCategory>('/admin/categories/', { method: 'POST', body: json(values) }),
  updateAdminCategory: (id: number, values: Partial<AdminCategory>) =>
    request<AdminCategory>(`/admin/categories/${id}/`, { method: 'PATCH', body: json(values) }),
  createAdminProduct: (values: Partial<AdminProduct>) =>
    request<AdminProduct>('/admin/products/', { method: 'POST', body: json(values) }),
  updateAdminProduct: (id: number, values: Partial<AdminProduct>) =>
    request<AdminProduct>(`/admin/products/${id}/`, { method: 'PATCH', body: json(values) }),
  updateAdminOrderStatus: (id: number, value: string) =>
    request<Order>(`/admin/orders/${id}/status/`, { method: 'PATCH', body: json({ status: value }) }),
  adminUrl: API_BASE.replace(/\/api\/v1\/?$/, '/admin/'),
}