import type {
  AdminCategory,
  AdminProduct,
  Cart,
  Category,
  CustomDesign,
  CraftswomanDashboard,
  AuditEvent,
  Order,
  Page,
  Product,
  RBACAction,
  RBACDelegation,
  RBACPermission,
  RBACNavigationItem,
  RBACNavigationInput,
  RBACRolePermissions,
  RBACUserPermissions,
  SessionUser,
  SuperadminUser,
  SuperadminUserInput,
  UserProfile,
} from '../types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '/api/v1').replace(/\/$/, '')

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
    const response = await fetch(`${API_BASE}/csrf/`, { credentials: 'include' })
    if (!response.ok) throw new ApiError('No fue posible obtener el token de seguridad.', response.status)
    const payload = await response.json().catch(() => null)
    token = typeof payload?.csrfToken === 'string' ? payload.csrfToken : csrfCookie()
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

  if (response.status === 401 && path !== '/auth/me/') {
    window.dispatchEvent(new Event('wayuu:session-expired'))
  }

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
  craftswomanProducts: () => request<Product[]>('/craftswoman/products/'),
  createCraftswomanProduct: (values: {
    sku: string; name: string; category: number; description?: string; region?: string;
    color?: string; size?: string; production_time?: string; price: string | number;
    stock: number; image_url?: string; made_to_order?: boolean;
  }) => request<Product>('/craftswoman/products/', { method: 'POST', body: json(values) }),
  updateCraftswomanProduct: (id: number, values: Record<string, string | number | boolean>) =>
    request<Product>(`/craftswoman/products/${id}/`, { method: 'PATCH', body: json(values) }),
  craftswomanDashboard: () => request<CraftswomanDashboard>('/craftswoman/dashboard/'),
  acceptOrder: (id: number) => request<Order>(`/craftswoman/orders/${id}/accept/`, { method: 'POST' }),
  updateOrderStatus: (id: number, value: string) =>
    request<Order>(`/craftswoman/orders/${id}/status/`, { method: 'PATCH', body: json({ status: value }) }),
  updateDesignStatus: (id: number, value: string) =>
    request<Pick<CustomDesign, 'id' | 'status'>>(`/craftswoman/designs/${id}/status/`, { method: 'PATCH', body: json({ status: value }) }),
  adminProducts: () => request<AdminProduct[]>('/admin/products/'),
  superadminUsers: (params: URLSearchParams) => request<SuperadminUser[]>(`/admin/users/?${params}`),
  createSuperadminUser: (values: SuperadminUserInput) =>
    request<SuperadminUser>('/admin/users/', { method: 'POST', body: json(values) }),
  superadminUser: (userId: number) => request<SuperadminUser>(`/admin/users/${userId}/`),
  updateSuperadminUser: (userId: number, values: Partial<SuperadminUserInput>) =>
    request<SuperadminUser>(`/admin/users/${userId}/`, { method: 'PATCH', body: json(values) }),
  rbacCatalog: () => request<{ permissions: RBACPermission[] }>('/admin/rbac/catalog/'),
  rolePermissions: (role: SessionUser['role']) =>
    request<RBACRolePermissions>(`/admin/rbac/roles/${role}/permissions/`),
  updateRolePermissions: (role: SessionUser['role'], permissions: Pick<RBACPermission, 'resource' | 'action' | 'allowed'>[]) =>
    request<RBACRolePermissions>(`/admin/rbac/roles/${role}/permissions/`, {
      method: 'PUT', body: json({ permissions }),
    }),
  setRoleActive: (role: SessionUser['role'], active: boolean) =>
    request<{ role: string; active: boolean }>(`/admin/rbac/roles/${role}/permissions/`, {
      method: 'PATCH', body: json({ active }),
    }),
  userPermissions: (userId: number) =>
    request<RBACUserPermissions>(`/admin/rbac/users/${userId}/permissions/`),
  updateUserPermissions: (userId: number, permissions: Pick<RBACPermission, 'resource' | 'action' | 'effect'>[]) =>
    request<RBACUserPermissions>(`/admin/rbac/users/${userId}/permissions/`, {
      method: 'PUT', body: json({ permissions }),
    }),
  permissionDelegations: () => request<RBACDelegation[]>('/admin/rbac/delegations/'),
  setPermissionDelegation: (values: { admin_user_id: number; resource: string; action: RBACAction; allowed: boolean }) =>
    request<{ detail: string }>('/admin/rbac/delegations/', { method: 'POST', body: json(values) }),
  setUserRole: (userId: number, role: SessionUser['role']) =>
    request<{ user_id: number; role: string }>(`/admin/users/${userId}/role/`, {
      method: 'PATCH', body: json({ role }),
    }),
  auditEvents: () => request<AuditEvent[]>('/admin/rbac/audit/'),
  roleNavigation: () => request<RBACNavigationItem[]>('/navigation/menu/'),
  navigationItems: () => request<RBACNavigationItem[]>('/admin/rbac/navigation/'),
  createNavigationItem: (values: RBACNavigationInput) =>
    request<RBACNavigationItem>('/admin/rbac/navigation/', { method: 'POST', body: json(values) }),
  updateNavigationItem: (id: number, values: Partial<RBACNavigationInput>) =>
    request<RBACNavigationItem>(`/admin/rbac/navigation/${id}/`, { method: 'PATCH', body: json(values) }),
  deleteNavigationItem: (id: number) =>
    request<void>(`/admin/rbac/navigation/${id}/`, { method: 'DELETE' }),

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