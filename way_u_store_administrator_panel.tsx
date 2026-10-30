import React, { useState, useMemo } from 'react';
import {
  LayoutDashboard,
  ShoppingBag,
  ShoppingCart,
  Boxes,
  Search,
  Filter,
  Plus,
  Edit,
  Trash2,
  CheckCircle2,
  XCircle,
  RotateCcw,
  AlertTriangle,
  ChevronRight,
  Eye,
  LogOut,
  Bell,
  ArrowUpRight,
  TrendingUp,
  Package,
  Clock,
  Check,
  X,
  FileText,
  DollarSign,
  Calendar,
  UserCheck,
  Upload,
  ArrowDownRight,
  ArrowUp,
  ArrowDown,
  Info,
  Sparkles,
  Layers,
  ChevronDown,
  CheckSquare
} from 'lucide-react';

// ==========================================
// MOCK DATA & TYPES
// ==========================================

const INITIAL_CATEGORIES = [
  'Mochilas (Susu)',
  'Hamacas y Chinchorros',
  'Sombreros Kumu',
  'Bisutería Kanaas',
  'Calzado & Accesorios'
];

const WEAVERS = [
  { id: 'W-01', name: 'Marta Uriana', rancheria: 'Mayapo' },
  { id: 'W-02', name: 'Aura Barros', rancheria: 'Cabo de la Vela' },
  { id: 'W-03', name: 'Rosa Pushaina', rancheria: 'Manaure' },
  { id: 'W-04', name: 'Sonia Epinayú', rancheria: 'Uribia Central' },
  { id: 'W-05', name: 'Luz Marina Jayaliyu', rancheria: 'Maicao' }
];

const INITIAL_PRODUCTS = [
  {
    id: 'PRD-101',
    name: 'Mochila Susu Kanaas Sol Naciente',
    category: 'Mochilas (Susu)',
    price: 280000,
    stock: 12,
    artisan: 'Marta Uriana',
    status: 'Aprobado',
    image: '🎒',
    description: 'Tejida a una sola hebra con simbología Kanaas geométrica tradicional.',
    feedback: ''
  },
  {
    id: 'PRD-102',
    name: 'Chinchorro Anatas Elegante Terracota',
    category: 'Hamacas y Chinchorros',
    price: 1200000,
    stock: 2,
    artisan: 'Aura Barros',
    status: 'Aprobado',
    image: '🛋️',
    description: 'Chinchorro de cabecera tejido doble hebra con flecos elaborados.',
    feedback: ''
  },
  {
    id: 'PRD-103',
    name: 'Sombrero Kumu Mawisa Guajiro',
    category: 'Sombreros Kumu',
    price: 110000,
    stock: 25,
    artisan: 'Sonia Epinayú',
    status: 'Aprobado',
    image: '👒',
    description: 'Sombrero de palma mawisa tejido a mano con cinta de color borgoña.',
    feedback: ''
  },
  {
    id: 'PRD-104',
    name: 'Pulsera Kanaas Relámpago',
    category: 'Bisutería Kanaas',
    price: 35000,
    stock: 3,
    artisan: 'Rosa Pushaina',
    status: 'Pendiente',
    image: '📿',
    description: 'Accesorios en mostacilla con patrones icónicos del desierto.',
    feedback: ''
  },
  {
    id: 'PRD-105',
    name: 'Mochila Mini Susu Palabrero',
    category: 'Mochilas (Susu)',
    price: 190000,
    stock: 0,
    artisan: 'Marta Uriana',
    status: 'Devuelto',
    image: '👛',
    description: 'Diseño compacto ideal para uso diario.',
    feedback: 'Falta agregar fotografías detalladas de la correa paleteada.'
  },
  {
    id: 'PRD-106',
    name: 'Clutch Tejido Wayúu Atardecer',
    category: 'Calzado & Accesorios',
    price: 145000,
    stock: 8,
    artisan: 'Luz Marina Jayaliyu',
    status: 'Pendiente',
    image: '👝',
    description: 'Bolso de mano con cremallera y forro de algodón orgánico.',
    feedback: ''
  }
];

const INITIAL_ORDERS = [
  {
    id: 'ORD-9821',
    customer: 'Kenia Iguarán',
    email: 'kenia.i@gmail.com',
    date: '2026-10-29',
    items: [
      { name: 'Mochila Susu Kanaas Sol Naciente', qty: 1, price: 280000 },
      { name: 'Pulsera Kanaas Relámpago', qty: 2, price: 35000 }
    ],
    total: 350000,
    status: 'En tejido/Elaboración',
    artisan: 'Marta Uriana',
    history: [
      { step: 'Pedido recibido', date: '2026-10-29 08:30 AM', done: true },
      { step: 'Asignación de hilos y tejedora', date: '2026-10-29 10:15 AM', done: true },
      { step: 'En proceso de tejido', date: '2026-10-29 02:00 PM', done: true },
      { step: 'Control de calidad', date: 'Pendiente', done: false },
      { step: 'Despacho y entrega', date: 'Pendiente', done: false }
    ]
  },
  {
    id: 'ORD-9820',
    customer: 'Juan Gómez',
    email: 'jmgomez@empresa.com',
    date: '2026-10-28',
    items: [{ name: 'Chinchorro Anatas Elegante Terracota', qty: 1, price: 1200000 }],
    total: 1200000,
    status: 'Enviado',
    artisan: 'Aura Barros',
    history: [
      { step: 'Pedido recibido', date: '2026-10-28 09:00 AM', done: true },
      { step: 'Asignación de hilos y tejedora', date: '2026-10-28 11:00 AM', done: true },
      { step: 'En proceso de tejido', date: '2026-10-28 04:00 PM', done: true },
      { step: 'Control de calidad', date: '2026-10-29 09:30 AM', done: true },
      { step: 'Despacho y entrega', date: '2026-10-29 03:20 PM', done: true }
    ]
  },
  {
    id: 'ORD-9819',
    customer: 'Artesanías del Norte Ltd',
    email: 'contacto@artesaniasnorte.co',
    date: '2026-10-25',
    items: [{ name: 'Sombrero Kumu Mawisa Guajiro', qty: 10, price: 110000 }],
    total: 1100000,
    status: 'Entregado',
    artisan: 'Sonia Epinayú',
    history: [
      { step: 'Pedido recibido', date: '2026-10-25 10:00 AM', done: true },
      { step: 'Asignación de hilos y tejedora', date: '2026-10-25 11:30 AM', done: true },
      { step: 'En proceso de tejido', date: '2026-10-26 09:00 AM', done: true },
      { step: 'Control de calidad', date: '2026-10-27 02:00 PM', done: true },
      { step: 'Despacho y entrega', date: '2026-10-28 11:00 AM', done: true }
    ]
  },
  {
    id: 'ORD-9818',
    customer: 'María Fernanda Ruiz',
    email: 'mf.ruiz@hotmail.com',
    date: '2026-10-24',
    items: [{ name: 'Mochila Mini Susu Palabrero', qty: 1, price: 190000 }],
    total: 190000,
    status: 'Pendiente',
    artisan: 'Marta Uriana',
    history: [
      { step: 'Pedido recibido', date: '2026-10-24 04:15 PM', done: true },
      { step: 'Asignación de hilos y tejedora', date: 'Pendiente', done: false },
      { step: 'En proceso de tejido', date: 'Pendiente', done: false },
      { step: 'Control de calidad', date: 'Pendiente', done: false },
      { step: 'Despacho y entrega', date: 'Pendiente', done: false }
    ]
  }
];

const INITIAL_MOVEMENTS = [
  { id: 'MOV-501', product: 'Mochila Susu Kanaas Sol Naciente', type: 'Entrada', quantity: 5, date: '2026-10-30 08:30 AM', reason: 'Recepción taller Mayapo' },
  { id: 'MOV-502', product: 'Pulsera Kanaas Relámpago', type: 'Salida', quantity: 2, date: '2026-10-29 02:15 PM', reason: 'Venta Directa #ORD-9821' },
  { id: 'MOV-503', product: 'Sombrero Kumu Mawisa Guajiro', type: 'Entrada', quantity: 10, date: '2026-10-28 11:00 AM', reason: 'Reabastecimiento Uribia' },
  { id: 'MOV-504', product: 'Chinchorro Anatas Elegante Terracota', type: 'Salida', quantity: 1, date: '2026-10-28 09:45 AM', reason: 'Despacho #ORD-9820' }
];

