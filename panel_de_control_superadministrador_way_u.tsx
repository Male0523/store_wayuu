import React, { useEffect, useState, useMemo } from 'react';
import { useUserSession } from './frontend/src/context/user-context';
import { api, ApiError } from './frontend/src/lib/api';
import type { RBACPermission, RBACRolePermissions, SessionUser, SuperadminUser } from './frontend/src/types';
import {
  Home,
  Shield,
  ShieldCheck,
  Users,
  Layers,
  FolderTree,
  ShoppingBag,
  Package,
  ShoppingCart,
  BarChart3,
  Settings,
  Bell,
  Search,
  Eye,
  Plus,
  Edit,
  Trash2,
  CheckCircle2,
  Cog,
  RotateCcw,
  Save,
  Check,
  X,
  AlertCircle,
  Filter,
  UserPlus,
  Activity,
  ChevronDown,
  ChevronRight,
  Database,
  Lock,
  Unlock,
  FileText,
  UserCheck,
  UserX,
  Info,
  Clock,
  Sparkles,
  Download,
  CheckSquare,
  Square,
  Truck,
  TrendingUp,
  Tag,
  AlertTriangle,
  Send,
  CreditCard,
  Globe,
  Sliders,
  DollarSign,
  Briefcase,
  MapPin,
  Calendar,
  RefreshCw,
  ExternalLink,
  LogOut
} from 'lucide-react';

// --- DEFINICIONES DE ROLES ---
const ROLES = [
  {
    id: 'superadmin',
    name: 'Superadministrador',
    shortName: 'Superadmin.',
    badgeColor: 'bg-rose-100 text-rose-800 border-rose-200',
    dotColor: 'bg-[#5C1D24]',
    description: 'Acceso total al sistema',
    usersCount: 3,
  },
  {
    id: 'admin',
    name: 'Administrador de tienda',
    shortName: 'Admin. tienda',
    badgeColor: 'bg-pink-100 text-pink-800 border-pink-200',
    dotColor: 'bg-pink-500',
    description: 'Gestión comercial y operativa',
    usersCount: 8,
  },
  {
    id: 'craftswoman',
    name: 'Tejedora',
    shortName: 'Tejedora',
    badgeColor: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    dotColor: 'bg-emerald-500',
    description: 'Gestión de sus productos y pedidos',
    usersCount: 42,
  },
  {
    id: 'customer',
    name: 'Cliente',
    shortName: 'Cliente',
    badgeColor: 'bg-amber-100 text-amber-800 border-amber-200',
    dotColor: 'bg-amber-600',
    description: 'Exploración y compras',
    usersCount: 1250,
  },
];

// --- LOS 14 RECURSOS REQUERIDOS ---
const RESOURCES = [
  { id: 'panel_principal', name: 'Panel principal', description: 'Vista general del sistema con accesos rápidos y estadísticas.', icon: Home, slug: '/admin/dashboard' },
  { id: 'catalogo', name: 'Catálogo', description: 'Navegación visual de la oferta artesanal para clientes.', icon: ShoppingBag, slug: '/catalogo' },
  { id: 'productos', name: 'Productos', description: 'Listado global, especificaciones, técnicas y asignación de artesanías.', icon: Package, slug: '/admin/productos' },
  { id: 'publicacion_productos', name: 'Publicación de productos', description: 'Aprobación y publicación de nuevos productos tejidos.', icon: Plus, slug: '/admin/publicacion' },
  { id: 'inventario', name: 'Inventario', description: 'Control de stock de hilo, mochilas, chinchorros y artesanías disponibles.', icon: Layers, slug: '/admin/inventario' },
  { id: 'pedidos', name: 'Pedidos', description: 'Gestión de órdenes de compra, pagos y guías de envío.', icon: ShoppingCart, slug: '/admin/pedidos' },
  { id: 'ventas', name: 'Ventas', description: 'Historial de transacciones, ingresos y comprobantes.', icon: BarChart3, slug: '/admin/ventas' },
  { id: 'clientes', name: 'Clientes', description: 'Directorio de compradores, historial de compras y puntos.', icon: Users, slug: '/admin/clientes' },
  { id: 'tejedoras', name: 'Tejedoras', description: 'Registro de artesanas Wayúu, comunidades y asignación de trabajos.', icon: UserCheck, slug: '/admin/tejedoras' },
  { id: 'usuarios', name: 'Usuarios', description: 'Administración de cuentas de usuario, credenciales y estados.', icon: Users, slug: '/admin/usuarios' },
  { id: 'roles_permisos', name: 'Roles y permisos', description: 'Configuración del sistema RBAC y matices de acceso.', icon: ShieldCheck, slug: '/admin/seguridad/roles' },
  { id: 'recursos_menu', name: 'Recursos y menú dinámico', description: 'Estructuración de rutas, menús y recursos del sistema.', icon: FolderTree, slug: '/admin/seguridad/recursos' },
  { id: 'reportes', name: 'Reportes', description: 'Estadísticas avanzadas de ventas, rendimiento de tejedoras e impacto comunitario.', icon: FileText, slug: '/admin/reportes' },
  { id: 'perfil_personal', name: 'Perfil personal', description: 'Datos del usuario autenticado, preferencias y clave.', icon: Cog, slug: '/perfil' },
];

// --- ACCIONES RBAC REALES DEL BACKEND ---
const ACTIONS = [
  { id: 'view', label: 'Ver', code: 'V', icon: Eye },
  { id: 'add', label: 'Crear', code: 'C', icon: Plus },
  { id: 'change', label: 'Editar', code: 'E', icon: Edit },
  { id: 'delete', label: 'Eliminar', code: 'X', icon: Trash2 },
];

function buildRolePermissionsMatrix(
  catalog: RBACPermission[],
  roleResponses: RBACRolePermissions[]
): Record<string, Record<string, Record<string, boolean>>> {
  const matrix: Record<string, Record<string, Record<string, boolean>>> = {};

  for (const resource of Array.from(new Set(catalog.map((permission) => permission.resource)))) {
    matrix[resource] = {};
    for (const role of ROLES) {
      matrix[resource][role.id] = {};
    }
  }

  for (const permission of catalog) {
    for (const role of ROLES) {
      const matchingRole = roleResponses.find((entry) => entry.role === role.id);
      const matchingPermission = matchingRole?.permissions.find(
        (entry) => entry.resource === permission.resource && entry.action === permission.action,
      );
      matrix[permission.resource][role.id][permission.action] = Boolean(matchingPermission?.allowed ?? false);
    }
  }

  return matrix;
}

// MATRIZ INICIAL RBAC
const INITIAL_PERMISSIONS = {
  panel_principal: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    admin_tienda: { ver: true, crear: true, editar: true, eliminar: false, aprobar: true, gestionar: false },
    tejedora: { ver: true, crear: false, editar: true, eliminar: false, aprobar: false, gestionar: false },
    cliente: { ver: true, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
  },
  catalogo: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    admin_tienda: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    tejedora: { ver: true, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
    cliente: { ver: true, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
  },
  productos: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    admin_tienda: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    tejedora: { ver: true, crear: true, editar: true, eliminar: false, aprobar: false, gestionar: false },
    cliente: { ver: true, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
  },
  publicacion_productos: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    admin_tienda: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    tejedora: { ver: true, crear: true, editar: true, eliminar: false, aprobar: false, gestionar: false },
    cliente: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
  },
  inventario: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    admin_tienda: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    tejedora: { ver: true, crear: false, editar: true, eliminar: false, aprobar: false, gestionar: false },
    cliente: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
  },
  pedidos: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    admin_tienda: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    tejedora: { ver: true, crear: false, editar: true, eliminar: false, aprobar: false, gestionar: false },
    cliente: { ver: true, crear: true, editar: false, eliminar: false, aprobar: false, gestionar: false },
  },
  ventas: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    admin_tienda: { ver: true, crear: false, editar: true, eliminar: false, aprobar: true, gestionar: true },
    tejedora: { ver: true, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
    cliente: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
  },
  clientes: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    admin_tienda: { ver: true, crear: true, editar: true, eliminar: false, aprobar: false, gestionar: true },
    tejedora: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
    cliente: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
  },
  tejedoras: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    admin_tienda: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    tejedora: { ver: true, crear: false, editar: true, eliminar: false, aprobar: false, gestionar: false },
    cliente: { ver: true, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
  },
  usuarios: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    admin_tienda: { ver: true, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
    tejedora: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
    cliente: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
  },
  roles_permisos: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    admin_tienda: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
    tejedora: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
    cliente: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
  },
  recursos_menu: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    admin_tienda: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
    tejedora: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
    cliente: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
  },
  reportes: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: true, aprobar: true, gestionar: true },
    admin_tienda: { ver: true, crear: true, editar: false, eliminar: false, aprobar: false, gestionar: true },
    tejedora: { ver: true, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
    cliente: { ver: false, crear: false, editar: false, eliminar: false, aprobar: false, gestionar: false },
  },
  perfil_personal: {
    superadmin: { ver: true, crear: true, editar: true, eliminar: false, aprobar: true, gestionar: true },
    admin_tienda: { ver: true, crear: true, editar: true, eliminar: false, aprobar: false, gestionar: true },
    tejedora: { ver: true, crear: true, editar: true, eliminar: false, aprobar: false, gestionar: true },
    cliente: { ver: true, crear: true, editar: true, eliminar: false, aprobar: false, gestionar: true },
  },
};

const INITIAL_AUDIT_LOGS = [
  { id: 'LOG-8902', timestamp: '2026-10-30 08:45:12', user: 'Sonia Epinayú', role: 'Superadministrador', action: 'Actualización RBAC', resource: 'Roles y permisos', details: 'Modificó permiso "Aprobar" en Recurso "Publicación de productos"' },
  { id: 'LOG-8901', timestamp: '2026-10-30 08:12:00', user: 'Carlos Pushaina', role: 'Administrador de tienda', action: 'Cambio de Estado', resource: 'Usuarios', details: 'Activó la cuenta de Marta Uriana' },
  { id: 'LOG-8900', timestamp: '2026-10-29 16:30:45', user: 'Marta Uriana', role: 'Tejedora', action: 'Creación de Producto', resource: 'Productos', details: 'Registró nuevo diseño Mochila Susu Wane' },
  { id: 'LOG-8899', timestamp: '2026-10-29 14:15:22', user: 'Sonia Epinayú', role: 'Superadministrador', action: 'Asignación de Rol', resource: 'Usuarios', details: 'Asignó rol "Administrador de tienda" a Luz Marina Jayaliyu' },
  { id: 'LOG-8898', timestamp: '2026-10-28 11:05:10', user: 'Sistema Django', role: 'Kernel RBAC', action: 'Sincronización', resource: 'Recursos y menú', details: 'Verificación de políticas de seguridad completada con éxito' },
];

