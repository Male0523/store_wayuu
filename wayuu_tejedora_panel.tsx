import React, { useState, useMemo } from 'react';
import {
  LayoutDashboard,
  ShoppingBag,
  Boxes,
  ShoppingCart,
  Search,
  Filter,
  Plus,
  Edit,
  Trash2,
  Clock,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  LogOut,
  Bell,
  Sparkles,
  ChevronRight,
  Upload,
  X,
  Eye,
  User,
  Phone,
  MapPin,
  Palette,
  Info,
  Check,
  ArrowDown,
  ArrowUp,
  FileText,
  Calendar,
  Layers,
  Award
} from 'lucide-react';

// ==========================================
// MOCK DATA FOR CURRENT WEAVER (MARÍA LÓPEZ)
// ==========================================

const ARTISAN_PROFILE = {
  name: 'María López',
  role: 'Tejedora Wayúu',
  rancheria: 'Ranchería Mayapo, Manaure',
  phone: '+57 312 849 2011',
  specialty: 'Mochilas Susu a una hebra y Kanaas Geométricos',
  yearsExperience: 14,
  avatar: 'ML'
};

const CATEGORIES = [
  'Mochilas (Susu)',
  'Hamacas y Chinchorros',
  'Sombreros Kumu',
  'Bisutería Kanaas',
  'Mantas y Vestimenta',
  'Calzado & Accesorios'
];

const INITIAL_WEAVER_PRODUCTS = [
  {
    id: 'PRD-101',
    name: 'Mochila Susu Kanaas Sol Naciente',
    category: 'Mochilas (Susu)',
    price: 280000,
    stock: 12,
    status: 'Aprobado y publicado',
    image: '🎒',
    description: 'Tejida a una sola hebra con simbología Kanaas geométrica tradicional en tonos tierra y terracotta.',
    technique: 'Single-thread (Una hebra)',
    colors: 'Borgoña, Marfil, Terracota',
    registerDate: '2026-10-15',
    feedback: ''
  },
  {
    id: 'PRD-105',
    name: 'Mochila Mini Susu Palabrero',
    category: 'Mochilas (Susu)',
    price: 190000,
    stock: 0,
    status: 'Devuelto para correcciones',
    image: '👛',
    description: 'Diseño compacto ideal para uso diario con correas paleteadas de alta resistencia.',
    technique: 'Doble hebra con gasa acordonada',
    colors: 'Ocre, Crema y Borgoña',
    registerDate: '2026-10-22',
    feedback: 'Por favor adjuntar fotografías detalladas con mejor iluminación del patrón de la gasa y especificar si incluye forro interior.'
  },
  {
    id: 'PRD-108',
    name: 'Manta Wayúu Tradicional Jiwatou',
    category: 'Mantas y Vestimenta',
    price: 340000,
    stock: 4,
    status: 'Pendiente de revisión',
    image: '👗',
    description: 'Manta de seda fría ligera elaborada con técnica de pliegues en telar de cintura.',
    technique: 'Telar tradicional de cintura',
    colors: 'Terracota, Verde esmeralda, Dorado',
    registerDate: '2026-10-28',
    feedback: ''
  },
  {
    id: 'PRD-112',
    name: 'Pulsera Kanaas Iwouya (Estrella)',
    category: 'Bisutería Kanaas',
    price: 45000,
    stock: 2,
    status: 'Aprobado y publicado',
    image: '📿',
    description: 'Tejido minucioso en mostacilla calibrada representando la estrella matutina Iwouya.',
    technique: 'Tejido en peineta de mostacillas',
    colors: 'Blanco marfil, Amarillo, Borgoña',
    registerDate: '2026-10-10',
    feedback: ''
  },
  {
    id: 'PRD-115',
    name: 'Chinchorro Anatas Pulowi Especial',
    category: 'Hamacas y Chinchorros',
    price: 1450000,
    stock: 1,
    status: 'Pendiente de revisión',
    image: '🛋️',
    description: 'Chinchorro de cabecera tejido doble hebra con flecos calados y detalles geométricos complejos.',
    technique: 'Tejido doble hebra con cañuela',
    colors: 'Borgoña, Marfil y Arena',
    registerDate: '2026-10-29',
    feedback: ''
  }
];

const INITIAL_WEAVER_MOVEMENTS = [
  { id: 'MOV-801', product: 'Mochila Susu Kanaas Sol Naciente', type: 'Entrada', quantity: 5, date: '2026-10-30 08:30 AM', reason: 'Entrega de lote terminado desde Mayapo' },
  { id: 'MOV-802', product: 'Pulsera Kanaas Iwouya (Estrella)', type: 'Salida', quantity: 2, date: '2026-10-29 02:15 PM', reason: 'Venta directa en pedido #ORD-9821' },
  { id: 'MOV-803', product: 'Manta Wayúu Tradicional Jiwatou', type: 'Entrada', quantity: 4, date: '2026-10-28 11:00 AM', reason: 'Registro inicial de prendas en taller' }
];

const INITIAL_WEAVER_ORDERS = [
  {
    id: 'ORD-9821',
    customer: 'Kenia Iguarán',
    email: 'kenia.i@gmail.com',
    date: '2026-10-29',
    items: [
      { name: 'Mochila Susu Kanaas Sol Naciente', qty: 1, price: 280000 },
      { name: 'Pulsera Kanaas Iwouya (Estrella)', qty: 2, price: 45000 }
    ],
    total: 370000,
    status: 'En elaboración / Tejido',
    progress: 60,
    history: [
      { step: 'Pedido recibido y asignado', date: '2026-10-29 08:30 AM', done: true },
      { step: 'Selección y urdido de hilos', date: '2026-10-29 10:15 AM', done: true },
      { step: 'Tejido de cuerpo / estructura', date: '2026-10-29 02:00 PM', done: true },
      { step: 'Elaboración de gasa y acabados', date: 'En proceso', done: false },
      { step: 'Control de calidad y despacho', date: 'Pendiente', done: false }
    ]
  },
  {
    id: 'ORD-9818',
    customer: 'María Fernanda Ruiz',
    email: 'mf.ruiz@hotmail.com',
    date: '2026-10-24',
    items: [{ name: 'Mochila Mini Susu Palabrero', qty: 1, price: 190000 }],
    total: 190000,
    status: 'Pendiente inicio',
    progress: 20,
    history: [
      { step: 'Pedido recibido y asignado', date: '2026-10-24 04:15 PM', done: true },
      { step: 'Selección y urdido de hilos', date: 'Pendiente', done: false },
      { step: 'Tejido de cuerpo / estructura', date: 'Pendiente', done: false },
      { step: 'Elaboración de gasa y acabados', date: 'Pendiente', done: false },
      { step: 'Control de calidad y despacho', date: 'Pendiente', done: false }
    ]
  }
];

const WEAVER_NOTIFICATIONS = [
  { id: 1, text: 'Tu producto "Mochila Mini Susu Palabrero" requiere correcciones del Administrador.', time: 'Hace 2 horas', priority: 'warning' },
  { id: 2, text: 'Se ha asignado el inicio del tejido para la orden #ORD-9821.', time: 'Hace 1 día', priority: 'info' },
  { id: 3, text: 'Tu producto "Mochila Susu Kanaas" fue publicado con éxito en la tienda.', time: 'Hace 3 días', priority: 'success' }
];

// ==========================================
// MAIN APP COMPONENT - ROLE: TEJEDORA
// ==========================================