const INITIAL_SALES = [
  { id: 'VTA-4091', date: '2026-10-30', customer: 'Carlos Mendoza', product: 'Mochila Susu Kanaas', amount: 280000, paymentMethod: 'Transferencia Wompi' },
  { id: 'VTA-4090', date: '2026-10-29', customer: 'Lucía Fernández', product: 'Sombrero Kumu Mawisa', amount: 110000, paymentMethod: 'Efectivo Punto Físico' },
  { id: 'VTA-4089', date: '2026-10-28', customer: 'Juan Gómez', product: 'Chinchorro Anatas', amount: 1200000, paymentMethod: 'Tarjeta de Crédito' },
  { id: 'VTA-4088', date: '2026-10-25', customer: 'Artesanías del Norte', product: 'Lote Sombreros (x10)', amount: 1100000, paymentMethod: 'Transferencia Bancaria' }
];

const RECENT_ACTIVITIES = [
  { id: 1, user: 'Marta Uriana', action: 'registró una nueva artesanía:', target: 'Mochila Susu Kanaas', time: 'Hace 25 min' },
  { id: 2, user: 'Ana García', action: 'cambió el estado del pedido #ORD-9821 a:', target: 'En tejido/Elaboración', time: 'Hace 1 hora' },
  { id: 3, user: 'Aura Barros', action: 'envió para revisión el producto:', target: 'Chinchorro Anatas Terracota', time: 'Hace 3 horas' },
  { id: 4, user: 'Sistema', action: 'generó alerta de stock bajo para:', target: 'Pulsera Kanaas Relámpago (3 und)', time: 'Hace 5 horas' }
];

// ==========================================
// MAIN APP COMPONENT
// ==========================================