const INITIAL_PRODUCTS = [
  { id: 'PROD-01', title: 'Mochila Wayúu Susu Wane', category: 'Mochilas', price: 280000, stock: 12, artisan: 'Marta Uriana', rancheria: 'Mayapo', status: 'Aprobado', image: '🎒' },
  { id: 'PROD-02', title: 'Chinchorro Elegante Anatas', category: 'Hamacas', price: 1200000, stock: 3, artisan: 'Aura Barros', rancheria: 'Cabo de la Vela', status: 'Aprobado', image: '🛋️' },
  { id: 'PROD-03', title: 'Sombrero Kumu La Guajira', category: 'Sombreros Kumu', price: 110000, stock: 25, artisan: 'Sonia Epinayú', rancheria: 'Uribia Central', status: 'Aprobado', image: '👒' },
  { id: 'PROD-04', title: 'Pulsera Kanaas Geométrica', category: 'Bisutería Kanaas', price: 35000, stock: 50, artisan: 'Rosa Pushaina', rancheria: 'Manaure', status: 'Aprobado', image: '📿' },
  { id: 'PROD-05', title: 'Mochila Mini Susu Palabrero', category: 'Mochilas', price: 190000, stock: 0, artisan: 'Marta Uriana', rancheria: 'Mayapo', status: 'Pendiente', image: '👛' },
];

const INITIAL_ORDERS = [
  { id: 'ORD-9821', customer: 'Kenia Iguarán', date: '2026-10-29', total: 390000, status: 'En tejido/Elaboración', itemsCount: 2, artisan: 'Marta Uriana', rancheria: 'Mayapo' },
  { id: 'ORD-9820', customer: 'Juan Gómez', date: '2026-10-28', total: 1200000, status: 'Enviado', itemsCount: 1, artisan: 'Aura Barros', rancheria: 'Cabo de la Vela' },
  { id: 'ORD-9819', customer: 'Artesanías del Norte Ltd', date: '2026-10-25', total: 3400000, status: 'Entregado', itemsCount: 15, artisan: 'Varias (Colectivo Uribia)', rancheria: 'Uribia' },
  { id: 'ORD-9818', customer: 'María Fernanda Ruiz', date: '2026-10-22', total: 280000, status: 'Pendiente', itemsCount: 1, artisan: 'Sonia Epinayú', rancheria: 'Uribia' },
];

type SessionUserWithIdentity = SessionUser & {
  first_name?: string | null
  last_name?: string | null
}

function resolveSessionDisplayName(user: SessionUserWithIdentity | null | undefined) {
  const firstName = (user?.first_name ?? '').trim()
  const lastName = (user?.last_name ?? '').trim()
  const fullNameFromNames = [firstName, lastName].filter(Boolean).join(' ').trim()
  if (fullNameFromNames) return fullNameFromNames

  const sessionName = (user?.name ?? '').trim()
  if (sessionName) return sessionName

  const username = (user?.username ?? '').trim()
  if (username) return username

  const profileName = ((user as SessionUserWithIdentity | null | undefined)?.profile?.name ?? '').trim()
  if (profileName) return profileName

  return 'Usuario'
}

function resolveSessionRoleLabel(role?: SessionUser['role'] | null) {
  switch (role) {
    case 'superadmin': return 'Superadministrador'
    case 'admin': return 'Administrador'
    case 'craftswoman': return 'Artesana'
    case 'customer': return 'Cliente'
    default: return 'Usuario'
  }
}

