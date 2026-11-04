export interface Category {
  id: number
  name: string
  description: string
}

export interface AdminCategory extends Category {
  active: boolean
}

export interface CraftswomanSummary {
  id: number
  name: string
  community: string
  region: string
  biography?: string
}

export interface Product {
  id: number
  sku: string
  name: string
  category: Category
  craftswoman: CraftswomanSummary | null
  description: string
  region: string
  color: string
  size: string
  production_time: string
  price: string
  stock: number
  image_url: string
  made_to_order: boolean
  is_custom_design?: boolean
  created_at: string
  updated_at: string
  active?: boolean
}

export interface AdminProduct extends Omit<Product, 'category' | 'craftswoman'> {
  category: number
  craftswoman: number | null
  craftswoman_name?: string | null
  active: boolean
}

export interface CartItem {
  product: Pick<Product, 'id' | 'name' | 'image_url' | 'price'> & Partial<Product>
  quantity: number
  subtotal: string
}

export interface Cart {
  items: CartItem[]
  total: string
  count: number
}

export interface UserProfile {
  id?: number
  name: string
  email: string
  phone?: string
  address?: string
  city?: string
  community?: string
  region?: string
  active?: boolean
}

export interface CustomDesign {
  id: number
  pattern: string
  base_color: string
  accent_color_one: string
  accent_color_two: string
  size: string
  quantity: number
  notes: string
  estimated_price: string
  status: string
  status_label?: string
  created_at: string
  craftswoman_name?: string | null
}

export interface SessionUser {
  id: number
  username: string
  name: string
  email: string
  role: 'customer' | 'craftswoman' | 'admin' | 'superadmin'
  permissions?: string[]
  profile: UserProfile | null
}

export interface OrderItem {
  id: number
  product: Pick<Product, 'id' | 'name' | 'image_url' | 'price'>
  quantity: number
  unit_price: string
  subtotal: string
}

export interface Order {
  id: number
  customer_name?: string
  customer_username?: string
  status: string
  status_label: string
  payment_method: string
  shipping_address: string
  notes: string
  created_at: string
  updated_at: string
  items: OrderItem[]
  total: string
  craftswoman: CraftswomanSummary | null
}

export interface Page<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface PublicCraftswoman extends CraftswomanSummary {}

export interface CraftswomanDashboard {
  active: boolean
  available_orders: Order[]
  orders: Order[]
  designs: CustomDesign[]
}

export interface SuperadminUser {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: 'customer' | 'craftswoman' | 'admin' | 'superadmin' | 'unassigned'
  role_name: string
  is_active: boolean
  active: boolean
  location: string
  date_joined: string
  profile: ManagedUserProfile | null
}

export interface ManagedUserProfile {
  id?: number
  name: string
  email?: string
  phone?: string
  address?: string
  city?: string
  community?: string
  region?: string
  active?: boolean
}

export interface SuperadminUserInput {
  username: string
  email: string
  first_name?: string
  last_name?: string
  role: SessionUser['role']
  is_active?: boolean
  password?: string
  phone?: string
  address?: string
  city?: string
  community?: string
  region?: string
  craftswoman_active?: boolean
}

export type RBACAction = 'view' | 'add' | 'change' | 'delete'

export interface RBACPermission {
  resource: string
  action: RBACAction
  codename: string
  name: string
  allowed?: boolean
  effect?: 'allow' | 'deny' | null
}

export interface RBACRolePermissions {
  role: SessionUser['role']
  active: boolean
  permissions: RBACPermission[]
}

export interface RBACUserPermissions {
  user_id: number
  username: string
  permissions: RBACPermission[]
}

export interface RBACDelegation {
  admin_user_id: number
  username: string
  resource: string
  action: RBACAction
  codename: string
  granted_by: string
}

export interface AuditEvent {
  id: number
  actor: string | null
  action: string
  resource: string
  affected_user: string | null
  object_type: string
  object_id: string
  result: 'success' | 'denied'
  details: Record<string, unknown>
  created_at: string
}
export interface RBACNavigationItem {
  id: number
  label: string
  route_name: string
  anchor: string
  description: string
  role_codes: SessionUser['role'][]
  permission_resource: string | null
  permission_action: RBACAction | null
  order: number
  active: boolean
}

export interface RBACNavigationInput {
  label: string
  route_name: string
  anchor?: string
  description?: string
  role_codes: SessionUser['role'][]
  permission_resource?: string | null
  permission_action?: RBACAction | null
  order?: number
  active?: boolean
}
