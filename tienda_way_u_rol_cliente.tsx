import React, { useState, useMemo } from 'react';
import {
  Home,
  ShoppingBag,
  ShoppingCart,
  User,
  Search,
  Filter,
  ArrowLeft,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Truck,
  Package,
  X,
  Edit,
  Trash2,
  LogOut,
  Info,
  MapPin,
  Phone,
  Mail,
  Award,
  Clock,
  Sparkles,
  ChevronRight,
  ChevronDown,
  Plus,
  Minus,
  Check,
  SlidersHorizontal,
  Tag,
  Heart,
  Menu,
  AlertCircle
} from 'lucide-react';

// ==========================================
// MOCK DATA - WAYUU ARTISAN TIENDA
// ==========================================

const INITIAL_CLIENT_USER = {
  id: 'USR-WAY-8821',
  name: 'Maria López',
  email: 'maria.lopez@email.com',
  phone: '+57 300 456 7890',
  address: 'Calle 15 # 8-42, Barrio Coquivacoa',
  city: 'Riohacha',
  department: 'La Guajira',
  rancheriaPreferred: 'Mayapo',
  registeredDate: '2025-03-12'
};

const CATEGORIES = [
  'Todas',
  'Mochilas Susu',
  'Mantas Wayúu',
  'Chinchorros y Hamacas',
  'Sombreros Kumu',
  'Bisutería Kanaas'
];

const SAMPLE_PRODUCTS = [
  {
    id: 'PROD-WAY-01',
    name: 'Mochila Susu Kanaas Sol Naciente',
    category: 'Mochilas Susu',
    price: 280000,
    stock: 8,
    isFeatured: true,
    image: 'https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&q=80&w=800',
    shortDescription: 'Mochila tradicional tejida a una sola hebra con motivos geométricos Kanaas.',
    fullDescription: 'Esta emblemática mochila Susu representa la cosmovisión Wayúu a través de sus intrincados dibujos Kanaas. Cada hilo refleja el pensamiento y el tiempo dedicado por la tejedora en la enramada. Es una pieza única con gasa calada paleteada de alta resistencia y cordón de cierre de doble hebra con borlas tupidas.',
    symbolism: 'El patrón Kanaas (Jiwatou) representa el rastro de la serpiente en la arena y la sabiduría ancestral transmitida entre generaciones de mujeres de la casta Epinayú.',
    weaver: {
      name: 'Marta Uriana',
      rancheria: 'Ranchería Mayapo',
      experienceYears: 18,
      technique: 'Tejido a una hebra (Susu wane puliruü)',
      casta: 'Uriana'
    }
  },
  {
    id: 'PROD-WAY-02',
    name: 'Manta Wayúu Elegante Terracota',
    category: 'Mantas Wayúu',
    price: 340000,
    stock: 4,
    isFeatured: true,
    image: 'https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&q=80&w=800',
    shortDescription: 'Manta holgada de seda fría con bordados finos en cuello y pliegues tradicionales.',
    fullDescription: 'Confeccionada en tela suave y fresca ideal para climas cálidos. Presenta un escote con técnica de nido de abeja hecho a mano por artesanas de la Guajira. Los tonos terracota y arena evocan el atardecer sobre el Cabo de la Vela.',
    symbolism: 'Los pliegues frontales simbolizan el vuelo libre de la brisa marina sobre la serranía de Makuira.',
    weaver: {
      name: 'Aura Barros',
      rancheria: 'Ranchería Cabo de la Vela',
      experienceYears: 22,
      technique: 'Costura y pliegue artesanal en telar',
      casta: 'Pushaina'
    }
  },
  {
    id: 'PROD-WAY-03',
    name: 'Chinchorro Anatas Pulowi Doble',
    category: 'Chinchorros y Hamacas',
    price: 1250000,
    stock: 2,
    isFeatured: true,
    image: 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&q=80&w=800',
    shortDescription: 'Chinchorro de cabecera tejido en técnica suelta con flecos o cañuelotas caladas.',
    fullDescription: 'Obra maestra del tejido Wayúu. A diferencia de una hamaca común, el chinchorro es elástico y extremadamente fresco gracias a su tejido de malla abierta. Incluye faldones laterales (cañuelotas) con motivos geométricos tupidos de gran belleza estética.',
    symbolism: 'El tejido de la cañuela imita la red del pescador y las constelaciones nocturnas de la mística Pulowi.',
    weaver: {
      name: 'Rosa Pushaina',
      rancheria: 'Ranchería Manaure',
      experienceYears: 30,
      technique: 'Telar vertical de dos vigas y tejido calado',
      casta: 'Epinayú'
    }
  },
  {
    id: 'PROD-WAY-04',
    name: 'Sombrero Kumu Mawisa Tradicional',
    category: 'Sombreros Kumu',
    price: 110000,
    stock: 15,
    isFeatured: false,
    image: 'https://images.unsplash.com/photo-1521369909029-2afed882baee?auto=format&fit=crop&q=80&w=800',
    shortDescription: 'Tejido en fibra de palma Mawisa teñida con tintes naturales de la región.',
    fullDescription: 'Sombrero elaborado con la fibra que crece en las dunas de la alta Guajira. Resistente al sol desértico, cuenta con una cinta tejida en cinta de algodón borgoña que adorna la copa.',
    symbolism: 'Su copa redonda representa el sol del mediodía que ilumina los caminos de la ranchería.',
    weaver: {
      name: 'Sonia Epinayú',
      rancheria: 'Uribia Central',
      experienceYears: 15,
      technique: 'Trenzado en paja Mawisa',
      casta: 'Epinayú'
    }
  },
  {
    id: 'PROD-WAY-05',
    name: 'Pulsera Kanaas Iwouya (Estrella)',
    category: 'Bisutería Kanaas',
    price: 45000,
    stock: 20,
    isFeatured: false,
    image: 'https://images.unsplash.com/photo-1611591475179-420dac0319db?auto=format&fit=crop&q=80&w=800',
    shortDescription: 'Tejido minucioso en hilo fino con diseño de estrella vespertina.',
    fullDescription: 'Brazalete ajustador tejido a mano en hilo acrílico pulido que no pierde color. Ideal para lucir elementos identitarios Wayúu de forma sobria y elegante.',
    symbolism: 'El diseño Iwouya rinde tributo a la estrella que anuncia la época de lluvias y la fertilidad de la tierra.',
    weaver: {
      name: 'Luz Marina Jayaliyu',
      rancheria: 'Ranchería Maicao',
      experienceYears: 10,
      technique: 'Tejido en peineta pequeña',
      casta: 'Jayaliyu'
    }
  },
  {
    id: 'PROD-WAY-06',
    name: 'Mochila Susu Mini Palabrero',
    category: 'Mochilas Susu',
    price: 190000,
    stock: 5,
    isFeatured: false,
    image: 'https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&q=80&w=800',
    shortDescription: 'Mochila de tamaño mediano compacta con correa ancha y patrones vivos.',
    fullDescription: 'Versión práctica de la mochila tradicional, pensada para llevar lo esencial durante el día. Tejida a dos hebras con combinación armónica de tonos marfil, marrones y rosado suave.',
    symbolism: 'Inspirada en las palabras pacíficas del Pütchipü’ü (palabrero), mediador de la cultura Wayúu.',
    weaver: {
      name: 'Marta Uriana',
      rancheria: 'Ranchería Mayapo',
      experienceYears: 18,
      technique: 'Tejido a dos hebras (Susu piamawü)',
      casta: 'Uriana'
    }
  }
];

const INITIAL_ORDERS = [
  {
    id: 'ORD-WAY-9821',
    date: '2026-10-24',
    total: 325000,
    status: 'En tejido/Elaboración',
    canCancel: true,
    items: [
      {
        product: SAMPLE_PRODUCTS[0],
        quantity: 1,
        unitPrice: 280000,
        subtotal: 280000
      },
      {
        product: SAMPLE_PRODUCTS[4],
        quantity: 1,
        unitPrice: 45000,
        subtotal: 45000
      }
    ],
    shippingInfo: {
      fullName: 'Maria López',
      phone: '+57 300 456 7890',
      address: 'Calle 15 # 8-42, Barrio Coquivacoa',
      city: 'Riohacha',
      department: 'La Guajira',
      notes: 'Empacar con la etiqueta artesanal de la tejedora.'
    },
    timeline: [
      { title: 'Pedido recibido en tienda', date: '2026-10-24 09:15 AM', completed: true },
      { title: 'Asignación de hilos a la tejedora', date: '2026-10-24 11:30 AM', completed: true },
      { title: 'Tejido del cuerpo y gasa en proceso', date: '2026-10-25 08:00 AM', completed: true },
      { title: 'Control de calidad e inspección Kanaas', date: 'Pendiente', completed: false },
      { title: 'Despacho y entrega con guía nacional', date: 'Pendiente', completed: false }
    ]
  },
  {
    id: 'ORD-WAY-9750',
    date: '2026-09-15',
    total: 340000,
    status: 'Entregado',
    canCancel: false,
    items: [
      {
        product: SAMPLE_PRODUCTS[1],
        quantity: 1,
        unitPrice: 340000,
        subtotal: 340000
      }
    ],
    shippingInfo: {
      fullName: 'Maria López',
      phone: '+57 300 456 7890',
      address: 'Calle 15 # 8-42, Barrio Coquivacoa',
      city: 'Riohacha',
      department: 'La Guajira',
      notes: ''
    },
    timeline: [
      { title: 'Pedido recibido en tienda', date: '2026-09-15 02:20 PM', completed: true },
      { title: 'Asignación de hilos a la tejedora', date: '2026-09-15 04:00 PM', completed: true },
      { title: 'Tejido del cuerpo y gasa en proceso', date: '2026-09-16 09:00 AM', completed: true },
      { title: 'Control de calidad e inspección Kanaas', date: '2026-09-18 11:15 AM', completed: true },
      { title: 'Despacho y entrega realizada', date: '2026-09-20 03:45 PM', completed: true }
    ]
  }
];