export default function App() {
  const { user, loaded, logout } = useUserSession();
  const displayName = resolveSessionDisplayName(user as SessionUserWithIdentity | null)
  const roleLabel = resolveSessionRoleLabel(user?.role ?? null)

  // Navigation & Submenu Toggle States
  const [activeTab, setActiveTab] = useState('roles_permisos');
  const [isSeguridadOpen, setIsSeguridadOpen] = useState(true);
  const [isComercialOpen, setIsComercialOpen] = useState(false);
  const [isProductosOpen, setIsProductosOpen] = useState(false);
  const [isPedidosOpen, setIsPedidosOpen] = useState(false);
  const [isConfigOpen, setIsConfigOpen] = useState(false);

  // Core Data States
  const [permissions, setPermissions] = useState<Record<string, Record<string, Record<string, boolean>>>>({});
  const [catalog, setCatalog] = useState<RBACPermission[]>([]);
  const [selectedRole, setSelectedRole] = useState<SessionUser['role']>('admin');
  const [selectedResource, setSelectedResource] = useState('');
  const [resourceSearch, setResourceSearch] = useState('');
  const [users, setUsers] = useState<SuperadminUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [usersError, setUsersError] = useState('');
  const [products, setProducts] = useState(INITIAL_PRODUCTS);
  const [orders, setOrders] = useState(INITIAL_ORDERS);
  const [auditLogs, setAuditLogs] = useState(INITIAL_AUDIT_LOGS);

  // App Interactivity & Modal States
  const [toast, setToast] = useState(null);
  const [userSearchTerm, setUserSearchTerm] = useState('');
  const [userRoleFilter, setUserRoleFilter] = useState('all');
  const [selectedUserForEdit, setSelectedUserForEdit] = useState(null);
  const [isEditUserModalOpen, setIsEditUserModalOpen] = useState(false);
  const [isCreateUserModalOpen, setIsCreateUserModalOpen] = useState(false);
  const [isCreatingUser, setIsCreatingUser] = useState(false);
  const [createUserError, setCreateUserError] = useState('');
  const [newUserDraft, setNewUserDraft] = useState({
    username: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    role: 'admin' as Exclude<SessionUser['role'], 'superadmin'>,
    phone: '',
    address: '',
    city: '',
    community: '',
    region: '',
    craftswoman_active: true,
    is_active: true,
  });
  const [selectedOrderForDetail, setSelectedOrderForDetail] = useState(null);

  const loadUsers = async (nextSearch = userSearchTerm, nextRole = userRoleFilter) => {
    const params = new URLSearchParams();
    if (nextSearch.trim()) params.set('search', nextSearch.trim());
    if (nextRole !== 'all') params.set('role', nextRole);
    setUsersLoading(true);
    setUsersError('');
    try {
      const result = await api.superadminUsers(params);
      setUsers(result);
    } catch (error) {
      setUsersError(error instanceof ApiError ? error.message : 'No fue posible consultar los usuarios en Django.');
    } finally {
      setUsersLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    const fetchUsers = async () => {
      const params = new URLSearchParams();
      if (userSearchTerm.trim()) params.set('search', userSearchTerm.trim());
      if (userRoleFilter !== 'all') params.set('role', userRoleFilter);
      setUsersLoading(true);
      setUsersError('');
      try {
        const result = await api.superadminUsers(params);
        if (active) setUsers(result);
      } catch (error) {
        if (active) setUsersError(error instanceof ApiError ? error.message : 'No fue posible consultar los usuarios en Django.');
      } finally {
        if (active) setUsersLoading(false);
      }
    };

    void fetchUsers();
    return () => { active = false; };
  }, [userSearchTerm, userRoleFilter]);

  useEffect(() => {
    let active = true;
    setUsersLoading(true);
    Promise.all([
      api.rbacCatalog(),
      ...ROLES.map((role) => api.rolePermissions(role.id as SessionUser['role'])),
    ])
      .then(([catalogResponse, ...roleResponses]) => {
        if (!active) return;
        setCatalog(catalogResponse.permissions);
        setPermissions(buildRolePermissionsMatrix(catalogResponse.permissions, roleResponses));
        setSelectedResource((current) => current || catalogResponse.permissions[0]?.resource || 'users');
      })
      .catch((error) => {
        if (!active) return;
        setUsersError(error instanceof ApiError ? error.message : 'No fue posible consultar permisos en Django.');
      })
      .finally(() => { if (active) setUsersLoading(false); });
    return () => { active = false; };
  }, []);

  // Form State: Configuración Tienda
  const [storeConfig, setStoreConfig] = useState({
    name: 'Wayúu - Artesanía Que Transforma',
    nit: '901.345.890-2',
    email: 'contacto@artesaniaswayuu.co',
    phone: '+57 310 456 7890',
    currency: 'COP ($)',
    language: 'es',
    wayuunaikiSupport: true,
    autoApproveProducts: false,
    emailNotifications: true,
    smsNotifications: true,
    gateway: 'wompi'
  });

  // Trigger Toast Notification
  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Auth Handlers
  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      showToast('No se pudo cerrar la sesión con Django.', 'info');
      return;
    }
    window.history.replaceState(null, '', '/');
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  const resources = useMemo(() => {
    if (catalog.length > 0) {
      return Array.from(new Map(catalog.map((permission) => {
        const resourceName = permission.name || permission.resource;
        return [permission.resource, { id: permission.resource, name: resourceName, description: permission.resource, icon: Layers }];
      })).values());
    }

    return RESOURCES.map((resource) => ({ ...resource }));
  }, [catalog]);

  // Filtered resources for search
  const filteredResources = useMemo(() => {
    return resources.filter((resource) =>
      resource.name.toLowerCase().includes(resourceSearch.toLowerCase()) ||
      resource.description.toLowerCase().includes(resourceSearch.toLowerCase())
    );
  }, [resourceSearch, resources]);

  const currentResourceObj = useMemo(() => {
    return resources.find((resource) => resource.id === selectedResource) || resources[0] || RESOURCES[0];
  }, [resources, selectedResource]);

  // Permission Matrix Handler
  const handlePermissionToggle = (roleId, actionId) => {
    if (roleId === 'superadmin' || selectedRole === 'superadmin') {
      showToast('La matriz global del rol superadmin es informativa y no puede modificarse.', 'info');
      return;
    }
    if (!selectedResource || !permissions[selectedResource]?.[roleId]) return;
    setPermissions((prev) => ({
      ...prev,
      [selectedResource]: {
        ...prev[selectedResource],
        [roleId]: {
          ...prev[selectedResource][roleId],
          [actionId]: !prev[selectedResource]?.[roleId]?.[actionId],
        },
      },
    }));
  };

  const handleResetPermissions = async () => {
    if (selectedRole === 'superadmin') {
      showToast('La matriz del superadmin es informativa y no puede sobrescribirse.', 'info');
      return;
    }

    try {
      const roleResponses = await Promise.all(ROLES.map((role) => api.rolePermissions(role.id as SessionUser['role'])));
      setPermissions(buildRolePermissionsMatrix(catalog, roleResponses));
      showToast('Matriz de permisos recargada desde Django.', 'info');
    } catch (error) {
      showToast(error instanceof ApiError ? error.message : 'No fue posible recargar la matriz de permisos.', 'info');
    }
  };

  const handleSavePermissions = async () => {
    if (selectedRole === 'superadmin') {
      showToast('La matriz del rol superadmin es informativa y no se guarda por API.', 'info');
      return;
    }

    const entries = Object.entries(permissions[selectedResource]?.[selectedRole] ?? {}).map(([action, allowed]) => ({
      resource: selectedResource,
      action,
      allowed,
    }));

    if (!entries.length) {
      showToast('No hay permisos reales para guardar en este recurso.', 'info');
      return;
    }

    try {
      await api.updateRolePermissions(selectedRole, entries);
      const refreshed = await Promise.all(ROLES.map((role) => api.rolePermissions(role.id as SessionUser['role'])));
      setPermissions(buildRolePermissionsMatrix(catalog, refreshed));
      showToast('Matriz de permisos guardada en Django.', 'success');
    } catch (error) {
      showToast(error instanceof ApiError ? error.message : 'No fue posible guardar la matriz de permisos.', 'info');
    }
  };

  // User Actions
  const handleToggleUserStatus = async (userId: number) => {
    const target = users.find((user) => user.id === userId);
    if (!target) return;

    try {
      const updated = await api.updateSuperadminUser(userId, { is_active: !target.is_active, active: !target.active });
      await loadUsers();
      showToast(`Estado del usuario ${updated.full_name || updated.username} actualizado.`, 'success');
    } catch (error) {
      showToast(error instanceof ApiError ? error.message : 'No fue posible cambiar el estado del usuario.', 'info');
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    const username = newUserDraft.username.trim();
    const email = newUserDraft.email.trim();
    const firstName = newUserDraft.first_name.trim();
    const lastName = newUserDraft.last_name.trim();
    const password = newUserDraft.password.trim();

    if (!username || !email || !password || !newUserDraft.role) {
      setCreateUserError('Completa usuario, correo, contraseña y rol antes de guardar.');
      return;
    }

    if (!email.includes('@')) {
      setCreateUserError('El correo electrónico no tiene un formato válido.');
      return;
    }

    const payload = {
      username,
      email,
      first_name: firstName,
      last_name: lastName,
      role: newUserDraft.role,
      password,
      is_active: newUserDraft.is_active,
      phone: newUserDraft.phone.trim(),
      address: newUserDraft.address.trim(),
      city: newUserDraft.city.trim(),
      community: newUserDraft.community.trim(),
      region: newUserDraft.region.trim(),
      craftswoman_active: newUserDraft.role === 'craftswoman' ? newUserDraft.craftswoman_active : false,
    };

    setIsCreatingUser(true);
    try {
      setCreateUserError('');
      const created = await api.createSuperadminUser(payload);
      setIsCreateUserModalOpen(false);
      setNewUserDraft({
        username: '',
        email: '',
        password: '',
        first_name: '',
        last_name: '',
        role: 'admin',
        phone: '',
        address: '',
        city: '',
        community: '',
        region: '',
        craftswoman_active: true,
        is_active: true,
      });
      await loadUsers();
      showToast(`Usuario ${created.full_name || created.username} creado correctamente.`, 'success');
    } catch (error) {
      setCreateUserError(error instanceof ApiError ? error.message : 'No fue posible crear el usuario en Django.');
    } finally {
      setIsCreatingUser(false);
    }
  };

  const handleSaveUserModal = async (e) => {
    e.preventDefault();
    if (!selectedUserForEdit) return;

    const fullName = (selectedUserForEdit.full_name || '').trim();
    const parts = fullName ? fullName.split(/\s+/) : [];
    const firstName = parts.shift() || selectedUserForEdit.first_name || '';
    const lastName = parts.join(' ') || selectedUserForEdit.last_name || '';

    try {
      const updated = await api.updateSuperadminUser(selectedUserForEdit.id, {
        username: selectedUserForEdit.username,
        email: selectedUserForEdit.email,
        first_name: firstName,
        last_name: lastName,
        role: selectedUserForEdit.role,
        is_active: selectedUserForEdit.is_active,
        active: selectedUserForEdit.active,
      });
      await loadUsers();
      setIsEditUserModalOpen(false);
      showToast(`Datos del usuario ${updated.full_name || updated.username} actualizados.`, 'success');
    } catch (error) {
      showToast(error instanceof ApiError ? error.message : 'No fue posible guardar los datos del usuario.', 'info');
    }
  };

  // Product Approval
  const handleApproveProduct = (prodId, isApproved) => {
    setProducts(prev => prev.map(p => {
      if (p.id === prodId) {
        const status = isApproved ? 'Aprobado' : 'Rechazado';
        showToast(`Producto ${p.title} marcado como ${status}.`);
        return { ...p, status };
      }
      return p;
    }));
  };

  const filteredUsers = users;

  if (!loaded) {
    return (
      <div className="min-h-screen bg-[#FDFBF7] flex items-center justify-center p-4 text-[#3D1E16]">
        <div className="rounded-2xl border border-[#E2D9D5] bg-white px-6 py-4 text-sm font-medium shadow-sm">
          Cargando sesión…
        </div>
      </div>
    );
  }

  if (!user || user.role !== 'superadmin') {
    return (
      <div className="min-h-screen bg-[#FDFBF7] flex items-center justify-center p-4 text-[#3D1E16]">
        <div className="w-full max-w-md rounded-3xl border border-[#E2D9D5] bg-white p-8 text-center shadow-xl">
          <h1 className="text-xl font-bold text-[#3D1E16]">Acceso no autorizado</h1>
          <p className="mt-3 text-sm text-stone-600">Esta vista solo está disponible para usuarios con rol superadministrador.</p>
          <button
            type="button"
            onClick={() => {
              window.history.replaceState(null, '', '/');
              window.dispatchEvent(new PopStateEvent('popstate'));
            }}
            className="mt-6 inline-flex items-center justify-center rounded-xl bg-[#5C1D24] px-4 py-2 text-xs font-bold text-white transition-colors hover:bg-[#4A121A]"
          >
            Volver al sitio público
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#FDFBF7] text-[#3D1E16] font-sans overflow-hidden selection:bg-[#5C1D24] selection:text-white">

      {/* TOAST NOTIFICATION BANNER */}
      {toast && (
        <div className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-5 py-3.5 rounded-xl shadow-2xl text-xs font-semibold transition-all duration-300 ${
          toast.type === 'info' ? 'bg-[#3D1E16] text-amber-100 border border-amber-800' : 'bg-[#5C1D24] text-white border border-[#4A121A]'
        }`}>
          {toast.type === 'info' ? <Info className="w-5 h-5 text-amber-300 shrink-0" /> : <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* SIDEBAR NAVIGATION */}
      <aside className="w-64 bg-[#5C1D24] text-white flex flex-col justify-between shrink-0 shadow-2xl relative z-20">
        <div className="flex flex-col h-full overflow-y-auto">
          
          {/* Logo Artesanal Wayúu */}
          <div className="p-6 pb-5 flex items-center gap-3.5 border-b border-rose-900/50">
            <div className="p-2.5 bg-[#FDFBF7]/10 rounded-xl border border-white/20 shadow-inner flex items-center justify-center">
              <svg className="w-7 h-7 text-[#FDFBF7]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
            </div>
            <div>
              <h1 className="font-bold text-lg tracking-wide text-[#FDFBF7] leading-tight">Wayúu</h1>
              <p className="text-[10px] text-rose-200/90 tracking-wider uppercase font-semibold">Artesanía que transforma</p>
            </div>
          </div>

          {/* Menú de Navegación Expandible */}
          <nav className="p-4 space-y-1.5 text-xs font-medium flex-1">
            
            {/* Inicio / Resumen General */}
            <button
              onClick={() => setActiveTab('overview')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg transition-colors ${
                activeTab === 'overview' ? 'bg-[#FDFBF7]/20 text-white font-bold shadow-inner' : 'text-rose-100 hover:bg-white/10'
              }`}
            >
              <Home className="w-4 h-4 text-rose-200" />
              <span>Inicio / Resumen</span>
            </button>

            {/* SEGURIDAD */}
            <div>
              <button
                onClick={() => setIsSeguridadOpen(!isSeguridadOpen)}
                className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-rose-100 hover:bg-white/10 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Shield className="w-4 h-4 text-rose-200" />
                  <span>Seguridad</span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isSeguridadOpen ? 'rotate-180' : ''}`} />
              </button>

              {isSeguridadOpen && (
                <div className="ml-4 pl-3 border-l border-rose-300/20 my-1 space-y-1">
                  <button
                    onClick={() => setActiveTab('roles_permisos')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'roles_permisos' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Roles y permisos</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('usuarios')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'usuarios' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <Users className="w-3.5 h-3.5" />
                    <span>Usuarios</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('recursos')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'recursos' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <FolderTree className="w-3.5 h-3.5" />
                    <span>Recursos y menú</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('audit_logs')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'audit_logs' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <Activity className="w-3.5 h-3.5" />
                    <span>Registro de actividad</span>
                  </button>
                </div>
              )}
            </div>

            {/* COMERCIAL */}
            <div>
              <button
                onClick={() => setIsComercialOpen(!isComercialOpen)}
                className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-rose-100 hover:bg-white/10 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <ShoppingBag className="w-4 h-4 text-rose-200" />
                  <span>Comercial</span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isComercialOpen ? 'rotate-180' : ''}`} />
              </button>

              {isComercialOpen && (
                <div className="ml-4 pl-3 border-l border-rose-300/20 my-1 space-y-1">
                  <button
                    onClick={() => setActiveTab('comercial_panel')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'comercial_panel' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <TrendingUp className="w-3.5 h-3.5" />
                    <span>Panel comercial</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('comercial_clientes')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'comercial_clientes' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <Users className="w-3.5 h-3.5" />
                    <span>Clientes</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('comercial_ventas')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'comercial_ventas' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <BarChart3 className="w-3.5 h-3.5" />
                    <span>Ventas</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('comercial_reportes')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'comercial_reportes' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Reportes comerciales</span>
                  </button>
                </div>
              )}
            </div>

            {/* PRODUCTOS */}
            <div>
              <button
                onClick={() => setIsProductosOpen(!isProductosOpen)}
                className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-rose-100 hover:bg-white/10 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Package className="w-4 h-4 text-rose-200" />
                  <span>Productos</span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isProductosOpen ? 'rotate-180' : ''}`} />
              </button>

              {isProductosOpen && (
                <div className="ml-4 pl-3 border-l border-rose-300/20 my-1 space-y-1">
                  <button
                    onClick={() => setActiveTab('productos_listado')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'productos_listado' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <Package className="w-3.5 h-3.5" />
                    <span>Listado de productos</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('productos_categorias')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'productos_categorias' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <Tag className="w-3.5 h-3.5" />
                    <span>Categorías</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('productos_aprobacion')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'productos_aprobacion' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <CheckSquare className="w-3.5 h-3.5" />
                    <span>Revisión y aprobación</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('productos_inventario')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'productos_inventario' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <Layers className="w-3.5 h-3.5" />
                    <span>Gestión de inventario</span>
                  </button>
                </div>
              )}
            </div>

            {/* PEDIDOS */}
            <div>
              <button
                onClick={() => setIsPedidosOpen(!isPedidosOpen)}
                className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-rose-100 hover:bg-white/10 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <ShoppingCart className="w-4 h-4 text-rose-200" />
                  <span>Pedidos</span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isPedidosOpen ? 'rotate-180' : ''}`} />
              </button>

              {isPedidosOpen && (
                <div className="ml-4 pl-3 border-l border-rose-300/20 my-1 space-y-1">
                  <button
                    onClick={() => setActiveTab('pedidos_listado')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'pedidos_listado' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <ShoppingCart className="w-3.5 h-3.5" />
                    <span>Listado de pedidos</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('pedidos_seguimiento')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'pedidos_seguimiento' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <Truck className="w-3.5 h-3.5" />
                    <span>Seguimiento de estados</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('pedidos_historial')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'pedidos_historial' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <Clock className="w-3.5 h-3.5" />
                    <span>Historial de pedidos</span>
                  </button>
                </div>
              )}
            </div>

            {/* CONFIGURACIÓN */}
            <div>
              <button
                onClick={() => setIsConfigOpen(!isConfigOpen)}
                className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-rose-100 hover:bg-white/10 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Settings className="w-4 h-4 text-rose-200" />
                  <span>Configuración</span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isConfigOpen ? 'rotate-180' : ''}`} />
              </button>

              {isConfigOpen && (
                <div className="ml-4 pl-3 border-l border-rose-300/20 my-1 space-y-1">
                  <button
                    onClick={() => setActiveTab('config_general')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'config_general' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    <span>Datos generales</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('config_notificaciones')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'config_notificaciones' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <Bell className="w-3.5 h-3.5" />
                    <span>Notificaciones</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('config_seguridad')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'config_seguridad' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <Lock className="w-3.5 h-3.5" />
                    <span>Seguridad Django</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('config_preferencias')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === 'config_preferencias' ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-sm' : 'text-rose-100/90 hover:bg-white/10'
                    }`}
                  >
                    <Globe className="w-3.5 h-3.5" />
                    <span>Preferencias sistema</span>
                  </button>
                </div>
              )}
            </div>

          </nav>

          {/* Cierre de Sesión en el Sidebar Footer */}
          <div className="p-4 mt-auto border-t border-rose-300/10 bg-black/10 relative overflow-hidden space-y-3">
            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-white/10 hover:bg-rose-900/60 border border-rose-300/20 rounded-xl text-xs font-semibold text-rose-100 transition-colors shadow-sm"
              title="Cerrar sesión actual"
            >
              <LogOut className="w-4 h-4 text-rose-300" />
              <span>Cerrar Sesión</span>
            </button>

            <div className="text-center">
              <p className="text-xs font-semibold text-rose-100">Tienda Wayúu</p>
              <p className="text-[11px] text-rose-300/80">v1.0 (RBAC Django Simulado)</p>
            </div>
          </div>

        </div>
      </aside>

      {/* WORKSPACE BODY */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        
        {/* TOP HEADER */}
        <header className="bg-white border-b border-[#E2D9D5] px-8 py-3.5 flex items-center justify-between shrink-0 shadow-sm z-10">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-[#5C1D24] bg-rose-50 px-2.5 py-1 rounded-md border border-rose-200">
              Panel Superadministrador
            </span>
            <span className="text-xs text-stone-300">/</span>
            <span className="text-xs font-medium text-stone-600 capitalize">
              {activeTab.replace('_', ' ')}
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Conexión Backend Django Simulado</span>
            </div>

            <button className="relative p-2 text-stone-600 hover:text-[#5C1D24] hover:bg-rose-50 rounded-full transition-colors">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-600 rounded-full ring-2 ring-white"></span>
            </button>

            <div className="flex items-center gap-3 pl-3 border-l border-stone-200">
              <div className="w-8 h-8 rounded-full bg-[#5C1D24] text-white flex items-center justify-center text-xs font-bold shadow-sm">
                SA
              </div>
              <div className="hidden sm:block text-left">
                <p className="text-xs font-bold text-stone-800 leading-tight">{displayName}</p>
                <p className="text-[11px] text-stone-500">{roleLabel}</p>
              </div>

              {/* Botón rápido de cierre de sesión en Header */}
              <button
                onClick={handleLogout}
                className="p-1.5 text-stone-400 hover:text-[#5C1D24] hover:bg-rose-50 rounded-lg transition-colors ml-1"
                title="Cerrar sesión"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </header>

        {/* MAIN SCROLLABLE VISTAS */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-[#FDFBF7]">

          {/* 1. VISTA: INICIO / RESUMEN GENERAL */}
          {activeTab === 'overview' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Resumen General del Sistema</h2>
                <p className="text-xs text-stone-600 mt-1">Visión global de usuarios, roles, métricas comerciales e inventario artesanal Wayúu.</p>
              </div>

              {/* KPIS */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-center gap-4">
                  <div className="p-3 bg-rose-50 text-[#5C1D24] rounded-xl"><Users className="w-6 h-6" /></div>
                  <div>
                    <p className="text-xs font-bold text-stone-500 uppercase">Usuarios Totales</p>
                    <p className="text-2xl font-black text-stone-800">{users.length}</p>
                    <p className="text-[11px] text-emerald-600 font-medium">100% activos en backend</p>
                  </div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-center gap-4">
                  <div className="p-3 bg-rose-50 text-[#5C1D24] rounded-xl"><ShieldCheck className="w-6 h-6" /></div>
                  <div>
                    <p className="text-xs font-bold text-stone-500 uppercase">Roles Definidos</p>
                    <p className="text-2xl font-black text-stone-800">{ROLES.length}</p>
                    <p className="text-[11px] text-stone-500">Superadmin, Admin, Tejedora, Cliente</p>
                  </div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-center gap-4">
                  <div className="p-3 bg-rose-50 text-[#5C1D24] rounded-xl"><Layers className="w-6 h-6" /></div>
                  <div>
                    <p className="text-xs font-bold text-stone-500 uppercase">Recursos RBAC</p>
                    <p className="text-2xl font-black text-stone-800">{RESOURCES.length}</p>
                    <p className="text-[11px] text-stone-500">Módulos protegidos</p>
                  </div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-center gap-4">
                  <div className="p-3 bg-rose-50 text-[#5C1D24] rounded-xl"><TrendingUp className="w-6 h-6" /></div>
                  <div>
                    <p className="text-xs font-bold text-stone-500 uppercase">Ventas del Mes</p>
                    <p className="text-2xl font-black text-stone-800">$5.270.000</p>
                    <p className="text-[11px] text-emerald-600 font-medium">+14% impacto comunitario</p>
                  </div>
                </div>
              </div>

              {/* Accesos Rápidos */}
              <div className="bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-4">
                <h3 className="font-bold text-stone-800 text-sm">Accesos Rápidos de Administración</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <button onClick={() => setActiveTab('roles_permisos')} className="p-4 rounded-xl border border-stone-200 hover:border-[#5C1D24] bg-stone-50 hover:bg-rose-50 text-left transition-colors">
                    <ShieldCheck className="w-5 h-5 text-[#5C1D24] mb-2" />
                    <p className="font-bold text-xs text-stone-800">Matriz de Permisos</p>
                    <p className="text-[11px] text-stone-500">Configurar V, C, E, X, A, G</p>
                  </button>

                  <button onClick={() => setActiveTab('productos_aprobacion')} className="p-4 rounded-xl border border-stone-200 hover:border-[#5C1D24] bg-stone-50 hover:bg-rose-50 text-left transition-colors">
                    <CheckSquare className="w-5 h-5 text-[#5C1D24] mb-2" />
                    <p className="font-bold text-xs text-stone-800">Aprobar Piezas</p>
                    <p className="text-[11px] text-stone-500">Revisar envíos artesanas</p>
                  </button>

                  <button onClick={() => setActiveTab('pedidos_listado')} className="p-4 rounded-xl border border-stone-200 hover:border-[#5C1D24] bg-stone-50 hover:bg-rose-50 text-left transition-colors">
                    <ShoppingCart className="w-5 h-5 text-[#5C1D24] mb-2" />
                    <p className="font-bold text-xs text-stone-800">Gestión Pedidos</p>
                    <p className="text-[11px] text-stone-500">Despachos y asignaciones</p>
                  </button>

                  <button onClick={() => setActiveTab('usuarios')} className="p-4 rounded-xl border border-stone-200 hover:border-[#5C1D24] bg-stone-50 hover:bg-rose-50 text-left transition-colors">
                    <Users className="w-5 h-5 text-[#5C1D24] mb-2" />
                    <p className="font-bold text-xs text-stone-800">Directorio Usuarios</p>
                    <p className="text-[11px] text-stone-500">Asignar roles e hipervínculos</p>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 2. VISTA: ROLES Y PERMISOS (MATRIZ RBAC EXACTA) */}
          {activeTab === 'roles_permisos' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Roles y permisos</h2>
                <p className="text-xs text-stone-600 mt-1">Gestiona qué vistas y acciones puede realizar cada rol en el sistema.</p>
              </div>

              {/* Role Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {ROLES.map(role => (
                  <button
                    key={role.id}
                    type="button"
                    onClick={() => setSelectedRole(role.id as SessionUser['role'])}
                    className={`w-full text-left bg-white border rounded-2xl p-4 shadow-sm transition-shadow ${
                      selectedRole === role.id ? 'border-[#5C1D24] ring-1 ring-[#5C1D24] bg-[#FDFBF7]' : 'border-[#E2D9D5] hover:shadow-md'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="p-2.5 rounded-xl bg-rose-50 text-[#5C1D24] border border-rose-100">
                        <Users className="w-5 h-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-xs font-bold text-stone-800 truncate">{role.name}</h3>
                        <p className="text-[11px] text-stone-500 mt-0.5 line-clamp-2">{role.description}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {/* Main Matrix Split */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                
                {/* Left Resources Panel */}
                <div className="lg:col-span-4 bg-white rounded-2xl border border-[#E2D9D5] shadow-sm overflow-hidden flex flex-col h-[620px]">
                  <div className="p-4 border-b border-[#E2D9D5] bg-[#FDFBF7] flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-stone-800 font-bold text-xs">
                      <Layers className="w-4 h-4 text-[#5C1D24]" />
                      <span>Recursos ({RESOURCES.length})</span>
                    </div>

                    <div className="relative flex-1 max-w-[160px]">
                      <Search className="w-3.5 h-3.5 text-stone-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        placeholder="Buscar..."
                        value={resourceSearch}
                        onChange={(e) => setResourceSearch(e.target.value)}
                        className="w-full text-xs pl-8 pr-2 py-1.5 bg-white border border-stone-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                      />
                    </div>
                  </div>

                  <div className="divide-y divide-stone-100 overflow-y-auto flex-1">
                    {filteredResources.map((res) => {
                      const IconComp = res.icon;
                      const isSelected = selectedResource === res.id;
                      return (
                        <button
                          key={res.id}
                          onClick={() => setSelectedResource(res.id)}
                          className={`w-full text-left px-4 py-3 flex items-center justify-between transition-colors ${
                            isSelected ? 'bg-[#FBEAEB] text-[#5C1D24] font-bold border-l-4 border-[#5C1D24]' : 'hover:bg-stone-50 text-stone-700'
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <IconComp className={`w-4 h-4 shrink-0 ${isSelected ? 'text-[#5C1D24]' : 'text-stone-400'}`} />
                            <span className="text-xs truncate">{res.name}</span>
                          </div>
                          <ChevronRight className={`w-4 h-4 shrink-0 ${isSelected ? 'text-[#5C1D24]' : 'text-stone-300'}`} />
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Right Matrix Action Panel */}
                <div className="lg:col-span-8 bg-white rounded-2xl border border-[#E2D9D5] shadow-sm overflow-hidden flex flex-col justify-between h-[620px]">
                  <div className="overflow-y-auto">
                    <div className="p-5 border-b border-[#E2D9D5] bg-[#FDFBF7] flex items-start gap-4">
                      <div className="p-3 bg-white border border-[#E2D9D5] rounded-xl shadow-sm text-[#5C1D24]">
                        {React.createElement(currentResourceObj.icon, { className: 'w-6 h-6' })}
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-stone-800">{currentResourceObj.name}</h3>
                        <p className="text-xs text-stone-500 mt-0.5">{currentResourceObj.description}</p>
                      </div>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse">
                        <thead>
                          <tr className="bg-stone-50 border-b border-[#E2D9D5] text-xs font-semibold text-stone-600">
                            <th className="py-3.5 px-5">Acción</th>
                            {ROLES.map(role => (
                              <th key={role.id} className="py-3.5 px-4 text-center">
                                <div className="inline-flex items-center gap-1.5">
                                  <span className={`w-2 h-2 rounded-full ${role.dotColor}`}></span>
                                  <span>{role.shortName}</span>
                                </div>
                              </th>
                            ))}
                          </tr>
                        </thead>

                        <tbody className="divide-y divide-stone-100 text-xs">
                          {ACTIONS.map((action) => {
                            const ActionIcon = action.icon;
                            return (
                              <tr key={action.id} className="hover:bg-stone-50/60 transition-colors">
                                <td className="py-4 px-5 font-medium text-stone-800">
                                  <div className="flex items-center gap-3">
                                    <ActionIcon className="w-4 h-4 text-stone-500" />
                                    <span>{action.label} ({action.code})</span>
                                  </div>
                                </td>

                                {ROLES.map((role) => {
                                  const isChecked = permissions[selectedResource]?.[role.id]?.[action.id] ?? false;
                                  return (
                                    <td key={role.id} className="py-4 px-4 text-center">
                                      <button
                                        type="button"
                                        onClick={() => handlePermissionToggle(role.id, action.id)}
                                        className={`w-6 h-6 rounded-md inline-flex items-center justify-center transition-all ${
                                          isChecked
                                            ? 'bg-[#5C1D24] text-white shadow-sm hover:bg-[#4A121A]'
                                            : 'border border-stone-300 hover:border-stone-400 bg-white'
                                        }`}
                                      >
                                        {isChecked && <Check className="w-4 h-4 stroke-[3]" />}
                                      </button>
                                    </td>
                                  );
                                })}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="border-t border-[#E2D9D5] p-4 bg-stone-50/50 space-y-3">
                    <div className="p-3 bg-[#FDFBF7] border border-stone-200 rounded-xl flex items-center gap-3 text-xs text-stone-600">
                      <Info className="w-4 h-4 text-[#5C1D24] shrink-0" />
                      <span>Los permisos pueden ser modificados en cualquier momento por el superadministrador.</span>
                    </div>

                    <div className="flex items-center justify-end gap-3">
                      <button
                        onClick={handleResetPermissions}
                        className="flex items-center gap-2 px-4 py-2 border border-stone-300 rounded-xl text-xs font-semibold text-stone-700 bg-white hover:bg-stone-100 transition-colors"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Restablecer</span>
                      </button>

                      <button
                        onClick={handleSavePermissions}
                        className="flex items-center gap-2 px-5 py-2 bg-[#5C1D24] hover:bg-[#4A121A] text-white rounded-xl text-xs font-semibold transition-colors shadow-sm"
                      >
                        <Save className="w-3.5 h-3.5" />
                        <span>Guardar cambios</span>
                      </button>
                    </div>
                  </div>

                </div>

              </div>
            </div>
          )}

          {/* 3. VISTA: GESTIÓN DE USUARIOS */}
          {activeTab === 'usuarios' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Gestión de Usuarios</h2>
                  <p className="text-xs text-stone-600 mt-1">Consultar usuarios registrados, asignar roles y cambiar estado de acceso.</p>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setCreateUserError('');
                    setNewUserDraft({
                      username: '',
                      email: '',
                      password: '',
                      first_name: '',
                      last_name: '',
                      role: 'admin',
                      phone: '',
                      address: '',
                      city: '',
                      community: '',
                      region: '',
                      craftswoman_active: true,
                      is_active: true,
                    });
                    setIsCreateUserModalOpen(true);
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-[#5C1D24] text-white text-xs font-bold rounded-xl shadow-sm hover:bg-[#4A121A] transition-colors"
                >
                  <UserPlus className="w-4 h-4" />
                  <span>Nuevo Usuario</span>
                </button>
              </div>

              {/* Filtros */}
              <div className="bg-white p-4 rounded-2xl border border-[#E2D9D5] shadow-sm flex flex-col sm:flex-row gap-4 items-center justify-between">
                <div className="relative w-full sm:w-80">
                  <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Buscar por nombre, username, email o ubicación..."
                    value={userSearchTerm}
                    onChange={(e) => setUserSearchTerm(e.target.value)}
                    className="w-full text-xs pl-9 pr-3 py-2 bg-[#FDFBF7] border border-stone-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  />
                </div>

                <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
                  <Filter className="w-4 h-4 text-stone-400" />
                  <span className="text-xs text-stone-600 font-medium">Filtrar por rol:</span>
                  <select
                    value={userRoleFilter}
                    onChange={(e) => setUserRoleFilter(e.target.value)}
                    className="text-xs bg-white border border-stone-300 rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  >
                    <option value="all">Todos los roles</option>
                    {ROLES.map(r => (
                      <option key={r.id} value={r.id}>{r.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              {usersError && <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs font-semibold text-red-700" role="alert">{usersError}</p>}

              {/* Tabla de usuarios */}
              <div className="bg-white rounded-2xl border border-[#E2D9D5] shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-stone-50 border-b border-[#E2D9D5] text-xs font-semibold text-stone-600">
                        <th className="py-3.5 px-6">Nombre / cuenta</th>
                        <th className="py-3.5 px-4">Rol Asignado</th>
                        <th className="py-3.5 px-4">Ubicación / Ranchería</th>
                        <th className="py-3.5 px-4">Estado</th>
                        <th className="py-3.5 px-6 text-right">Acciones</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-100 text-xs">
                      {usersLoading && <tr><td className="py-6 px-6 text-stone-500" colSpan={5}>Consultando usuarios en Django...</td></tr>}
                      {!usersLoading && !usersError && filteredUsers.length === 0 && <tr><td className="py-6 px-6 text-stone-500" colSpan={5}>No hay usuarios para este filtro.</td></tr>}
                      {filteredUsers.map((u) => {
                        const roleObj = ROLES.find(r => r.id === u.role);
                        return (
                          <tr key={u.id} className="hover:bg-stone-50/60 transition-colors">
                            <td className="py-4 px-6">
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-[#5C1D24]/10 text-[#5C1D24] flex items-center justify-center font-bold text-xs uppercase">
                                  {u.full_name.substring(0, 2)}
                                </div>
                                <div>
                                  <p className="font-bold text-stone-800">{u.full_name}</p>
                                  <p className="text-stone-500 text-[11px]">{u.username} · {u.email || 'Sin correo'}</p>
                                </div>
                              </div>
                            </td>

                            <td className="py-4 px-4">
                              <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold border ${roleObj?.badgeColor ?? 'bg-stone-100 text-stone-700 border-stone-200'}`}>
                                {u.role_name}
                              </span>
                            </td>

                            <td className="py-4 px-4 text-stone-600 font-medium">{u.location || '—'}</td>

                            <td className="py-4 px-4">
                              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium ${
                                u.active ? 'bg-emerald-100 text-emerald-800' : 'bg-stone-100 text-stone-600'
                              }`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${u.active ? 'bg-emerald-600' : 'bg-stone-400'}`}></span>
                                {u.active ? 'Activo' : 'Inactivo'}
                              </span>
                            </td>

                            <td className="py-4 px-6 text-right">
                              <div className="flex items-center justify-end gap-2">
                                <button
                                  type="button"
                                  onClick={() => void handleToggleUserStatus(u.id)}
                                  title={u.is_active ? 'Desactivar usuario' : 'Activar usuario'}
                                  className="p-1.5 rounded-lg border border-stone-200 text-stone-600 hover:bg-stone-100 transition-colors"
                                >
                                  {u.is_active ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                                </button>

                                <button
                                  type="button"
                                  onClick={() => {
                                    setSelectedUserForEdit(u);
                                    setIsEditUserModalOpen(true);
                                  }}
                                  title="Editar usuario"
                                  className="p-1.5 text-stone-600 border border-stone-200 rounded-lg hover:bg-stone-100 transition-colors"
                                >
                                  <Edit className="w-4 h-4" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {isCreateUserModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#3D1E16]/45 p-4">
                  <div className="w-full max-w-2xl rounded-3xl border border-[#E2D9D5] bg-white p-6 shadow-2xl">
                    <div className="flex items-center justify-between gap-4 pb-4 border-b border-[#E2D9D5]">
                      <div>
                        <h3 className="text-base font-black text-[#3D1E16]">Crear usuario</h3>
                        <p className="text-[11px] text-stone-500 mt-1">Registra una cuenta real en Django para el rol seleccionado.</p>
                      </div>
                      <button type="button" onClick={() => { setIsCreateUserModalOpen(false); setCreateUserError(''); }} className="p-2 rounded-lg border border-stone-200 text-stone-500 hover:bg-stone-100">
                        <X className="w-4 h-4" />
                      </button>
                    </div>

                    <form onSubmit={handleCreateUser} className="mt-5 space-y-4">
                      {createUserError && (
                        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs font-semibold text-red-700" role="alert">{createUserError}</div>
                      )}

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <label className="space-y-1.5 text-[11px] font-semibold text-stone-700">
                          <span>Usuario</span>
                          <input
                            type="text"
                            value={newUserDraft.username}
                            onChange={(e) => setNewUserDraft((current) => ({ ...current, username: e.target.value }))}
                            className="w-full rounded-xl border border-stone-300 bg-[#FDFBF7] px-3 py-2 text-xs text-stone-800 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                            placeholder="ej. kenia.wayuu"
                            required
                          />
                        </label>

                        <label className="space-y-1.5 text-[11px] font-semibold text-stone-700">
                          <span>Correo electrónico</span>
                          <input
                            type="email"
                            value={newUserDraft.email}
                            onChange={(e) => setNewUserDraft((current) => ({ ...current, email: e.target.value }))}
                            className="w-full rounded-xl border border-stone-300 bg-[#FDFBF7] px-3 py-2 text-xs text-stone-800 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                            placeholder="usuario@wayuuwaa.co"
                            required
                          />
                        </label>

                        <label className="space-y-1.5 text-[11px] font-semibold text-stone-700">
                          <span>Nombre</span>
                          <input
                            type="text"
                            value={newUserDraft.first_name}
                            onChange={(e) => setNewUserDraft((current) => ({ ...current, first_name: e.target.value }))}
                            className="w-full rounded-xl border border-stone-300 bg-[#FDFBF7] px-3 py-2 text-xs text-stone-800 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                            placeholder="Nombre"
                          />
                        </label>

                        <label className="space-y-1.5 text-[11px] font-semibold text-stone-700">
                          <span>Apellido</span>
                          <input
                            type="text"
                            value={newUserDraft.last_name}
                            onChange={(e) => setNewUserDraft((current) => ({ ...current, last_name: e.target.value }))}
                            className="w-full rounded-xl border border-stone-300 bg-[#FDFBF7] px-3 py-2 text-xs text-stone-800 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                            placeholder="Apellido"
                          />
                        </label>

                        <label className="space-y-1.5 text-[11px] font-semibold text-stone-700">
                          <span>Contraseña</span>
                          <input
                            type="password"
                            value={newUserDraft.password}
                            onChange={(e) => setNewUserDraft((current) => ({ ...current, password: e.target.value }))}
                            className="w-full rounded-xl border border-stone-300 bg-[#FDFBF7] px-3 py-2 text-xs text-stone-800 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                            placeholder="********"
                            required
                          />
                        </label>

                        <label className="space-y-1.5 text-[11px] font-semibold text-stone-700">
                          <span>Rol</span>
                          <select
                            value={newUserDraft.role}
                            onChange={(e) => setNewUserDraft((current) => ({ ...current, role: e.target.value as Exclude<SessionUser['role'], 'superadmin'> }))}
                            className="w-full rounded-xl border border-stone-300 bg-[#FDFBF7] px-3 py-2 text-xs text-stone-800 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                          >
                            <option value="admin">Administrador</option>
                            <option value="craftswoman">Artesana</option>
                            <option value="customer">Cliente</option>
                          </select>
                        </label>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <label className="space-y-1.5 text-[11px] font-semibold text-stone-700">
                          <span>Teléfono</span>
                          <input
                            type="text"
                            value={newUserDraft.phone}
                            onChange={(e) => setNewUserDraft((current) => ({ ...current, phone: e.target.value }))}
                            className="w-full rounded-xl border border-stone-300 bg-[#FDFBF7] px-3 py-2 text-xs text-stone-800 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                            placeholder="300 123 4567"
                          />
                        </label>

                        <label className="space-y-1.5 text-[11px] font-semibold text-stone-700">
                          <span>Ciudad</span>
                          <input
                            type="text"
                            value={newUserDraft.city}
                            onChange={(e) => setNewUserDraft((current) => ({ ...current, city: e.target.value }))}
                            className="w-full rounded-xl border border-stone-300 bg-[#FDFBF7] px-3 py-2 text-xs text-stone-800 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                            placeholder="Riohacha"
                          />
                        </label>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <label className="space-y-1.5 text-[11px] font-semibold text-stone-700">
                          <span>Dirección</span>
                          <input
                            type="text"
                            value={newUserDraft.address}
                            onChange={(e) => setNewUserDraft((current) => ({ ...current, address: e.target.value }))}
                            className="w-full rounded-xl border border-stone-300 bg-[#FDFBF7] px-3 py-2 text-xs text-stone-800 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                            placeholder="Calle o barrio"
                          />
                        </label>

                        {newUserDraft.role === 'craftswoman' ? (
                          <label className="space-y-1.5 text-[11px] font-semibold text-stone-700">
                            <span>Región</span>
                            <input
                              type="text"
                              value={newUserDraft.region}
                              onChange={(e) => setNewUserDraft((current) => ({ ...current, region: e.target.value }))}
                              className="w-full rounded-xl border border-stone-300 bg-[#FDFBF7] px-3 py-2 text-xs text-stone-800 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                              placeholder="Guajira"
                            />
                          </label>
                        ) : (
                          <label className="space-y-1.5 text-[11px] font-semibold text-stone-700">
                            <span>Región</span>
                            <input
                              type="text"
                              value={newUserDraft.region}
                              onChange={(e) => setNewUserDraft((current) => ({ ...current, region: e.target.value }))}
                              className="w-full rounded-xl border border-stone-300 bg-[#FDFBF7] px-3 py-2 text-xs text-stone-800 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                              placeholder="Región"
                            />
                          </label>
                        )}
                      </div>

                      {newUserDraft.role === 'craftswoman' && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <label className="space-y-1.5 text-[11px] font-semibold text-stone-700">
                            <span>Comunidad</span>
                            <input
                              type="text"
                              value={newUserDraft.community}
                              onChange={(e) => setNewUserDraft((current) => ({ ...current, community: e.target.value }))}
                              className="w-full rounded-xl border border-stone-300 bg-[#FDFBF7] px-3 py-2 text-xs text-stone-800 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                              placeholder="Comunidad de la tejedora"
                            />
                          </label>

                          <label className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-stone-50 px-3 py-2 text-[11px] font-medium text-stone-700 self-end">
                            <input
                              type="checkbox"
                              checked={newUserDraft.craftswoman_active}
                              onChange={(e) => setNewUserDraft((current) => ({ ...current, craftswoman_active: e.target.checked }))}
                              className="h-4 w-4 rounded border-stone-300 text-[#5C1D24] focus:ring-[#5C1D24]"
                            />
                            Artesana activa
                          </label>
                        </div>
                      )}

                      <div className="flex items-center justify-end gap-3 border-t border-[#E2D9D5] pt-4">
                        <button type="button" onClick={() => { setIsCreateUserModalOpen(false); setCreateUserError(''); }} className="px-4 py-2 rounded-xl border border-stone-300 bg-white text-xs font-semibold text-stone-700 hover:bg-stone-100">
                          Cancelar
                        </button>
                        <button
                          type="submit"
                          disabled={isCreatingUser}
                          className={`px-5 py-2 rounded-xl text-xs font-bold text-white transition-colors ${isCreatingUser ? 'bg-[#7D4B4F] cursor-not-allowed' : 'bg-[#5C1D24] hover:bg-[#4A121A]'}`}
                        >
                          {isCreatingUser ? 'Guardando...' : 'Guardar usuario'}
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 4. VISTA: RECURSOS Y MENÚ */}
          {activeTab === 'recursos' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Directorio de Recursos del Sistema</h2>
                <p className="text-xs text-stone-600 mt-1">Los 14 recursos definidos para la tienda artesanal Wayúu.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {RESOURCES.map((res) => {
                  const ResIcon = res.icon;
                  return (
                    <div key={res.id} className="bg-white rounded-2xl border border-[#E2D9D5] p-5 shadow-sm hover:shadow-md transition-shadow">
                      <div className="flex items-start gap-4">
                        <div className="p-3 bg-rose-50 text-[#5C1D24] rounded-xl border border-rose-100 shrink-0">
                          <ResIcon className="w-6 h-6" />
                        </div>
                        <div className="space-y-1">
                          <h3 className="font-bold text-stone-800 text-xs">{res.name}</h3>
                          <p className="text-[11px] text-stone-500 leading-relaxed">{res.description}</p>
                          <p className="text-[10px] font-mono text-[#5C1D24] bg-rose-50 px-2 py-0.5 rounded border border-rose-100 inline-block mt-2">
                            {res.slug}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 5. VISTA: REGISTRO DE ACTIVIDAD Y AUDITORÍA */}
          {activeTab === 'audit_logs' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Registro de Actividad y Auditoría</h2>
                <p className="text-xs text-stone-600 mt-1">Historial de accesos, modificaciones de permisos y operaciones en tiempo real.</p>
              </div>

              <div className="bg-white rounded-2xl border border-[#E2D9D5] shadow-sm overflow-hidden">
                <div className="p-4 border-b border-[#E2D9D5] bg-stone-50 flex items-center justify-between text-xs text-stone-600 font-semibold">
                  <span>Auditoría de Sesiones y Permisos</span>
                  <span>{auditLogs.length} eventos</span>
                </div>

                <div className="divide-y divide-stone-100 text-xs">
                  {auditLogs.map((log) => (
                    <div key={log.id} className="p-4 hover:bg-stone-50/80 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-rose-50 text-[#5C1D24] rounded-lg mt-0.5 shrink-0">
                          <Clock className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-stone-800">{log.user}</span>
                            <span className="text-stone-400">•</span>
                            <span className="text-stone-600 font-medium">{log.role}</span>
                            <span className="bg-stone-100 text-stone-700 px-2 py-0.5 rounded text-[10px] font-mono font-semibold">{log.action}</span>
                          </div>
                          <p className="text-stone-600 mt-1">{log.details}</p>
                        </div>
                      </div>

                      <div className="text-right shrink-0 md:pl-4">
                        <p className="font-mono text-[11px] text-stone-500">{log.timestamp}</p>
                        <p className="text-[10px] text-rose-800 font-semibold mt-0.5">{log.resource}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 6. VISTA: PANEL COMERCIAL */}
          {activeTab === 'comercial_panel' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Panel Comercial</h2>
                <p className="text-xs text-stone-600 mt-1">Métricas de ingresos, ventas por ranchería e impacto socioeconómico.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm">
                  <p className="text-xs font-bold text-stone-500 uppercase">Ingresos Totales (Mes)</p>
                  <p className="text-2xl font-black text-[#5C1D24] mt-1">$18.450.000 COP</p>
                  <p className="text-[11px] text-emerald-600 font-medium mt-1">↑ +18% vs mes anterior</p>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm">
                  <p className="text-xs font-bold text-stone-500 uppercase">Ventas por Comercio Justo</p>
                  <p className="text-2xl font-black text-stone-800 mt-1">82.4%</p>
                  <p className="text-[11px] text-stone-500 mt-1">Retorno directo a tejedoras</p>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm">
                  <p className="text-xs font-bold text-stone-500 uppercase">Ticket Promedio</p>
                  <p className="text-2xl font-black text-stone-800 mt-1">$320.000 COP</p>
                  <p className="text-[11px] text-stone-500 mt-1">Mochilas y Chinchorros</p>
                </div>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm">
                <h3 className="font-bold text-xs text-stone-800 uppercase mb-4">Métricas por Comunidad Artesanal (Ranchería)</h3>
                <div className="space-y-3 text-xs">
                  <div>
                    <div className="flex justify-between font-semibold mb-1">
                      <span>Uribia Central</span>
                      <span>$7.800.000 COP (42%)</span>
                    </div>
                    <div className="w-full bg-stone-100 h-2 rounded-full overflow-hidden">
                      <div className="bg-[#5C1D24] h-full w-[42%]"></div>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between font-semibold mb-1">
                      <span>Manaure</span>
                      <span>$5.200.000 COP (28%)</span>
                    </div>
                    <div className="w-full bg-stone-100 h-2 rounded-full overflow-hidden">
                      <div className="bg-rose-700 h-full w-[28%]"></div>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between font-semibold mb-1">
                      <span>Mayapo</span>
                      <span>$3.650.000 COP (20%)</span>
                    </div>
                    <div className="w-full bg-stone-100 h-2 rounded-full overflow-hidden">
                      <div className="bg-amber-600 h-full w-[20%]"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 7. VISTA: CLIENTES */}
          {activeTab === 'comercial_clientes' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Directorio de Clientes</h2>
                <p className="text-xs text-stone-600 mt-1">Clientes mayoristas, detallistas y su nivel de fidelización.</p>
              </div>

              <div className="bg-white rounded-2xl border border-[#E2D9D5] shadow-sm overflow-hidden">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-stone-50 border-b border-[#E2D9D5] font-semibold text-stone-600">
                      <th className="py-3.5 px-6">Cliente</th>
                      <th className="py-3.5 px-4">Tipo</th>
                      <th className="py-3.5 px-4">Compras Realizadas</th>
                      <th className="py-3.5 px-4">Puntos Wayúu</th>
                      <th className="py-3.5 px-6 text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    <tr className="hover:bg-stone-50">
                      <td className="py-4 px-6 font-bold text-stone-800">Kenia Iguarán <br/><span className="font-normal text-stone-500">kenia.i@gmail.com</span></td>
                      <td className="py-4 px-4"><span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full font-semibold">Detallista</span></td>
                      <td className="py-4 px-4 font-semibold text-stone-700">3 pedidos ($670.000 COP)</td>
                      <td className="py-4 px-4 text-emerald-700 font-bold">120 pts</td>
                      <td className="py-4 px-6 text-right">
                        <button onClick={() => showToast('Detalles de cliente cargados.', 'info')} className="text-[#5C1D24] font-bold hover:underline">Ver ficha</button>
                      </td>
                    </tr>

                    <tr className="hover:bg-stone-50">
                      <td className="py-4 px-6 font-bold text-stone-800">Artesanías del Norte Ltd <br/><span className="font-normal text-stone-500">compras@artesaniasnorte.com</span></td>
                      <td className="py-4 px-4"><span className="bg-rose-100 text-rose-800 px-2 py-0.5 rounded-full font-semibold">Mayorista</span></td>
                      <td className="py-4 px-4 font-semibold text-stone-700">12 pedidos ($14.200.000 COP)</td>
                      <td className="py-4 px-4 text-emerald-700 font-bold">1.450 pts</td>
                      <td className="py-4 px-6 text-right">
                        <button onClick={() => showToast('Detalles de cliente cargados.', 'info')} className="text-[#5C1D24] font-bold hover:underline">Ver ficha</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 8. VISTA: VENTAS */}
          {activeTab === 'comercial_ventas' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Historial de Ventas</h2>
                <p className="text-xs text-stone-600 mt-1">Registro de transacciones comerciales y comprobantes de pago.</p>
              </div>

              <div className="bg-white rounded-2xl border border-[#E2D9D5] shadow-sm overflow-hidden text-xs">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-stone-50 border-b border-[#E2D9D5] font-semibold text-stone-600">
                      <th className="py-3.5 px-6">ID Venta</th>
                      <th className="py-3.5 px-4">Fecha</th>
                      <th className="py-3.5 px-4">Método de Pago</th>
                      <th className="py-3.5 px-4">Monto</th>
                      <th className="py-3.5 px-6 text-right">Comprobante</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    <tr className="hover:bg-stone-50">
                      <td className="py-4 px-6 font-bold text-stone-800">VTA-4091</td>
                      <td className="py-4 px-4 text-stone-600">2026-10-30</td>
                      <td className="py-4 px-4 font-semibold text-stone-700">Wompi (Tarjeta Crédito)</td>
                      <td className="py-4 px-4 font-bold text-emerald-700">$280.000 COP</td>
                      <td className="py-4 px-6 text-right">
                        <button onClick={() => showToast('Descargando comprobante PDF...', 'info')} className="p-1.5 bg-rose-50 text-[#5C1D24] rounded-lg border border-rose-200">
                          <Download className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>

                    <tr className="hover:bg-stone-50">
                      <td className="py-4 px-6 font-bold text-stone-800">VTA-4090</td>
                      <td className="py-4 px-4 text-stone-600">2026-10-29</td>
                      <td className="py-4 px-4 font-semibold text-stone-700">Transferencia Bancaria</td>
                      <td className="py-4 px-4 font-bold text-emerald-700">$1.200.000 COP</td>
                      <td className="py-4 px-6 text-right">
                        <button onClick={() => showToast('Descargando comprobante PDF...', 'info')} className="p-1.5 bg-rose-50 text-[#5C1D24] rounded-lg border border-rose-200">
                          <Download className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 9. VISTA: REPORTES COMERCIALES */}
          {activeTab === 'comercial_reportes' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Reportes Comerciales</h2>
                <p className="text-xs text-stone-600 mt-1">Generador de informes de rentabilidad y exportación simulada.</p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-4">
                <h3 className="font-bold text-xs text-stone-800 uppercase">Exportar Reportes Consolidados</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 border border-stone-200 rounded-xl bg-stone-50 flex items-center justify-between">
                    <div>
                      <p className="font-bold text-xs text-stone-800">Reporte de Ventas por Categoría (Excel)</p>
                      <p className="text-[11px] text-stone-500">Mochilas, Hamacas, Sombreros, Bisutería</p>
                    </div>
                    <button onClick={() => showToast('Generando reporte Excel simulado...')} className="px-3 py-1.5 bg-[#5C1D24] text-white rounded-lg text-xs font-semibold">
                      Exportar .XLSX
                    </button>
                  </div>

                  <div className="p-4 border border-stone-200 rounded-xl bg-stone-50 flex items-center justify-between">
                    <div>
                      <p className="font-bold text-xs text-stone-800">Impacto y Comercio Justo Wayúu (PDF)</p>
                      <p className="text-[11px] text-stone-500">Distribución de pago directo a artesanas</p>
                    </div>
                    <button onClick={() => showToast('Generando informe PDF simulado...')} className="px-3 py-1.5 bg-[#5C1D24] text-white rounded-lg text-xs font-semibold">
                      Exportar .PDF
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 10. VISTA: LISTADO DE PRODUCTOS */}
          {activeTab === 'productos_listado' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Listado de Productos Artesanales</h2>
                  <p className="text-xs text-stone-600 mt-1">Catálogo general de piezas Wayúu y control de stock.</p>
                </div>
                <button onClick={() => showToast('Modal para agregar producto.', 'info')} className="px-4 py-2 bg-[#5C1D24] text-white rounded-xl text-xs font-bold">
                  + Registrar Producto
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {products.map(p => (
                  <div key={p.id} className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex flex-col justify-between space-y-3">
                    <div className="flex items-start gap-3">
                      <span className="text-3xl p-2 bg-rose-50 rounded-xl">{p.image}</span>
                      <div>
                        <span className="text-[10px] font-bold text-[#5C1D24] bg-rose-50 px-2 py-0.5 rounded uppercase">{p.category}</span>
                        <h3 className="font-bold text-xs text-stone-800 mt-1">{p.title}</h3>
                        <p className="text-[11px] text-stone-500">Tejida por: <span className="font-medium text-stone-700">{p.artisan}</span> ({p.rancheria})</p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-stone-100 text-xs">
                      <p className="font-black text-[#5C1D24]">${p.price.toLocaleString()} COP</p>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${p.stock > 0 ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
                        {p.stock > 0 ? `${p.stock} dispon.` : 'Agotado'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 11. VISTA: CATEGORÍAS DE PRODUCTOS */}
          {activeTab === 'productos_categorias' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Categorías Artesanales</h2>
                <p className="text-xs text-stone-600 mt-1">Tipologías de tejido Wayúu (Kanaas, Susu, Kumu).</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-2">
                  <h3 className="font-bold text-xs text-stone-800">🎒 Mochilas (Susu)</h3>
                  <p className="text-xs text-stone-500">Mochilas tradicionales tejidas a una hebra y dos hebras con gasa paleteada.</p>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-2">
                  <h3 className="font-bold text-xs text-stone-800">🛋️ Hamacas & Chinchorros</h3>
                  <p className="text-xs text-stone-500">Chinchorros de cabecera y entramado grueso con flecos elaborados a mano.</p>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-2">
                  <h3 className="font-bold text-xs text-stone-800">👒 Sombreros Kumu</h3>
                  <p className="text-xs text-stone-500">Sombreros de paja mawisa teñidos con pigmentos naturales.</p>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-2">
                  <h3 className="font-bold text-xs text-stone-800">📿 Bisutería Kanaas</h3>
                  <p className="text-xs text-stone-500">Accesorios con simbología geométrica representativa de los clanes.</p>
                </div>
              </div>
            </div>
          )}

          {/* 12. VISTA: REVISIÓN Y APROBACIÓN DE PRODUCTOS */}
          {activeTab === 'productos_aprobacion' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Revisión y Aprobación de Artesanías</h2>
                <p className="text-xs text-stone-600 mt-1">Control de calidad y validación técnica antes de publicación en la tienda.</p>
              </div>

              <div className="bg-white rounded-2xl border border-[#E2D9D5] shadow-sm overflow-hidden text-xs">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-stone-50 border-b border-[#E2D9D5] font-semibold text-stone-600">
                      <th className="py-3.5 px-6">Producto</th>
                      <th className="py-3.5 px-4">Tejedora</th>
                      <th className="py-3.5 px-4">Estado Calidad</th>
                      <th className="py-3.5 px-6 text-right">Aprobar / Rechazar</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    {products.map(p => (
                      <tr key={p.id} className="hover:bg-stone-50">
                        <td className="py-4 px-6 font-bold text-stone-800">{p.title}</td>
                        <td className="py-4 px-4 text-stone-600">{p.artisan} ({p.rancheria})</td>
                        <td className="py-4 px-4">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            p.status === 'Aprobado' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                          }`}>
                            {p.status}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleApproveProduct(p.id, true)}
                              className="px-3 py-1 bg-emerald-700 text-white rounded-lg font-semibold hover:bg-emerald-800"
                            >
                              Aprobar
                            </button>
                            <button
                              onClick={() => handleApproveProduct(p.id, false)}
                              className="px-3 py-1 bg-rose-700 text-white rounded-lg font-semibold hover:bg-rose-800"
                            >
                              Rechazar
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 13. VISTA: GESTIÓN DEL INVENTARIO */}
          {activeTab === 'productos_inventario' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Gestión del Inventario por Taller</h2>
                <p className="text-xs text-stone-600 mt-1">Disponibilidad de hilo acrílico e inventario listo por ranchería.</p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-4">
                <h3 className="font-bold text-xs text-stone-800 uppercase">Alertas de Bajo Stock</h3>
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-center justify-between text-xs text-amber-900">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                    <span><strong>Mochila Mini Susu Palabrero</strong> sin stock disponible en el taller Mayapo.</span>
                  </div>
                  <button onClick={() => showToast('Orden de hilo de reabastecimiento enviada.', 'info')} className="px-3 py-1 bg-amber-800 text-white rounded-lg font-semibold">
                    Enviar Hilo
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 14. VISTA: LISTADO DE PEDIDOS */}
          {activeTab === 'pedidos_listado' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Listado de Pedidos</h2>
                <p className="text-xs text-stone-600 mt-1">Órdenes artesanales en proceso de elaboración y envío.</p>
              </div>

              <div className="bg-white rounded-2xl border border-[#E2D9D5] shadow-sm overflow-hidden text-xs">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-stone-50 border-b border-[#E2D9D5] font-semibold text-stone-600">
                      <th className="py-3.5 px-6">ID Pedido</th>
                      <th className="py-3.5 px-4">Cliente</th>
                      <th className="py-3.5 px-4">Tejedora Asignada</th>
                      <th className="py-3.5 px-4">Estado</th>
                      <th className="py-3.5 px-4">Total</th>
                      <th className="py-3.5 px-6 text-right">Detalle</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    {orders.map(o => (
                      <tr key={o.id} className="hover:bg-stone-50">
                        <td className="py-4 px-6 font-bold text-stone-800">{o.id}</td>
                        <td className="py-4 px-4 text-stone-700">{o.customer}</td>
                        <td className="py-4 px-4 text-stone-600">{o.artisan}</td>
                        <td className="py-4 px-4">
                          <span className="px-2.5 py-1 bg-rose-50 text-[#5C1D24] border border-rose-200 rounded-full font-semibold">
                            {o.status}
                          </span>
                        </td>
                        <td className="py-4 px-4 font-bold text-stone-800">${o.total.toLocaleString()} COP</td>
                        <td className="py-4 px-6 text-right">
                          <button onClick={() => { setSelectedOrderForDetail(o); setActiveTab('pedidos_seguimiento'); }} className="text-[#5C1D24] font-bold hover:underline">
                            Seguimiento
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 15. VISTA: SEGUIMIENTO DE ESTADOS DE PEDIDO */}
          {activeTab === 'pedidos_seguimiento' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Seguimiento de Flujo de Elaboración</h2>
                <p className="text-xs text-stone-600 mt-1">Timeline artesanal desde asignación de hilos hasta entrega final.</p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-6">
                <div className="flex items-center justify-between border-b border-stone-200 pb-4">
                  <div>
                    <p className="font-bold text-sm text-stone-800">Pedido seleccionado: {selectedOrderForDetail ? selectedOrderForDetail.id : 'ORD-9821'}</p>
                    <p className="text-xs text-stone-500">Cliente: {selectedOrderForDetail ? selectedOrderForDetail.customer : 'Kenia Iguarán'}</p>
                  </div>
                  <span className="px-3 py-1 bg-emerald-100 text-emerald-800 rounded-full text-xs font-bold">En Tejido Activo</span>
                </div>

                {/* Timeline Component */}
                <div className="relative pl-6 border-l-2 border-[#5C1D24] space-y-6 text-xs">
                  <div className="relative">
                    <span className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-[#5C1D24] border-2 border-white"></span>
                    <p className="font-bold text-stone-800">1. Asignación de Hilo y Diseño</p>
                    <p className="text-stone-500">Completado por tejedora Marta Uriana en Mayapo.</p>
                  </div>

                  <div className="relative">
                    <span className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-[#5C1D24] border-2 border-white animate-pulse"></span>
                    <p className="font-bold text-[#5C1D24]">2. Tejido del Cuerpo y Gasa (En proceso)</p>
                    <p className="text-stone-500">Avance estimado: 65% completado.</p>
                  </div>

                  <div className="relative">
                    <span className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-stone-300 border-2 border-white"></span>
                    <p className="font-bold text-stone-400">3. Control de Calidad Artesanal & Empaque</p>
                    <p className="text-stone-400">Pendiente de tejido.</p>
                  </div>

                  <div className="relative">
                    <span className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-stone-300 border-2 border-white"></span>
                    <p className="font-bold text-stone-400">4. Despacho e Integración con Transporte Nacional</p>
                    <p className="text-stone-400">Guía nacional pendiente.</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 16. VISTA: HISTORIAL DE PEDIDOS */}
          {activeTab === 'pedidos_historial' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Historial Completo de Pedidos</h2>
                <p className="text-xs text-stone-600 mt-1">Registro de pedidos históricos procesados en el backend.</p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm text-xs">
                <p className="text-stone-600 mb-4">Mostrando histórico de los últimos 12 meses. Todas las transacciones han sido liquidadas directamente a las artesanas.</p>
                <button onClick={() => showToast('Exportando historial completo en CSV...')} className="px-4 py-2 bg-[#5C1D24] text-white font-semibold rounded-xl">
                  Exportar Histórico
                </button>
              </div>
            </div>
          )}

          {/* 17. VISTA: CONFIGURACIÓN - DATOS GENERALES */}
          {activeTab === 'config_general' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Datos Generales de la Tienda</h2>
                <p className="text-xs text-stone-600 mt-1">Información corporativa e identidad de la tienda artesanal.</p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-4 max-w-2xl text-xs">
                <div>
                  <label className="block font-bold text-stone-700 mb-1">Nombre de la Plataforma</label>
                  <input
                    type="text"
                    value={storeConfig.name}
                    onChange={(e) => setStoreConfig({ ...storeConfig, name: e.target.value })}
                    className="w-full p-2.5 bg-stone-50 border border-stone-300 rounded-xl"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block font-bold text-stone-700 mb-1">NIT / Identificación</label>
                    <input
                      type="text"
                      value={storeConfig.nit}
                      onChange={(e) => setStoreConfig({ ...storeConfig, nit: e.target.value })}
                      className="w-full p-2.5 bg-stone-50 border border-stone-300 rounded-xl"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-stone-700 mb-1">Moneda Principal</label>
                    <input
                      type="text"
                      value={storeConfig.currency}
                      onChange={(e) => setStoreConfig({ ...storeConfig, currency: e.target.value })}
                      className="w-full p-2.5 bg-stone-50 border border-stone-300 rounded-xl"
                    />
                  </div>
                </div>

                <button onClick={() => showToast('Datos generales actualizados.')} className="px-5 py-2.5 bg-[#5C1D24] text-white font-bold rounded-xl">
                  Guardar Datos
                </button>
              </div>
            </div>
          )}

          {/* 18. VISTA: CONFIGURACIÓN - NOTIFICACIONES */}
          {activeTab === 'config_notificaciones' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Configuración de Notificaciones</h2>
                <p className="text-xs text-stone-600 mt-1">Canales de mensajería SMS y correo para artesanas y clientes.</p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-4 max-w-xl text-xs">
                <div className="flex items-center justify-between p-3 bg-stone-50 rounded-xl">
                  <div>
                    <p className="font-bold text-stone-800">Alertas Email a Tejedoras</p>
                    <p className="text-stone-500">Notificar nuevo pedido asignado</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={storeConfig.emailNotifications}
                    onChange={(e) => setStoreConfig({ ...storeConfig, emailNotifications: e.target.checked })}
                    className="w-4 h-4 accent-[#5C1D24]"
                  />
                </div>

                <div className="flex items-center justify-between p-3 bg-stone-50 rounded-xl">
                  <div>
                    <p className="font-bold text-stone-800">Alertas SMS / WhatsApp a Clientes</p>
                    <p className="text-stone-500">Notificaciones de envío de productos</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={storeConfig.smsNotifications}
                    onChange={(e) => setStoreConfig({ ...storeConfig, smsNotifications: e.target.checked })}
                    className="w-4 h-4 accent-[#5C1D24]"
                  />
                </div>

                <button onClick={() => showToast('Preferencias de notificación guardadas.')} className="px-5 py-2.5 bg-[#5C1D24] text-white font-bold rounded-xl">
                  Guardar Canales
                </button>
              </div>
            </div>
          )}

          {/* 19. VISTA: CONFIGURACIÓN - SEGURIDAD DJANGO */}
          {activeTab === 'config_seguridad' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Configuración de Seguridad Backend</h2>
                <p className="text-xs text-stone-600 mt-1">Tokens JWT Django, doble factor autenticación (2FA) y reglas de sesión.</p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-4 max-w-xl text-xs">
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900">
                  <p className="font-bold">✓ Kernel de Autenticación Django Conectado</p>
                  <p className="mt-1">Políticas RBAC enforced a nivel de middleware REST API.</p>
                </div>

                <button onClick={() => showToast('Tokens de sesión actualizados.')} className="px-5 py-2.5 bg-[#5C1D24] text-white font-bold rounded-xl">
                  Regenerar Keys JWT
                </button>
              </div>
            </div>
          )}

          {/* 20. VISTA: CONFIGURACIÓN - PREFERENCIAS DEL SISTEMA */}
          {activeTab === 'config_preferencias' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Preferencias del Sistema</h2>
                <p className="text-xs text-stone-600 mt-1">Soporte bilingüe Wayuunaiki y pasarelas de pago colombianas.</p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-4 max-w-xl text-xs">
                <div className="flex items-center justify-between p-3 bg-stone-50 rounded-xl">
                  <div>
                    <p className="font-bold text-stone-800">Soporte de Lengua Wayuunaiki</p>
                    <p className="text-stone-500">Traducción de menús y etiquetas</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={storeConfig.wayuunaikiSupport}
                    onChange={(e) => setStoreConfig({ ...storeConfig, wayuunaikiSupport: e.target.checked })}
                    className="w-4 h-4 accent-[#5C1D24]"
                  />
                </div>

                <div>
                  <label className="block font-bold text-stone-700 mb-1">Pasarela de Pago Integrada</label>
                  <select
                    value={storeConfig.gateway}
                    onChange={(e) => setStoreConfig({ ...storeConfig, gateway: e.target.value })}
                    className="w-full p-2.5 bg-white border border-stone-300 rounded-xl"
                  >
                    <option value="wompi">Wompi Bancolombia</option>
                    <option value="mercadopago">MercadoPago Colombia</option>
                    <option value="ePayco">ePayco</option>
                  </select>
                </div>

                <button onClick={() => showToast('Preferencias del sistema guardadas.')} className="px-5 py-2.5 bg-[#5C1D24] text-white font-bold rounded-xl">
                  Guardar Preferencias
                </button>
              </div>
            </div>
          )}

        </main>
      </div>

      {/* MODAL EDICIÓN USUARIO */}
      {isEditUserModalOpen && selectedUserForEdit && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <h3 className="font-bold text-stone-800 text-sm">Editar Usuario & Rol Asignado</h3>
              <button onClick={() => setIsEditUserModalOpen(false)} className="text-stone-400 hover:text-stone-600"><X className="w-5 h-5" /></button>
            </div>

            <form onSubmit={handleSaveUserModal} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold mb-1">Nombre Completo</label>
                <input
                  type="text"
                  value={selectedUserForEdit.name}
                  onChange={(e) => setSelectedUserForEdit({ ...selectedUserForEdit, name: e.target.value })}
                  className="w-full p-2 bg-stone-50 border border-stone-300 rounded-lg"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold mb-1">Correo Electrónico</label>
                <input
                  type="email"
                  value={selectedUserForEdit.email}
                  onChange={(e) => setSelectedUserForEdit({ ...selectedUserForEdit, email: e.target.value })}
                  className="w-full p-2 bg-stone-50 border border-stone-300 rounded-lg"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold mb-1">Rol Asignado</label>
                <select
                  value={selectedUserForEdit.role}
                  onChange={(e) => setSelectedUserForEdit({ ...selectedUserForEdit, role: e.target.value })}
                  className="w-full p-2 bg-white border border-stone-300 rounded-lg"
                >
                  {ROLES.map(r => (
                    <option key={r.id} value={r.id}>{r.name}</option>
                  ))}
                </select>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button type="button" onClick={() => setIsEditUserModalOpen(false)} className="px-3 py-1.5 border border-stone-300 rounded-lg">
                  Cancelar
                </button>
                <button type="submit" className="px-4 py-1.5 bg-[#5C1D24] text-white rounded-lg font-bold">
                  Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}