export default function App() {
  // Navigation State
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard', 'catalog', 'orders', 'inventory'

  // Data States
  const [products, setProducts] = useState(INITIAL_PRODUCTS);
  const [categories, setCategories] = useState(INITIAL_CATEGORIES);
  const [orders, setOrders] = useState(INITIAL_ORDERS);
  const [movements, setMovements] = useState(INITIAL_MOVEMENTS);
  const [sales, setSales] = useState(INITIAL_SALES);

  // Modal Controls
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);
  const [isAddProductModalOpen, setIsAddProductModalOpen] = useState(false);
  const [isEditProductModalOpen, setIsEditProductModalOpen] = useState(false);
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);
  const [isOrderDetailModalOpen, setIsOrderDetailModalOpen] = useState(false);
  const [isKardexModalOpen, setIsKardexModalOpen] = useState(false);
  const [isReturnModalOpen, setIsReturnModalOpen] = useState(false);

  // Selected Entities
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [returnObservations, setReturnObservations] = useState('');

  // Toast Notification
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Catalog Filters
  const [catalogSearch, setCatalogSearch] = useState('');
  const [catalogCategoryFilter, setCatalogCategoryFilter] = useState('all');
  const [catalogStatusFilter, setCatalogStatusFilter] = useState('all');

  // Orders Filters
  const [orderSearch, setOrderSearch] = useState('');
  const [orderStatusFilter, setOrderStatusFilter] = useState('all');

  // New Product Form State
  const [newProduct, setNewProduct] = useState({
    name: '',
    category: INITIAL_CATEGORIES[0],
    price: '',
    stock: '',
    artisan: WEAVERS[0].name,
    description: '',
    image: '🎒'
  });

  // New Movement Form State
  const [newMovement, setNewMovement] = useState({
    productName: INITIAL_PRODUCTS[0].name,
    type: 'Entrada',
    quantity: 1,
    reason: ''
  });

  // New Category State
  const [newCategoryName, setNewCategoryName] = useState('');

  // Sales Inner Tab & Date Filter
  const [inventorySubTab, setInventorySubTab] = useState('inventory'); // 'inventory' | 'sales'
  const [salesDateFilter, setSalesDateFilter] = useState('month');

  // ==========================================
  // COMPUTED / FILTERED DATA
  // ==========================================

  const filteredProducts = useMemo(() => {
    return products.filter(p => {
      const matchesSearch = p.name.toLowerCase().includes(catalogSearch.toLowerCase()) ||
                            p.artisan.toLowerCase().includes(catalogSearch.toLowerCase());
      const matchesCategory = catalogCategoryFilter === 'all' || p.category === catalogCategoryFilter;
      const matchesStatus = catalogStatusFilter === 'all' || p.status === catalogStatusFilter;
      return matchesSearch && matchesCategory && matchesStatus;
    });
  }, [products, catalogSearch, catalogCategoryFilter, catalogStatusFilter]);

  const filteredOrders = useMemo(() => {
    return orders.filter(o => {
      const matchesSearch = o.id.toLowerCase().includes(orderSearch.toLowerCase()) ||
                            o.customer.toLowerCase().includes(orderSearch.toLowerCase());
      const matchesStatus = orderStatusFilter === 'all' || o.status === orderStatusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [orders, orderSearch, orderStatusFilter]);

  const pendingApprovals = useMemo(() => {
    return products.filter(p => p.status === 'Pendiente');
  }, [products]);

  const lowStockProducts = useMemo(() => {
    return products.filter(p => p.stock < 5);
  }, [products]);

  const totalSalesAmount = useMemo(() => {
    return sales.reduce((acc, curr) => acc + curr.amount, 0);
  }, [sales]);

  // ==========================================
  // HANDLERS
  // ==========================================

  const handleCreateProduct = (e) => {
    e.preventDefault();
    if (!newProduct.name || !newProduct.price) return;

    const created = {
      id: `PRD-${Math.floor(100 + Math.random() * 900)}`,
      name: newProduct.name,
      category: newProduct.category,
      price: Number(newProduct.price),
      stock: Number(newProduct.stock) || 0,
      artisan: newProduct.artisan,
      status: 'Aprobado',
      image: newProduct.image || '🎒',
      description: newProduct.description,
      feedback: ''
    };

    setProducts([created, ...products]);
    setIsAddProductModalOpen(false);
    setNewProduct({
      name: '',
      category: categories[0],
      price: '',
      stock: '',
      artisan: WEAVERS[0].name,
      description: '',
      image: '🎒'
    });
    showToast(`Producto "${created.name}" registrado con éxito.`);
  };

  const handleEditProduct = (e) => {
    e.preventDefault();
    if (!selectedProduct) return;

    setProducts(products.map(p => p.id === selectedProduct.id ? selectedProduct : p));
    setIsEditProductModalOpen(false);
    showToast(`Producto "${selectedProduct.name}" actualizado.`);
  };

  const handleDeleteProduct = (id) => {
    setProducts(products.filter(p => p.id !== id));
    showToast('Producto eliminado del catálogo.', 'info');
  };

  const handleApproveProduct = (id) => {
    setProducts(products.map(p => p.id === id ? { ...p, status: 'Aprobado', feedback: '' } : p));
    showToast('Publicación aprobada y visible en catálogo público.');
  };

  const handleRejectProduct = (id) => {
    setProducts(products.map(p => p.id === id ? { ...p, status: 'Rechazado' } : p));
    showToast('Producto rechazado.', 'info');
  };

  const handleConfirmReturnForCorrection = (e) => {
    e.preventDefault();
    if (!selectedProduct) return;

    setProducts(products.map(p => p.id === selectedProduct.id ? { ...p, status: 'Devuelto', feedback: returnObservations } : p));
    setIsReturnModalOpen(false);
    setReturnObservations('');
    showToast(`Producto devuelto a ${selectedProduct.artisan} para correcciones.`, 'info');
  };

  const handleAddCategory = (e) => {
    e.preventDefault();
    if (!newCategoryName.trim()) return;

    if (!categories.includes(newCategoryName)) {
      setCategories([...categories, newCategoryName.trim()]);
      showToast(`Nueva categoría "${newCategoryName}" agregada.`);
      setNewCategoryName('');
      setIsCategoryModalOpen(false);
    } else {
      showToast('Esta categoría ya existe.', 'info');
    }
  };

  const handleUpdateOrderStatus = (orderId, newStatus) => {
    setOrders(orders.map(o => {
      if (o.id === orderId) {
        const updatedHistory = o.history.map((h, index) => {
          if (newStatus === 'En tejido/Elaboración' && index <= 2) return { ...h, done: true, date: h.done ? h.date : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
          if (newStatus === 'Enviado' && index <= 4) return { ...h, done: true, date: h.done ? h.date : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
          if (newStatus === 'Entregado') return { ...h, done: true, date: h.done ? h.date : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
          return h;
        });
        return { ...o, status: newStatus, history: updatedHistory };
      }
      return o;
    }));

    if (selectedOrder && selectedOrder.id === orderId) {
      setSelectedOrder(prev => ({ ...prev, status: newStatus }));
    }

    showToast(`Estado del pedido ${orderId} actualizado a "${newStatus}".`);
  };

  const handleAddKardexMovement = (e) => {
    e.preventDefault();

    const targetProduct = products.find(p => p.name === newMovement.productName);
    const qty = Number(newMovement.quantity);

    if (newMovement.type === 'Salida' && targetProduct && targetProduct.stock < qty) {
      showToast('No hay suficiente stock disponible para esta salida.', 'info');
      return;
    }

    // Update Product Stock
    setProducts(products.map(p => {
      if (p.name === newMovement.productName) {
        const nextStock = newMovement.type === 'Entrada' ? p.stock + qty : p.stock - qty;
        return { ...p, stock: Math.max(0, nextStock) };
      }
      return p;
    }));

    // Add Movement Entry
    const movementEntry = {
      id: `MOV-${Math.floor(500 + Math.random() * 500)}`,
      product: newMovement.productName,
      type: newMovement.type,
      quantity: qty,
      date: new Date().toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }),
      reason: newMovement.reason || (newMovement.type === 'Entrada' ? 'Reabastecimiento' : 'Ajuste de inventario')
    };

    setMovements([movementEntry, ...movements]);
    setIsKardexModalOpen(false);
    setNewMovement({
      productName: products[0]?.name || '',
      type: 'Entrada',
      quantity: 1,
      reason: ''
    });
    showToast(`Movimiento registrado: ${newMovement.type} de ${qty} unidades.`);
  };

  return (
    <div className="flex h-screen bg-[#FDFBF7] text-[#3D1E16] font-sans overflow-hidden selection:bg-[#5C1D24] selection:text-white">

      {/* TOAST NOTIFICATION */}
      {toast && (
        <div className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-5 py-3.5 rounded-xl shadow-2xl text-xs font-semibold transition-all duration-300 animate-slide-in ${
          toast.type === 'info' ? 'bg-[#3D1E16] text-amber-100 border border-amber-800' : 'bg-[#5C1D24] text-white border border-[#4A121A]'
        }`}>
          {toast.type === 'info' ? <Info className="w-5 h-5 text-amber-300 shrink-0" /> : <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* SIDEBAR NAVIGATION (STRICTLY 4 MAIN OPTIONS) */}
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
              <p className="text-[10px] text-rose-200/90 tracking-wider uppercase font-semibold">Administración de Tienda</p>
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

            {/* 2. Catálogo y publicaciones */}
            <button
              onClick={() => setActiveTab('catalog')}
              className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all duration-200 ${
                activeTab === 'catalog'
                  ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-md transform translate-x-1'
                  : 'text-rose-100 hover:bg-white/10'
              }`}
            >
              <ShoppingBag className={`w-4 h-4 ${activeTab === 'catalog' ? 'text-[#5C1D24]' : 'text-rose-200'}`} />
              <span>Catálogo y publicaciones</span>
            </button>

            {/* 3. Pedidos */}
            <button
              onClick={() => setActiveTab('orders')}
              className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all duration-200 ${
                activeTab === 'orders'
                  ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-md transform translate-x-1'
                  : 'text-rose-100 hover:bg-white/10'
              }`}
            >
              <ShoppingCart className={`w-4 h-4 ${activeTab === 'orders' ? 'text-[#5C1D24]' : 'text-rose-200'}`} />
              <span>Pedidos</span>
            </button>

            {/* 4. Inventario y ventas */}
            <button
              onClick={() => setActiveTab('inventory')}
              className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all duration-200 ${
                activeTab === 'inventory'
                  ? 'bg-[#FDFBF7] text-[#5C1D24] font-bold shadow-md transform translate-x-1'
                  : 'text-rose-100 hover:bg-white/10'
              }`}
            >
              <Boxes className={`w-4 h-4 ${activeTab === 'inventory' ? 'text-[#5C1D24]' : 'text-rose-200'}`} />
              <span>Inventario y ventas</span>
            </button>
          </nav>

          {/* User Profile Badge in Sidebar Bottom */}
          <div className="p-4 m-3 rounded-2xl bg-black/20 border border-white/10 space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-[#FDFBF7] text-[#5C1D24] flex items-center justify-center font-bold text-xs shadow-md shrink-0">
                AG
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-white truncate">Ana García</p>
                <p className="text-[10px] text-rose-200/80 truncate">Administrador de tienda</p>
              </div>
            </div>

            <button
              onClick={() => setIsLogoutModalOpen(true)}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-white/10 hover:bg-rose-900/60 text-white text-xs font-semibold transition-colors border border-white/10"
            >
              <LogOut className="w-3.5 h-3.5 text-rose-200" />
              <span>Cerrar sesión</span>
            </button>
          </div>

          {/* Footer Pattern */}
          <div className="p-3 text-center border-t border-rose-900/40 bg-black/10">
            <p className="text-[10px] text-rose-300/60 font-mono">Wayúu Store Admin v2.5</p>
          </div>

        </div>
      </aside>

      {/* WORKSPACE BODY */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        
        {/* TOP HEADER */}
        <header className="bg-white border-b border-[#E2D9D5] px-8 py-4 flex items-center justify-between shrink-0 shadow-sm z-10">
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold uppercase tracking-wider text-[#5C1D24] bg-rose-50 px-3 py-1 rounded-lg border border-rose-200">
              Módulo Comercial
            </span>
            <span className="text-xs text-stone-300">/</span>
            <span className="text-xs font-medium text-stone-600 capitalize">
              {activeTab === 'dashboard' && 'Panel Principal'}
              {activeTab === 'catalog' && 'Catálogo y Publicaciones'}
              {activeTab === 'orders' && 'Gestión de Pedidos'}
              {activeTab === 'inventory' && 'Inventario y Ventas'}
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Django REST API: Conectado</span>
            </div>

            <button
              onClick={() => showToast('Notificaciones actualizadas.', 'info')}
              className="relative p-2 text-stone-600 hover:text-[#5C1D24] hover:bg-rose-50 rounded-full transition-colors"
            >
              <Bell className="w-5 h-5" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-600 rounded-full ring-2 ring-white"></span>
            </button>

            {/* Profile Dropdown Header */}
            <div className="flex items-center gap-3 pl-4 border-l border-stone-200">
              <div className="w-9 h-9 rounded-full bg-[#5C1D24] text-white flex items-center justify-center text-xs font-bold shadow-sm">
                AG
              </div>
              <div className="hidden sm:block text-left">
                <p className="text-xs font-bold text-stone-800 leading-tight">Ana García</p>
                <p className="text-[11px] text-stone-500">Administrador de tienda</p>
              </div>

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

        {/* MAIN SCROLLABLE VISTAS CONTENT */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-[#FDFBF7]">

          {/* ========================================== */}
          {/* VISTA 1: PANEL PRINCIPAL */}
          {/* ========================================== */}
          {activeTab === 'dashboard' && (
            <div className="max-w-7xl mx-auto space-y-6">
              
              {/* Banner de Bienvenida */}
              <div className="relative rounded-3xl bg-gradient-to-r from-[#5C1D24] via-[#7A2832] to-[#3D1E16] text-white p-6 md:p-8 shadow-xl overflow-hidden">
                <div className="absolute top-0 right-0 w-96 h-96 bg-white/5 rounded-full blur-3xl -mr-20 -mt-20"></div>
                <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-rose-200 text-xs font-medium border border-white/10">
                      <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                      <span>Comercio Justo Wayúu</span>
                    </div>
                    <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-[#FDFBF7]">
                      Bienvenida, Ana García
                    </h2>
                    <p className="text-xs md:text-sm text-rose-100/90 max-w-xl">
                      Supervisa la comercialización de artesanías, valida publicaciones de las tejedoras y gestiona los pedidos en tiempo real.
                    </p>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => setActiveTab('catalog')}
                      className="px-4 py-2.5 bg-[#FDFBF7] text-[#5C1D24] hover:bg-amber-50 rounded-xl text-xs font-bold transition-all shadow-md flex items-center gap-2"
                    >
                      <Plus className="w-4 h-4" />
                      <span>Nuevo Producto</span>
                    </button>
                    <button
                      onClick={() => setActiveTab('orders')}
                      className="px-4 py-2.5 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-semibold transition-all border border-white/20 flex items-center gap-2"
                    >
                      <ShoppingCart className="w-4 h-4" />
                      <span>Ver Pedidos ({orders.length})</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Grid de Métricas Principales */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
                
                {/* Total Ventas */}
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[11px] font-bold text-stone-500 uppercase">Total Ventas</span>
                    <div className="p-2 bg-rose-50 text-[#5C1D24] rounded-xl"><DollarSign className="w-4 h-4" /></div>
                  </div>
                  <p className="text-xl font-black text-[#3D1E16]">$12.460.000</p>
                  <p className="text-[11px] text-emerald-600 font-semibold flex items-center gap-1 mt-1">
                    <ArrowUpRight className="w-3.5 h-3.5" /> +19% este mes
                  </p>
                </div>

                {/* Pedidos Pendientes */}
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[11px] font-bold text-stone-500 uppercase">Pendientes</span>
                    <div className="p-2 bg-amber-50 text-amber-700 rounded-xl"><Clock className="w-4 h-4" /></div>
                  </div>
                  <p className="text-xl font-black text-stone-800">14</p>
                  <p className="text-[11px] text-amber-600 font-medium mt-1">Requiere asignación</p>
                </div>

                {/* Pedidos en Proceso */}
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[11px] font-bold text-stone-500 uppercase">En Proceso</span>
                    <div className="p-2 bg-blue-50 text-blue-700 rounded-xl"><Package className="w-4 h-4" /></div>
                  </div>
                  <p className="text-xl font-black text-stone-800">18</p>
                  <p className="text-[11px] text-blue-600 font-medium mt-1">En tejido activo</p>
                </div>

                {/* Productos Registrados */}
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[11px] font-bold text-stone-500 uppercase">Registrados</span>
                    <div className="p-2 bg-emerald-50 text-emerald-700 rounded-xl"><ShoppingBag className="w-4 h-4" /></div>
                  </div>
                  <p className="text-xl font-black text-stone-800">128</p>
                  <p className="text-[11px] text-emerald-600 font-medium mt-1">En catálogo activo</p>
                </div>

                {/* Productos por Aprobar */}
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[11px] font-bold text-stone-500 uppercase">Por Aprobar</span>
                    <div className="p-2 bg-purple-50 text-purple-700 rounded-xl"><UserCheck className="w-4 h-4" /></div>
                  </div>
                  <p className="text-xl font-black text-[#5C1D24]">{pendingApprovals.length}</p>
                  <p className="text-[11px] text-purple-600 font-medium mt-1">De tejedoras</p>
                </div>

                {/* Alertas Inventario */}
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[11px] font-bold text-stone-500 uppercase">Bajo Stock</span>
                    <div className="p-2 bg-rose-50 text-rose-700 rounded-xl"><AlertTriangle className="w-4 h-4" /></div>
                  </div>
                  <p className="text-xl font-black text-rose-700">{lowStockProducts.length}</p>
                  <p className="text-[11px] text-rose-600 font-medium mt-1">Alerta reposición</p>
                </div>

              </div>

              {/* Middle Section: Gráfico de Ventas & Accesos Rápidos */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                
                {/* Visual Sales Chart (Últimos 7 días) */}
                <div className="lg:col-span-8 bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-stone-800">Ventas de los últimos 7 días</h3>
                      <p className="text-xs text-stone-500">Ingresos comerciales acumulados en COP</p>
                    </div>
                    <span className="text-xs font-bold text-[#5C1D24] bg-rose-50 px-3 py-1 rounded-full border border-rose-200">
                      Promedio diario: $1.780.000
                    </span>
                  </div>

                  {/* SVG Line Chart Representation */}
                  <div className="h-56 w-full pt-4 relative">
                    <svg className="w-full h-full overflow-visible" viewBox="0 0 500 150">
                      <defs>
                        <linearGradient id="salesGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#5C1D24" stopOpacity="0.3" />
                          <stop offset="100%" stopColor="#5C1D24" stopOpacity="0.0" />
                        </linearGradient>
                      </defs>

                      {/* Grid Horizontal Lines */}
                      <line x1="0" y1="30" x2="500" y2="30" stroke="#F0EAE6" strokeDasharray="4" />
                      <line x1="0" y1="75" x2="500" y2="75" stroke="#F0EAE6" strokeDasharray="4" />
                      <line x1="0" y1="120" x2="500" y2="120" stroke="#F0EAE6" strokeDasharray="4" />

                      {/* Area Fill */}
                      <path
                        d="M 10 110 L 80 100 L 150 70 L 220 75 L 290 35 L 360 60 L 430 40 L 430 150 L 10 150 Z"
                        fill="url(#salesGrad)"
                      />

                      {/* Smooth Path Line */}
                      <path
                        d="M 10 110 L 80 100 L 150 70 L 220 75 L 290 35 L 360 60 L 430 40"
                        fill="none"
                        stroke="#5C1D24"
                        strokeWidth="3.5"
                        strokeLinecap="round"
                      />

                      {/* Data Dots */}
                      {[
                        { x: 10, y: 110, val: '$2.0M' },
                        { x: 80, y: 100, val: '$2.2M' },
                        { x: 150, y: 70, val: '$3.8M' },
                        { x: 220, y: 75, val: '$3.6M' },
                        { x: 290, y: 35, val: '$5.4M' },
                        { x: 360, y: 60, val: '$4.1M' },
                        { x: 430, y: 40, val: '$4.9M' }
                      ].map((pt, idx) => (
                        <g key={idx}>
                          <circle cx={pt.x} cy={pt.y} r="5" fill="#5C1D24" className="hover:r-7 transition-all cursor-pointer" />
                          <circle cx={pt.x} cy={pt.y} r="2" fill="#FFFFFF" />
                        </g>
                      ))}
                    </svg>

                    {/* X Axis Labels */}
                    <div className="flex justify-between text-[11px] font-semibold text-stone-500 mt-2 px-1">
                      <span>Lun</span>
                      <span>Mar</span>
                      <span>Mié</span>
                      <span>Jue</span>
                      <span>Vie</span>
                      <span>Sáb</span>
                      <span>Dom</span>
                    </div>
                  </div>
                </div>

                {/* Accesos Rápidos */}
                <div className="lg:col-span-4 bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm flex flex-col justify-between space-y-4">
                  <div>
                    <h3 className="text-sm font-bold text-stone-800">Accesos rápidos</h3>
                    <p className="text-xs text-stone-500 mt-0.5">Atajos para la gestión diaria</p>
                  </div>

                  <div className="space-y-2.5 flex-1">
                    <button
                      onClick={() => setActiveTab('catalog')}
                      className="w-full p-3.5 rounded-xl border border-stone-200 hover:border-[#5C1D24] bg-[#FDFBF7] hover:bg-rose-50 text-left transition-all flex items-center justify-between group"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-rose-100 text-[#5C1D24] rounded-lg">
                          <CheckSquare className="w-4 h-4" />
                        </div>
                        <div>
                          <p className="font-bold text-xs text-stone-800">Revisar productos</p>
                          <p className="text-[10px] text-stone-500">{pendingApprovals.length} solicitudes de tejedoras</p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-stone-400 group-hover:text-[#5C1D24] group-hover:translate-x-1 transition-all" />
                    </button>

                    <button
                      onClick={() => setActiveTab('orders')}
                      className="w-full p-3.5 rounded-xl border border-stone-200 hover:border-[#5C1D24] bg-[#FDFBF7] hover:bg-rose-50 text-left transition-all flex items-center justify-between group"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-amber-100 text-amber-800 rounded-lg">
                          <ShoppingCart className="w-4 h-4" />
                        </div>
                        <div>
                          <p className="font-bold text-xs text-stone-800">Gestionar pedidos</p>
                          <p className="text-[10px] text-stone-500">14 órdenes por procesar</p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-stone-400 group-hover:text-[#5C1D24] group-hover:translate-x-1 transition-all" />
                    </button>

                    <button
                      onClick={() => setActiveTab('inventory')}
                      className="w-full p-3.5 rounded-xl border border-stone-200 hover:border-[#5C1D24] bg-[#FDFBF7] hover:bg-rose-50 text-left transition-all flex items-center justify-between group"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-emerald-100 text-emerald-800 rounded-lg">
                          <Boxes className="w-4 h-4" />
                        </div>
                        <div>
                          <p className="font-bold text-xs text-stone-800">Gestionar inventario</p>
                          <p className="text-[10px] text-stone-500">Alertas y Kardex de stock</p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-stone-400 group-hover:text-[#5C1D24] group-hover:translate-x-1 transition-all" />
                    </button>
                  </div>
                </div>

              </div>

              {/* Feed de Actividad Reciente */}
              <div className="bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-[#5C1D24]" />
                    <h3 className="text-sm font-bold text-stone-800">Actividad reciente en el sistema</h3>
                  </div>
                  <span className="text-[11px] text-stone-500">Actualizado en tiempo real</span>
                </div>

                <div className="divide-y divide-stone-100 text-xs">
                  {RECENT_ACTIVITIES.map((act) => (
                    <div key={act.id} className="py-3 flex items-center justify-between hover:bg-stone-50/80 px-2 rounded-lg transition-colors">
                      <div className="flex items-center gap-3">
                        <span className="w-2 h-2 rounded-full bg-[#5C1D24]"></span>
                        <p className="text-stone-700">
                          <span className="font-bold text-stone-900">{act.user}</span> {act.action}{' '}
                          <span className="font-semibold text-[#5C1D24]">{act.target}</span>
                        </p>
                      </div>
                      <span className="text-[11px] text-stone-400 font-medium">{act.time}</span>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          )}

          {/* ========================================== */}
          {/* VISTA 2: CATÁLOGO Y PUBLICACIONES */}
          {/* ========================================== */}
          {activeTab === 'catalog' && (
            <div className="max-w-7xl mx-auto space-y-6">
              
              {/* Header section & Add Action */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Catálogo y Publicaciones</h2>
                  <p className="text-xs text-stone-600 mt-1">
                    Administra las piezas artesanales, aprueba registros de tejedoras y gestiona categorías.
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setIsCategoryModalOpen(true)}
                    className="px-4 py-2 border border-[#E2D9D5] bg-white hover:bg-stone-50 text-stone-700 rounded-xl text-xs font-semibold transition-colors shadow-sm flex items-center gap-2"
                  >
                    <Layers className="w-4 h-4 text-[#5C1D24]" />
                    <span>Categorías ({categories.length})</span>
                  </button>

                  <button
                    onClick={() => setIsAddProductModalOpen(true)}
                    className="px-4 py-2 bg-[#5C1D24] hover:bg-[#4A121A] text-white rounded-xl text-xs font-bold transition-colors shadow-sm flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    <span>+ Agregar Producto</span>
                  </button>
                </div>
              </div>

              {/* Filtros & Búsqueda */}
              <div className="bg-white p-4 rounded-2xl border border-[#E2D9D5] shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
                <div className="relative w-full md:w-80">
                  <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Buscar por nombre o tejedora..."
                    value={catalogSearch}
                    onChange={(e) => setCatalogSearch(e.target.value)}
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
                    value={catalogCategoryFilter}
                    onChange={(e) => setCatalogCategoryFilter(e.target.value)}
                    className="text-xs bg-white border border-stone-300 rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  >
                    <option value="all">Todas las categorías</option>
                    {categories.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>

                  {/* Selector Estado */}
                  <select
                    value={catalogStatusFilter}
                    onChange={(e) => setCatalogStatusFilter(e.target.value)}
                    className="text-xs bg-white border border-stone-300 rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  >
                    <option value="all">Todos los estados</option>
                    <option value="Aprobado">Aprobados</option>
                    <option value="Pendiente">Pendientes de aprobación</option>
                    <option value="Devuelto">Devueltos a corrección</option>
                    <option value="Rechazado">Rechazados</option>
                  </select>
                </div>
              </div>

              {/* SECCIÓN 1: REVISIÓN DE PRODUCTOS DE TEJEDORAS (SI HAY PENDIENTES) */}
              {pendingApprovals.length > 0 && (
                <div className="bg-amber-50/60 border border-amber-200 rounded-2xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <UserCheck className="w-5 h-5 text-amber-700" />
                      <h3 className="font-bold text-stone-800 text-xs uppercase tracking-wider">
                        Revisión de productos registrados por las tejedoras ({pendingApprovals.length})
                      </h3>
                    </div>
                    <span className="text-[11px] text-amber-800 font-semibold bg-amber-100 px-2.5 py-1 rounded-full">
                      Acción requerida
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {pendingApprovals.map(prod => (
                      <div key={prod.id} className="bg-white p-4 rounded-xl border border-amber-200 shadow-sm space-y-3 flex flex-col justify-between">
                        <div>
                          <div className="flex items-start justify-between gap-2">
                            <span className="text-3xl p-2 bg-amber-50 rounded-xl">{prod.image}</span>
                            <span className="text-[10px] font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded-full">
                              Pendiente
                            </span>
                          </div>
                          <h4 className="font-bold text-xs text-stone-800 mt-2">{prod.name}</h4>
                          <p className="text-[11px] text-stone-500 mt-0.5">Tejedora: <span className="font-semibold text-stone-700">{prod.artisan}</span></p>
                          <p className="text-[11px] text-stone-600 font-bold mt-1">${prod.price.toLocaleString()} COP | Stock: {prod.stock}</p>
                          <p className="text-[11px] text-stone-500 italic mt-1 line-clamp-2">"{prod.description}"</p>
                        </div>

                        {/* Botones de Aprobación/Devolución/Rechazo */}
                        <div className="pt-3 border-t border-stone-100 flex items-center gap-1.5">
                          <button
                            onClick={() => handleApproveProduct(prod.id)}
                            className="flex-1 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-[11px] font-bold flex items-center justify-center gap-1"
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Aprobar</span>
                          </button>

                          <button
                            onClick={() => { setSelectedProduct(prod); setIsReturnModalOpen(true); }}
                            className="flex-1 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-[11px] font-bold flex items-center justify-center gap-1"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                            <span>Devolver</span>
                          </button>

                          <button
                            onClick={() => handleRejectProduct(prod.id)}
                            className="p-1.5 text-rose-700 hover:bg-rose-50 border border-rose-200 rounded-lg text-[11px] font-bold"
                            title="Rechazar"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* SECCIÓN 2: LISTADO GENERAL DE PRODUCTOS (GRID/CARDS) */}
              <div className="bg-white rounded-2xl border border-[#E2D9D5] p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                  <h3 className="font-bold text-stone-800 text-sm">Catálogo General ({filteredProducts.length})</h3>
                  <span className="text-xs text-stone-500">Mostrando productos en inventario y tienda</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                  {filteredProducts.map(prod => (
                    <div key={prod.id} className="border border-[#E2D9D5] rounded-2xl p-4 bg-[#FDFBF7]/50 hover:bg-white transition-all hover:shadow-md flex flex-col justify-between space-y-3">
                      
                      <div>
                        {/* Top Badge & Photo */}
                        <div className="flex items-start justify-between">
                          <span className="text-4xl p-2.5 bg-white rounded-2xl border border-stone-200 shadow-sm">{prod.image}</span>
                          <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full border ${
                            prod.status === 'Aprobado' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                            prod.status === 'Pendiente' ? 'bg-amber-50 text-amber-800 border-amber-200' :
                            prod.status === 'Devuelto' ? 'bg-orange-50 text-orange-800 border-orange-200' :
                            'bg-rose-50 text-rose-800 border-rose-200'
                          }`}>
                            {prod.status}
                          </span>
                        </div>

                        <div className="mt-3 space-y-1">
                          <span className="text-[10px] font-bold text-[#5C1D24] uppercase tracking-wider">{prod.category}</span>
                          <h4 className="font-bold text-xs text-stone-800 leading-snug">{prod.name}</h4>
                          <p className="text-[11px] text-stone-500">Tejedora: <span className="font-medium text-stone-700">{prod.artisan}</span></p>
                        </div>

                        {prod.feedback && (
                          <div className="mt-2 p-2 bg-orange-50 border border-orange-200 rounded-lg text-[10px] text-orange-900">
                            <strong>Observación:</strong> {prod.feedback}
                          </div>
                        )}
                      </div>

                      <div className="pt-3 border-t border-stone-200/60 flex items-center justify-between">
                        <div>
                          <p className="text-xs font-black text-[#5C1D24]">${prod.price.toLocaleString()} COP</p>
                          <p className={`text-[10px] font-medium ${prod.stock < 5 ? 'text-rose-600 font-bold' : 'text-stone-500'}`}>
                            {prod.stock > 0 ? `${prod.stock} en stock` : 'Agotado'}
                          </p>
                        </div>

                        {/* Card Actions */}
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => { setSelectedProduct(prod); setIsEditProductModalOpen(true); }}
                            className="p-1.5 text-stone-600 hover:text-[#5C1D24] hover:bg-rose-50 rounded-lg border border-stone-200 transition-colors"
                            title="Editar"
                          >
                            <Edit className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => handleDeleteProduct(prod.id)}
                            className="p-1.5 text-stone-400 hover:text-rose-700 hover:bg-rose-50 rounded-lg border border-stone-200 transition-colors"
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

            </div>
          )}

          {/* ========================================== */}
          {/* VISTA 3: PEDIDOS */}
          {/* ========================================== */}
          {activeTab === 'orders' && (
            <div className="max-w-7xl mx-auto space-y-6">
              
              <div>
                <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Gestión de Pedidos</h2>
                <p className="text-xs text-stone-600 mt-1">
                  Monitorea las órdenes de compra, asigna el tejido a las artesanas y actualiza el flujo de despacho.
                </p>
              </div>

              {/* Filtros & Búsqueda */}
              <div className="bg-white p-4 rounded-2xl border border-[#E2D9D5] shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
                <div className="relative w-full md:w-80">
                  <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Buscar por ID de pedido o cliente..."
                    value={orderSearch}
                    onChange={(e) => setOrderSearch(e.target.value)}
                    className="w-full text-xs pl-9 pr-3 py-2 bg-[#FDFBF7] border border-stone-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  />
                </div>

                <div className="flex items-center gap-3 w-full md:w-auto">
                  <Filter className="w-3.5 h-3.5 text-stone-400" />
                  <span className="text-xs text-stone-600 font-medium">Estado:</span>
                  <select
                    value={orderStatusFilter}
                    onChange={(e) => setOrderStatusFilter(e.target.value)}
                    className="text-xs bg-white border border-stone-300 rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  >
                    <option value="all">Todos los estados</option>
                    <option value="Pendiente">Pendientes</option>
                    <option value="En tejido/Elaboración">En tejido/Elaboración</option>
                    <option value="Enviado">Enviados</option>
                    <option value="Entregado">Entregados</option>
                  </select>
                </div>
              </div>

              {/* Tabla Interactiva de Pedidos */}
              <div className="bg-white rounded-2xl border border-[#E2D9D5] shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-stone-50 border-b border-[#E2D9D5] font-semibold text-stone-600">
                        <th className="py-3.5 px-6">N° Pedido</th>
                        <th className="py-3.5 px-4">Cliente</th>
                        <th className="py-3.5 px-4">Fecha</th>
                        <th className="py-3.5 px-4">Productos</th>
                        <th className="py-3.5 px-4">Total</th>
                        <th className="py-3.5 px-4">Estado</th>
                        <th className="py-3.5 px-6 text-right">Acción</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-100">
                      {filteredOrders.map(order => (
                        <tr key={order.id} className="hover:bg-stone-50/80 transition-colors">
                          <td className="py-4 px-6 font-bold text-[#5C1D24]">{order.id}</td>
                          
                          <td className="py-4 px-4">
                            <p className="font-bold text-stone-800">{order.customer}</p>
                            <p className="text-[10px] text-stone-400">{order.email}</p>
                          </td>

                          <td className="py-4 px-4 text-stone-600 font-medium">{order.date}</td>

                          <td className="py-4 px-4 text-stone-700">
                            {order.items.map((it, idx) => (
                              <span key={idx} className="block text-[11px]">
                                • {it.name} <strong className="text-stone-900">(x{it.qty})</strong>
                              </span>
                            ))}
                          </td>

                          <td className="py-4 px-4 font-black text-stone-800">
                            ${order.total.toLocaleString()} COP
                          </td>

                          <td className="py-4 px-4">
                            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold border ${
                              order.status === 'Entregado' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                              order.status === 'Enviado' ? 'bg-blue-50 text-blue-800 border-blue-200' :
                              order.status === 'En tejido/Elaboración' ? 'bg-rose-50 text-[#5C1D24] border-rose-200' :
                              'bg-amber-50 text-amber-800 border-amber-200'
                            }`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${
                                order.status === 'Entregado' ? 'bg-emerald-500' :
                                order.status === 'Enviado' ? 'bg-blue-500' :
                                order.status === 'En tejido/Elaboración' ? 'bg-[#5C1D24]' :
                                'bg-amber-500'
                              }`}></span>
                              {order.status}
                            </span>
                          </td>

                          <td className="py-4 px-6 text-right">
                            <button
                              onClick={() => { setSelectedOrder(order); setIsOrderDetailModalOpen(true); }}
                              className="px-3 py-1.5 bg-stone-100 hover:bg-[#5C1D24] hover:text-white text-stone-700 rounded-lg text-xs font-bold transition-all border border-stone-200 inline-flex items-center gap-1.5"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              <span>Detalle</span>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}

          {/* ========================================== */}
          {/* VISTA 4: INVENTARIO Y VENTAS */}
          {/* ========================================== */}
          {activeTab === 'inventory' && (
            <div className="max-w-7xl mx-auto space-y-6">
              
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-bold text-[#3D1E16] tracking-tight">Inventario y Ventas</h2>
                  <p className="text-xs text-stone-600 mt-1">
                    Control de existencias, Kardex de entradas/salidas y registro comercial de ventas.
                  </p>
                </div>

                {/* SubTab Toggle Switcher */}
                <div className="bg-stone-200/80 p-1 rounded-2xl flex items-center shrink-0">
                  <button
                    onClick={() => setInventorySubTab('inventory')}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                      inventorySubTab === 'inventory' ? 'bg-white text-[#5C1D24] shadow-sm' : 'text-stone-600 hover:text-stone-900'
                    }`}
                  >
                    Inventario General
                  </button>
                  <button
                    onClick={() => setInventorySubTab('sales')}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                      inventorySubTab === 'sales' ? 'bg-white text-[#5C1D24] shadow-sm' : 'text-stone-600 hover:text-stone-900'
                    }`}
                  >
                    Registro de Ventas
                  </button>
                </div>
              </div>

              {/* SUBSECCIÓN 1: INVENTARIO GENERAL & KARDEX */}
              {inventorySubTab === 'inventory' && (
                <div className="space-y-6">
                  
                  {/* Top Action & Alert Banner */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-center justify-between">
                      <div>
                        <p className="text-xs font-bold text-stone-500 uppercase">Alertas Stock Bajo</p>
                        <p className="text-2xl font-black text-rose-700 mt-1">{lowStockProducts.length} artesanías</p>
                        <p className="text-[10px] text-stone-500">Stock menor a 5 unidades</p>
                      </div>
                      <div className="p-3 bg-rose-50 text-rose-700 rounded-xl"><AlertTriangle className="w-6 h-6" /></div>
                    </div>

                    <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-center justify-between">
                      <div>
                        <p className="text-xs font-bold text-stone-500 uppercase">Total Piezas Disponibles</p>
                        <p className="text-2xl font-black text-stone-800 mt-1">
                          {products.reduce((acc, p) => acc + p.stock, 0)} und.
                        </p>
                        <p className="text-[10px] text-emerald-600 font-medium">Distribuidas en talleres</p>
                      </div>
                      <div className="p-3 bg-emerald-50 text-emerald-700 rounded-xl"><Boxes className="w-6 h-6" /></div>
                    </div>

                    <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-center justify-between">
                      <div>
                        <p className="text-xs font-bold text-stone-500 uppercase">Movimientos Recientes</p>
                        <p className="text-2xl font-black text-stone-800 mt-1">{movements.length} registro(s)</p>
                        <button
                          onClick={() => setIsKardexModalOpen(true)}
                          className="text-[11px] font-bold text-[#5C1D24] underline hover:text-[#4A121A] mt-1 block"
                        >
                          + Registrar Entrada / Salida
                        </button>
                      </div>
                      <div className="p-3 bg-rose-50 text-[#5C1D24] rounded-xl"><RotateCcw className="w-6 h-6" /></div>
                    </div>
                  </div>

                  {/* Tabla de Existencias por Producto */}
                  <div className="bg-white rounded-2xl border border-[#E2D9D5] shadow-sm overflow-hidden space-y-3 p-6">
                    <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                      <h3 className="font-bold text-stone-800 text-sm">Existencias de Productos</h3>
                      <span className="text-xs text-stone-500">Control de stock de la tienda</span>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="bg-stone-50 border-b border-[#E2D9D5] font-semibold text-stone-600">
                            <th className="py-3 px-4">Producto</th>
                            <th className="py-3 px-4">Categoría</th>
                            <th className="py-3 px-4">Tejedora Responsable</th>
                            <th className="py-3 px-4">Stock</th>
                            <th className="py-3 px-4">Disponibilidad</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-stone-100">
                          {products.map(p => (
                            <tr key={p.id} className="hover:bg-stone-50 transition-colors">
                              <td className="py-3.5 px-4 font-bold text-stone-800 flex items-center gap-2">
                                <span className="text-xl p-1 bg-stone-100 rounded-lg">{p.image}</span>
                                <span>{p.name}</span>
                              </td>

                              <td className="py-3.5 px-4 text-stone-600">{p.category}</td>
                              <td className="py-3.5 px-4 text-stone-600 font-medium">{p.artisan}</td>

                              <td className="py-3.5 px-4 font-black text-stone-800">
                                {p.stock} unidades
                              </td>

                              <td className="py-3.5 px-4">
                                {p.stock === 0 ? (
                                  <span className="bg-rose-100 text-rose-800 font-bold px-2.5 py-1 rounded-full text-[10px]">
                                    Agotado
                                  </span>
                                ) : p.stock < 5 ? (
                                  <span className="bg-amber-100 text-amber-800 font-bold px-2.5 py-1 rounded-full text-[10px] flex items-center gap-1 w-max">
                                    <AlertTriangle className="w-3 h-3" /> Bajo stock ({p.stock})
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

                  {/* Historial de Movimientos de Inventario (Kardex) */}
                  <div className="bg-white rounded-2xl border border-[#E2D9D5] p-6 shadow-sm space-y-3">
                    <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                      <h3 className="font-bold text-stone-800 text-sm">Historial de Movimientos (Kardex)</h3>
                      <span className="text-xs text-stone-500">{movements.length} movimientos registrados</span>
                    </div>

                    <div className="divide-y divide-stone-100 text-xs">
                      {movements.map(m => (
                        <div key={m.id} className="py-3 flex items-center justify-between hover:bg-stone-50/80 px-2 rounded-lg transition-colors">
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

              {/* SUBSECCIÓN 2: REGISTRO DE VENTAS */}
              {inventorySubTab === 'sales' && (
                <div className="space-y-6">
                  
                  {/* Filtro por Fecha & Resumen */}
                  <div className="bg-white p-6 rounded-2xl border border-[#E2D9D5] shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                      <h3 className="font-bold text-stone-800 text-sm">Resumen Consolidado de Ventas</h3>
                      <p className="text-xs text-stone-500 mt-0.5">Consulta transacciones comerciales registradas</p>
                    </div>

                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-stone-400" />
                      <span className="text-xs text-stone-600 font-medium">Período:</span>
                      <select
                        value={salesDateFilter}
                        onChange={(e) => setSalesDateFilter(e.target.value)}
                        className="text-xs bg-[#FDFBF7] border border-stone-300 rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                      >
                        <option value="today">Hoy</option>
                        <option value="week">Esta semana</option>
                        <option value="month">Este mes</option>
                        <option value="all">Histórico completo</option>
                      </select>
                    </div>
                  </div>

                  {/* KPIS Ventas */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm">
                      <p className="text-xs font-bold text-stone-500 uppercase">Total de Ventas Recaudado</p>
                      <p className="text-2xl font-black text-[#5C1D24] mt-1">${totalSalesAmount.toLocaleString()} COP</p>
                      <p className="text-[11px] text-emerald-600 font-medium mt-1">↑ Pagos liquidados</p>
                    </div>

                    <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm">
                      <p className="text-xs font-bold text-stone-500 uppercase">Productos Vendidos</p>
                      <p className="text-2xl font-black text-stone-800 mt-1">{sales.length} transacciones</p>
                      <p className="text-[11px] text-stone-500 mt-1">Comercialización directa</p>
                    </div>
                  </div>

                  {/* Tabla de Transacciones */}
                  <div className="bg-white rounded-2xl border border-[#E2D9D5] shadow-sm overflow-hidden p-6 space-y-3">
                    <h3 className="font-bold text-stone-800 text-sm border-b border-stone-100 pb-3">
                      Transacciones de Ventas
                    </h3>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="bg-stone-50 border-b border-[#E2D9D5] font-semibold text-stone-600">
                            <th className="py-3 px-4">ID Venta</th>
                            <th className="py-3 px-4">Fecha</th>
                            <th className="py-3 px-4">Cliente</th>
                            <th className="py-3 px-4">Producto</th>
                            <th className="py-3 px-4">Método de Pago</th>
                            <th className="py-3 px-4">Monto Total</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-stone-100">
                          {sales.map(s => (
                            <tr key={s.id} className="hover:bg-stone-50 transition-colors">
                              <td className="py-3.5 px-4 font-bold text-[#5C1D24]">{s.id}</td>
                              <td className="py-3.5 px-4 text-stone-600 font-mono">{s.date}</td>
                              <td className="py-3.5 px-4 text-stone-800 font-semibold">{s.customer}</td>
                              <td className="py-3.5 px-4 text-stone-700">{s.product}</td>
                              <td className="py-3.5 px-4 text-stone-600">{s.paymentMethod}</td>
                              <td className="py-3.5 px-4 font-black text-emerald-700">${s.amount.toLocaleString()} COP</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                </div>
              )}

            </div>
          )}

        </main>
      </div>

      {/* ========================================== */}
      {/* MODALES & VENTANAS EMERGENTES */}
      {/* ========================================== */}

      {/* MODAL 1: CONFIRMACIÓN CERRAR SESIÓN */}
      {isLogoutModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4 text-center">
            <div className="w-12 h-12 rounded-full bg-rose-100 text-[#5C1D24] flex items-center justify-center mx-auto">
              <LogOut className="w-6 h-6" />
            </div>

            <div>
              <h3 className="font-extrabold text-stone-800 text-base">¿Cerrar sesión de administrador?</h3>
              <p className="text-xs text-stone-500 mt-1">
                Tendrás que volver a autenticarte para gestionar el panel comercial de la tienda Wayúu.
              </p>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={() => setIsLogoutModalOpen(false)}
                className="flex-1 py-2.5 border border-stone-300 rounded-xl text-xs font-semibold text-stone-700 hover:bg-stone-100 transition-colors"
              >
                Cancelar
              </button>

              <button
                onClick={() => {
                  setIsLogoutModalOpen(false);
                  showToast('Sesión cerrada correctamente.', 'info');
                }}
                className="flex-1 py-2.5 bg-[#5C1D24] hover:bg-[#4A121A] text-white rounded-xl text-xs font-bold transition-colors shadow-md"
              >
                Sí, Cerrar sesión
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: REGISTRAR NUEVO PRODUCTO */}
      {isAddProductModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4 my-8">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <h3 className="font-bold text-stone-800 text-sm flex items-center gap-2">
                <Plus className="w-4 h-4 text-[#5C1D24]" />
                <span>Registrar Nueva Artesanía</span>
              </h3>
              <button onClick={() => setIsAddProductModalOpen(false)} className="text-stone-400 hover:text-stone-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateProduct} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-stone-700 mb-1">Nombre del producto *</label>
                <input
                  type="text"
                  placeholder="Ej: Mochila Susu Kanaas..."
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
                    {categories.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-stone-700 mb-1">Tejedora Responsable</label>
                  <select
                    value={newProduct.artisan}
                    onChange={(e) => setNewProduct({ ...newProduct, artisan: e.target.value })}
                    className="w-full p-2.5 bg-white border border-stone-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  >
                    {WEAVERS.map(w => (
                      <option key={w.id} value={w.name}>{w.name} ({w.rancheria})</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-stone-700 mb-1">Precio (COP) *</label>
                  <input
                    type="number"
                    placeholder="280000"
                    value={newProduct.price}
                    onChange={(e) => setNewProduct({ ...newProduct, price: e.target.value })}
                    className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                    required
                  />
                </div>

                <div>
                  <label className="block font-bold text-stone-700 mb-1">Cantidad Inicial (Stock)</label>
                  <input
                    type="number"
                    placeholder="5"
                    value={newProduct.stock}
                    onChange={(e) => setNewProduct({ ...newProduct, stock: e.target.value })}
                    className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-stone-700 mb-1">Descripción artesanal</label>
                <textarea
                  rows={2}
                  placeholder="Detalles del tejido, hilos y patrones..."
                  value={newProduct.description}
                  onChange={(e) => setNewProduct({ ...newProduct, description: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                ></textarea>
              </div>

              {/* Photo Upload Simulator */}
              <div>
                <label className="block font-bold text-stone-700 mb-1">Fotografías del producto</label>
                <div className="border-2 border-dashed border-stone-300 rounded-xl p-4 text-center hover:border-[#5C1D24] transition-colors cursor-pointer bg-stone-50">
                  <Upload className="w-5 h-5 text-stone-400 mx-auto mb-1" />
                  <p className="text-[11px] font-semibold text-stone-600">Haz clic o arrastra fotos del producto</p>
                  <p className="text-[10px] text-stone-400">Formatos JPG, PNG (Simulado)</p>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsAddProductModalOpen(false)}
                  className="px-4 py-2 border border-stone-300 rounded-xl font-semibold text-stone-700 hover:bg-stone-100"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-[#5C1D24] hover:bg-[#4A121A] text-white font-bold rounded-xl shadow-md"
                >
                  Guardar Producto
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: EDICIÓN RÁPIDA DE PRODUCTO */}
      {isEditProductModalOpen && selectedProduct && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <h3 className="font-bold text-stone-800 text-sm">Editar Producto: {selectedProduct.id}</h3>
              <button onClick={() => setIsEditProductModalOpen(false)} className="text-stone-400 hover:text-stone-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleEditProduct} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold mb-1">Nombre</label>
                <input
                  type="text"
                  value={selectedProduct.name}
                  onChange={(e) => setSelectedProduct({ ...selectedProduct, name: e.target.value })}
                  className="w-full p-2 bg-stone-50 border border-stone-300 rounded-xl"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold mb-1">Precio (COP)</label>
                  <input
                    type="number"
                    value={selectedProduct.price}
                    onChange={(e) => setSelectedProduct({ ...selectedProduct, price: Number(e.target.value) })}
                    className="w-full p-2 bg-stone-50 border border-stone-300 rounded-xl"
                  />
                </div>

                <div>
                  <label className="block font-bold mb-1">Stock</label>
                  <input
                    type="number"
                    value={selectedProduct.stock}
                    onChange={(e) => setSelectedProduct({ ...selectedProduct, stock: Number(e.target.value) })}
                    className="w-full p-2 bg-stone-50 border border-stone-300 rounded-xl"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button type="button" onClick={() => setIsEditProductModalOpen(false)} className="px-3 py-1.5 border rounded-xl">Cancelar</button>
                <button type="submit" className="px-4 py-1.5 bg-[#5C1D24] text-white font-bold rounded-xl">Guardar Cambios</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: CREAR NUEVA CATEGORÍA */}
      {isCategoryModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <h3 className="font-bold text-stone-800 text-sm">Gestión de Categorías</h3>
              <button onClick={() => setIsCategoryModalOpen(false)} className="text-stone-400 hover:text-stone-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddCategory} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-stone-700 mb-1">Nueva Categoría</label>
                <input
                  type="text"
                  placeholder="Ej: Accesorios de madera de Trupillo..."
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl"
                />
              </div>

              <button type="submit" className="w-full py-2 bg-[#5C1D24] text-white font-bold rounded-xl">
                + Crear Categoría
              </button>
            </form>

            <div className="pt-2 border-t border-stone-100">
              <p className="text-[10px] uppercase font-bold text-stone-400 mb-2">Categorías Actuales ({categories.length})</p>
              <div className="flex flex-wrap gap-1.5">
                {categories.map(c => (
                  <span key={c} className="text-[10px] font-semibold bg-stone-100 text-stone-700 px-2.5 py-1 rounded-full border border-stone-200">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 5: DETALLE DE PEDIDO & CAMBIO DE ESTADO */}
      {isOrderDetailModalOpen && selectedOrder && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-5">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <div>
                <h3 className="font-bold text-stone-800 text-base">Detalle del Pedido #{selectedOrder.id}</h3>
                <p className="text-xs text-stone-500">Cliente: {selectedOrder.customer}</p>
              </div>
              <button onClick={() => setIsOrderDetailModalOpen(false)} className="text-stone-400 hover:text-stone-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              
              {/* Cambiar Estado Selector */}
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-2xl flex items-center justify-between">
                <div>
                  <p className="font-bold text-[#5C1D24]">Actualizar Estado</p>
                  <p className="text-[10px] text-stone-600">Cambia el flujo del pedido</p>
                </div>

                <select
                  value={selectedOrder.status}
                  onChange={(e) => handleUpdateOrderStatus(selectedOrder.id, e.target.value)}
                  className="p-2 bg-white border border-stone-300 rounded-xl font-bold text-[#5C1D24] focus:outline-none"
                >
                  <option value="Pendiente">Pendiente</option>
                  <option value="En tejido/Elaboración">En tejido/Elaboración</option>
                  <option value="Enviado">Enviado</option>
                  <option value="Entregado">Entregado</option>
                </select>
              </div>

              {/* Items Comprados */}
              <div className="bg-stone-50 p-3 rounded-2xl space-y-2">
                <p className="font-bold text-stone-700 text-[11px] uppercase">Productos en la Orden</p>
                {selectedOrder.items.map((it, idx) => (
                  <div key={idx} className="flex justify-between font-semibold text-stone-800">
                    <span>{it.name} (x{it.qty})</span>
                    <span>${(it.price * it.qty).toLocaleString()} COP</span>
                  </div>
                ))}
                <div className="pt-2 border-t border-stone-200 flex justify-between font-black text-sm text-[#5C1D24]">
                  <span>Total Pedido:</span>
                  <span>${selectedOrder.total.toLocaleString()} COP</span>
                </div>
              </div>

              {/* Tracking Timeline */}
              <div className="space-y-2">
                <p className="font-bold text-stone-700 text-[11px] uppercase">Historial de Seguimiento artesanal</p>
                <div className="relative pl-5 border-l-2 border-[#5C1D24] space-y-3">
                  {selectedOrder.history.map((step, idx) => (
                    <div key={idx} className="relative">
                      <span className={`absolute -left-[25px] top-0.5 w-3.5 h-3.5 rounded-full border-2 border-white ${
                        step.done ? 'bg-[#5C1D24]' : 'bg-stone-300'
                      }`}></span>
                      <p className={`font-bold ${step.done ? 'text-stone-800' : 'text-stone-400'}`}>{step.step}</p>
                      <p className="text-[10px] text-stone-400">{step.date}</p>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          </div>
        </div>
      )}

      {/* MODAL 6: REGISTRO KARDEX INVENTARIO */}
      {isKardexModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <h3 className="font-bold text-stone-800 text-sm">Registrar Movimiento Stock</h3>
              <button onClick={() => setIsKardexModalOpen(false)} className="text-stone-400 hover:text-stone-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddKardexMovement} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold mb-1">Producto</label>
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
                <label className="block font-bold mb-1">Motivo / Observación</label>
                <input
                  type="text"
                  placeholder="Ej: Reabastecimiento taller Mayapo..."
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

      {/* MODAL 7: DEVOLVER PRODUCTO CON OBSERVACIONES */}
      {isReturnModalOpen && selectedProduct && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <h3 className="font-bold text-stone-800 text-sm">Devolver a Corrección</h3>
              <button onClick={() => setIsReturnModalOpen(false)} className="text-stone-400 hover:text-stone-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleConfirmReturnForCorrection} className="space-y-3 text-xs">
              <p className="text-stone-600">
                Se enviarán observaciones a la tejedora <strong>{selectedProduct.artisan}</strong> para ajustar el registro.
              </p>

              <div>
                <label className="block font-bold mb-1">Observaciones de corrección *</label>
                <textarea
                  rows={3}
                  placeholder="Ej: Adjuntar fotos de mejor iluminación o corregir precio..."
                  value={returnObservations}
                  onChange={(e) => setReturnObservations(e.target.value)}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-stone-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                  required
                ></textarea>
              </div>

              <div className="flex gap-2">
                <button type="button" onClick={() => setIsReturnModalOpen(false)} className="flex-1 py-2 border rounded-xl font-semibold">
                  Cancelar
                </button>
                <button type="submit" className="flex-1 py-2 bg-amber-700 hover:bg-amber-800 text-white font-bold rounded-xl">
                  Enviar Corrección
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}