export default function App() {
  // Navigation State (Exclusively 4 Main Options)
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard', 'products', 'inventory', 'orders'

  // Data States
  const [profile, setProfile] = useState(ARTISAN_PROFILE);
  const [products, setProducts] = useState(INITIAL_WEAVER_PRODUCTS);
  const [movements, setMovements] = useState(INITIAL_WEAVER_MOVEMENTS);
  const [orders, setOrders] = useState(INITIAL_WEAVER_ORDERS);

  // Modals
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [isAddProductModalOpen, setIsAddProductModalOpen] = useState(false);
  const [isEditProductModalOpen, setIsEditProductModalOpen] = useState(false);
  const [isKardexModalOpen, setIsKardexModalOpen] = useState(false);
  const [isOrderDetailModalOpen, setIsOrderDetailModalOpen] = useState(false);

  // Selected Entities
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);

  // Toast
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Filters
  const [productSearch, setProductSearch] = useState('');
  const [productCategoryFilter, setProductCategoryFilter] = useState('all');
  const [productStatusFilter, setProductStatusFilter] = useState('all');

  // New Product Form State
  const [newProduct, setNewProduct] = useState({
    name: '',
    category: CATEGORIES[0],
    price: '',
    stock: 1,
    description: '',
    technique: '',
    colors: '',
    image: '🎒'
  });

  // Kardex Movement Form State
  const [newMovement, setNewMovement] = useState({
    productName: INITIAL_WEAVER_PRODUCTS[0].name,
    type: 'Entrada',
    quantity: 1,
    reason: ''
  });

  // Profile Edit State
  const [editProfile, setEditProfile] = useState(ARTISAN_PROFILE);

  // ==========================================
  // COMPUTED / METRICS
  // ==========================================

  const filteredProducts = useMemo(() => {
    return products.filter(p => {
      const matchesSearch = p.name.toLowerCase().includes(productSearch.toLowerCase());
      const matchesCategory = productCategoryFilter === 'all' || p.category === productCategoryFilter;
      const matchesStatus = productStatusFilter === 'all' || p.status === productStatusFilter;
      return matchesSearch && matchesCategory && matchesStatus;
    });
  }, [products, productSearch, productCategoryFilter, productStatusFilter]);

  const approvedCount = useMemo(() => products.filter(p => p.status === 'Aprobado y publicado').length, [products]);
  const pendingCount = useMemo(() => products.filter(p => p.status === 'Pendiente de revisión').length, [products]);
  const returnedCount = useMemo(() => products.filter(p => p.status === 'Devuelto para correcciones').length, [products]);
  const lowStockCount = useMemo(() => products.filter(p => p.stock < 3 && p.stock > 0).length, [products]);
  const outOfStockCount = useMemo(() => products.filter(p => p.stock === 0).length, [products]);
  const totalStockUnits = useMemo(() => products.reduce((sum, p) => sum + p.stock, 0), [products]);

  // ==========================================
  // HANDLERS
  // ==========================================

  // Create Product Flow -> STRICT RULE: ENTERS IN "Pendiente de revisión"
  const handleCreateProduct = (e) => {
    e.preventDefault();
    if (!newProduct.name || !newProduct.price) return;

    const created = {
      id: `PRD-${Math.floor(200 + Math.random() * 800)}`,
      name: newProduct.name,
      category: newProduct.category,
      price: Number(newProduct.price),
      stock: Number(newProduct.stock) || 1,
      status: 'Pendiente de revisión', // Always pending upon creation
      image: newProduct.image || '🎒',
      description: newProduct.description,
      technique: newProduct.technique || 'Tejido a mano Wayúu',
      colors: newProduct.colors || 'Multicolor',
      registerDate: new Date().toISOString().split('T')[0],
      feedback: ''
    };

    setProducts([created, ...products]);
    setIsAddProductModalOpen(false);
    setNewProduct({
      name: '',
      category: CATEGORIES[0],
      price: '',
      stock: 1,
      description: '',
      technique: '',
      colors: '',
      image: '🎒'
    });

    showToast('Tejido registrado con éxito. Se encuentra en "Pendiente de revisión" por el Administrador.');
  };

  // Edit/Correct Product Flow -> ALWAYS RE-ENTERS "Pendiente de revisión"
  const handleSaveProductCorrection = (e) => {
    e.preventDefault();
    if (!selectedProduct) return;

    setProducts(products.map(p => {
      if (p.id === selectedProduct.id) {
        return {
          ...selectedProduct,
          status: 'Pendiente de revisión', // Sent back for review
          feedback: '' // Clear feedback on resubmission
        };
      }
      return p;
    }));

    setIsEditProductModalOpen(false);
    showToast('Corrección enviada nuevamente a revisión del Administrador de tienda.');
  };

  const handleDeleteProduct = (id) => {
    setProducts(products.filter(p => p.id !== id));
    showToast('Tejido eliminado de tus registros.', 'info');
  };

  const handleSaveProfile = (e) => {
    e.preventDefault();
    setProfile(editProfile);
    setIsProfileModalOpen(false);
    showToast('Perfil de tejedora actualizado correctamente.');
  };

  const handleAddKardexMovement = (e) => {
    e.preventDefault();

    const targetProduct = products.find(p => p.name === newMovement.productName);
    const qty = Number(newMovement.quantity);

    if (newMovement.type === 'Salida' && targetProduct && targetProduct.stock < qty) {
      showToast('No tienes suficiente stock registrado para realizar esta salida.', 'info');
      return;
    }

    setProducts(products.map(p => {
      if (p.name === newMovement.productName) {
        const nextStock = newMovement.type === 'Entrada' ? p.stock + qty : p.stock - qty;
        return { ...p, stock: Math.max(0, nextStock) };
      }
      return p;
    }));

    const movementEntry = {
      id: `MOV-${Math.floor(800 + Math.random() * 200)}`,
      product: newMovement.productName,
      type: newMovement.type,
      quantity: qty,
      date: new Date().toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }),
      reason: newMovement.reason || (newMovement.type === 'Entrada' ? 'Reabastecimiento de taller' : 'Ajuste de inventario personal')
    };

    setMovements([movementEntry, ...movements]);
    setIsKardexModalOpen(false);
    showToast(`Movimiento de inventario registrado: ${newMovement.type} de ${qty} und.`);
  };

  const handleUpdateOrderProductionStep = (orderId, stepIndex) => {
    setOrders(orders.map(ord => {
      if (ord.id === orderId) {
        const updatedHistory = ord.history.map((h, idx) => {
          if (idx <= stepIndex) {
            return {
              ...h,
              done: true,
              date: h.done ? h.date : new Date().toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })
            };
          }
          return h;
        });

        const completedSteps = updatedHistory.filter(h => h.done).length;
        const newProgress = Math.round((completedSteps / updatedHistory.length) * 100);

        let newStatus = 'En elaboración / Tejido';
        if (newProgress === 100) newStatus = 'Listo para entrega / Despacho';
        else if (completedSteps <= 1) newStatus = 'Pendiente inicio';

        return { ...ord, history: updatedHistory, progress: newProgress, status: newStatus };
      }
      return ord;
    }));

    if (selectedOrder && selectedOrder.id === orderId) {
      const targetOrd = orders.find(o => o.id === orderId);
      if (targetOrd) {
        const updatedHist = targetOrd.history.map((h, idx) => idx <= stepIndex ? { ...h, done: true, date: new Date().toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) } : h);
        setSelectedOrder({ ...targetOrd, history: updatedHist });
      }
    }

    showToast('Etapa de tejido de la orden actualizada.');
  };

  return (
    <div className="flex h-screen bg-[#FDFBF7] text-[#3D1E16] font-sans overflow-hidden selection:bg-[#5C1D24] selection:text-white">

      {/* TOAST NOTIFICATION */}
      {toast && (
        <div className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-5 py-3.5 rounded-xl shadow-2xl text-xs font-semibold transition-all duration-300 ${
          toast.type === 'info' ? 'bg-[#3D1E16] text-amber-100 border border-amber-800' : 'bg-[#5C1D24] text-white border border-[#4A121A]'
        }`}>
          {toast.type === 'info' ? <Info className="w-5 h-5 text-amber-300 shrink-0" /> : <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* SIDEBAR NAVIGATION (STRICTLY 4 MAIN OPTIONS FOR TEJEDORA) */}
      <aside className="w-64 bg-[#5C1D24] text-white flex flex-col justify-between shrink-0 shadow-2xl relative z-20">
        <div className="flex flex-col h-full overflow-y-auto">

          {/* Wayúu Geometric Branding */}
          <div className="p-6 pb-5 flex items-center gap-3.5 border-b border-rose-900/50">
            <div className="p-2.5 bg-[#FDFBF7]/10 rounded-xl border border-white/20 shadow-inner flex items-center justify-center">
              <svg className="w-7 h-7 text-[#FDFBF7]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
            </div>
            <div>
              <h1 className="font-bold text-lg tracking-wide text-[#FDFBF7] leading-tight">Wayúu</h1>
              <p className="text-[10px] text-rose-200/90 tracking-wider uppercase font-semibold">Portal de Tejedora</p>
            </div>
          </div>

          {/* Menú de Navegación Exclusivo de 4 Opciones */}
          <nav className="p-4 space-y-2 text-xs font-medium flex-1">
            <p className="text-[10px] uppercase font-bold text-rose-300/60 px-3 pb-1 tracking-wider">Menú Principal</p>

            {/* 1. Panel principal */}
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all duration-200 ${
                activeTab === 'dashboard'
                  ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-md transform translate-x-1'
                  : 'text-rose-100 hover:bg-white/10'
              }`}
            >
              <LayoutDashboard className={`w-4 h-4 ${activeTab === 'dashboard' ? 'text-[#5C1D24]' : 'text-rose-200'}`} />
              <span>Panel principal</span>
            </button>

            {/* 2. Mis tejidos / productos */}
            <button
              onClick={() => setActiveTab('products')}
              className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all duration-200 ${
                activeTab === 'products'
                  ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-md transform translate-x-1'
                  : 'text-rose-100 hover:bg-white/10'
              }`}
            >
              <ShoppingBag className={`w-4 h-4 ${activeTab === 'products' ? 'text-[#5C1D24]' : 'text-rose-200'}`} />
              <span>Mis tejidos / productos</span>
            </button>

            {/* 3. Mi inventario */}
            <button
              onClick={() => setActiveTab('inventory')}
              className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all duration-200 ${
                activeTab === 'inventory'
                  ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-md transform translate-x-1'
                  : 'text-rose-100 hover:bg-white/10'
              }`}
            >
              <Boxes className={`w-4 h-4 ${activeTab === 'inventory' ? 'text-[#5C1D24]' : 'text-rose-200'}`} />
              <span>Mi inventario</span>
            </button>

            {/* 4. Mis pedidos */}
            <button
              onClick={() => setActiveTab('orders')}
              className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all duration-200 ${
                activeTab === 'orders'
                  ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-md transform translate-x-1'
                  : 'text-rose-100 hover:bg-white/10'
              }`}
            >
              <ShoppingCart className={`w-4 h-4 ${activeTab === 'orders' ? 'text-[#5C1D24]' : 'text-rose-200'}`} />
              <span>Mis pedidos</span>
            </button>
          </nav>

          {/* User Profile Badge in Sidebar Bottom */}
          <div className="p-4 m-3 rounded-2xl bg-black/20 border border-white/10 space-y-3">
            <button
              onClick={() => { setEditProfile(profile); setIsProfileModalOpen(true); }}
              className="w-full flex items-center gap-3 text-left group"
            >
              <div className="w-9 h-9 rounded-full bg-[#FDFBF7] text-[#5C1D24] flex items-center justify-center font-bold text-xs shadow-md shrink-0 border border-rose-200">
                {profile.avatar}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-white truncate group-hover:underline">{profile.name}</p>
                <p className="text-[10px] text-rose-200/80 truncate">{profile.role}</p>
              </div>
            </button>

            <button
              onClick={() => setIsLogoutModalOpen(true)}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-white/10 hover:bg-rose-900/60 text-white text-xs font-semibold transition-colors border border-white/10"
            >
              <LogOut className="w-3.5 h-3.5 text-rose-200" />
              <span>Cerrar sesión</span>
            </button>
          </div>

          <div className="p-3 text-center border-t border-rose-900/40 bg-black/10">
            <p className="text-[10px] text-rose-300/60 font-mono">Wayúu Tejedora v2.5</p>
          </div>

        </div>
      </aside>

      {/* WORKSPACE AREA */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">

        {/* TOP HEADER */}
        <header className="bg-white border-b border-[#E2D9D5] px-8 py-4 flex items-center justify-between shrink-0 shadow-sm z-10">
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold uppercase tracking-wider text-[#5C1D24] bg-rose-50 px-3 py-1 rounded-lg border border-rose-200">
              Rol: Tejedora
            </span>
            <span className="text-xs text-stone-300">/</span>
            <span className="text-xs font-medium text-stone-600 capitalize">
              {activeTab === 'dashboard' && 'Panel Principal'}
              {activeTab === 'products' && 'Mis Tejidos y Productos'}
              {activeTab === 'inventory' && 'Mi Inventario de Piezas'}
              {activeTab === 'orders' && 'Mis Pedidos Asignados'}
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 text-xs font-semibold text-[#5C1D24] bg-rose-50 px-3 py-1.5 rounded-full border border-rose-200">
              <MapPin className="w-3.5 h-3.5" />
              <span>{profile.rancheria}</span>
            </div>

            <button
              onClick={() => showToast('Notificaciones de la tejedora actualizadas.', 'info')}
              className="relative p-2 text-stone-600 hover:text-[#5C1D24] hover:bg-rose-50 rounded-full transition-colors"
              title="Notificaciones"
            >
              <Bell className="w-5 h-5" />
              {returnedCount > 0 && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-amber-500 rounded-full ring-2 ring-white animate-pulse"></span>
              )}
            </button>

            {/* Profile Header Button */}
            <div className="flex items-center gap-3 pl-4 border-l border-stone-200">
              <button
                onClick={() => { setEditProfile(profile); setIsProfileModalOpen(true); }}
                className="flex items-center gap-2.5 text-left hover:opacity-80 transition-opacity"
              >
                <div className="w-9 h-9 rounded-full bg-[#5C1D24] text-white flex items-center justify-center text-xs font-bold shadow-sm">
                  {profile.avatar}
                </div>
                <div className="hidden sm:block">
                  <p className="text-xs font-bold text-stone-800 leading-tight">{profile.name}</p>
                  <p className="text-[11px] text-stone-500">{profile.role}</p>
                </div>
              </button>

              <button
                onClick={() => setIsLogoutModalOpen(true)}
                title="Cerrar sesión"
                className="ml-2 p-2 text-stone-500 hover:text-rose-700 hover:bg-rose-50 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </header>

        {/* MAIN VISTAS CONTENT */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-[#FDFBF7]">

          {/* ========================================== */}
          {/* VISTA 1: PANEL PRINCIPAL */}
          {/* ========================================== */}
          {activeTab === 'dashboard' && (
            <div className="max-w-7xl mx-auto space-y-6">

              {/* Banner Cultural Motivacional Wayúu */}
              <div className="relative rounded-3xl bg-gradient-to-r from-[#5C1D24] via-[#7A2832] to-[#3D1E16] text-white p-6 md:p-8 shadow-xl overflow-hidden">
                <div className="absolute top-0 right-0 w-96 h-96 bg-white/5 rounded-full blur-3xl -mr-20 -mt-20"></div>
                <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-rose-200 text-xs font-medium border border-white/10">
                      <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                      <span>Süchiki Kanaas - Legado Cultural</span>
                    </div>
                    <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-[#FDFBF7]">
                      Jamaya, {profile.name}!
                    </h2>
                    <p className="text-xs md:text-sm text-rose-100/90 max-w-xl italic">
                      "El tejido no solo une hilos, une el pensamiento y la memoria ancestral de nuestro pueblo Wayúu."
                    </p>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => setIsAddProductModalOpen(true)}
                      className="px-4 py-2.5 bg-[#FDFBF7] text-[#5C1D24] hover:bg-amber-50 rounded-xl text-xs font-bold transition-all shadow-md flex items-center gap-2"
                    >
                      <Plus className="w-4 h-4" />
                      <span>+ Registrar Nuevo Tejido</span>
                    </button>
                    <button
                      onClick={() => setActiveTab('orders')}
                      className="px-4 py-2.5 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-semibold transition-all border border-white/20 flex items-center gap-2"
                    >
                      <ShoppingCart className="w-4 h-4" />
                      <span>Ver Mis Pedidos ({orders.length})</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Grid de Tarjetas de Resumen Personal */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">

                {/* Total Registrados */}
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold text-stone-500 uppercase">Total Tejidos</span>
                    <div className="p-2 bg-rose-50 text-[#5C1D24] rounded-xl"><ShoppingBag className="w-4 h-4" /></div>
                  </div>
                  <p className="text-2xl font-black text-[#3D1E16]">{products.length}</p>
                  <p className="text-[10px] text-stone-500 mt-1">Registrados por ti</p>
                </div>

                {/* Publicados / Aprobados */}
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold text-stone-500 uppercase">Publicados</span>
                    <div className="p-2 bg-emerald-50 text-emerald-700 rounded-xl"><CheckCircle2 className="w-4 h-4" /></div>
                  </div>
                  <p className="text-2xl font-black text-emerald-800">{approvedCount}</p>
                  <p className="text-[10px] text-emerald-600 font-semibold mt-1">Visibles en tienda</p>
                </div>

                {/* Pendientes de Revisión */}
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold text-stone-500 uppercase">En Revisión</span>
                    <div className="p-2 bg-amber-50 text-amber-700 rounded-xl"><Clock className="w-4 h-4" /></div>
                  </div>
                  <p className="text-2xl font-black text-amber-800">{pendingCount}</p>
                  <p className="text-[10px] text-amber-600 font-medium mt-1">Esperando aprobación</p>
                </div>

                {/* Devueltos para Corrección */}
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold text-stone-500 uppercase">Por Corregir</span>
                    <div className="p-2 bg-orange-50 text-orange-700 rounded-xl"><RotateCcw className="w-4 h-4" /></div>
                  </div>
                  <p className="text-2xl font-black text-orange-800">{returnedCount}</p>
                  <p className="text-[10px] text-orange-600 font-bold mt-1">Revisa las observaciones</p>
                </div>

                {/* Inventario Disponible */}
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold text-stone-500 uppercase">En Inventario</span>
                    <div className="p-2 bg-blue-50 text-blue-700 rounded-xl"><Boxes className="w-4 h-4" /></div>
                  </div>
                  <p className="text-2xl font-black text-stone-800">{totalStockUnits} <span className="text-xs font-normal">und.</span></p>
                  <p className="text-[10px] text-blue-600 font-medium mt-1">Piezas listos</p>
                </div>

                {/* Pedidos en Curso */}
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold text-stone-500 uppercase">Pedidos Activos</span>
                    <div className="p-2 bg-purple-50 text-purple-700 rounded-xl"><ShoppingCart className="w-4 h-4" /></div>
                  </div>
                  <p className="text-2xl font-black text-[#5C1D24]">{orders.length}</p>
                  <p className="text-[10px] text-purple-600 font-medium mt-1">En proceso de tejido</p>
                </div>

              </div>

              {/* Banner de Atención si hay productos Devueltos */}
              {returnedCount > 0 && (
                <div className="bg-amber-50 border border-amber-300 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-amber-100 text-amber-800 rounded-xl shrink-0">
                      <AlertTriangle className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-bold text-xs text-amber-900">Tienes {returnedCount} producto(s) devuelto(s) para corrección</h4>
                      <p className="text-[11px] text-amber-700">El Administrador de tienda ha dejado observaciones que debes ajustar para publicar tus prendas.</p>
                    </div>
                  </div>

                  <button
                    onClick={() => { setProductStatusFilter('Devuelto para correcciones'); setActiveTab('products'); }}
                    className="px-4 py-2 bg-amber-700 hover:bg-amber-800 text-white rounded-xl text-xs font-bold shrink-0 transition-colors"
                  >
                    Ver Observaciones
                  </button>
                </div>
              )}

              {/* Middle Section: Accesos Rápidos & Notificaciones */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

                {/* Accesos Rápidos */}
                <div className="lg:col-span-6 bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-4">
                  <h3 className="text-sm font-bold text-stone-800 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-[#5C1D24]" />
                    <span>Accesos rápidos</span>
                  </h3>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <button
                      onClick={() => setIsAddProductModalOpen(true)}
                      className="p-4 rounded-xl border border-stone-200 hover:border-[#5C1D24] bg-[#FDFBF7] hover:bg-rose-50 text-left transition-all group"
                    >
                      <div className="p-2 bg-rose-100 text-[#5C1D24] rounded-lg w-max mb-2">
                        <Plus className="w-4 h-4" />
                      </div>
                      <p className="font-bold text-xs text-stone-800">Registrar nuevo tejido</p>
                      <p className="text-[10px] text-stone-500">Ingresa mochila, chinchorro o prenda</p>
                    </button>

                    <button
                      onClick={() => setActiveTab('orders')}
                      className="p-4 rounded-xl border border-stone-200 hover:border-[#5C1D24] bg-[#FDFBF7] hover:bg-rose-50 text-left transition-all group"
                    >
                      <div className="p-2 bg-purple-100 text-purple-800 rounded-lg w-max mb-2">
                        <ShoppingCart className="w-4 h-4" />
                      </div>
                      <p className="font-bold text-xs text-stone-800">Mis pedidos asignados</p>
                      <p className="text-[10px] text-stone-500">Actualiza avance de producción</p>
                    </button>

                    <button
                      onClick={() => setActiveTab('inventory')}
                      className="p-4 rounded-xl border border-stone-200 hover:border-[#5C1D24] bg-[#FDFBF7] hover:bg-rose-50 text-left transition-all group"
                    >
                      <div className="p-2 bg-blue-100 text-blue-800 rounded-lg w-max mb-2">
                        <Boxes className="w-4 h-4" />
                      </div>
                      <p className="font-bold text-xs text-stone-800">Mi inventario</p>
                      <p className="text-[10px] text-stone-500">Kardex y control de existencias</p>
                    </button>

                    <button
                      onClick={() => { setEditProfile(profile); setIsProfileModalOpen(true); }}
                      className="p-4 rounded-xl border border-stone-200 hover:border-[#5C1D24] bg-[#FDFBF7] hover:bg-rose-50 text-left transition-all group"
                    >
                      <div className="p-2 bg-emerald-100 text-emerald-800 rounded-lg w-max mb-2">
                        <User className="w-4 h-4" />
                      </div>
                      <p className="font-bold text-xs text-stone-800">Mi perfil de tejedora</p>
                      <p className="text-[10px] text-stone-500">Datos personales y ranchería</p>
                    </button>
                  </div>
                </div>

                {/* Notificaciones Recientes */}
                <div className="lg:col-span-6 bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-4">
                  <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                    <h3 className="text-sm font-bold text-stone-800 flex items-center gap-2">
                      <Bell className="w-4 h-4 text-[#5C1D24]" />
                      <span>Notificaciones y actividad personal</span>
                    </h3>
                    <span className="text-[10px] text-stone-400">Recientes</span>
                  </div>

                  <div className="space-y-3 text-xs">
                    {WEAVER_NOTIFICATIONS.map(notif => (
                      <div key={notif.id} className="p-3 rounded-xl border border-stone-100 bg-[#FDFBF7] flex items-start gap-3">
                        <span className={`w-2 h-2 rounded-full mt-1 shrink-0 ${
                          notif.priority === 'warning' ? 'bg-amber-500' : notif.priority === 'success' ? 'bg-emerald-500' : 'bg-blue-500'
                        }`}></span>
                        <div className="flex-1">
                          <p className="text-stone-800 font-medium leading-snug">{notif.text}</p>
                          <span className="text-[10px] text-stone-400 mt-1 block">{notif.time}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>

            </div>
          )}

          {/* ========================================== */}
          {/* VISTA 2: MIS TEJIDOS / PRODUCTOS */}
          {/* ========================================== */}
          {activeTab === 'products' && (
            <div className="max-w-7xl mx-auto space-y-6">

              {/* Top Header & Actions */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Mis Tejidos y Productos</h2>
                  <p className="text-xs text-stone-600 mt-1">
                    Gestión de artesanías registradas por {profile.name}. Todos los nuevos productos entran en revisión antes de ser publicados.
                  </p>
                </div>

                <button
                  onClick={() => setIsAddProductModalOpen(true)}
                  className="px-4 py-2.5 bg-[#5C1D24] hover:bg-[#4A121A] text-white rounded-xl text-xs font-bold transition-colors shadow-sm flex items-center gap-2 self-start sm:self-auto"
                >
                  <Plus className="w-4 h-4" />
                  <span>+ Registrar Nuevo Tejido</span>
                </button>
              </div>

              {/* Filtros & Búsqueda */}
              <div className="bg-white p-4 rounded-2xl border border-[#E2D9D5] shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
                <div className="relative w-full md:w-80">
                  <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Buscar en mis tejidos..."
                    value={productSearch}
                    onChange={(e) => setProductSearch(e.target.value)}
                    className="w-full text-xs pl-9 pr-3 py-2 bg-[#FDFBF7] border border-stone-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  />
                </div>

                <div className="flex items-center gap-3 w-full md:w-auto overflow-x-auto">
                  <div className="flex items-center gap-1 text-xs text-stone-500 font-medium shrink-0">
                    <Filter className="w-3.5 h-3.5" />
                    <span>Filtros:</span>
                  </div>

                  {/* Selector Categoría */}
                  <select
                    value={productCategoryFilter}
                    onChange={(e) => setProductCategoryFilter(e.target.value)}
                    className="text-xs bg-white border border-stone-300 rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  >
                    <option value="all">Todas las categorías</option>
                    {CATEGORIES.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>

                  {/* Selector Estado */}
                  <select
                    value={productStatusFilter}
                    onChange={(e) => setProductStatusFilter(e.target.value)}
                    className="text-xs bg-white border border-stone-300 rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  >
                    <option value="all">Todos los estados</option>
                    <option value="Aprobado y publicado">Aprobado y publicado</option>
                    <option value="Pendiente de revisión">Pendiente de revisión</option>
                    <option value="Devuelto para correcciones">Devuelto para correcciones</option>
                    <option value="Rechazado">Rechazado</option>
                  </select>
                </div>
              </div>

              {/* GRID DE PRODUCTOS DE LA TEJEDORA */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredProducts.map(prod => (
                  <div key={prod.id} className="bg-white border border-[#E2D9D5] rounded-2xl p-5 shadow-sm hover:shadow-md transition-all flex flex-col justify-between space-y-4">

                    <div>
                      {/* Emoji Image & Badge Status */}
                      <div className="flex items-start justify-between">
                        <span className="text-4xl p-3 bg-[#FDFBF7] rounded-2xl border border-stone-200 shadow-sm">{prod.image}</span>
                        
                        {/* BADGES STRICT REQUIREMENTS */}
                        <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full border ${
                          prod.status === 'Aprobado y publicado' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                          prod.status === 'Pendiente de revisión' ? 'bg-amber-50 text-amber-800 border-amber-200' :
                          prod.status === 'Devuelto para correcciones' ? 'bg-orange-50 text-orange-900 border-orange-300 font-extrabold' :
                          'bg-rose-50 text-rose-800 border-rose-200'
                        }`}>
                          {prod.status}
                        </span>
                      </div>

                      <div className="mt-3 space-y-1">
                        <span className="text-[10px] font-bold text-[#5C1D24] uppercase tracking-wider">{prod.category}</span>
                        <h3 className="font-bold text-sm text-stone-800 leading-snug">{prod.name}</h3>
                        <p className="text-[11px] text-stone-500 italic line-clamp-2">{prod.description}</p>
                      </div>

                      {/* Technical Specs */}
                      <div className="mt-3 p-2.5 bg-[#FDFBF7] rounded-xl border border-stone-200 space-y-1 text-[10px]">
                        <p className="text-stone-600"><strong>Técnica:</strong> {prod.technique}</p>
                        <p className="text-stone-600"><strong>Colores:</strong> {prod.colors}</p>
                        <p className="text-stone-400"><strong>Fecha registro:</strong> {prod.registerDate}</p>
                      </div>

                      {/* OBSERVACIONES DEL ADMIN (SI ES DEVUELTO) */}
                      {prod.status === 'Devuelto para correcciones' && prod.feedback && (
                        <div className="mt-3 p-3 bg-orange-50 border border-orange-300 rounded-xl space-y-1 text-[11px] text-orange-900">
                          <p className="font-bold flex items-center gap-1.5 text-orange-950">
                            <AlertTriangle className="w-3.5 h-3.5 text-orange-600" />
                            <span>Observaciones del Administrador:</span>
                          </p>
                          <p className="italic bg-white/70 p-2 rounded-lg border border-orange-200 text-stone-800">
                            "{prod.feedback}"
                          </p>
                        </div>
                      )}
                    </div>

                    <div className="pt-3 border-t border-stone-100 flex items-center justify-between">
                      <div>
                        <p className="text-sm font-black text-[#5C1D24]">${prod.price.toLocaleString()} COP</p>
                        <p className={`text-[10px] font-semibold ${prod.stock === 0 ? 'text-rose-600' : 'text-stone-500'}`}>
                          {prod.stock > 0 ? `Stock: ${prod.stock} und.` : 'Agotado'}
                        </p>
                      </div>

                      {/* WEAVER ACTIONS: Editar/Corregir y Eliminar (NO TIENE BOTÓN DE APROBAR) */}
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => { setSelectedProduct(prod); setIsEditProductModalOpen(true); }}
                          className="px-3 py-1.5 bg-[#5C1D24] hover:bg-[#4A121A] text-white rounded-xl text-xs font-bold transition-all shadow-sm flex items-center gap-1"
                          title="Editar / Corregir"
                        >
                          <Edit className="w-3.5 h-3.5" />
                          <span>{prod.status === 'Devuelto para correcciones' ? 'Corregir' : 'Editar'}</span>
                        </button>

                        <button
                          onClick={() => handleDeleteProduct(prod.id)}
                          className="p-1.5 text-stone-400 hover:text-rose-700 hover:bg-rose-50 rounded-xl border border-stone-200 transition-colors"
                          title="Eliminar"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                  </div>
                ))}
              </div>

            </div>
          )}

          {/* ========================================== */}
          {/* VISTA 3: MI INVENTARIO */}
          {/* ========================================== */}
          {activeTab === 'inventory' && (
            <div className="max-w-7xl mx-auto space-y-6">

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Mi Inventario de Piezas</h2>
                  <p className="text-xs text-stone-600 mt-1">
                    Control de existencias personal de {profile.name}. Registra ingresos y salidas de tus piezas.
                  </p>
                </div>

                <button
                  onClick={() => setIsKardexModalOpen(true)}
                  className="px-4 py-2.5 bg-[#5C1D24] hover:bg-[#4A121A] text-white rounded-xl text-xs font-bold transition-colors shadow-sm flex items-center gap-2 self-start sm:self-auto"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>+ Registrar Movimiento Stock</span>
                </button>
              </div>

              {/* Tarjetas de Resumen de Stock */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-stone-500 uppercase">Stock Total Personal</p>
                    <p className="text-2xl font-black text-[#5C1D24] mt-1">{totalStockUnits} unidades</p>
                    <p className="text-[10px] text-stone-500">Listas para comercializar</p>
                  </div>
                  <div className="p-3 bg-rose-50 text-[#5C1D24] rounded-xl"><Boxes className="w-6 h-6" /></div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-stone-500 uppercase">Bajo Stock (&lt;3 und.)</p>
                    <p className="text-2xl font-black text-amber-700 mt-1">{lowStockCount} artesanías</p>
                    <p className="text-[10px] text-amber-600 font-medium">Considerar tejido de reposición</p>
                  </div>
                  <div className="p-3 bg-amber-50 text-amber-700 rounded-xl"><AlertTriangle className="w-6 h-6" /></div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-stone-500 uppercase">Productos Agotados</p>
                    <p className="text-2xl font-black text-rose-700 mt-1">{outOfStockCount} artesanías</p>
                    <p className="text-[10px] text-rose-600 font-medium">Requieren producción</p>
                  </div>
                  <div className="p-3 bg-rose-50 text-rose-700 rounded-xl"><X className="w-6 h-6" /></div>
                </div>
              </div>

              {/* Tabla de Existencias de la Tejedora */}
              <div className="bg-white rounded-2xl border border-[#E2D9D5] shadow-sm overflow-hidden p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                  <h3 className="font-bold text-stone-800 text-sm">Existencias por Tejido</h3>
                  <span className="text-xs text-stone-500">Mostrando tus piezas registradas</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-stone-50 border-b border-[#E2D9D5] font-semibold text-stone-600">
                        <th className="py-3 px-4">Artesanía</th>
                        <th className="py-3 px-4">Categoría</th>
                        <th className="py-3 px-4">Precio (COP)</th>
                        <th className="py-3 px-4">Stock Actual</th>
                        <th className="py-3 px-4">Estado Disponibilidad</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-100">
                      {products.map(p => (
                        <tr key={p.id} className="hover:bg-stone-50 transition-colors">
                          <td className="py-3.5 px-4 font-bold text-stone-800 flex items-center gap-2">
                            <span className="text-2xl p-1 bg-stone-100 rounded-lg">{p.image}</span>
                            <span>{p.name}</span>
                          </td>

                          <td className="py-3.5 px-4 text-stone-600">{p.category}</td>
                          <td className="py-3.5 px-4 font-bold text-[#5C1D24]">${p.price.toLocaleString()} COP</td>

                          <td className="py-3.5 px-4 font-black text-stone-900">
                            {p.stock} und.
                          </td>

                          <td className="py-3.5 px-4">
                            {p.stock === 0 ? (
                              <span className="bg-rose-100 text-rose-800 font-bold px-2.5 py-1 rounded-full text-[10px]">
                                Agotado
                              </span>
                            ) : p.stock < 3 ? (
                              <span className="bg-amber-100 text-amber-800 font-bold px-2.5 py-1 rounded-full text-[10px]">
                                Stock Bajo ({p.stock})
                              </span>
                            ) : (
                              <span className="bg-emerald-100 text-emerald-800 font-bold px-2.5 py-1 rounded-full text-[10px]">
                                Disponible
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Historial Kardex de Movimientos Personales */}
              <div className="bg-white rounded-2xl border border-[#E2D9D5] p-6 shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                  <h3 className="font-bold text-stone-800 text-sm">Historial de Entradas y Salidas (Kardex Personal)</h3>
                  <span className="text-xs text-stone-500">{movements.length} registro(s)</span>
                </div>

                <div className="divide-y divide-stone-100 text-xs">
                  {movements.map(m => (
                    <div key={m.id} className="py-3 flex items-center justify-between hover:bg-stone-50 px-2 rounded-lg transition-colors">
                      <div className="flex items-center gap-3">
                        <span className={`p-2 rounded-xl text-white font-bold ${m.type === 'Entrada' ? 'bg-emerald-600' : 'bg-rose-600'}`}>
                          {m.type === 'Entrada' ? <ArrowDown className="w-3.5 h-3.5" /> : <ArrowUp className="w-3.5 h-3.5" />}
                        </span>
                        <div>
                          <p className="font-bold text-stone-800">{m.product}</p>
                          <p className="text-[10px] text-stone-500">{m.reason} • <span className="font-mono">{m.date}</span></p>
                        </div>
                      </div>

                      <div className="text-right">
                        <span className={`font-black ${m.type === 'Entrada' ? 'text-emerald-700' : 'text-rose-700'}`}>
                          {m.type === 'Entrada' ? '+' : '-'}{m.quantity} und.
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          )}

          {/* ========================================== */}
          {/* VISTA 4: MIS PEDIDOS */}
          {/* ========================================== */}
          {activeTab === 'orders' && (
            <div className="max-w-7xl mx-auto space-y-6">

              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Mis Pedidos Asignados</h2>
                <p className="text-xs text-stone-600 mt-1">
                  Muestra únicamente las órdenes de clientes que solicitan artesanías tejidas por {profile.name}.
                </p>
              </div>

              {/* Lista de Pedidos en Tarjetas con Detalle de Producción */}
              <div className="space-y-4">
                {orders.map(order => (
                  <div key={order.id} className="bg-white rounded-2xl border border-[#E2D9D5] p-6 shadow-sm space-y-4 hover:shadow-md transition-shadow">
                    
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-stone-100 pb-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-black text-sm text-[#5C1D24]">{order.id}</span>
                          <span className="text-xs text-stone-400">•</span>
                          <span className="text-xs font-bold text-stone-700">Cliente: {order.customer}</span>
                        </div>
                        <p className="text-[11px] text-stone-400 mt-0.5">Fecha pedido: {order.date}</p>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-[#5C1D24] border border-rose-200">
                          {order.status}
                        </span>

                        <button
                          onClick={() => { setSelectedOrder(order); setIsOrderDetailModalOpen(true); }}
                          className="px-3.5 py-1.5 bg-stone-100 hover:bg-[#5C1D24] hover:text-white text-stone-700 rounded-xl text-xs font-bold transition-all border border-stone-200 flex items-center gap-1.5"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Gestionar Avance</span>
                        </button>
                      </div>
                    </div>

                    {/* Contenido de la Orden: Tejidos de la Tejedora */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      
                      {/* Productos */}
                      <div className="p-3 bg-[#FDFBF7] rounded-xl border border-stone-200 space-y-2">
                        <p className="text-[10px] uppercase font-bold text-stone-500">Piezas solicitadas a tu taller:</p>
                        {order.items.map((it, idx) => (
                          <div key={idx} className="flex justify-between items-center text-xs">
                            <span className="font-bold text-stone-800">• {it.name} (x{it.qty})</span>
                            <span className="font-bold text-[#5C1D24]">${(it.price * it.qty).toLocaleString()} COP</span>
                          </div>
                        ))}
                      </div>

                      {/* Progreso de Producción */}
                      <div className="p-3 bg-[#FDFBF7] rounded-xl border border-stone-200 space-y-2 flex flex-col justify-center">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-bold text-stone-700">Progreso de tejido:</span>
                          <span className="font-black text-[#5C1D24]">{order.progress}%</span>
                        </div>
                        <div className="w-full h-2.5 bg-stone-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#5C1D24] transition-all duration-500 rounded-full"
                            style={{ width: `${order.progress}%` }}
                          ></div>
                        </div>
                      </div>

                    </div>

                  </div>
                ))}
              </div>

            </div>
          )}

        </main>
      </div>

      {/* ========================================== */}
      {/* MODALES & VENTANAS EMERGENTES */}
      {/* ========================================== */}

      {/* MODAL 1: PERFIL DE LA TEJEDORA */}
      {isProfileModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <h3 className="font-bold text-stone-800 text-sm flex items-center gap-2">
                <User className="w-4 h-4 text-[#5C1D24]" />
                <span>Perfil de la Tejedora</span>
              </h3>
              <button onClick={() => setIsProfileModalOpen(false)} className="text-stone-400 hover:text-stone-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveProfile} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-stone-700 mb-1">Nombre completo</label>
                <input
                  type="text"
                  value={editProfile.name}
                  onChange={(e) => setEditProfile({ ...editProfile, name: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl"
                  required
                />
              </div>

              <div>
                <label className="block font-bold text-stone-700 mb-1">Ranchería / Comunidad</label>
                <input
                  type="text"
                  value={editProfile.rancheria}
                  onChange={(e) => setEditProfile({ ...editProfile, rancheria: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl"
                  required
                />
              </div>

              <div>
                <label className="block font-bold text-stone-700 mb-1">Teléfono de contacto</label>
                <input
                  type="text"
                  value={editProfile.phone}
                  onChange={(e) => setEditProfile({ ...editProfile, phone: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-bold text-stone-700 mb-1">Especialidad / Técnica principal</label>
                <input
                  type="text"
                  value={editProfile.specialty}
                  onChange={(e) => setEditProfile({ ...editProfile, specialty: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsProfileModalOpen(false)}
                  className="px-4 py-2 border border-stone-300 rounded-xl font-semibold text-stone-700 hover:bg-stone-100"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-[#5C1D24] text-white font-bold rounded-xl shadow-md"
                >
                  Guardar Perfil
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: REGISTRAR NUEVO TEJIDO (ENTRA EN "Pendiente de revisión") */}
      {isAddProductModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4 my-8">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <div>
                <h3 className="font-bold text-stone-800 text-sm flex items-center gap-2">
                  <Plus className="w-4 h-4 text-[#5C1D24]" />
                  <span>Registrar Nuevo Tejido</span>
                </h3>
                <p className="text-[11px] text-stone-500">El producto se guardará con estado "Pendiente de revisión"</p>
              </div>
              <button onClick={() => setIsAddProductModalOpen(false)} className="text-stone-400 hover:text-stone-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateProduct} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-stone-700 mb-1">Nombre de la pieza *</label>
                <input
                  type="text"
                  placeholder="Ej: Mochila Susu Kanaas Sol..."
                  value={newProduct.name}
                  onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-stone-700 mb-1">Categoría</label>
                  <select
                    value={newProduct.category}
                    onChange={(e) => setNewProduct({ ...newProduct, category: e.target.value })}
                    className="w-full p-2.5 bg-white border border-stone-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  >
                    {CATEGORIES.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-stone-700 mb-1">Precio sugerido (COP) *</label>
                  <input
                    type="number"
                    placeholder="280000"
                    value={newProduct.price}
                    onChange={(e) => setNewProduct({ ...newProduct, price: e.target.value })}
                    className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-stone-700 mb-1">Cantidad inicial (Stock)</label>
                  <input
                    type="number"
                    min="1"
                    value={newProduct.stock}
                    onChange={(e) => setNewProduct({ ...newProduct, stock: e.target.value })}
                    className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl"
                  />
                </div>

                <div>
                  <label className="block font-bold text-stone-700 mb-1">Icono / Representación</label>
                  <select
                    value={newProduct.image}
                    onChange={(e) => setNewProduct({ ...newProduct, image: e.target.value })}
                    className="w-full p-2.5 bg-white border border-stone-300 rounded-xl"
                  >
                    <option value="🎒">🎒 Mochila Susu</option>
                    <option value="🛋️">🛋️ Chinchorro / Hamaca</option>
                    <option value="👒">👒 Sombrero Kumu</option>
                    <option value="📿">📿 Bisutería Kanaas</option>
                    <option value="👗">👗 Manta / Vestimenta</option>
                    <option value="𑁍">𑁍 Accesorio</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-bold text-stone-700 mb-1">Técnica de tejido y Hebras</label>
                <input
                  type="text"
                  placeholder="Ej: Una sola hebra, telar de cintura, etc."
                  value={newProduct.technique}
                  onChange={(e) => setNewProduct({ ...newProduct, technique: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-bold text-stone-700 mb-1">Colores principales de los hilos</label>
                <input
                  type="text"
                  placeholder="Ej: Borgoña, Marfil, Verde Esmeralda"
                  value={newProduct.colors}
                  onChange={(e) => setNewProduct({ ...newProduct, colors: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-bold text-stone-700 mb-1">Descripción del simbolismo Kanaas</label>
                <textarea
                  rows={2}
                  placeholder="Explica el significado del patrón y la historia del tejido..."
                  value={newProduct.description}
                  onChange={(e) => setNewProduct({ ...newProduct, description: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl"
                ></textarea>
              </div>

              {/* Upload Simulator */}
              <div>
                <label className="block font-bold text-stone-700 mb-1">Cargar fotografías de la pieza</label>
                <div className="border-2 border-dashed border-stone-300 rounded-xl p-4 text-center hover:border-[#5C1D24] transition-colors cursor-pointer bg-stone-50">
                  <Upload className="w-5 h-5 text-stone-400 mx-auto mb-1" />
                  <p className="text-[11px] font-semibold text-stone-600">Haz clic o arrastra fotos del tejido</p>
                  <p className="text-[10px] text-stone-400">Captura clara de la gasa y detalles (Simulado)</p>
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsAddProductModalOpen(false)}
                  className="px-4 py-2 border border-stone-300 rounded-xl font-semibold text-stone-700 hover:bg-stone-100"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-[#5C1D24] text-white font-bold rounded-xl shadow-md"
                >
                  Enviar a Revisión
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: EDITAR / CORREGIR PRODUCTO (RE-ENVÍA A "Pendiente de revisión") */}
      {isEditProductModalOpen && selectedProduct && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <div>
                <h3 className="font-bold text-stone-800 text-sm">Editar / Corregir Tejido</h3>
                <p className="text-[10px] text-amber-700 font-semibold">
                  Al guardar, se re-enviará como "Pendiente de revisión" al Admin.
                </p>
              </div>
              <button onClick={() => setIsEditProductModalOpen(false)} className="text-stone-400 hover:text-stone-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveProductCorrection} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold mb-1">Nombre</label>
                <input
                  type="text"
                  value={selectedProduct.name}
                  onChange={(e) => setSelectedProduct({ ...selectedProduct, name: e.target.value })}
                  className="w-full p-2.5 bg-stone-50 border border-stone-300 rounded-xl"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold mb-1">Precio (COP)</label>
                  <input
                    type="number"
                    value={selectedProduct.price}
                    onChange={(e) => setSelectedProduct({ ...selectedProduct, price: Number(e.target.value) })}
                    className="w-full p-2.5 bg-stone-50 border border-stone-300 rounded-xl"
                    required
                  />
                </div>

                <div>
                  <label className="block font-bold mb-1">Stock disponible</label>
                  <input
                    type="number"
                    value={selectedProduct.stock}
                    onChange={(e) => setSelectedProduct({ ...selectedProduct, stock: Number(e.target.value) })}
                    className="w-full p-2.5 bg-stone-50 border border-stone-300 rounded-xl"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold mb-1">Descripción y detalles</label>
                <textarea
                  rows={3}
                  value={selectedProduct.description}
                  onChange={(e) => setSelectedProduct({ ...selectedProduct, description: e.target.value })}
                  className="w-full p-2.5 bg-stone-50 border border-stone-300 rounded-xl"
                ></textarea>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button type="button" onClick={() => setIsEditProductModalOpen(false)} className="px-4 py-2 border rounded-xl font-semibold">
                  Cancelar
                </button>
                <button type="submit" className="px-5 py-2 bg-[#5C1D24] text-white font-bold rounded-xl shadow-md">
                  Re-enviar a Revisión
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: DETALLE Y SEGUIMIENTO DE PRODUCCIÓN EN PEDIDO */}
      {isOrderDetailModalOpen && selectedOrder && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <div>
                <h3 className="font-bold text-stone-800 text-base">Detalle de Avance del Pedido #{selectedOrder.id}</h3>
                <p className="text-xs text-stone-500">Cliente: {selectedOrder.customer}</p>
              </div>
              <button onClick={() => setIsOrderDetailModalOpen(false)} className="text-stone-400 hover:text-stone-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="p-3 bg-stone-50 rounded-2xl space-y-1">
                <p className="font-bold text-stone-700 text-[11px] uppercase">Piezas a elaborar en tu taller:</p>
                {selectedOrder.items.map((it, idx) => (
                  <div key={idx} className="flex justify-between font-semibold text-stone-800">
                    <span>{it.name} (x{it.qty})</span>
                    <span>${(it.price * it.qty).toLocaleString()} COP</span>
                  </div>
                ))}
              </div>

              {/* Steps Updater */}
              <div className="space-y-2">
                <p className="font-bold text-stone-800 text-[11px] uppercase">Actualizar etapa de tejido:</p>
                <p className="text-[10px] text-stone-500">Haz clic en el botón de la etapa que has completado:</p>

                <div className="space-y-2 pt-1">
                  {selectedOrder.history.map((step, idx) => (
                    <div key={idx} className={`p-3 rounded-xl border flex items-center justify-between ${
                      step.done ? 'bg-emerald-50 border-emerald-200' : 'bg-stone-50 border-stone-200'
                    }`}>
                      <div>
                        <p className={`font-bold ${step.done ? 'text-emerald-950' : 'text-stone-700'}`}>{step.step}</p>
                        <p className="text-[10px] text-stone-400">{step.date}</p>
                      </div>

                      <button
                        onClick={() => handleUpdateOrderProductionStep(selectedOrder.id, idx)}
                        className={`px-3 py-1 rounded-lg text-[10px] font-bold transition-all ${
                          step.done ? 'bg-emerald-600 text-white' : 'bg-[#5C1D24] text-white hover:bg-[#4A121A]'
                        }`}
                      >
                        {step.done ? '✓ Completado' : 'Marcar Listo'}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 5: KARDEX MOVIMIENTO INVENTARIO */}
      {isKardexModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <h3 className="font-bold text-stone-800 text-sm">Registrar Movimiento en Stock</h3>
              <button onClick={() => setIsKardexModalOpen(false)} className="text-stone-400 hover:text-stone-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddKardexMovement} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold mb-1">Producto tejido</label>
                <select
                  value={newMovement.productName}
                  onChange={(e) => setNewMovement({ ...newMovement, productName: e.target.value })}
                  className="w-full p-2.5 bg-white border border-stone-300 rounded-xl"
                >
                  {products.map(p => (
                    <option key={p.id} value={p.name}>{p.name} (Stock: {p.stock})</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold mb-1">Tipo Movimiento</label>
                  <select
                    value={newMovement.type}
                    onChange={(e) => setNewMovement({ ...newMovement, type: e.target.value })}
                    className="w-full p-2.5 bg-white border border-stone-300 rounded-xl"
                  >
                    <option value="Entrada">Entrada (+)</option>
                    <option value="Salida">Salida (-)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold mb-1">Cantidad</label>
                  <input
                    type="number"
                    min="1"
                    value={newMovement.quantity}
                    onChange={(e) => setNewMovement({ ...newMovement, quantity: e.target.value })}
                    className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold mb-1">Motivo / Taller originario</label>
                <input
                  type="text"
                  placeholder="Ej: Entrega de lote desde Mayapo..."
                  value={newMovement.reason}
                  onChange={(e) => setNewMovement({ ...newMovement, reason: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl"
                />
              </div>

              <button type="submit" className="w-full py-2.5 bg-[#5C1D24] text-white font-bold rounded-xl">
                Guardar Movimiento
              </button>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 6: CERRAR SESIÓN */}
      {isLogoutModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4 text-center">
            <div className="w-12 h-12 rounded-full bg-rose-100 text-[#5C1D24] flex items-center justify-center mx-auto">
              <LogOut className="w-6 h-6" />
            </div>

            <div>
              <h3 className="font-extrabold text-stone-800 text-base">¿Cerrar sesión de tejedora?</h3>
              <p className="text-xs text-stone-500 mt-1">
                Tendrás que identificarte nuevamente para registrar artesanías y consultar tus pedidos asignados.
              </p>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={() => setIsLogoutModalOpen(false)}
                className="flex-1 py-2.5 border border-stone-300 rounded-xl text-xs font-semibold text-stone-700 hover:bg-stone-100"
              >
                Cancelar
              </button>

              <button
                onClick={() => {
                  setIsLogoutModalOpen(false);
                  showToast('Sesión de tejedora cerrada.', 'info');
                }}
                className="flex-1 py-2.5 bg-[#5C1D24] hover:bg-[#4A121A] text-white rounded-xl text-xs font-bold transition-colors shadow-md"
              >
                Sí, Salir
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}