// ==========================================
// MAIN APP COMPONENT
// ==========================================

export default function App() {
  // Navigation View State (Exclusively 4 Main Options in Menu)
  // 1 = Inicio y catálogo
  // 2 = Mis favoritos
  // 3 = Mi carrito
  // 4 = Mi cuenta y pedidos
  // (Secondary contextual view: 'detail')
  const [activeView, setActiveView] = useState(1);
  const [previousView, setPreviousView] = useState(1);

  // Mobile Sidebar Drawer Overlay Toggle
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Selected Product for Secondary Detail View
  const [selectedProductId, setSelectedProductId] = useState('PROD-WAY-01');

  // Favorites List State
  const [favoriteProductIds, setFavoriteProductIds] = useState(['PROD-WAY-01', 'PROD-WAY-03']);

  // Cart State
  const [cart, setCart] = useState([
    {
      product: SAMPLE_PRODUCTS[0],
      quantity: 1
    }
  ]);

  // Catalog Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('Todas');
  const [priceOrder, setPriceOrder] = useState('default');

  // User & Orders State
  const [userProfile, setUserProfile] = useState(INITIAL_CLIENT_USER);
  const [myOrders, setMyOrders] = useState(INITIAL_ORDERS);

  // Detail View Quantity State
  const [detailQuantity, setDetailQuantity] = useState(1);

  // Modals
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);
  const [isEditProfileModalOpen, setIsEditProfileModalOpen] = useState(false);
  const [isPurchaseCompletedModalOpen, setIsPurchaseCompletedModalOpen] = useState(false);
  const [recentCompletedOrder, setRecentCompletedOrder] = useState(null);
  const [expandedOrderId, setExpandedOrderId] = useState(null);

  // Form States
  const [editProfileForm, setEditProfileForm] = useState(INITIAL_CLIENT_USER);
  const [checkoutForm, setCheckoutForm] = useState({
    fullName: INITIAL_CLIENT_USER.name,
    email: INITIAL_CLIENT_USER.email,
    phone: INITIAL_CLIENT_USER.phone,
    address: INITIAL_CLIENT_USER.address,
    city: INITIAL_CLIENT_USER.city,
    department: INITIAL_CLIENT_USER.department,
    notes: ''
  });

  // Notification Toast
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (text) => {
    setToastMessage(text);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Selected Product Computation
  const currentProduct = useMemo(() => {
    return SAMPLE_PRODUCTS.find((p) => p.id === selectedProductId) || SAMPLE_PRODUCTS[0];
  }, [selectedProductId]);

  // Favorite Products List Computation
  const favoriteProducts = useMemo(() => {
    return SAMPLE_PRODUCTS.filter((p) => favoriteProductIds.includes(p.id));
  }, [favoriteProductIds]);

  // Cart Quantities Computation
  const totalCartItemsCount = useMemo(() => {
    return cart.reduce((sum, item) => sum + item.quantity, 0);
  }, [cart]);

  const cartSubtotal = useMemo(() => {
    return cart.reduce((sum, item) => sum + item.product.price * item.quantity, 0);
  }, [cart]);

  const estimatedShipping = cartSubtotal > 300000 || cartSubtotal === 0 ? 0 : 15000;
  const grandTotal = cartSubtotal + estimatedShipping;

  // Filtered Catalog Items
  const filteredProducts = useMemo(() => {
    return SAMPLE_PRODUCTS.filter((p) => {
      const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            p.shortDescription.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            p.weaver.name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = selectedCategory === 'Todas' || p.category === selectedCategory;
      return matchesSearch && matchesCategory;
    }).sort((a, b) => {
      if (priceOrder === 'lowToHigh') return a.price - b.price;
      if (priceOrder === 'highToLow') return b.price - a.price;
      return 0;
    });
  }, [searchQuery, selectedCategory, priceOrder]);

  // ==========================================
  // HANDLERS
  // ==========================================

  const handleSelectView = (viewNumber) => {
    setActiveView(viewNumber);
    setIsMobileSidebarOpen(false);
  };

  const handleOpenProductDetail = (productId) => {
    setPreviousView(activeView);
    setSelectedProductId(productId);
    setDetailQuantity(1);
    setActiveView('detail');
  };

  const handleToggleFavorite = (productId, e) => {
    if (e) e.stopPropagation();
    setFavoriteProductIds((prev) => {
      const exists = prev.includes(productId);
      if (exists) {
        showToast('Producto eliminado de tus favoritos.');
        return prev.filter((id) => id !== productId);
      } else {
        showToast('Producto agregado a tus favoritos.');
        return [...prev, productId];
      }
    });
  };

  const handleAddToCart = (product, qty = 1, e) => {
    if (e) e.stopPropagation();
    const existingIndex = cart.findIndex((item) => item.product.id === product.id);
    let updatedCart = [...cart];

    if (existingIndex > -1) {
      const currentQty = updatedCart[existingIndex].quantity;
      const newQty = Math.min(currentQty + qty, product.stock);
      updatedCart[existingIndex].quantity = newQty;
      showToast(`Se actualizó la cantidad de "${product.name}" en el carrito.`);
    } else {
      const initialQty = Math.min(qty, product.stock);
      updatedCart.push({ product, quantity: initialQty });
      showToast(`"${product.name}" agregado al carrito de compras.`);
    }

    setCart(updatedCart);
  };

  const handleUpdateCartQuantity = (productId, delta) => {
    setCart((prevCart) =>
      prevCart.map((item) => {
        if (item.product.id === productId) {
          const nextQty = item.quantity + delta;
          if (nextQty <= 0) return item;
          if (nextQty > item.product.stock) {
            showToast(`Límite de stock alcanzado (${item.product.stock} unidades disponibles).`);
            return item;
          }
          return { ...item, quantity: nextQty };
        }
        return item;
      })
    );
  };

  const handleRemoveFromCart = (productId) => {
    setCart((prevCart) => prevCart.filter((item) => item.product.id !== productId));
    showToast('Producto retirado del carrito.');
  };

  const handleProcessOrderConfirmation = (e) => {
    e.preventDefault();
    if (cart.length === 0) return;

    const newOrderId = `ORD-WAY-${Math.floor(1000 + Math.random() * 9000)}`;
    const newOrderObj = {
      id: newOrderId,
      date: new Date().toISOString().split('T')[0],
      total: grandTotal,
      status: 'En tejido/Elaboración',
      canCancel: true,
      items: cart.map((item) => ({
        product: item.product,
        quantity: item.quantity,
        unitPrice: item.product.price,
        subtotal: item.product.price * item.quantity
      })),
      shippingInfo: {
        fullName: checkoutForm.fullName,
        phone: checkoutForm.phone,
        address: checkoutForm.address,
        city: checkoutForm.city,
        department: checkoutForm.department,
        notes: checkoutForm.notes
      },
      timeline: [
        { title: 'Pedido recibido en tienda', date: new Date().toLocaleString(), completed: true },
        { title: 'Asignación de hilos a la tejedora', date: 'Procesando en taller', completed: true },
        { title: 'Tejido del cuerpo y gasa en proceso', date: 'Pendiente inicio', completed: false },
        { title: 'Control de calidad e inspección Kanaas', date: 'Pendiente', completed: false },
        { title: 'Despacho y entrega con guía nacional', date: 'Pendiente', completed: false }
      ]
    };

    setMyOrders([newOrderObj, ...myOrders]);
    setRecentCompletedOrder(newOrderObj);
    setIsPurchaseCompletedModalOpen(true);
    setCart([]);
  };

  const handleSaveEditedProfile = (e) => {
    e.preventDefault();
    setUserProfile(editProfileForm);
    setIsEditProfileModalOpen(false);
    showToast('Perfil de cliente actualizado con éxito.');
  };

  const handleRequestOrderCancellation = (orderId) => {
    setMyOrders((prevOrders) =>
      prevOrders.map((ord) => {
        if (ord.id === orderId) {
          showToast(`Solicitud de cancelación enviada para la orden ${orderId}.`);
          return { ...ord, status: 'Solicitud Cancelación', canCancel: false };
        }
        return ord;
      })
    );
  };

  const handleConfirmLogout = () => {
    setIsLogoutModalOpen(false);
    showToast('Sesión simulada de cliente cerrada correctamente.');
  };

  return (
    <div className="flex h-screen bg-[#FDFBF7] text-[#3D1E16] font-sans overflow-hidden selection:bg-[#5C1D24] selection:text-white">

      {/* TOAST NOTIFICATION FLOATING BANNER */}
      {toastMessage && (
        <div className="fixed top-5 right-5 z-50 bg-[#3D1E16] text-[#FDFBF7] px-5 py-3.5 rounded-2xl shadow-2xl flex items-center gap-3 border border-[#C86D51]/30 transition-all duration-300 text-xs md:text-sm font-medium">
          <Info className="w-5 h-5 text-[#C86D51] shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* =================================================================== */}
      {/* 1. PERMANENT LEFT VERTICAL NAVIGATION SIDEBAR                      */}
      {/* =================================================================== */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-40 w-72 bg-[#5C1D24] text-[#FDFBF7] flex flex-col justify-between shrink-0 shadow-2xl transform transition-transform duration-300 ${
          isMobileSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex flex-col h-full overflow-y-auto">

          {/* Logo & Branding Header */}
          <div className="p-6 pb-5 flex items-center justify-between border-b border-rose-900/50">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-[#FDFBF7]/10 rounded-2xl border border-white/20 shadow-inner flex items-center justify-center">
                <svg className="w-7 h-7 text-[#FDFBF7]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                </svg>
              </div>
              <div>
                <h1 className="font-extrabold text-xl tracking-wide text-[#FDFBF7] leading-none">Wayúu</h1>
                <p className="text-[10px] text-rose-200/90 tracking-wider uppercase font-semibold mt-1">
                  Portal del Cliente
                </p>
              </div>
            </div>

            {/* Mobile Close Button */}
            <button
              onClick={() => setIsMobileSidebarOpen(false)}
              className="lg:hidden p-1.5 text-rose-200 hover:text-white rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* EXACTLY 4 MAIN NAVIGATION OPTIONS (VERTICAL) */}
          <nav className="p-4 space-y-2 text-xs font-semibold flex-1">
            <p className="text-[10px] uppercase font-bold text-rose-300/60 px-3 pb-1 tracking-wider">
              Navegación Principal
            </p>

            {/* Option 1: Inicio y catálogo */}
            <button
              onClick={() => handleSelectView(1)}
              className={`w-full flex items-center justify-between px-4 py-3.5 rounded-2xl transition-all duration-200 ${
                activeView === 1
                  ? 'bg-[#FDFBF7] text-[#5C1D24] font-black shadow-md transform translate-x-1'
                  : 'text-rose-100 hover:bg-white/10'
              }`}
            >
              <div className="flex items-center gap-3.5">
                <Home className={`w-4 h-4 ${activeView === 1 ? 'text-[#5C1D24]' : 'text-rose-200'}`} />
                <span>1. Inicio y catálogo</span>
              </div>
              {activeView === 1 && <ChevronRight className="w-4 h-4 text-[#5C1D24]" />}
            </button>

            {/* Option 2: Mis favoritos */}
            <button
              onClick={() => handleSelectView(2)}
              className={`w-full flex items-center justify-between px-4 py-3.5 rounded-2xl transition-all duration-200 ${
                activeView === 2
                  ? 'bg-[#FDFBF7] text-[#5C1D24] font-black shadow-md transform translate-x-1'
                  : 'text-rose-100 hover:bg-white/10'
              }`}
            >
              <div className="flex items-center gap-3.5">
                <Heart className={`w-4 h-4 ${activeView === 2 ? 'text-[#5C1D24] fill-[#5C1D24]' : 'text-rose-200'}`} />
                <span>2. Mis favoritos</span>
              </div>
              {favoriteProductIds.length > 0 ? (
                <span className={`px-2 py-0.5 text-[10px] font-black rounded-full ${
                  activeView === 2 ? 'bg-[#5C1D24] text-white' : 'bg-rose-900/60 text-rose-100 border border-rose-300/20'
                }`}>
                  {favoriteProductIds.length}
                </span>
              ) : (
                activeView === 2 && <ChevronRight className="w-4 h-4 text-[#5C1D24]" />
              )}
            </button>

            {/* Option 3: Mi carrito */}
            <button
              onClick={() => handleSelectView(3)}
              className={`w-full flex items-center justify-between px-4 py-3.5 rounded-2xl transition-all duration-200 ${
                activeView === 3
                  ? 'bg-[#FDFBF7] text-[#5C1D24] font-black shadow-md transform translate-x-1'
                  : 'text-rose-100 hover:bg-white/10'
              }`}
            >
              <div className="flex items-center gap-3.5">
                <ShoppingCart className={`w-4 h-4 ${activeView === 3 ? 'text-[#5C1D24]' : 'text-rose-200'}`} />
                <span>3. Mi carrito</span>
              </div>
              {totalCartItemsCount > 0 ? (
                <span className={`px-2 py-0.5 text-[10px] font-black rounded-full ${
                  activeView === 3 ? 'bg-[#5C1D24] text-white' : 'bg-[#C86D51] text-white'
                }`}>
                  {totalCartItemsCount}
                </span>
              ) : (
                activeView === 3 && <ChevronRight className="w-4 h-4 text-[#5C1D24]" />
              )}
            </button>

            {/* Option 4: Mi cuenta y pedidos */}
            <button
              onClick={() => handleSelectView(4)}
              className={`w-full flex items-center justify-between px-4 py-3.5 rounded-2xl transition-all duration-200 ${
                activeView === 4
                  ? 'bg-[#FDFBF7] text-[#5C1D24] font-black shadow-md transform translate-x-1'
                  : 'text-rose-100 hover:bg-white/10'
              }`}
            >
              <div className="flex items-center gap-3.5">
                <User className={`w-4 h-4 ${activeView === 4 ? 'text-[#5C1D24]' : 'text-rose-200'}`} />
                <span>4. Mi cuenta y pedidos</span>
              </div>
              {activeView === 4 && <ChevronRight className="w-4 h-4 text-[#5C1D24]" />}
            </button>
          </nav>

          {/* User Profile Card & Sign Out at Sidebar Bottom */}
          <div className="p-4 m-3 rounded-2xl bg-black/20 border border-white/10 space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[#FDFBF7] text-[#5C1D24] flex items-center justify-center font-black text-xs shadow-md shrink-0 border border-rose-200">
                {userProfile.name.split(' ').map((n) => n[0]).join('')}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-extrabold text-white truncate">{userProfile.name}</p>
                <p className="text-[10px] text-rose-200/80 truncate">Rol: Cliente Registrado</p>
              </div>
            </div>

            <button
              onClick={() => setIsLogoutModalOpen(true)}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-white/10 hover:bg-rose-900/60 text-white text-xs font-semibold transition-colors border border-white/10"
            >
              <LogOut className="w-3.5 h-3.5 text-rose-200" />
              <span>Cerrar Sesión</span>
            </button>
          </div>

          <div className="p-3 text-center border-t border-rose-900/40 bg-black/10">
            <p className="text-[10px] text-rose-300/60 font-mono">Tienda Wayúu • Cliente v2.0</p>
          </div>

        </div>
      </aside>

      {/* MOBILE BACKDROP OVERLAY */}
      {isMobileSidebarOpen && (
        <div
          onClick={() => setIsMobileSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm lg:hidden"
        ></div>
      )}

      {/* =================================================================== */}
      {/* 2. MAIN CONTENT WORKSPACE AREA (TO THE RIGHT)                     */}
      {/* =================================================================== */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">

        {/* TOP HEADER */}
        <header className="bg-white border-b border-[#E2D9D5] px-6 py-4 flex items-center justify-between shrink-0 shadow-sm z-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsMobileSidebarOpen(true)}
              className="lg:hidden p-2 text-stone-700 hover:bg-stone-100 rounded-xl"
              title="Abrir Menú"
            >
              <Menu className="w-5 h-5" />
            </button>

            <span className="text-xs font-bold uppercase tracking-wider text-[#5C1D24] bg-rose-50 px-3 py-1 rounded-lg border border-rose-200">
              Rol: Cliente
            </span>
            <span className="text-xs text-stone-300 hidden sm:inline">/</span>
            <span className="text-xs font-medium text-stone-600 capitalize hidden sm:inline">
              {activeView === 1 && 'Inicio y Catálogo de Artesanías'}
              {activeView === 2 && 'Mis Productos Favoritos'}
              {activeView === 3 && 'Mi Carrito de Compras'}
              {activeView === 4 && 'Mi Cuenta y Histórico de Pedidos'}
              {activeView === 'detail' && 'Detalle del Producto'}
            </span>
          </div>

          <div className="flex items-center gap-4">
            {/* Quick Search trigger */}
            <div className="hidden md:flex items-center gap-2 relative">
              <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Buscar mochila, tejedora..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  if (activeView !== 1) setActiveView(1);
                }}
                className="text-xs pl-9 pr-3 py-1.5 bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl w-56 focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
              />
            </div>

            {/* Quick Favorites Counter Badge */}
            <button
              onClick={() => setActiveView(2)}
              className="relative p-2 text-stone-600 hover:text-[#5C1D24] hover:bg-rose-50 rounded-xl transition-colors border border-stone-200"
              title="Ir a Mis Favoritos"
            >
              <Heart className="w-5 h-5" />
              {favoriteProductIds.length > 0 && (
                <span className="absolute -top-1.5 -right-1.5 bg-[#5C1D24] text-white text-[10px] font-black w-5 h-5 rounded-full flex items-center justify-center border-2 border-white">
                  {favoriteProductIds.length}
                </span>
              )}
            </button>

            {/* Quick Cart Badge in Header */}
            <button
              onClick={() => setActiveView(3)}
              className="relative p-2 text-stone-600 hover:text-[#5C1D24] hover:bg-rose-50 rounded-xl transition-colors border border-stone-200"
              title="Ir al Carrito"
            >
              <ShoppingCart className="w-5 h-5" />
              {totalCartItemsCount > 0 && (
                <span className="absolute -top-1.5 -right-1.5 bg-[#C86D51] text-white text-[10px] font-black w-5 h-5 rounded-full flex items-center justify-center border-2 border-white">
                  {totalCartItemsCount}
                </span>
              )}
            </button>

            {/* User Avatar Direct Access */}
            <button
              onClick={() => setActiveView(4)}
              className="flex items-center gap-2 pl-3 border-l border-stone-200 text-left hover:opacity-80 transition-opacity"
            >
              <div className="w-8 h-8 rounded-full bg-[#5C1D24] text-white flex items-center justify-center text-xs font-bold shadow-sm">
                ML
              </div>
              <div className="hidden md:block">
                <p className="text-xs font-bold text-stone-800 leading-none">{userProfile.name}</p>
                <p className="text-[10px] text-stone-500 mt-0.5">{userProfile.city}</p>
              </div>
            </button>
          </div>
        </header>

        {/* MAIN SCROLLABLE VISTAS RENDER AREA */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-[#FDFBF7]">

          {/* =================================================================== */}
          {/* VISTA 1: INICIO Y CATÁLOGO                                         */}
          {/* =================================================================== */}
          {activeView === 1 && (
            <div className="max-w-7xl mx-auto space-y-8">

              {/* HERO BANNER CULTURAL */}
              <section className="relative rounded-3xl overflow-hidden bg-gradient-to-r from-[#5C1D24] via-[#7A2832] to-[#3D1E16] text-[#FDFBF7] p-8 sm:p-10 shadow-xl">
                <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#E2D9D5_1px,transparent_1px)] [background-size:16px_16px]"></div>

                <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
                  <div className="lg:col-span-7 space-y-5">
                    <div className="inline-flex items-center gap-2 bg-[#C86D51]/30 border border-[#C86D51]/50 px-3.5 py-1.5 rounded-full text-xs font-bold text-[#FDFBF7]">
                      <Sparkles className="w-4 h-4 text-[#C86D51]" />
                      <span>Comercio Justo y Tradición de La Guajira</span>
                    </div>

                    <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black leading-tight tracking-tight">
                      Tienda Wayúu <br />
                      <span className="text-[#C86D51]">Tejidos que cuentan historias</span>
                    </h1>

                    <p className="text-xs sm:text-sm text-[#E2D9D5] leading-relaxed max-w-xl">
                      Somos una tienda de productos artesanales elaborados por mujeres Wayúu de La Guajira. Cada manta y mochila es una pieza única, hecha a mano con tradición, identidad y mucho amor.
                    </p>

                    <div className="pt-2">
                      <button
                        onClick={() => {
                          const catalogElement = document.getElementById('catalogo-section');
                          if (catalogElement) catalogElement.scrollIntoView({ behavior: 'smooth' });
                        }}
                        className="px-6 py-3.5 bg-[#C86D51] hover:bg-[#a8553c] text-white font-bold text-xs sm:text-sm rounded-2xl shadow-lg transition-transform hover:scale-105 flex items-center gap-2"
                      >
                        <span>Explorar catálogo</span>
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div className="lg:col-span-5 relative">
                    <div className="relative rounded-2xl overflow-hidden border-4 border-[#FDFBF7]/20 shadow-2xl group">
                      <img
                        src="https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&q=80&w=800"
                        alt="Mujer Wayúu Tejiendo"
                        className="w-full h-80 object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent flex items-end p-6">
                        <div className="text-white">
                          <p className="text-xs font-bold uppercase text-[#C86D51]">Simbología Kanaas</p>
                          <p className="text-sm font-extrabold">Diseños geométricos tejidos a mano</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </section>

              {/* PILARES CULTURALES */}
              <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-start gap-3.5">
                  <div className="p-3 bg-[#FBEAEB] text-[#5C1D24] rounded-xl shrink-0">
                    <Award className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-xs uppercase tracking-wider text-[#3D1E16]">Artesanía 100% Hecha a Mano</h3>
                    <p className="text-xs text-stone-500 mt-0.5">Piezas elaboradas con hilos finos de alta resistencia.</p>
                  </div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-start gap-3.5">
                  <div className="p-3 bg-[#FBEAEB] text-[#5C1D24] rounded-xl shrink-0">
                    <Heart className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-xs uppercase tracking-wider text-[#3D1E16]">Mujeres Wayúu que Tejen Futuro</h3>
                    <p className="text-xs text-stone-500 mt-0.5">Sustento directo para las familias de las rancherías.</p>
                  </div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-start gap-3.5">
                  <div className="p-3 bg-[#FBEAEB] text-[#5C1D24] rounded-xl shrink-0">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-xs uppercase tracking-wider text-[#3D1E16]">Comercio Justo y Apoyo</h3>
                    <p className="text-xs text-stone-500 mt-0.5">Retribución ética y valoración del trabajo artesanal.</p>
                  </div>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-[#E2D9D5] shadow-sm flex items-start gap-3.5">
                  <div className="p-3 bg-[#FBEAEB] text-[#5C1D24] rounded-xl shrink-0">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-xs uppercase tracking-wider text-[#3D1E16]">Cultura y Tradición Viva</h3>
                    <p className="text-xs text-stone-500 mt-0.5">Legado cultural patrimonio de Colombia para el mundo.</p>
                  </div>
                </div>
              </section>

              {/* SECCIÓN PRODUCTOS DESTACADOS */}
              <section className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-black text-[#5C1D24] tracking-tight">Piezas Destacadas</h2>
                    <p className="text-xs text-stone-600 mt-0.5">Artesanías con mayor valor cultural y reconocimiento</p>
                  </div>
                  <div className="h-0.5 bg-[#E2D9D5] flex-1 mx-6 hidden sm:block"></div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {SAMPLE_PRODUCTS.filter((p) => p.isFeatured).map((item) => {
                    const isFav = favoriteProductIds.includes(item.id);
                    return (
                      <div
                        key={item.id}
                        onClick={() => handleOpenProductDetail(item.id)}
                        className="bg-white rounded-3xl border border-[#E2D9D5] overflow-hidden shadow-sm hover:shadow-md transition-all flex flex-col justify-between group cursor-pointer"
                      >
                        <div>
                          <div className="relative h-52 overflow-hidden bg-stone-100">
                            <img
                              src={item.image}
                              alt={item.name}
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                            />
                            <span className="absolute top-3 left-3 bg-[#5C1D24] text-white text-[10px] font-black uppercase tracking-wider px-3 py-1 rounded-full shadow">
                              {item.category}
                            </span>
                            <button
                              onClick={(e) => handleToggleFavorite(item.id, e)}
                              className={`absolute top-3 right-3 p-2 rounded-full backdrop-blur-sm transition-all shadow ${
                                isFav ? 'bg-white text-[#5C1D24]' : 'bg-black/30 text-white hover:bg-white hover:text-[#5C1D24]'
                              }`}
                              title={isFav ? 'Quitar de favoritos' : 'Agregar a favoritos'}
                            >
                              <Heart className={`w-4 h-4 ${isFav ? 'fill-[#5C1D24]' : ''}`} />
                            </button>
                          </div>

                          <div className="p-5 space-y-2">
                            <h3 className="font-extrabold text-sm text-[#3D1E16] group-hover:text-[#5C1D24] transition-colors leading-snug">
                              {item.name}
                            </h3>
                            <p className="text-xs text-stone-500 line-clamp-2">
                              {item.shortDescription}
                            </p>
                            <p className="text-[11px] font-semibold text-[#C86D51] italic">
                              Tejida por: {item.weaver.name} ({item.weaver.rancheria})
                            </p>
                          </div>
                        </div>

                        <div className="p-5 pt-0 flex items-center justify-between border-t border-stone-100 mt-2">
                          <div>
                            <span className="text-[10px] text-stone-400 block">Precio:</span>
                            <span className="text-base font-black text-[#5C1D24]">${item.price.toLocaleString()} COP</span>
                          </div>

                          <div className="flex gap-2">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenProductDetail(item.id);
                              }}
                              className="px-3 py-2 bg-[#FBEAEB] text-[#5C1D24] hover:bg-[#5C1D24] hover:text-white rounded-xl text-xs font-bold transition-colors"
                            >
                              Ver detalle
                            </button>
                            <button
                              onClick={(e) => handleAddToCart(item, 1, e)}
                              className="p-2 bg-[#5C1D24] text-white hover:bg-[#3D1E16] rounded-xl transition-colors shadow-sm"
                              title="Agregar al Carrito"
                            >
                              <ShoppingCart className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* SECCIÓN CATÁLOGO GENERAL Y FILTROS */}
              <section id="catalogo-section" className="space-y-6 pt-6 border-t border-[#E2D9D5]">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-2xl font-black text-[#5C1D24] tracking-tight">Catálogo General de Artesanías</h2>
                    <p className="text-xs text-stone-600 mt-1">Explora mochilas, mantas, chinchorros, sombreros y bisutería</p>
                  </div>

                  {/* Search Input Bar */}
                  <div className="relative w-full md:w-80">
                    <Search className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      placeholder="Buscar por nombre, tejedora..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 bg-white border border-[#E2D9D5] rounded-2xl text-xs font-medium focus:outline-none focus:ring-2 focus:ring-[#5C1D24]"
                    />
                    {searchQuery && (
                      <button
                        onClick={() => setSearchQuery('')}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Dynamic Filter Controls Bar */}
                <div className="bg-white p-4 rounded-2xl border border-[#E2D9D5] shadow-sm flex flex-col lg:flex-row gap-4 items-center justify-between">

                  {/* Categories Horizontal Pills */}
                  <div className="flex items-center gap-1.5 overflow-x-auto w-full lg:w-auto pb-2 lg:pb-0 scrollbar-none">
                    {CATEGORIES.map((cat) => (
                      <button
                        key={cat}
                        onClick={() => setSelectedCategory(cat)}
                        className={`px-3.5 py-2 rounded-xl text-xs font-bold shrink-0 transition-all ${
                          selectedCategory === cat
                            ? 'bg-[#5C1D24] text-white shadow-sm'
                            : 'bg-[#FDFBF7] text-stone-700 hover:bg-[#FBEAEB] border border-[#E2D9D5]'
                        }`}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>

                  {/* Price Sort Dropdown */}
                  <div className="flex items-center gap-2 shrink-0 self-end lg:self-auto">
                    <SlidersHorizontal className="w-4 h-4 text-stone-500" />
                    <span className="text-xs font-bold text-stone-600">Ordenar por precio:</span>
                    <select
                      value={priceOrder}
                      onChange={(e) => setPriceOrder(e.target.value)}
                      className="bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl text-xs font-bold px-3 py-2 text-[#3D1E16] focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                    >
                      <option value="default">Relevancia</option>
                      <option value="lowToHigh">Precio: Menor a Mayor</option>
                      <option value="highToLow">Precio: Mayor a Menor</option>
                    </select>
                  </div>
                </div>

                {/* Catalog Items Grid */}
                {filteredProducts.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredProducts.map((prod) => {
                      const isFav = favoriteProductIds.includes(prod.id);
                      return (
                        <div
                          key={prod.id}
                          onClick={() => handleOpenProductDetail(prod.id)}
                          className="bg-white rounded-3xl border border-[#E2D9D5] overflow-hidden shadow-sm hover:shadow-md transition-all flex flex-col justify-between group cursor-pointer"
                        >
                          <div>
                            <div className="relative h-56 overflow-hidden bg-stone-100">
                              <img
                                src={prod.image}
                                alt={prod.name}
                                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                              />
                              <span className="absolute top-3 left-3 bg-[#FDFBF7]/90 backdrop-blur-sm text-[#5C1D24] text-[10px] font-black uppercase tracking-wider px-3 py-1 rounded-full border border-[#E2D9D5]">
                                {prod.category}
                              </span>
                              <button
                                onClick={(e) => handleToggleFavorite(prod.id, e)}
                                className={`absolute top-3 right-3 p-2 rounded-full backdrop-blur-sm transition-all shadow ${
                                  isFav ? 'bg-white text-[#5C1D24]' : 'bg-black/30 text-white hover:bg-white hover:text-[#5C1D24]'
                                }`}
                                title={isFav ? 'Quitar de favoritos' : 'Agregar a favoritos'}
                              >
                                <Heart className={`w-4 h-4 ${isFav ? 'fill-[#5C1D24]' : ''}`} />
                              </button>
                            </div>

                            <div className="p-5 space-y-2">
                              <h3 className="font-extrabold text-sm text-[#3D1E16] leading-snug">
                                {prod.name}
                              </h3>
                              <p className="text-xs text-stone-500 line-clamp-2">
                                {prod.shortDescription}
                              </p>

                              <div className="p-2.5 bg-[#FDFBF7] rounded-xl border border-[#E2D9D5] text-[11px] text-stone-600 mt-2">
                                <p><strong>Tejedora:</strong> {prod.weaver.name}</p>
                                <p className="text-stone-400">Ranchería: {prod.weaver.rancheria}</p>
                              </div>
                            </div>
                          </div>

                          <div className="p-5 pt-0 flex items-center justify-between border-t border-stone-100 mt-2">
                            <div>
                              <span className="text-[10px] text-stone-400 block">Precio unitario:</span>
                              <span className="text-base font-black text-[#5C1D24]">${prod.price.toLocaleString()} COP</span>
                            </div>

                            <div className="flex gap-2">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleOpenProductDetail(prod.id);
                                }}
                                className="px-3.5 py-2 bg-[#FBEAEB] text-[#5C1D24] hover:bg-[#5C1D24] hover:text-white rounded-xl text-xs font-bold transition-colors"
                              >
                                Ver detalle
                              </button>
                              <button
                                onClick={(e) => handleAddToCart(prod, 1, e)}
                                className="p-2 bg-[#5C1D24] text-white hover:bg-[#3D1E16] rounded-xl transition-colors shadow-sm"
                                title="Agregar al Carrito"
                              >
                                <ShoppingCart className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="bg-white p-12 rounded-3xl border border-[#E2D9D5] text-center space-y-4">
                    <Info className="w-10 h-10 text-stone-400 mx-auto" />
                    <p className="text-base font-bold text-stone-700">No se encontraron artesanías para esta búsqueda.</p>
                    <p className="text-xs text-stone-500">Prueba ajustando los filtros de categoría o términos de búsqueda.</p>
                    <button
                      onClick={() => { setSearchQuery(''); setSelectedCategory('Todas'); }}
                      className="px-4 py-2 bg-[#5C1D24] text-white rounded-xl text-xs font-bold"
                    >
                      Restablecer Filtros
                    </button>
                  </div>
                )}
              </section>

            </div>
          )}

          {/* =================================================================== */}
          {/* VISTA 2: MIS FAVORITOS (NUEVA VISTA)                              */}
          {/* =================================================================== */}
          {activeView === 2 && (
            <div className="space-y-8 max-w-6xl mx-auto">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h1 className="text-2xl sm:text-3xl font-black text-[#5C1D24] tracking-tight flex items-center gap-2.5">
                    <Heart className="w-7 h-7 text-[#5C1D24] fill-[#5C1D24]" />
                    <span>Mis Favoritos</span>
                  </h1>
                  <p className="text-xs text-stone-600 mt-1">
                    Artesanías que has marcado con corazón para consultar o comprar posteriormente
                  </p>
                </div>

                {favoriteProducts.length > 0 && (
                  <span className="bg-[#FBEAEB] text-[#5C1D24] text-xs font-black px-4 py-2 rounded-2xl border border-[#E2D9D5] self-start sm:self-auto">
                    {favoriteProducts.length} {favoriteProducts.length === 1 ? 'producto guardado' : 'productos guardados'}
                  </span>
                )}
              </div>

              {favoriteProducts.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {favoriteProducts.map((prod) => (
                    <div
                      key={prod.id}
                      onClick={() => handleOpenProductDetail(prod.id)}
                      className="bg-white rounded-3xl border border-[#E2D9D5] overflow-hidden shadow-sm hover:shadow-md transition-all flex flex-col justify-between group cursor-pointer"
                    >
                      <div>
                        <div className="relative h-56 overflow-hidden bg-stone-100">
                          <img
                            src={prod.image}
                            alt={prod.name}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                          />
                          <span className="absolute top-3 left-3 bg-[#5C1D24] text-white text-[10px] font-black uppercase tracking-wider px-3 py-1 rounded-full shadow">
                            {prod.category}
                          </span>

                          <button
                            onClick={(e) => handleToggleFavorite(prod.id, e)}
                            className="absolute top-3 right-3 p-2 bg-white text-[#5C1D24] rounded-full shadow transition-transform hover:scale-110"
                            title="Quitar de favoritos"
                          >
                            <Heart className="w-4 h-4 fill-[#5C1D24]" />
                          </button>
                        </div>

                        <div className="p-5 space-y-2">
                          <h3 className="font-extrabold text-sm text-[#3D1E16] leading-snug">
                            {prod.name}
                          </h3>
                          <p className="text-xs text-stone-500 line-clamp-2">
                            {prod.shortDescription}
                          </p>

                          <div className="p-2.5 bg-[#FDFBF7] rounded-xl border border-[#E2D9D5] text-[11px] text-stone-600 mt-2">
                            <p><strong>Tejedora:</strong> {prod.weaver.name}</p>
                            <p className="text-stone-400">Ranchería: {prod.weaver.rancheria}</p>
                          </div>
                        </div>
                      </div>

                      <div className="p-5 pt-0 flex items-center justify-between border-t border-stone-100 mt-2 gap-2">
                        <div>
                          <span className="text-[10px] text-stone-400 block">Precio:</span>
                          <span className="text-base font-black text-[#5C1D24]">${prod.price.toLocaleString()} COP</span>
                        </div>

                        <div className="flex gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenProductDetail(prod.id);
                            }}
                            className="px-3 py-2 bg-[#FBEAEB] text-[#5C1D24] hover:bg-[#5C1D24] hover:text-white rounded-xl text-xs font-bold transition-colors"
                          >
                            Ver detalle
                          </button>
                          <button
                            onClick={(e) => handleAddToCart(prod, 1, e)}
                            className="px-3 py-2 bg-[#5C1D24] hover:bg-[#3D1E16] text-white rounded-xl text-xs font-bold transition-colors shadow-sm flex items-center gap-1.5"
                            title="Agregar al Carrito"
                          >
                            <ShoppingCart className="w-3.5 h-3.5" />
                            <span>Agregar</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="bg-white p-12 rounded-3xl border border-[#E2D9D5] text-center space-y-4 max-w-lg mx-auto shadow-sm">
                  <div className="w-16 h-16 bg-[#FBEAEB] rounded-full flex items-center justify-center mx-auto text-[#5C1D24]">
                    <Heart className="w-8 h-8" />
                  </div>
                  <h2 className="text-lg font-extrabold text-[#3D1E16]">Aún no tienes productos favoritos</h2>
                  <p className="text-xs text-stone-500 leading-relaxed">
                    Explora la tienda y marca con el corazón las mochilas, mantas o accesorios Wayúu que más te enamoren para guardarlos aquí.
                  </p>
                  <div className="pt-2">
                    <button
                      onClick={() => setActiveView(1)}
                      className="px-6 py-3 bg-[#5C1D24] text-white rounded-2xl text-xs font-bold shadow hover:bg-[#3D1E16] transition-colors"
                    >
                      Explorar el catálogo
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* =================================================================== */}
          {/* VISTA 3: CARRITO Y COMPRA                                          */}
          {/* =================================================================== */}
          {activeView === 3 && (
            <div className="space-y-8 max-w-6xl mx-auto">
              <div>
                <h1 className="text-2xl sm:text-3xl font-black text-[#5C1D24] tracking-tight">
                  Mi Carrito y Compra
                </h1>
                <p className="text-xs text-stone-600 mt-1">Revisa tus productos seleccionados y completa tus datos de entrega</p>
              </div>

              {cart.length > 0 ? (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">

                  {/* Left Column: Cart Items List */}
                  <div className="lg:col-span-7 space-y-4">
                    <div className="bg-white rounded-3xl border border-[#E2D9D5] p-6 shadow-sm space-y-4">
                      <div className="flex items-center justify-between border-b border-stone-200 pb-3">
                        <h2 className="font-bold text-sm text-[#3D1E16]">Productos en el carrito ({totalCartItemsCount})</h2>
                        <button
                          onClick={() => setCart([])}
                          className="text-xs text-stone-400 hover:text-rose-700 underline"
                        >
                          Vaciar carrito
                        </button>
                      </div>

                      <div className="divide-y divide-stone-100">
                        {cart.map((item) => (
                          <div key={item.product.id} className="py-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                            <div className="flex items-center gap-4 w-full sm:w-auto">
                              <img
                                src={item.product.image}
                                alt={item.product.name}
                                className="w-20 h-20 object-cover rounded-2xl border border-[#E2D9D5] shrink-0 cursor-pointer"
                                onClick={() => handleOpenProductDetail(item.product.id)}
                              />
                              <div>
                                <span className="text-[10px] font-bold text-[#C86D51] uppercase">{item.product.category}</span>
                                <h3
                                  onClick={() => handleOpenProductDetail(item.product.id)}
                                  className="font-bold text-xs sm:text-sm text-[#3D1E16] leading-tight hover:text-[#5C1D24] cursor-pointer"
                                >
                                  {item.product.name}
                                </h3>
                                <p className="text-xs font-black text-[#5C1D24] mt-1">${item.product.price.toLocaleString()} COP</p>
                              </div>
                            </div>

                            <div className="flex items-center justify-between w-full sm:w-auto gap-6 pt-2 sm:pt-0 border-t sm:border-0 border-stone-100">
                              {/* Quantity Controls */}
                              <div className="flex items-center gap-2 bg-stone-100 p-1 rounded-xl border border-stone-300">
                                <button
                                  onClick={() => handleUpdateCartQuantity(item.product.id, -1)}
                                  className="p-1 bg-white text-stone-800 rounded-lg hover:bg-stone-200"
                                >
                                  <Minus className="w-3.5 h-3.5" />
                                </button>
                                <span className="text-xs font-bold w-6 text-center">{item.quantity}</span>
                                <button
                                  onClick={() => handleUpdateCartQuantity(item.product.id, 1)}
                                  className="p-1 bg-white text-stone-800 rounded-lg hover:bg-stone-200"
                                >
                                  <Plus className="w-3.5 h-3.5" />
                                </button>
                              </div>

                              {/* Subtotal */}
                              <div className="text-right">
                                <span className="text-[10px] text-stone-400 block">Subtotal:</span>
                                <span className="text-xs font-black text-[#3D1E16]">
                                  ${(item.product.price * item.quantity).toLocaleString()} COP
                                </span>
                              </div>

                              {/* Delete Item */}
                              <button
                                onClick={() => handleRemoveFromCart(item.product.id)}
                                className="p-1.5 text-stone-400 hover:text-rose-700 hover:bg-rose-50 rounded-xl"
                                title="Eliminar"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="flex justify-between items-center pt-2">
                      <button
                        onClick={() => setActiveView(1)}
                        className="inline-flex items-center gap-2 text-xs font-bold text-[#5C1D24] hover:underline"
                      >
                        <ArrowLeft className="w-4 h-4" />
                        <span>Continuar comprando</span>
                      </button>
                    </div>
                  </div>

                  {/* Right Column: Order Summary & Checkout Form */}
                  <div className="lg:col-span-5 space-y-6">

                    {/* Financial Summary */}
                    <div className="bg-white rounded-3xl border border-[#E2D9D5] p-6 shadow-sm space-y-4">
                      <h2 className="font-bold text-sm text-[#3D1E16] border-b border-stone-200 pb-3">
                        Resumen de la compra
                      </h2>

                      <div className="space-y-2 text-xs text-stone-600">
                        <div className="flex justify-between">
                          <span>Subtotal productos:</span>
                          <span className="font-bold text-stone-900">${cartSubtotal.toLocaleString()} COP</span>
                        </div>

                        <div className="flex justify-between">
                          <span>Envío nacional estimado:</span>
                          <span className="font-bold text-stone-900">
                            {estimatedShipping === 0 ? '¡Gratis!' : `$${estimatedShipping.toLocaleString()} COP`}
                          </span>
                        </div>

                        <div className="flex justify-between text-emerald-800 font-medium">
                          <span>Retribución comercio justo Wayúu:</span>
                          <span>100% Directo</span>
                        </div>

                        <div className="pt-3 border-t border-stone-200 flex justify-between text-sm font-black text-[#5C1D24]">
                          <span>Total a pagar:</span>
                          <span>${grandTotal.toLocaleString()} COP</span>
                        </div>
                      </div>
                    </div>

                    {/* Checkout Information Form */}
                    <form onSubmit={handleProcessOrderConfirmation} className="bg-white rounded-3xl border border-[#E2D9D5] p-6 shadow-sm space-y-4">
                      <h2 className="font-bold text-sm text-[#3D1E16] border-b border-stone-200 pb-3 flex items-center gap-2">
                        <Truck className="w-4 h-4 text-[#5C1D24]" />
                        <span>Datos de envío y contacto</span>
                      </h2>

                      <div className="space-y-3 text-xs">
                        <div>
                          <label className="block font-bold text-stone-700 mb-1">Nombre completo *</label>
                          <input
                            type="text"
                            required
                            value={checkoutForm.fullName}
                            onChange={(e) => setCheckoutForm({ ...checkoutForm, fullName: e.target.value })}
                            className="w-full p-2.5 bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                          />
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block font-bold text-stone-700 mb-1">Teléfono *</label>
                            <input
                              type="text"
                              required
                              value={checkoutForm.phone}
                              onChange={(e) => setCheckoutForm({ ...checkoutForm, phone: e.target.value })}
                              className="w-full p-2.5 bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                            />
                          </div>

                          <div>
                            <label className="block font-bold text-stone-700 mb-1">Correo electrónico *</label>
                            <input
                              type="email"
                              required
                              value={checkoutForm.email}
                              onChange={(e) => setCheckoutForm({ ...checkoutForm, email: e.target.value })}
                              className="w-full p-2.5 bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block font-bold text-stone-700 mb-1">Ciudad / Municipio *</label>
                            <input
                              type="text"
                              required
                              value={checkoutForm.city}
                              onChange={(e) => setCheckoutForm({ ...checkoutForm, city: e.target.value })}
                              className="w-full p-2.5 bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                            />
                          </div>

                          <div>
                            <label className="block font-bold text-stone-700 mb-1">Departamento *</label>
                            <input
                              type="text"
                              required
                              value={checkoutForm.department}
                              onChange={(e) => setCheckoutForm({ ...checkoutForm, department: e.target.value })}
                              className="w-full p-2.5 bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                            />
                          </div>
                        </div>

                        <div>
                          <label className="block font-bold text-stone-700 mb-1">Dirección de entrega *</label>
                          <input
                            type="text"
                            required
                            value={checkoutForm.address}
                            onChange={(e) => setCheckoutForm({ ...checkoutForm, address: e.target.value })}
                            className="w-full p-2.5 bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                          />
                        </div>

                        <div>
                          <label className="block font-bold text-stone-700 mb-1">Notas adicionales para la tejedora</label>
                          <textarea
                            rows={2}
                            placeholder="Ej: Empaque especial para regalo o combinación de colores preferida..."
                            value={checkoutForm.notes}
                            onChange={(e) => setCheckoutForm({ ...checkoutForm, notes: e.target.value })}
                            className="w-full p-2.5 bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                          ></textarea>
                        </div>
                      </div>

                      <div className="pt-2">
                        <button
                          type="submit"
                          className="w-full py-3.5 bg-[#5C1D24] hover:bg-[#3D1E16] text-white font-bold text-xs sm:text-sm rounded-2xl shadow-md transition-colors flex items-center justify-center gap-2"
                        >
                          <CheckCircle2 className="w-5 h-5" />
                          <span>Finalizar compra (Modo demostración)</span>
                        </button>
                      </div>
                    </form>

                  </div>

                </div>
              ) : (
                <div className="bg-white p-12 rounded-3xl border border-[#E2D9D5] text-center space-y-4 max-w-lg mx-auto">
                  <ShoppingCart className="w-12 h-12 text-stone-300 mx-auto" />
                  <h2 className="text-lg font-bold text-stone-800">Tu carrito está vacío</h2>
                  <p className="text-xs text-stone-500">Explora nuestro catálogo para seleccionar hermosas piezas artesanales Wayúu.</p>
                  <button
                    onClick={() => setActiveView(1)}
                    className="px-6 py-3 bg-[#5C1D24] text-white rounded-2xl text-xs font-bold"
                  >
                    Ir al catálogo
                  </button>
                </div>
              )}
            </div>
          )}

          {/* =================================================================== */}
          {/* VISTA 4: MI CUENTA Y PEDIDOS                                       */}
          {/* =================================================================== */}
          {activeView === 4 && (
            <div className="space-y-8 max-w-5xl mx-auto">
              <div>
                <h1 className="text-2xl sm:text-3xl font-black text-[#5C1D24] tracking-tight">
                  Mi Cuenta y Mis Pedidos
                </h1>
                <p className="text-xs text-stone-600 mt-1">Administra tu perfil personal y haz seguimiento a tus compras artesanales</p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">

                {/* Left Column: Profile Card */}
                <div className="lg:col-span-4 bg-white rounded-3xl border border-[#E2D9D5] p-6 shadow-sm space-y-6">
                  <div className="text-center space-y-2">
                    <div className="w-20 h-20 bg-[#5C1D24] text-white rounded-full flex items-center justify-center font-black text-2xl mx-auto shadow-md border-4 border-[#FBEAEB]">
                      {userProfile.name.split(' ').map((n) => n[0]).join('')}
                    </div>
                    <h2 className="font-extrabold text-base text-[#3D1E16]">{userProfile.name}</h2>
                    <span className="inline-block bg-[#FBEAEB] text-[#5C1D24] text-[10px] font-black uppercase px-3 py-1 rounded-full border border-[#E2D9D5]">
                      Cliente Wayúu
                    </span>
                  </div>

                  <div className="space-y-3 text-xs text-stone-600 border-t border-stone-100 pt-4">
                    <div className="flex items-center gap-2.5">
                      <Mail className="w-4 h-4 text-[#C86D51] shrink-0" />
                      <span className="truncate">{userProfile.email}</span>
                    </div>

                    <div className="flex items-center gap-2.5">
                      <Phone className="w-4 h-4 text-[#C86D51] shrink-0" />
                      <span>{userProfile.phone}</span>
                    </div>

                    <div className="flex items-center gap-2.5">
                      <MapPin className="w-4 h-4 text-[#C86D51] shrink-0" />
                      <span>{userProfile.address}, {userProfile.city}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setEditProfileForm(userProfile);
                      setIsEditProfileModalOpen(true);
                    }}
                    className="w-full py-2.5 bg-[#FBEAEB] text-[#5C1D24] hover:bg-[#5C1D24] hover:text-white rounded-xl text-xs font-bold transition-colors flex items-center justify-center gap-2 border border-[#E2D9D5]"
                  >
                    <Edit className="w-4 h-4" />
                    <span>Editar datos personales</span>
                  </button>
                </div>

                {/* Right Column: User Orders List */}
                <div className="lg:col-span-8 bg-white rounded-3xl border border-[#E2D9D5] p-6 shadow-sm space-y-6">
                  <div className="flex items-center justify-between border-b border-stone-200 pb-3">
                    <h2 className="font-bold text-sm text-[#3D1E16] flex items-center gap-2">
                      <Package className="w-4 h-4 text-[#5C1D24]" />
                      <span>Mis pedidos registrados ({myOrders.length})</span>
                    </h2>
                    <span className="text-xs text-stone-400">Historial exclusivo</span>
                  </div>

                  {myOrders.length > 0 ? (
                    <div className="space-y-6">
                      {myOrders.map((order) => (
                        <div key={order.id} className="border border-[#E2D9D5] rounded-2xl p-5 space-y-4 bg-[#FDFBF7]/50">

                          {/* Order Header */}
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-stone-200/60 pb-3">
                            <div>
                              <span className="font-black text-sm text-[#5C1D24]">{order.id}</span>
                              <span className="text-xs text-stone-400 block sm:inline sm:ml-2">Fecha: {order.date}</span>
                            </div>

                            <div className="flex items-center gap-3">
                              <span className={`text-[10px] font-extrabold px-3 py-1 rounded-full border ${
                                order.status === 'Entregado'
                                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                                  : order.status === 'Solicitud Cancelación'
                                  ? 'bg-rose-50 text-rose-800 border-rose-200'
                                  : 'bg-amber-50 text-amber-800 border-amber-200'
                              }`}>
                                {order.status}
                              </span>

                              <span className="text-sm font-black text-[#3D1E16]">
                                ${order.total.toLocaleString()} COP
                              </span>
                            </div>
                          </div>

                          {/* Purchased Items List */}
                          <div className="space-y-2">
                            <p className="text-[10px] font-bold uppercase text-stone-400">Productos en el pedido:</p>
                            {order.items.map((item, idx) => (
                              <div key={idx} className="flex items-center justify-between text-xs text-stone-700 bg-white p-2.5 rounded-xl border border-stone-100">
                                <div className="flex items-center gap-3">
                                  <img
                                    src={item.product.image}
                                    alt={item.product.name}
                                    className="w-10 h-10 object-cover rounded-lg border border-stone-200"
                                  />
                                  <div>
                                    <p className="font-bold text-stone-900">{item.product.name}</p>
                                    <p className="text-[10px] text-stone-400">Cantidad: {item.quantity}</p>
                                  </div>
                                </div>
                                <span className="font-bold">${item.subtotal.toLocaleString()} COP</span>
                              </div>
                            ))}
                          </div>

                          {/* Expandable Tracking Timeline Toggle */}
                          <div className="pt-2 flex flex-wrap items-center justify-between gap-2">
                            <button
                              onClick={() => setExpandedOrderId(expandedOrderId === order.id ? null : order.id)}
                              className="text-xs font-bold text-[#5C1D24] hover:underline inline-flex items-center gap-1"
                            >
                              <Clock className="w-3.5 h-3.5" />
                              <span>{expandedOrderId === order.id ? 'Ocultar seguimiento' : 'Ver historial de seguimiento'}</span>
                              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${expandedOrderId === order.id ? 'rotate-180' : ''}`} />
                            </button>

                            {order.canCancel && order.status !== 'Solicitud Cancelación' && (
                              <button
                                onClick={() => handleRequestOrderCancellation(order.id)}
                                className="px-3 py-1 bg-rose-50 hover:bg-rose-100 text-rose-800 rounded-xl text-xs font-bold border border-rose-200 transition-colors"
                              >
                                Solicitar cancelación
                              </button>
                            )}
                          </div>

                          {/* Timeline Drawer Component */}
                          {expandedOrderId === order.id && (
                            <div className="p-4 bg-white rounded-2xl border border-[#E2D9D5] space-y-3 mt-2 animate-fadeIn">
                              <p className="text-xs font-bold text-[#3D1E16] uppercase tracking-wider">Seguimiento artesanal en tiempo real:</p>

                              <div className="space-y-3 text-xs pl-2 border-l-2 border-[#5C1D24]">
                                {order.timeline.map((step, idx) => (
                                  <div key={idx} className="relative pl-4">
                                    <span className={`absolute -left-[21px] top-0.5 w-3 h-3 rounded-full border-2 border-white ${
                                      step.completed ? 'bg-[#5C1D24]' : 'bg-stone-300'
                                    }`}></span>
                                    <p className={`font-bold ${step.completed ? 'text-stone-900' : 'text-stone-400'}`}>
                                      {step.title}
                                    </p>
                                    <p className="text-[10px] text-stone-400">{step.date}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-stone-400 space-y-2">
                      <Package className="w-8 h-8 mx-auto text-stone-300" />
                      <p className="text-xs">No tienes pedidos registrados en este momento.</p>
                    </div>
                  )}
                </div>

              </div>
            </div>
          )}

          {/* =================================================================== */}
          {/* VISTA SECUNDARIA CONTEXTUAL: DETALLE DEL PRODUCTO                  */}
          {/* =================================================================== */}
          {activeView === 'detail' && (
            <div className="space-y-8 max-w-5xl mx-auto">

              {/* Back Button to previous screen */}
              <button
                onClick={() => setActiveView(previousView || 1)}
                className="inline-flex items-center gap-2 text-xs font-bold text-[#5C1D24] hover:underline bg-[#FBEAEB] px-4 py-2 rounded-xl border border-[#E2D9D5]"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>
                  Regresar {previousView === 2 ? 'a mis favoritos' : 'al catálogo'}
                </span>
              </button>

              {/* Main Product Card Detail */}
              <div className="bg-white rounded-3xl border border-[#E2D9D5] shadow-md overflow-hidden grid grid-cols-1 lg:grid-cols-12 gap-8 p-6 sm:p-8">

                {/* Photo Showcase & Favorite Button Overlay */}
                <div className="lg:col-span-6 space-y-4">
                  <div className="relative h-80 sm:h-96 rounded-2xl overflow-hidden border border-[#E2D9D5] bg-stone-100">
                    <img
                      src={currentProduct.image}
                      alt={currentProduct.name}
                      className="w-full h-full object-cover"
                    />
                    <span className="absolute top-4 left-4 bg-[#5C1D24] text-white text-xs font-black uppercase tracking-wider px-3.5 py-1.5 rounded-full shadow">
                      {currentProduct.category}
                    </span>

                    <button
                      onClick={(e) => handleToggleFavorite(currentProduct.id, e)}
                      className={`absolute top-4 right-4 p-3 rounded-full backdrop-blur-md shadow-lg transition-transform hover:scale-110 ${
                        favoriteProductIds.includes(currentProduct.id)
                          ? 'bg-white text-[#5C1D24]'
                          : 'bg-black/30 text-white hover:bg-white hover:text-[#5C1D24]'
                      }`}
                      title={favoriteProductIds.includes(currentProduct.id) ? 'Quitar de favoritos' : 'Agregar a favoritos'}
                    >
                      <Heart className={`w-5 h-5 ${favoriteProductIds.includes(currentProduct.id) ? 'fill-[#5C1D24]' : ''}`} />
                    </button>
                  </div>

                  <div className="p-4 bg-[#FDFBF7] rounded-2xl border border-[#E2D9D5] space-y-2">
                    <p className="text-xs font-bold text-[#5C1D24] uppercase tracking-wider">Compromiso de Autenticidad</p>
                    <p className="text-xs text-stone-600 leading-relaxed">
                      Cada una de nuestras piezas incluye el sello de origen Wayúu y garantía de retribución directa a las comunidades indígenas de La Guajira.
                    </p>
                  </div>
                </div>

                {/* Product Info & Controls */}
                <div className="lg:col-span-6 space-y-6 flex flex-col justify-between">
                  <div className="space-y-4">
                    <div>
                      <span className="text-xs font-bold text-[#C86D51] uppercase tracking-wider block">Artesanía Wayúu</span>
                      <h1 className="text-2xl sm:text-3xl font-black text-[#3D1E16] mt-1 leading-tight">
                        {currentProduct.name}
                      </h1>
                    </div>

                    {/* Price & Stock Badge */}
                    <div className="flex items-center justify-between p-4 bg-[#FBEAEB] rounded-2xl border border-[#E2D9D5]">
                      <div>
                        <span className="text-xs text-stone-500 block">Precio total:</span>
                        <span className="text-2xl font-black text-[#5C1D24]">
                          ${currentProduct.price.toLocaleString()} COP
                        </span>
                      </div>

                      <div className="text-right">
                        <span className="text-xs text-stone-500 block">Disponibilidad:</span>
                        <span className="text-xs font-extrabold text-emerald-800 bg-emerald-100 px-3 py-1 rounded-full border border-emerald-200">
                          {currentProduct.stock} unidades disponibles
                        </span>
                      </div>
                    </div>

                    {/* Descriptions */}
                    <div className="space-y-2 text-xs text-stone-700 leading-relaxed">
                      <p className="font-bold text-[#3D1E16] text-sm">Descripción del tejido:</p>
                      <p>{currentProduct.fullDescription}</p>
                    </div>

                    {/* Cultural Symbolism */}
                    <div className="p-4 bg-amber-50/60 border border-amber-200 rounded-2xl space-y-1">
                      <p className="text-xs font-bold text-[#3D1E16] flex items-center gap-1.5">
                        <Sparkles className="w-4 h-4 text-[#C86D51]" />
                        <span>Simbolismo Kanaas:</span>
                      </p>
                      <p className="text-xs text-stone-600 italic">"{currentProduct.symbolism}"</p>
                    </div>

                    {/* Weaver Profile Card */}
                    <div className="p-4 bg-[#FDFBF7] rounded-2xl border border-[#E2D9D5] space-y-2">
                      <p className="text-xs font-bold uppercase tracking-wider text-[#5C1D24] flex items-center gap-2">
                        <User className="w-4 h-4" />
                        <span>Ficha de la tejedora responsable</span>
                      </p>

                      <div className="grid grid-cols-2 gap-2 text-xs text-stone-700 pt-1">
                        <div>
                          <span className="text-stone-400 block text-[10px]">Artesana:</span>
                          <strong className="text-stone-900">{currentProduct.weaver.name}</strong>
                        </div>
                        <div>
                          <span className="text-stone-400 block text-[10px]">Ranchería:</span>
                          <strong className="text-stone-900">{currentProduct.weaver.rancheria}</strong>
                        </div>
                        <div>
                          <span className="text-stone-400 block text-[10px]">Experiencia:</span>
                          <strong className="text-stone-900">{currentProduct.weaver.experienceYears} años tejiendo</strong>
                        </div>
                        <div>
                          <span className="text-stone-400 block text-[10px]">Técnica:</span>
                          <strong className="text-stone-900">{currentProduct.weaver.technique}</strong>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Quantity Controls & Actions */}
                  <div className="space-y-3 pt-4 border-t border-stone-200">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-stone-700">Seleccionar cantidad:</span>

                      {/* Stock Limited Quantity Selector */}
                      <div className="flex items-center gap-3 bg-stone-100 p-1.5 rounded-xl border border-stone-300">
                        <button
                          onClick={() => setDetailQuantity((q) => Math.max(1, q - 1))}
                          className="p-1.5 bg-white text-stone-800 rounded-lg hover:bg-stone-200"
                          title="Disminuir"
                        >
                          <Minus className="w-4 h-4" />
                        </button>

                        <span className="text-sm font-black w-8 text-center">{detailQuantity}</span>

                        <button
                          onClick={() => {
                            if (detailQuantity < currentProduct.stock) {
                              setDetailQuantity((q) => q + 1);
                            } else {
                              showToast(`Existencias máximas alcanzadas (${currentProduct.stock} unidades).`);
                            }
                          }}
                          className="p-1.5 bg-white text-stone-800 rounded-lg hover:bg-stone-200"
                          title="Aumentar"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    <div className="flex gap-3">
                      <button
                        onClick={(e) => handleToggleFavorite(currentProduct.id, e)}
                        className={`p-3.5 rounded-2xl border transition-colors flex items-center justify-center shrink-0 ${
                          favoriteProductIds.includes(currentProduct.id)
                            ? 'bg-[#FBEAEB] border-[#5C1D24] text-[#5C1D24]'
                            : 'bg-stone-100 border-stone-300 text-stone-600 hover:bg-stone-200'
                        }`}
                        title={favoriteProductIds.includes(currentProduct.id) ? 'Quitar de favoritos' : 'Guardar en favoritos'}
                      >
                        <Heart className={`w-5 h-5 ${favoriteProductIds.includes(currentProduct.id) ? 'fill-[#5C1D24]' : ''}`} />
                      </button>

                      <button
                        onClick={(e) => handleAddToCart(currentProduct, detailQuantity, e)}
                        className="flex-1 py-3.5 bg-[#5C1D24] hover:bg-[#3D1E16] text-white font-bold text-xs sm:text-sm rounded-2xl shadow-md transition-colors flex items-center justify-center gap-2"
                      >
                        <ShoppingCart className="w-5 h-5" />
                        <span>Agregar al carrito ({detailQuantity} unid.)</span>
                      </button>
                    </div>
                  </div>

                </div>

              </div>
            </div>
          )}

        </main>
      </div>

      {/* =================================================================== */}
      {/* MODAL 1: CONFIRMACIÓN CIERRE DE SESIÓN                             */}
      {/* =================================================================== */}
      {isLogoutModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4 text-center">
            <div className="w-12 h-12 rounded-full bg-[#FBEAEB] text-[#5C1D24] flex items-center justify-center mx-auto">
              <LogOut className="w-6 h-6" />
            </div>

            <div>
              <h3 className="font-black text-[#3D1E16] text-base">¿Cerrar sesión de cliente?</h3>
              <p className="text-xs text-stone-500 mt-1">
                Saldrás de la sesión interactiva del rol Cliente. Puedes ingresar de nuevo en cualquier momento.
              </p>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setIsLogoutModalOpen(false)}
                className="flex-1 py-2.5 border border-stone-300 rounded-xl text-xs font-semibold text-stone-700 hover:bg-stone-100"
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirmLogout}
                className="flex-1 py-2.5 bg-[#5C1D24] hover:bg-[#3D1E16] text-white rounded-xl text-xs font-bold"
              >
                Sí, cerrar sesión
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 2: EDITAR PERFIL DE USUARIO                                  */}
      {/* =================================================================== */}
      {isEditProfileModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-[#E2D9D5] space-y-4">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <h3 className="font-extrabold text-stone-900 text-sm flex items-center gap-2">
                <Edit className="w-4 h-4 text-[#5C1D24]" />
                <span>Editar datos de mi perfil</span>
              </h3>
              <button onClick={() => setIsEditProfileModalOpen(false)} className="text-stone-400 hover:text-stone-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveEditedProfile} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-stone-700 mb-1">Nombre completo</label>
                <input
                  type="text"
                  required
                  value={editProfileForm.name}
                  onChange={(e) => setEditProfileForm({ ...editProfileForm, name: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                />
              </div>

              <div>
                <label className="block font-bold text-stone-700 mb-1">Correo electrónico</label>
                <input
                  type="email"
                  required
                  value={editProfileForm.email}
                  onChange={(e) => setEditProfileForm({ ...editProfileForm, email: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                />
              </div>

              <div>
                <label className="block font-bold text-stone-700 mb-1">Teléfono</label>
                <input
                  type="text"
                  required
                  value={editProfileForm.phone}
                  onChange={(e) => setEditProfileForm({ ...editProfileForm, phone: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                />
              </div>

              <div>
                <label className="block font-bold text-stone-700 mb-1">Dirección de entrega</label>
                <input
                  type="text"
                  required
                  value={editProfileForm.address}
                  onChange={(e) => setEditProfileForm({ ...editProfileForm, address: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                />
              </div>

              <div>
                <label className="block font-bold text-stone-700 mb-1">Ciudad</label>
                <input
                  type="text"
                  required
                  value={editProfileForm.city}
                  onChange={(e) => setEditProfileForm({ ...editProfileForm, city: e.target.value })}
                  className="w-full p-2.5 bg-[#FDFBF7] border border-[#E2D9D5] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#5C1D24]"
                />
              </div>

              <div className="pt-2 flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={() => setIsEditProfileModalOpen(false)}
                  className="px-4 py-2 border border-stone-300 rounded-xl font-semibold text-stone-700"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-[#5C1D24] text-white font-bold rounded-xl shadow"
                >
                  Guardar cambios
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 3: PANTALLA ÉXITO COMPRA DEMOSTRACIÓN                        */}
      {/* =================================================================== */}
      {isPurchaseCompletedModalOpen && recentCompletedOrder && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-8 shadow-2xl border border-[#E2D9D5] text-center space-y-6">
            <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-10 h-10" />
            </div>

            <div className="space-y-2">
              <span className="bg-[#FBEAEB] text-[#5C1D24] text-[10px] font-black uppercase px-3 py-1 rounded-full border border-[#E2D9D5]">
                Modo demostración exitoso
              </span>
              <h2 className="text-2xl font-black text-[#3D1E16]">¡Compra realizada con éxito!</h2>
              <p className="text-xs text-stone-500">
                Tu orden ha sido registrada en el sistema de demostración de la Tienda Wayúu.
              </p>
            </div>

            <div className="p-4 bg-[#FDFBF7] rounded-2xl border border-[#E2D9D5] text-left text-xs space-y-2">
              <div className="flex justify-between font-bold">
                <span className="text-stone-500">Número de pedido:</span>
                <span className="text-[#5C1D24]">{recentCompletedOrder.id}</span>
              </div>
              <div className="flex justify-between font-bold">
                <span className="text-stone-500">Total registrado:</span>
                <span className="text-stone-900">${recentCompletedOrder.total.toLocaleString()} COP</span>
              </div>
              <div className="flex justify-between">
                <span className="text-stone-500">Destinatario:</span>
                <span className="font-medium text-stone-800">{recentCompletedOrder.shippingInfo.fullName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-stone-500">Dirección:</span>
                <span className="font-medium text-stone-800">{recentCompletedOrder.shippingInfo.address}, {recentCompletedOrder.shippingInfo.city}</span>
              </div>
            </div>

            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-[11px] text-amber-900 text-left">
              <strong>Nota de la simulación:</strong> No se han realizado cobros reales ni transacciones bancarias. La orden ha sido guardada en tu panel personal "Mi cuenta y pedidos".
            </div>

            <button
              onClick={() => {
                setIsPurchaseCompletedModalOpen(false);
                setActiveView(4);
              }}
              className="w-full py-3.5 bg-[#5C1D24] hover:bg-[#3D1E16] text-white font-bold text-xs sm:text-sm rounded-2xl shadow-md"
            >
              Ver mis pedidos y seguimiento
            </button>
          </div>
        </div>
      )}

    </div>
  );
}