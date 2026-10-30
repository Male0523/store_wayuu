import React, { useState, useMemo, useEffect } from 'react';
import { useUserSession } from './frontend/src/context/user-context';
import {
  ShoppingBag,
  Heart,
  Shield,
  Check,
  Sparkles,
  User,
  Mail,
  Lock,
  Phone,
  ArrowRight,
  Eye,
  EyeOff,
  Search,
  Menu,
  X,
  Globe,
  MapPin,
  ChevronRight,
  Award,
  Compass,
  Layers,
  Feather,
  HelpCircle,
  FileText,
  CheckCircle2,
  ChevronLeft,
  MessageSquare,
  Send,
  Star,
  ExternalLink,
  Info,
  Clock
} from 'lucide-react';

// ============================================================================
// DATA DE DEMOSTRACIÓN (PRODUCTOS, ARTESANAS Y CONTENIDO CULTURAL WAYÚU)
// ============================================================================

interface Product {
  id: string;
  name: string;
  category: string;
  price: number;
  image: string;
  shortDescription: string;
  fullDescription: string;
  technique: string;
  artisan: string;
  rancheria: string;
  material: string;
  symbolism: string;
}

interface Artisan {
  id: string;
  name: string;
  rancheria: string;
  experienceYears: number;
  specialty: string;
  quote: string;
  image: string;
  clan: string;
}

const CATEGORIES = [
  'Todas',
  'Mochilas (Susu)',
  'Mantas Wayúu',
  'Chinchorros (Anatas)',
  'Sombreros (Kumu)',
  'Bisutería (Kanaas)',
  'Calzado y Accesorios'
];

const PRODUCTS: Product[] = [
  {
    id: 'PRD-WAY-001',
    name: 'Mochila Susu Kanaas Sol Naciente',
    category: 'Mochilas (Susu)',
    price: 320000,
    image: 'https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&q=80&w=800',
    shortDescription: 'Tejida a una sola hebra con símbolos geométricos Kanaas que evocan el amanecer.',
    fullDescription: 'Esta emblemática mochila Susu representa la cosmovisión tradicional Wayúu. Cada hilo es seleccionado minuciosamente y tejido a una hebra durante semanas de dedicada labor en la enramada. Cuenta con una gasa paleteada de alta resistencia y cordón trenzado con borlas esponjosas.',
    technique: 'Tejido a una hebra (Susu wane puliruü)',
    artisan: 'Marta Uriana',
    rancheria: 'Ranchería Mayapo, Manaure',
    material: 'Hilo acrílico de alta durabilidad y solidez de color',
    symbolism: 'El diseño Kanaas "Jiwatou" simula el rastro del sol sobre las dunas y la sabiduría transmitida entre generaciones.'
  },
  {
    id: 'PRD-WAY-002',
    name: 'Manta Wayúu Elegante Atardecer Terracota',
    category: 'Mantas Wayúu',
    price: 380000,
    image: 'https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&q=80&w=800',
    shortDescription: 'Manta holgada de seda fría con bordados sutiles en escote y caída fluida.',
    fullDescription: 'Confeccionada en tela liviana, fresca y de excelente caída, ideal para climas cálidos y eventos especiales. Presenta detalles de pechera bordada a mano con la técnica nido de abeja tradicional de La Guajira.',
    technique: 'Pliegues y bordados a mano en telar',
    artisan: 'Aura Barros Pushaina',
    rancheria: 'Ranchería Cabo de la Vela',
    material: 'Seda fría y seda dacrón de textura suave',
    symbolism: 'El color terracota rinde tributo a la tierra arcillosa y la calidez del paisaje guajiro.'
  },
  {
    id: 'PRD-WAY-003',
    name: 'Chinchorro Anatas Pulowi Doble',
    category: 'Chinchorros (Anatas)',
    price: 1450000,
    image: 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&q=80&w=800',
    shortDescription: 'Chinchorro de cabecera con textura elástica de panal y cañuelotas caladas.',
    fullDescription: 'El chinchorro es la máxima representación del confort y lujo textil Wayúu. A diferencia de una hamaca tradicional, su tejido de malla abierta permite que el aire fluya libremente, brindando un descanso fresco. Incluye faldones laterales (cañuelotas) elaborados a mano con diseños geométricos complejos.',
    technique: 'Tejido suelto de malla elástica y cañuela calada',
    artisan: 'Rosa Pushaina',
    rancheria: 'Ranchería Uribia Central',
    material: 'Hilo hilado grueso de algodón y acrílico superior',
    symbolism: 'La cañuela imita la constelación nocturna y las redes del mar que alimentan a la comunidad.'
  },
  {
    id: 'PRD-WAY-004',
    name: 'Sombrero Kumu Mawisa Tradicional',
    category: 'Sombreros (Kumu)',
    price: 1200000 / 10, // 120,000 COP
    image: 'https://images.unsplash.com/photo-1521369909029-2afed882baee?auto=format&fit=crop&q=80&w=800',
    shortDescription: 'Tejido finamente en paja Mawisa recolectada en las dunas de la alta Guajira.',
    fullDescription: 'Sombrero protector para el intenso sol del desierto. La paja Mawisa es trenzada a mano creando una estructura liviana y resistente. Viene decorado con una cinta tejida en gasa con motivos multicolores.',
    technique: 'Sarga e hileras trenzadas en fibra Mawisa',
    artisan: 'Sonia Epinayú',
    rancheria: 'Ranchería Manaure',
    material: 'Fibra vegetal natural Mawisa y cinta acrílica',
    symbolism: 'La copa circular simboliza el astro solar que guía el caminar diario del pueblo Wayúu.'
  },
  {
    id: 'PRD-WAY-005',
    name: 'Pulsera Kanaas Iwouya (Estrella de Lluvia)',
    category: 'Bisutería (Kanaas)',
    price: 48000,
    image: 'https://images.unsplash.com/photo-1611591475179-420dac0319db?auto=format&fit=crop&q=80&w=800',
    shortDescription: 'Brazalete ajustador tejido con hilos pulidos y patrón de la estrella vespertina.',
    fullDescription: 'Un accesorio elegante y cargado de significado. Tejida de forma artesanal con hilo delgado que no decolora. Su cierre graduable se adapta cómodamente a cualquier muñeca.',
    technique: 'Tejido en peineta de telar pequeño',
    artisan: 'Luz Marina Jayaliyu',
    rancheria: 'Ranchería Maicao',
    material: 'Hilo fino mercerizado',
    symbolism: 'Iwouya representa la estrella que anuncia el florecer del desierto con la llegada de las lluvias.'
  },
  {
    id: 'PRD-WAY-006',
    name: 'Calzado Alpargatas Wayúu Kanaas',
    category: 'Calzado y Accesorios',
    price: 165000,
    image: 'https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&q=80&w=800',
    shortDescription: 'Alpargatas tradicionales con capellada tejida a mano y suela confort.',
    fullDescription: 'El calzado tradicional de la mujer y el hombre guajiro renovado con suela cómoda para uso diario. Capellada superior tejida con símbolos Kanaas e hilos de colores vibrantes.',
    technique: 'Tejido denso en capellada y montaje artesanal',
    artisan: 'Kenia Iguarán',
    rancheria: 'Ranchería Riohacha',
    material: 'Capellada acrílica tejida, suela sintética de alta fricción',
    symbolism: 'Protección para los pies que recorren los senderos de arena de la península.'
  }
];

const ARTISANS: Artisan[] = [
  {
    id: 'ART-01',
    name: 'Marta Uriana',
    rancheria: 'Ranchería Mayapo',
    experienceYears: 24,
    specialty: 'Mochilas Susu a una hebra y gasas paleteadas',
    quote: 'El tejido es nuestro lenguaje silencioso. A través de las manos expresamos nuestras alegrías, vivencias y el respeto por nuestros ancestros.',
    image: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=600',
    clan: 'Casta Uriana (Tigre)'
  },
  {
    id: 'ART-02',
    name: 'Aura Barros Pushaina',
    rancheria: 'Ranchería Cabo de la Vela',
    experienceYears: 30,
    specialty: 'Mantas tradicionales y vestidos ceremoniales',
    quote: 'Aprendí a tejer en mi encierro de señorita con mi abuela. Cada manta lleva el viento del mar y la dignidad de la mujer Wayúu.',
    image: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&q=80&w=600',
    clan: 'Casta Pushaina (Warrat - Culebra sabanera)'
  },
  {
    id: 'ART-03',
    name: 'Rosa Pushaina Epinayú',
    rancheria: 'Ranchería Uribia',
    experienceYears: 18,
    specialty: 'Chinchorros de cabecera y cañuelotas complejas',
    quote: 'Un chinchorro requiere meses de paciencia y dedicación. Cuando alguien descansa en él, se abriga con la paz de nuestro territorio.',
    image: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&q=80&w=600',
    clan: 'Casta Epinayú (Venado)'
  }
];

export default function App() {
  const { login, register, user } = useUserSession();
  // Estado de navegación entre las tres vistas principales solicitadas
  const [currentView, setCurrentView] = useState<'home' | 'login' | 'register'>('home');

  // Estado del Modal para "Ver Producto" (Muestra detalle de producto sin ser una 4ta vista principal)
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  // Filtros de categoría y búsqueda en la tienda
  const [selectedCategory, setSelectedCategory] = useState<string>('Todas');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Formulario de Iniciar Sesión
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [loginSimulationMessage, setLoginSimulationMessage] = useState<string | null>(null);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Formulario de Registro
  const [regFirstName, setRegFirstName] = useState('');
  const [regLastName, setRegLastName] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');
  const [regAcceptTerms, setRegAcceptTerms] = useState(false);
  const [showRegPassword, setShowRegPassword] = useState(false);

  // Errores de validación de Registro
  const [regErrors, setRegErrors] = useState<{ [key: string]: string }>({});
  const [regSuccess, setRegSuccess] = useState(false);

  // Estado de envío del formulario de contacto demostrativo
  const [contactSent, setContactSent] = useState(false);

  // Estado del menú móvil para la barra de navegación
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Scroll automático al tope al cambiar de vista
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [currentView]);

  // Filtrado de productos por categoría y búsqueda
  const filteredProducts = useMemo(() => {
    return PRODUCTS.filter((p) => {
      const matchesCategory = selectedCategory === 'Todas' || p.category === selectedCategory;
      const matchesSearch =
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.shortDescription.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.artisan.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [selectedCategory, searchQuery]);

  // Navegación suave por secciones dentro de la Página Principal
  const scrollToSection = (sectionId: string) => {
    if (currentView !== 'home') {
      setCurrentView('home');
      setTimeout(() => {
        const element = document.getElementById(sectionId);
        if (element) element.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } else {
      const element = document.getElementById(sectionId);
      if (element) element.scrollIntoView({ behavior: 'smooth' });
    }
    setIsMobileMenuOpen(false);
  };

  const goToRolePanel = (role: string) => {
    const destinations: Record<string, string> = {
      customer: '/cliente',
      craftswoman: '/tejedora',
      admin: '/admin',
      superadmin: '/superadmin',
    };
    const destination = destinations[role];
    if (!destination) return;
    window.history.pushState(null, '', destination);
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail || !loginPassword) return;
    setLoginError(null);
    try {
      const account = await login(loginEmail, loginPassword);
      setLoginSimulationMessage('Sesión iniciada correctamente.');
      goToRolePanel(account.role);
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'No fue posible iniciar sesión.');
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errors: { [key: string]: string } = {};

    if (!regFirstName.trim()) errors.firstName = 'El nombre es obligatorio.';
    if (!regLastName.trim()) errors.lastName = 'Los apellidos son obligatorios.';
    if (!regUsername.trim()) errors.username = 'El nombre de usuario es obligatorio.';
    
    if (!regEmail.trim()) {
      errors.email = 'El correo electrónico es obligatorio.';
    } else if (!/\S+@\S+\.\S+/.test(regEmail)) {
      errors.email = 'Introduce una dirección de correo electrónico válida (ejemplo@dominio.com).';
    }

    if (!regPhone.trim()) errors.phone = 'El número telefónico es obligatorio.';

    if (!regPassword) {
      errors.password = 'La contraseña es obligatoria.';
    } else if (regPassword.length < 8) {
      errors.password = 'La contraseña debe tener al menos 8 caracteres.';
    }

    if (regPassword !== regConfirmPassword) {
      errors.confirmPassword = 'Las contraseñas no coinciden.';
    }

    if (!regAcceptTerms) {
      errors.terms = 'Debes aceptar los términos y condiciones de servicio para continuar.';
    }

    setRegErrors(errors);

    if (Object.keys(errors).length > 0) return;
    try {
      const account = await register({
        name: `${regFirstName.trim()} ${regLastName.trim()}`,
        username: regUsername.trim(),
        email: regEmail.trim(),
        phone: regPhone.trim(),
        password: regPassword,
      });
      setRegSuccess(true);
      goToRolePanel(account.role);
    } catch (error) {
      setRegErrors({ server: error instanceof Error ? error.message : 'No fue posible crear la cuenta.' });
    }
  };

  return (
    <div className="min-h-screen bg-[#FDFBF7] text-[#3D1E16] font-sans selection:bg-[#C85A32] selection:text-white flex flex-col">
      
      {/* Patrón Geométrico Sutil Wayúu Kanaas en Encabezado Superior */}
      <div className="h-1.5 bg-gradient-to-r from-[#5C1D24] via-[#C85A32] to-[#A03C1B]"></div>

      {/* ========================================================================= */}
      {/* BARRA DE NAVEGACIÓN SUPERIOR (ELEGANTE Y CLARA) */}
      {/* ========================================================================= */}
      <header className="sticky top-0 z-40 bg-[#FAF6F0]/95 backdrop-blur-md border-b border-[#EFE6DC] shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          
          {/* Logo Artesanal Wayúu */}
          <div
            onClick={() => setCurrentView('home')}
            className="flex items-center gap-3 cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-2xl bg-[#5C1D24] text-[#FDFBF7] flex items-center justify-center shadow-md border border-[#A03C1B]/20 group-hover:bg-[#C85A32] transition-colors">
              <Feather className="w-5 h-5 text-[#FDFBF7]" />
            </div>
            <div>
              <span className="text-xl font-extrabold tracking-wide text-[#3D1E16] block leading-tight font-serif">
                WAYÚU
              </span>
              <span className="text-[10px] uppercase font-bold tracking-widest text-[#C85A32] block">
                Tienda Artesanal
              </span>
            </div>
          </div>

          {/* Menú Desktop (Visible en pantallas medianas/grandes) */}
          <nav className="hidden md:flex items-center gap-8 text-xs font-bold uppercase tracking-wider text-[#3D1E16]">
            <button
              onClick={() => scrollToSection('hero')}
              className="hover:text-[#C85A32] transition-colors py-1 border-b-2 border-transparent hover:border-[#C85A32]"
            >
              Inicio
            </button>
            <button
              onClick={() => scrollToSection('quienes-somos')}
              className="hover:text-[#C85A32] transition-colors py-1 border-b-2 border-transparent hover:border-[#C85A32]"
            >
              Nuestra historia
            </button>
            <button
              onClick={() => scrollToSection('productos')}
              className="hover:text-[#C85A32] transition-colors py-1 border-b-2 border-transparent hover:border-[#C85A32]"
            >
              Productos
            </button>
            <button
              onClick={() => scrollToSection('que-hacemos')}
              className="hover:text-[#C85A32] transition-colors py-1 border-b-2 border-transparent hover:border-[#C85A32]"
            >
              Nuestro trabajo
            </button>
            <button
              onClick={() => scrollToSection('contacto')}
              className="hover:text-[#C85A32] transition-colors py-1 border-b-2 border-transparent hover:border-[#C85A32]"
            >
              Contacto
            </button>
          </nav>

          {/* Botones de Autenticación */}
          <div className="hidden md:flex items-center gap-3">
            <button
              onClick={() => {
                setLoginSimulationMessage(null);
                setCurrentView('login');
              }}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                currentView === 'login'
                  ? 'bg-[#3D1E16] text-[#FDFBF7] shadow-inner'
                  : 'text-[#3D1E16] hover:bg-[#F5EFE6] border border-[#EFE6DC]'
              }`}
            >
              Iniciar sesión
            </button>

            <button
              onClick={() => {
                setRegSuccess(false);
                setRegErrors({});
                setCurrentView('register');
              }}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-md flex items-center gap-2 ${
                currentView === 'register'
                  ? 'bg-[#5C1D24] text-white'
                  : 'bg-[#C85A32] hover:bg-[#A03C1B] text-white'
              }`}
            >
              <User className="w-3.5 h-3.5" />
              <span>Registrarse</span>
            </button>
          </div>

          {/* Botón Menú Móvil */}
          <div className="md:hidden flex items-center gap-2">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 text-[#3D1E16] bg-[#F5EFE6] rounded-xl border border-[#EFE6DC]"
            >
              {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Desplegable Menú Móvil */}
        {isMobileMenuOpen && (
          <div className="md:hidden bg-[#FAF6F0] border-b border-[#EFE6DC] px-4 pt-3 pb-6 space-y-3 shadow-lg">
            <nav className="flex flex-col space-y-2 text-xs font-bold uppercase tracking-wider text-[#3D1E16]">
              <button
                onClick={() => scrollToSection('hero')}
                className="text-left px-3 py-2 rounded-lg hover:bg-[#F5EFE6]"
              >
                Inicio
              </button>
              <button
                onClick={() => scrollToSection('quienes-somos')}
                className="text-left px-3 py-2 rounded-lg hover:bg-[#F5EFE6]"
              >
                Nuestra historia
              </button>
              <button
                onClick={() => scrollToSection('productos')}
                className="text-left px-3 py-2 rounded-lg hover:bg-[#F5EFE6]"
              >
                Productos
              </button>
              <button
                onClick={() => scrollToSection('que-hacemos')}
                className="text-left px-3 py-2 rounded-lg hover:bg-[#F5EFE6]"
              >
                Nuestro trabajo
              </button>
              <button
                onClick={() => scrollToSection('contacto')}
                className="text-left px-3 py-2 rounded-lg hover:bg-[#F5EFE6]"
              >
                Contacto
              </button>
            </nav>

            <div className="pt-3 border-t border-[#EFE6DC] flex flex-col gap-2">
              <button
                onClick={() => {
                  setLoginSimulationMessage(null);
                  setCurrentView('login');
                  setIsMobileMenuOpen(false);
                }}
                className="w-full py-2.5 text-center text-xs font-bold bg-[#F5EFE6] text-[#3D1E16] rounded-xl border border-[#EFE6DC]"
              >
                Iniciar sesión
              </button>
              <button
                onClick={() => {
                  setRegSuccess(false);
                  setRegErrors({});
                  setCurrentView('register');
                  setIsMobileMenuOpen(false);
                }}
                className="w-full py-2.5 text-center text-xs font-bold bg-[#C85A32] text-white rounded-xl shadow"
              >
                Registrarse
              </button>
            </div>
          </div>
        )}
      </header>

      {/* ========================================================================= */}
      {/* VISTA 1: PÁGINA PRINCIPAL DE LA TIENDA ('home') */}
      {/* ========================================================================= */}
      {currentView === 'home' && (
        <main className="flex-1">

          {/* 1. SECCIÓN PRINCIPAL / HERO */}
          <section id="hero" className="relative bg-[#FAF6F0] border-b border-[#EFE6DC] overflow-hidden py-12 md:py-20">
            {/* Patrón Geométrico sutil SVG de fondo */}
            <div className="absolute inset-0 opacity-5 pointer-events-none flex justify-center items-center">
              <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <pattern id="kanaas-pattern" width="60" height="60" patternUnits="userSpaceOnUse">
                    <path d="M 30 0 L 60 30 L 30 60 L 0 30 Z" fill="none" stroke="#3D1E16" strokeWidth="2" />
                    <path d="M 30 15 L 45 30 L 30 45 L 15 30 Z" fill="none" stroke="#C85A32" strokeWidth="1.5" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#kanaas-pattern)" />
              </svg>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
                
                {/* Columna Texto */}
                <div className="lg:col-span-7 space-y-6 text-center lg:text-left">
                  <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#E8C5C8]/40 border border-[#E8C5C8] text-[#5C1D24] text-xs font-bold">
                    <Sparkles className="w-3.5 h-3.5 text-[#C85A32]" />
                    <span>Tejidos Ancestrales de La Guajira, Colombia</span>
                  </div>

                  <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#3D1E16] tracking-tight leading-tight font-serif">
                    El Legado Cultural Wayúu <br className="hidden sm:inline" />
                    <span className="text-[#C85A32]">Tejido a Mano con Amor</span>
                  </h1>

                  <p className="text-sm sm:text-base text-[#3D1E16]/80 leading-relaxed max-w-2xl mx-auto lg:mx-0">
                    Bienvenido a nuestra tienda artesanal. Un espacio dedicado a preservar el arte sagrado de las tejedoras Wayúu, conectando la sabiduría de las rancherías con personas de todo el mundo mediante el comercio justo.
                  </p>

                  <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4 pt-2">
                    <button
                      onClick={() => scrollToSection('productos')}
                      className="w-full sm:w-auto px-6 py-3.5 bg-[#C85A32] hover:bg-[#A03C1B] text-white text-xs font-bold uppercase tracking-wider rounded-xl shadow-lg transition-all hover:shadow-xl flex items-center justify-center gap-2"
                    >
                      <ShoppingBag className="w-4 h-4" />
                      <span>Conoce nuestros productos</span>
                    </button>

                    <button
                      onClick={() => {
                        setLoginSimulationMessage(null);
                        setCurrentView('login');
                      }}
                      className="w-full sm:w-auto px-6 py-3.5 bg-[#F5EFE6] hover:bg-[#EFE6DC] text-[#3D1E16] text-xs font-bold uppercase tracking-wider rounded-xl border border-[#EFE6DC] transition-all flex items-center justify-center gap-2"
                    >
                      <User className="w-4 h-4 text-[#5C1D24]" />
                      <span>Iniciar sesión</span>
                    </button>
                  </div>

                  {/* Badges de Confianza */}
                  <div className="pt-6 border-t border-[#EFE6DC] grid grid-cols-3 gap-4 text-center lg:text-left">
                    <div>
                      <p className="text-lg font-extrabold text-[#5C1D24]">100%</p>
                      <p className="text-[11px] text-[#3D1E16]/70 font-medium">Hecho a mano</p>
                    </div>
                    <div>
                      <p className="text-lg font-extrabold text-[#5C1D24]">Comercio</p>
                      <p className="text-[11px] text-[#3D1E16]/70 font-medium">Ético y directo</p>
                    </div>
                    <div>
                      <p className="text-lg font-extrabold text-[#5C1D24]">Cultura</p>
                      <p className="text-[11px] text-[#3D1E16]/70 font-medium">Tradición viva</p>
                    </div>
                  </div>
                </div>

                {/* Columna Imagen Principal */}
                <div className="lg:col-span-5 relative">
                  <div className="relative rounded-3xl overflow-hidden shadow-2xl border-4 border-[#FAF6F0] bg-[#EFE6DC]">
                    <img
                      src="https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&q=80&w=800"
                      alt="Artesanía y Tejido Wayúu"
                      className="w-full h-[420px] object-cover hover:scale-105 transition-transform duration-700"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#3D1E16]/80 via-transparent to-transparent flex items-end p-6">
                      <div className="text-[#FDFBF7] space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-widest bg-[#C85A32] px-2.5 py-0.5 rounded-md">
                          Simbología Kanaas
                        </span>
                        <p className="text-sm font-bold font-serif">Mochila Susu de una hebra</p>
                        <p className="text-xs text-[#EFE6DC]/90">Elaborada en la Ranchería Mayapo</p>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </section>

          {/* 2. SECCIÓN: QUIÉNES SOMOS */}
          <section id="quienes-somos" className="py-16 bg-[#FDFBF7]">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="max-w-3xl mx-auto text-center space-y-4 mb-12">
                <span className="text-xs font-bold uppercase tracking-widest text-[#C85A32] bg-[#F5EFE6] px-3 py-1 rounded-full border border-[#EFE6DC]">
                  Nuestra Identidad
                </span>
                <h2 className="text-2xl sm:text-3xl font-extrabold text-[#3D1E16] font-serif">
                  ¿Quiénes Somos?
                </h2>
                <div className="w-16 h-1 bg-[#C85A32] mx-auto rounded-full"></div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div className="bg-[#FAF6F0] p-8 rounded-2xl border border-[#EFE6DC] shadow-sm space-y-4 text-center hover:border-[#C85A32] transition-colors">
                  <div className="w-12 h-12 rounded-2xl bg-[#E8C5C8]/50 text-[#5C1D24] flex items-center justify-center mx-auto">
                    <Compass className="w-6 h-6" />
                  </div>
                  <h3 className="text-base font-bold text-[#3D1E16]">Nuestro Propósito</h3>
                  <p className="text-xs text-[#3D1E16]/80 leading-relaxed">
                    Somos una tienda artesanal nacida con la misión de salvaguardar el legado textil de la etnia Wayúu, garantizando un canal comercial transparente, digno y sostenible para las comunidades de La Guajira.
                  </p>
                </div>

                <div className="bg-[#FAF6F0] p-8 rounded-2xl border border-[#EFE6DC] shadow-sm space-y-4 text-center hover:border-[#C85A32] transition-colors">
                  <div className="w-12 h-12 rounded-2xl bg-[#E8C5C8]/50 text-[#5C1D24] flex items-center justify-center mx-auto">
                    <Award className="w-6 h-6" />
                  </div>
                  <h3 className="text-base font-bold text-[#3D1E16]">Conservación Cultural</h3>
                  <p className="text-xs text-[#3D1E16]/80 leading-relaxed">
                    Promovemos la importancia de los clanes ancestrales (Epinayú, Pushaina, Uriana, Jayaliyu), transmitiendo la historia de sus símbolos geométricos para que el comprador valore cada puntada.
                  </p>
                </div>

                <div className="bg-[#FAF6F0] p-8 rounded-2xl border border-[#EFE6DC] shadow-sm space-y-4 text-center hover:border-[#C85A32] transition-colors">
                  <div className="w-12 h-12 rounded-2xl bg-[#E8C5C8]/50 text-[#5C1D24] flex items-center justify-center mx-auto">
                    <Shield className="w-6 h-6" />
                  </div>
                  <h3 className="text-base font-bold text-[#3D1E16]">Comercio Justo</h3>
                  <p className="text-xs text-[#3D1E16]/80 leading-relaxed">
                    Ofrecemos retribución justa y equitativa sin intermediarios abusivos. Cada compra apoya directamente el bienestar de las familias en las rancherías y el sustento de sus hogares.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* 3. SECCIÓN: NUESTRA HISTORIA */}
          <section className="py-16 bg-[#F5EFE6] border-y border-[#EFE6DC]">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
                
                <div className="lg:col-span-6 relative">
                  <div className="rounded-3xl overflow-hidden shadow-xl border-4 border-[#FAF6F0]">
                    <img
                      src="https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&q=80&w=800"
                      alt="Historia del Tejido Wayúu"
                      className="w-full h-[400px] object-cover"
                    />
                  </div>
                </div>

                <div className="lg:col-span-6 space-y-6">
                  <span className="text-xs font-bold uppercase tracking-widest text-[#C85A32]">
                    Leyenda y Tradición
                  </span>
                  <h2 className="text-2xl sm:text-3xl font-extrabold text-[#3D1E16] font-serif">
                    Nuestra Historia: El Mito de Wale’kerü
                  </h2>

                  <p className="text-xs sm:text-sm text-[#3D1E16]/80 leading-relaxed">
                    Según la tradición oral Wayúu, la araña mitológica conocida como <strong>Wale’kerü</strong> fue quien enseñó a tejer a las primeras mujeres de la etnia. Ella dibujaba con sus hilos los símbolos sagrados en la naturaleza antes del amanecer.
                  </p>

                  <p className="text-xs sm:text-sm text-[#3D1E16]/80 leading-relaxed">
                    Este conocimiento ancestral se transmite de abuelas a madres e hijas durante la etapa del encierro ritual de la pubertad. Tejer no es una simple labor técnica; es un ejercicio de pensamiento, paciencia y conexión espiritual con el territorio semidesértico de La Guajira.
                  </p>

                  <div className="p-4 rounded-2xl bg-[#FAF6F0] border border-[#EFE6DC] flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-[#5C1D24] text-white flex items-center justify-center shrink-0">
                      <Feather className="w-5 h-5" />
                    </div>
                    <p className="text-xs italic text-[#3D1E16]/90 font-medium">
                      "Un tejido Wayúu nunca es igual a otro; cada mochila refleja el pensamiento de la tejedora el día que la creó."
                    </p>
                  </div>
                </div>

              </div>
            </div>
          </section>

          {/* 4. SECCIÓN: ¿QUÉ HACEMOS? */}
          <section id="que-hacemos" className="py-16 bg-[#FDFBF7]">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="max-w-3xl mx-auto text-center space-y-4 mb-12">
                <span className="text-xs font-bold uppercase tracking-widest text-[#C85A32] bg-[#F5EFE6] px-3 py-1 rounded-full border border-[#EFE6DC]">
                  Gestión Comercial Ética
                </span>
                <h2 className="text-2xl sm:text-3xl font-extrabold text-[#3D1E16] font-serif">
                  ¿Qué Hacemos en Nuestra Tienda?
                </h2>
                <p className="text-xs sm:text-sm text-[#3D1E16]/80">
                  Organizamos, promocionamos y acercamos las creaciones de las tejedoras a clientes apasionados por el arte auténtico.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="p-6 rounded-2xl bg-[#FAF6F0] border border-[#EFE6DC] space-y-3">
                  <span className="w-8 h-8 rounded-lg bg-[#C85A32] text-white font-bold flex items-center justify-center text-xs">
                    01
                  </span>
                  <h3 className="text-sm font-bold text-[#3D1E16]">Reunión en Rancherías</h3>
                  <p className="text-xs text-[#3D1E16]/70 leading-relaxed">
                    Visitamos directamente los talleres familiares en Manaure, Uribia, Mayapo y Riohacha para seleccionar piezas auténticas.
                  </p>
                </div>

                <div className="p-6 rounded-2xl bg-[#FAF6F0] border border-[#EFE6DC] space-y-3">
                  <span className="w-8 h-8 rounded-lg bg-[#C85A32] text-white font-bold flex items-center justify-center text-xs">
                    02
                  </span>
                  <h3 className="text-sm font-bold text-[#3D1E16]">Control de Calidad</h3>
                  <p className="text-xs text-[#3D1E16]/70 leading-relaxed">
                    Verificamos la densidad del tejido, firmeza del hilo, acabado de las gasas y simetría de los patrones Kanaas.
                  </p>
                </div>

                <div className="p-6 rounded-2xl bg-[#FAF6F0] border border-[#EFE6DC] space-y-3">
                  <span className="w-8 h-8 rounded-lg bg-[#C85A32] text-white font-bold flex items-center justify-center text-xs">
                    03
                  </span>
                  <h3 className="text-sm font-bold text-[#3D1E16]">Catalogación Cultural</h3>
                  <p className="text-xs text-[#3D1E16]/70 leading-relaxed">
                    Documentamos el nombre de la artesana, su ranchería, la historia detrás del patrón y las horas de dedicación invertidas.
                  </p>
                </div>

                <div className="p-6 rounded-2xl bg-[#FAF6F0] border border-[#EFE6DC] space-y-3">
                  <span className="w-8 h-8 rounded-lg bg-[#C85A32] text-white font-bold flex items-center justify-center text-xs">
                    04
                  </span>
                  <h3 className="text-sm font-bold text-[#3D1E16]">Comercialización Directa</h3>
                  <p className="text-xs text-[#3D1E16]/70 leading-relaxed">
                    Llevamos las piezas al mercado nacional e internacional, ofreciendo una plataforma segura de adquisición.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* 5. SECCIÓN: NUESTROS PRODUCTOS */}
          <section id="productos" className="py-16 bg-[#FAF6F0] border-t border-[#EFE6DC]">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              
              <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
                <div className="space-y-2">
                  <span className="text-xs font-bold uppercase tracking-widest text-[#C85A32]">
                    Catálogo Seleccionado
                  </span>
                  <h2 className="text-2xl sm:text-3xl font-extrabold text-[#3D1E16] font-serif">
                    Nuestros Productos Artesanales
                  </h2>
                  <p className="text-xs text-[#3D1E16]/80 max-w-xl">
                    Explora nuestra variada selección de artesanías Wayúu: desde icónicas mochilas Susu y elegantes mantas hasta chinchorros de lujo y accesorios.
                  </p>
                </div>

                {/* Filtro de Búsqueda */}
                <div className="relative w-full md:w-72">
                  <Search className="w-4 h-4 text-[#3D1E16]/40 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Buscar producto o artesana..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-[#FDFBF7] border border-[#EFE6DC] rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]"
                  />
                </div>
              </div>

              {/* Botones de Filtro por Categorías */}
              <div className="flex items-center gap-2 overflow-x-auto pb-4 mb-8">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-4 py-2 rounded-xl text-xs font-bold shrink-0 transition-all ${
                      selectedCategory === cat
                        ? 'bg-[#5C1D24] text-white shadow'
                        : 'bg-[#FDFBF7] text-[#3D1E16] hover:bg-[#F5EFE6] border border-[#EFE6DC]'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Grid de Productos */}
              {filteredProducts.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
                  {filteredProducts.map((product) => (
                    <div
                      key={product.id}
                      className="bg-[#FDFBF7] rounded-3xl border border-[#EFE6DC] overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col justify-between group"
                    >
                      <div>
                        {/* Contenedor Imagen */}
                        <div className="relative h-64 overflow-hidden bg-[#EFE6DC]">
                          <img
                            src={product.image}
                            alt={product.name}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                          />
                          <span className="absolute top-3 left-3 bg-[#FDFBF7]/90 backdrop-blur-md text-[#5C1D24] text-[10px] font-black uppercase tracking-wider px-3 py-1 rounded-full border border-[#EFE6DC]">
                            {product.category}
                          </span>
                        </div>

                        {/* Detalle Texto */}
                        <div className="p-6 space-y-3">
                          <h3 className="text-base font-extrabold text-[#3D1E16] leading-snug group-hover:text-[#C85A32] transition-colors">
                            {product.name}
                          </h3>
                          <p className="text-xs text-[#3D1E16]/75 line-clamp-2">
                            {product.shortDescription}
                          </p>

                          <div className="pt-2 flex items-center justify-between text-xs border-t border-[#EFE6DC]">
                            <span className="text-[#3D1E16]/60">Tejedora:</span>
                            <span className="font-bold text-[#3D1E16]">{product.artisan}</span>
                          </div>
                        </div>
                      </div>

                      {/* Footer Tarjeta con Precio y Botón Ver Producto */}
                      <div className="p-6 pt-0 flex items-center justify-between">
                        <div>
                          <span className="text-[10px] text-[#3D1E16]/60 uppercase block">Precio COP</span>
                          <span className="text-base font-extrabold text-[#5C1D24]">
                            ${product.price.toLocaleString()}
                          </span>
                        </div>

                        <button
                          onClick={() => setSelectedProduct(product)}
                          className="px-4 py-2 bg-[#C85A32] hover:bg-[#A03C1B] text-white text-xs font-bold rounded-xl transition-colors shadow flex items-center gap-1.5"
                        >
                          <span>Ver producto</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="bg-[#FDFBF7] p-12 rounded-3xl border border-[#EFE6DC] text-center space-y-3">
                  <HelpCircle className="w-10 h-10 text-[#C85A32] mx-auto opacity-60" />
                  <p className="text-sm font-bold text-[#3D1E16]">
                    No se encontraron productos para esta búsqueda.
                  </p>
                  <p className="text-xs text-[#3D1E16]/60">
                    Intenta cambiar la categoría o limpiar los términos de búsqueda.
                  </p>
                  <button
                    onClick={() => {
                      setSelectedCategory('Todas');
                      setSearchQuery('');
                    }}
                    className="mt-2 px-4 py-2 bg-[#C85A32] text-white text-xs font-bold rounded-xl"
                  >
                    Restablecer filtros
                  </button>
                </div>
              )}

            </div>
          </section>

          {/* 6. SECCIÓN: NUESTRAS ARTESANAS */}
          <section className="py-16 bg-[#FDFBF7]">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="max-w-3xl mx-auto text-center space-y-4 mb-12">
                <span className="text-xs font-bold uppercase tracking-widest text-[#C85A32] bg-[#F5EFE6] px-3 py-1 rounded-full border border-[#EFE6DC]">
                  Manos Creadoras
                </span>
                <h2 className="text-2xl sm:text-3xl font-extrabold text-[#3D1E16] font-serif">
                  Nuestras Artesanas Tejedoras
                </h2>
                <p className="text-xs sm:text-sm text-[#3D1E16]/80">
                  Reconocemos el talento, la dedicación y el liderazgo de las mujeres en las rancherías de La Guajira.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {ARTISANS.map((artisan) => (
                  <div
                    key={artisan.id}
                    className="bg-[#FAF6F0] rounded-3xl border border-[#EFE6DC] overflow-hidden shadow-sm hover:shadow-md transition-shadow p-6 space-y-4 flex flex-col justify-between"
                  >
                    <div className="space-y-4">
                      <div className="flex items-center gap-4">
                        <img
                          src={artisan.image}
                          alt={artisan.name}
                          className="w-16 h-16 rounded-2xl object-cover border-2 border-[#C85A32]"
                        />
                        <div>
                          <h3 className="text-base font-extrabold text-[#3D1E16]">{artisan.name}</h3>
                          <p className="text-xs font-bold text-[#C85A32]">{artisan.clan}</p>
                          <p className="text-[11px] text-[#3D1E16]/60">{artisan.rancheria}</p>
                        </div>
                      </div>

                      <div className="p-3.5 rounded-xl bg-[#FDFBF7] border border-[#EFE6DC] text-xs text-[#3D1E16]/80 italic">
                        "{artisan.quote}"
                      </div>
                    </div>

                    <div className="pt-3 border-t border-[#EFE6DC] flex items-center justify-between text-xs text-[#3D1E16]/70">
                      <span>Especialidad:</span>
                      <span className="font-bold text-[#3D1E16]">{artisan.specialty}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* 7. SECCIÓN: CONTÁCTANOS */}
          <section id="contacto" className="py-16 bg-[#F5EFE6] border-t border-[#EFE6DC]">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
                
                {/* Información de Contacto Demostrativa */}
                <div className="lg:col-span-5 space-y-6">
                  <span className="text-xs font-bold uppercase tracking-widest text-[#C85A32]">
                    Atención e Inquietudes
                  </span>
                  <h2 className="text-2xl sm:text-3xl font-extrabold text-[#3D1E16] font-serif">
                    Ponte en Contacto
                  </h2>
                  <p className="text-xs sm:text-sm text-[#3D1E16]/80 leading-relaxed">
                    ¿Tienes dudas sobre los productos, requerimientos especiales o compras al por mayor? Comunícate con nuestro equipo de atención.
                  </p>

                  <div className="space-y-4 pt-2">
                    <div className="p-4 rounded-2xl bg-[#FAF6F0] border border-[#EFE6DC] flex items-start gap-4">
                      <div className="p-2.5 rounded-xl bg-[#E8C5C8]/50 text-[#5C1D24] shrink-0">
                        <MapPin className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-[#3D1E16]">Ubicación Principal</h4>
                        <p className="text-xs text-[#3D1E16]/70">
                          Calle 15 # 8-42, Centro Histórico <br />
                          Riohacha, La Guajira, Colombia (Sede Demostración)
                        </p>
                      </div>
                    </div>

                    <div className="p-4 rounded-2xl bg-[#FAF6F0] border border-[#EFE6DC] flex items-start gap-4">
                      <div className="p-2.5 rounded-xl bg-[#E8C5C8]/50 text-[#5C1D24] shrink-0">
                        <Phone className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-[#3D1E16]">Teléfono de Demostración</h4>
                        <p className="text-xs text-[#3D1E16]/70">+57 300 000 0000 / +57 605 000 0000</p>
                      </div>
                    </div>

                    <div className="p-4 rounded-2xl bg-[#FAF6F0] border border-[#EFE6DC] flex items-start gap-4">
                      <div className="p-2.5 rounded-xl bg-[#E8C5C8]/50 text-[#5C1D24] shrink-0">
                        <Mail className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-[#3D1E16]">Correo Electrónico</h4>
                        <p className="text-xs text-[#3D1E16]/70">contacto.demo@tiendawayuu.co</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Formulario de Mensaje Demostrativo */}
                <div className="lg:col-span-7 bg-[#FAF6F0] p-8 rounded-3xl border border-[#EFE6DC] shadow-md">
                  <h3 className="text-lg font-bold text-[#3D1E16] mb-2 font-serif">
                    Envíanos un mensaje
                  </h3>
                  <p className="text-xs text-[#3D1E16]/70 mb-6">
                    Completa el formulario de contacto para demostración del sistema.
                  </p>

                  {contactSent ? (
                    <div className="p-6 rounded-2xl bg-[#E8C5C8]/40 border border-[#E8C5C8] text-center space-y-3">
                      <CheckCircle2 className="w-10 h-10 text-[#5C1D24] mx-auto" />
                      <h4 className="text-sm font-bold text-[#5C1D24]">¡Mensaje enviado con éxito!</h4>
                      <p className="text-xs text-[#3D1E16]/80">
                        Gracias por comunicarte con la tienda artesanal Wayúu. Esta es una interacción de demostración.
                      </p>
                      <button
                        onClick={() => setContactSent(false)}
                        className="px-4 py-2 bg-[#C85A32] text-white text-xs font-bold rounded-xl mt-2"
                      >
                        Enviar otro mensaje
                      </button>
                    </div>
                  ) : (
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        setContactSent(true);
                      }}
                      className="space-y-4"
                    >
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-bold text-[#3D1E16] mb-1">Nombre completo *</label>
                          <input
                            type="text"
                            required
                            placeholder="Ej. Ana María Gómez"
                            className="w-full p-3 bg-[#FDFBF7] border border-[#EFE6DC] rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-bold text-[#3D1E16] mb-1">Correo electrónico *</label>
                          <input
                            type="email"
                            required
                            placeholder="ejemplo@correo.com"
                            className="w-full p-3 bg-[#FDFBF7] border border-[#EFE6DC] rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-[#3D1E16] mb-1">Asunto *</label>
                        <input
                          type="text"
                          required
                          placeholder="Consulta sobre productos o envíos"
                          className="w-full p-3 bg-[#FDFBF7] border border-[#EFE6DC] rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-[#3D1E16] mb-1">Mensaje *</label>
                        <textarea
                          rows={4}
                          required
                          placeholder="Escribe tu mensaje aquí..."
                          className="w-full p-3 bg-[#FDFBF7] border border-[#EFE6DC] rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]"
                        ></textarea>
                      </div>

                      <button
                        type="submit"
                        className="w-full py-3.5 bg-[#C85A32] hover:bg-[#A03C1B] text-white text-xs font-bold uppercase tracking-wider rounded-xl shadow transition-colors flex items-center justify-center gap-2"
                      >
                        <Send className="w-4 h-4" />
                        <span>Enviar mensaje demostrativo</span>
                      </button>
                    </form>
                  )}
                </div>

              </div>

            </div>
          </section>

        </main>
      )}

      {/* ========================================================================= */}
      {/* VISTA 2: INICIAR SESIÓN ('login') */}
      {/* ========================================================================= */}
      {currentView === 'login' && (
        <main className="flex-1 py-12 md:py-16 bg-[#FAF6F0] flex items-center justify-center px-4">
          <div className="w-full max-w-md bg-[#FDFBF7] rounded-3xl border border-[#EFE6DC] shadow-xl overflow-hidden">
            
            {/* Header del Formulario */}
            <div className="bg-[#5C1D24] text-white p-8 text-center relative overflow-hidden">
              <div className="w-12 h-12 rounded-2xl bg-white/10 text-[#FDFBF7] flex items-center justify-center mx-auto mb-3 border border-white/20">
                <Feather className="w-6 h-6" />
              </div>
              <h1 className="text-xl font-bold font-serif">Tienda Wayúu</h1>
              <p className="text-xs text-[#E8C5C8] mt-1 font-medium">Acceso de Clientes</p>
            </div>

            {/* Cuerpo del Formulario */}
            <div className="p-8 space-y-6">
              <div className="text-center">
                <h2 className="text-lg font-extrabold text-[#3D1E16]">Bienvenido de nuevo</h2>
                <p className="text-xs text-[#3D1E16]/70 mt-1">
                  Ingresa tus credenciales para acceder a la tienda.
                </p>
              </div>

              {/* Banner de Simulación de Redirección Futura */}
              {loginSimulationMessage && (
                <div className="p-4 rounded-2xl bg-[#E8C5C8]/40 border border-[#E8C5C8] text-xs text-[#5C1D24] space-y-2">
                  <div className="flex items-center gap-2 font-bold">
                    <CheckCircle2 className="w-4 h-4 text-[#5C1D24] shrink-0" />
                    <span>Inicio de sesión correcto</span>
                  </div>
                  <p className="text-[#3D1E16]/80 leading-relaxed">
                    {loginSimulationMessage}
                  </p>
                  <div className="pt-2 flex gap-2">
                    <button
                      onClick={() => setCurrentView('home')}
                      className="px-3 py-1.5 bg-[#5C1D24] text-white text-[11px] font-bold rounded-lg"
                    >
                      Volver a la tienda
                    </button>
                  </div>
                </div>
              )}

              {loginError && <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs font-semibold text-red-700" role="alert">{loginError}</p>}

              <form onSubmit={handleLoginSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-[#3D1E16] mb-1.5">
                    Correo electrónico *
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-[#3D1E16]/40 absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="email"
                      required
                      placeholder="tu.correo@ejemplo.com"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 bg-[#FAF6F0] border border-[#EFE6DC] rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#3D1E16] mb-1.5">
                    Contraseña *
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-[#3D1E16]/40 absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type={showLoginPassword ? 'text' : 'password'}
                      required
                      placeholder="••••••••"
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      className="w-full pl-10 pr-10 py-3 bg-[#FAF6F0] border border-[#EFE6DC] rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowLoginPassword(!showLoginPassword)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#3D1E16]/50 hover:text-[#3D1E16]"
                    >
                      {showLoginPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px]">
                  <label className="flex items-center gap-2 text-[#3D1E16]/70 cursor-pointer">
                    <input type="checkbox" defaultChecked className="rounded accent-[#C85A32]" />
                    <span>Recordarme</span>
                  </label>
                  <a
                    href="#forgot"
                    onClick={(e) => {
                      e.preventDefault();
                      alert('Demostración: En la versión final enviará un enlace de recuperación por correo.');
                    }}
                    className="text-[#C85A32] font-bold hover:underline"
                  >
                    ¿Olvidaste tu contraseña?
                  </a>
                </div>

                <button
                  type="submit"
                  className="w-full py-3.5 bg-[#C85A32] hover:bg-[#A03C1B] text-white text-xs font-bold uppercase tracking-wider rounded-xl shadow transition-colors flex items-center justify-center gap-2"
                >
                  <User className="w-4 h-4" />
                  <span>Iniciar sesión</span>
                </button>
              </form>

              {/* Navegación y Enlaces */}
              <div className="pt-4 border-t border-[#EFE6DC] space-y-3 text-center text-xs">
                <p className="text-[#3D1E16]/70">
                  ¿No tienes una cuenta?{' '}
                  <button
                    onClick={() => {
                      setRegSuccess(false);
                      setRegErrors({});
                      setCurrentView('register');
                    }}
                    className="text-[#C85A32] font-bold hover:underline"
                  >
                    Regístrate aquí
                  </button>
                </p>

                <div>
                  <button
                    onClick={() => setCurrentView('home')}
                    className="inline-flex items-center gap-1.5 text-xs text-[#5C1D24] font-bold hover:underline"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    <span>Volver a la tienda principal</span>
                  </button>
                </div>
              </div>

            </div>
          </div>
        </main>
      )}

      {/* ========================================================================= */}
      {/* VISTA 3: REGISTRARSE ('register') */}
      {/* ========================================================================= */}
      {currentView === 'register' && (
        <main className="flex-1 py-12 md:py-16 bg-[#FAF6F0] flex items-center justify-center px-4">
          <div className="w-full max-w-lg bg-[#FDFBF7] rounded-3xl border border-[#EFE6DC] shadow-xl overflow-hidden">
            
            {/* Header del Formulario */}
            <div className="bg-[#5C1D24] text-white p-8 text-center">
              <div className="w-12 h-12 rounded-2xl bg-white/10 text-[#FDFBF7] flex items-center justify-center mx-auto mb-3 border border-white/20">
                <User className="w-6 h-6" />
              </div>
              <h1 className="text-xl font-bold font-serif">Crear una Cuenta</h1>
              <p className="text-xs text-[#E8C5C8] mt-1 font-medium">Únete a la comunidad de la Tienda Wayúu</p>
            </div>

            <div className="p-8 space-y-6">
              
              {/* Pantalla de Confirmación Exitosa del Registro */}
              {regSuccess ? (
                <div className="p-6 rounded-2xl bg-[#E8C5C8]/40 border border-[#E8C5C8] text-center space-y-4">
                  <CheckCircle2 className="w-12 h-12 text-[#5C1D24] mx-auto" />
                  <h2 className="text-lg font-extrabold text-[#5C1D24]">¡Registro completado con éxito!</h2>
                  <p className="text-xs text-[#3D1E16]/80 leading-relaxed">
                    Tu cuenta fue creada y la sesión quedó iniciada. Ya puedes entrar a tu panel de cliente.
                  </p>
                  <div className="pt-2">
                    <button
                      onClick={() => user ? goToRolePanel(user.role) : setCurrentView('login')}
                      className="w-full py-3 bg-[#C85A32] text-white text-xs font-bold uppercase tracking-wider rounded-xl shadow"
                    >
                      Ir a mi panel
                    </button>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleRegisterSubmit} className="space-y-4">
                  {regErrors.server && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs font-semibold text-red-700">{regErrors.server}</p>}
                  
                  {/* Nombres y Apellidos */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-[#3D1E16] mb-1">
                        Nombres *
                      </label>
                      <input
                        type="text"
                        placeholder="Ej. María Fernanda"
                        value={regFirstName}
                        onChange={(e) => setRegFirstName(e.target.value)}
                        className={`w-full p-3 bg-[#FAF6F0] border ${
                          regErrors.firstName ? 'border-red-500' : 'border-[#EFE6DC]'
                        } rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]`}
                      />
                      {regErrors.firstName && (
                        <p className="text-[11px] text-red-600 font-bold mt-1">{regErrors.firstName}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-[#3D1E16] mb-1">
                        Apellidos *
                      </label>
                      <input
                        type="text"
                        placeholder="Ej. Gómez López"
                        value={regLastName}
                        onChange={(e) => setRegLastName(e.target.value)}
                        className={`w-full p-3 bg-[#FAF6F0] border ${
                          regErrors.lastName ? 'border-red-500' : 'border-[#EFE6DC]'
                        } rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]`}
                      />
                      {regErrors.lastName && (
                        <p className="text-[11px] text-red-600 font-bold mt-1">{regErrors.lastName}</p>
                      )}
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-[#3D1E16] mb-1">Nombre de usuario *</label>
                    <input
                      type="text"
                      autoComplete="username"
                      value={regUsername}
                      onChange={(e) => setRegUsername(e.target.value)}
                      className={`w-full p-3 bg-[#FAF6F0] border ${regErrors.username ? 'border-red-500' : 'border-[#EFE6DC]'} rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]`}
                    />
                    {regErrors.username && <p className="text-[11px] text-red-600 font-bold mt-1">{regErrors.username}</p>}
                  </div>

                  {/* Correo Electrónico y Teléfono */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-[#3D1E16] mb-1">
                        Correo electrónico *
                      </label>
                      <input
                        type="email"
                        placeholder="ejemplo@correo.com"
                        value={regEmail}
                        onChange={(e) => setRegEmail(e.target.value)}
                        className={`w-full p-3 bg-[#FAF6F0] border ${
                          regErrors.email ? 'border-red-500' : 'border-[#EFE6DC]'
                        } rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]`}
                      />
                      {regErrors.email && (
                        <p className="text-[11px] text-red-600 font-bold mt-1">{regErrors.email}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-[#3D1E16] mb-1">
                        Teléfono de contacto *
                      </label>
                      <input
                        type="tel"
                        placeholder="+57 300 000 0000"
                        value={regPhone}
                        onChange={(e) => setRegPhone(e.target.value)}
                        className={`w-full p-3 bg-[#FAF6F0] border ${
                          regErrors.phone ? 'border-red-500' : 'border-[#EFE6DC]'
                        } rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]`}
                      />
                      {regErrors.phone && (
                        <p className="text-[11px] text-red-600 font-bold mt-1">{regErrors.phone}</p>
                      )}
                    </div>
                  </div>

                  {/* Contraseñas */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-[#3D1E16] mb-1">
                        Contraseña *
                      </label>
                      <div className="relative">
                        <input
                          type={showRegPassword ? 'text' : 'password'}
                          placeholder="Mínimo 8 caracteres"
                          value={regPassword}
                          onChange={(e) => setRegPassword(e.target.value)}
                          className={`w-full p-3 pr-10 bg-[#FAF6F0] border ${
                            regErrors.password ? 'border-red-500' : 'border-[#EFE6DC]'
                          } rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]`}
                        />
                        <button
                          type="button"
                          onClick={() => setShowRegPassword(!showRegPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-[#3D1E16]/50 hover:text-[#3D1E16]"
                        >
                          {showRegPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                      {regErrors.password && (
                        <p className="text-[11px] text-red-600 font-bold mt-1">{regErrors.password}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-[#3D1E16] mb-1">
                        Confirmar contraseña *
                      </label>
                      <input
                        type={showRegPassword ? 'text' : 'password'}
                        placeholder="Repite tu contraseña"
                        value={regConfirmPassword}
                        onChange={(e) => setRegConfirmPassword(e.target.value)}
                        className={`w-full p-3 bg-[#FAF6F0] border ${
                          regErrors.confirmPassword ? 'border-red-500' : 'border-[#EFE6DC]'
                        } rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#C85A32]`}
                      />
                      {regErrors.confirmPassword && (
                        <p className="text-[11px] text-red-600 font-bold mt-1">{regErrors.confirmPassword}</p>
                      )}
                    </div>
                  </div>

                  {/* Términos y Condiciones */}
                  <div className="pt-2">
                    <label className="flex items-start gap-2.5 text-xs text-[#3D1E16]/80 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={regAcceptTerms}
                        onChange={(e) => setRegAcceptTerms(e.target.checked)}
                        className="mt-0.5 rounded accent-[#C85A32]"
                      />
                      <span>
                        Acepto los <strong>Términos y Condiciones</strong> y las políticas de tratamiento de datos personales de la Tienda Artesanal Wayúu.
                      </span>
                    </label>
                    {regErrors.terms && (
                      <p className="text-[11px] text-red-600 font-bold mt-1">{regErrors.terms}</p>
                    )}
                  </div>

                  <button
                    type="submit"
                    className="w-full py-3.5 bg-[#C85A32] hover:bg-[#A03C1B] text-white text-xs font-bold uppercase tracking-wider rounded-xl shadow transition-colors flex items-center justify-center gap-2 mt-4"
                  >
                    <User className="w-4 h-4" />
                    <span>Crear cuenta</span>
                  </button>
                </form>
              )}

              {/* Enlaces de Navegación */}
              <div className="pt-4 border-t border-[#EFE6DC] space-y-3 text-center text-xs">
                <p className="text-[#3D1E16]/70">
                  ¿Ya tienes una cuenta?{' '}
                  <button
                    onClick={() => {
                      setLoginSimulationMessage(null);
                      setCurrentView('login');
                    }}
                    className="text-[#C85A32] font-bold hover:underline"
                  >
                    Inicia sesión aquí
                  </button>
                </p>

                <div>
                  <button
                    onClick={() => setCurrentView('home')}
                    className="inline-flex items-center gap-1.5 text-xs text-[#5C1D24] font-bold hover:underline"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    <span>Volver a la tienda principal</span>
                  </button>
                </div>
              </div>

            </div>
          </div>
        </main>
      )}

      {/* ========================================================================= */}
      {/* MODAL INTERACTIVO DE DETALLE DE PRODUCTO (SIN SER UNA 4TA VISTA) */}
      {/* ========================================================================= */}
      {selectedProduct && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-[#FDFBF7] rounded-3xl max-w-2xl w-full p-6 sm:p-8 shadow-2xl border border-[#EFE6DC] relative my-8 space-y-6">
            
            {/* Botón Cerrar Modal */}
            <button
              onClick={() => setSelectedProduct(null)}
              className="absolute top-4 right-4 p-2 text-[#3D1E16]/60 hover:text-[#3D1E16] bg-[#FAF6F0] rounded-full border border-[#EFE6DC]"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="grid grid-cols-1 sm:grid-cols-12 gap-6 items-start">
              
              {/* Imagen Producto */}
              <div className="sm:col-span-5">
                <div className="rounded-2xl overflow-hidden border border-[#EFE6DC] bg-[#EFE6DC] h-64 sm:h-72">
                  <img
                    src={selectedProduct.image}
                    alt={selectedProduct.name}
                    className="w-full h-full object-cover"
                  />
                </div>
                <span className="inline-block mt-3 bg-[#E8C5C8]/40 border border-[#E8C5C8] text-[#5C1D24] text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full">
                  {selectedProduct.category}
                </span>
              </div>

              {/* Información y Especificaciones */}
              <div className="sm:col-span-7 space-y-4">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#C85A32]">
                    Detalle del Producto
                  </span>
                  <h3 className="text-xl font-extrabold text-[#3D1E16] font-serif leading-tight mt-0.5">
                    {selectedProduct.name}
                  </h3>
                  <p className="text-lg font-black text-[#5C1D24] mt-1">
                    ${selectedProduct.price.toLocaleString()} COP
                  </p>
                </div>

                <p className="text-xs text-[#3D1E16]/80 leading-relaxed">
                  {selectedProduct.fullDescription}
                </p>

                {/* Símbolo Kanaas */}
                <div className="p-3.5 rounded-2xl bg-[#FAF6F0] border border-[#EFE6DC] space-y-1">
                  <p className="text-xs font-bold text-[#3D1E16]">Simbología Kanaas:</p>
                  <p className="text-xs text-[#3D1E16]/75 italic">{selectedProduct.symbolism}</p>
                </div>

                {/* Ficha Tejedora */}
                <div className="space-y-1 text-xs text-[#3D1E16]/80 border-t border-[#EFE6DC] pt-3">
                  <p><strong>Artesana:</strong> {selectedProduct.artisan}</p>
                  <p><strong>Ranchería:</strong> {selectedProduct.rancheria}</p>
                  <p><strong>Técnica:</strong> {selectedProduct.technique}</p>
                  <p><strong>Materiales:</strong> {selectedProduct.material}</p>
                </div>
              </div>

            </div>

            {/* Footer Modal con Acción */}
            <div className="pt-4 border-t border-[#EFE6DC] flex flex-col sm:flex-row items-center justify-between gap-3">
              <span className="text-xs text-[#3D1E16]/60">
                Pieza artesanal garantizada con sello de origen.
              </span>

              <div className="flex items-center gap-2 w-full sm:w-auto">
                <button
                  onClick={() => {
                    setSelectedProduct(null);
                    setLoginSimulationMessage(null);
                    setCurrentView('login');
                  }}
                  className="flex-1 sm:flex-none px-4 py-2.5 bg-[#C85A32] hover:bg-[#A03C1B] text-white text-xs font-bold rounded-xl shadow transition-colors"
                >
                  Iniciar sesión para comprar
                </button>
                <button
                  onClick={() => setSelectedProduct(null)}
                  className="px-4 py-2.5 bg-[#FAF6F0] text-[#3D1E16] text-xs font-bold rounded-xl border border-[#EFE6DC]"
                >
                  Cerrar
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* PIE DE PÁGINA / FOOTER PÚBLICO */}
      {/* ========================================================================= */}
      <footer className="bg-[#3D1E16] text-[#FDFBF7] border-t border-[#A03C1B]/30 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
            
            {/* Logo y Descripción */}
            <div className="md:col-span-4 space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-[#C85A32] text-white flex items-center justify-center">
                  <Feather className="w-5 h-5" />
                </div>
                <span className="text-lg font-bold tracking-wide font-serif">WAYÚU</span>
              </div>
              <p className="text-xs text-[#EFE6DC]/80 leading-relaxed">
                Tienda pública de artesanías y tejidos elaborados por tejedoras de las rancherías de La Guajira, Colombia. Conservación cultural y comercio justo.
              </p>
            </div>

            {/* Navegación Rápida */}
            <div className="md:col-span-4 space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#C85A32]">Navegación</h4>
              <ul className="space-y-2 text-xs text-[#EFE6DC]/80">
                <li>
                  <button onClick={() => scrollToSection('hero')} className="hover:text-white transition-colors">
                    Inicio
                  </button>
                </li>
                <li>
                  <button onClick={() => scrollToSection('quienes-somos')} className="hover:text-white transition-colors">
                    Nuestra Historia y Cultura
                  </button>
                </li>
                <li>
                  <button onClick={() => scrollToSection('productos')} className="hover:text-white transition-colors">
                    Catálogo de Productos
                  </button>
                </li>
                <li>
                  <button onClick={() => scrollToSection('contacto')} className="hover:text-white transition-colors">
                    Atención y Contacto
                  </button>
                </li>
              </ul>
            </div>

            {/* Contacto y Ubicación */}
            <div className="md:col-span-4 space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#C85A32]">Ubicación y Contacto</h4>
              <div className="space-y-2 text-xs text-[#EFE6DC]/80">
                <p>Riohacha, La Guajira - Colombia</p>
                <p>Teléfono: +57 300 000 0000 (Demostración)</p>
                <p>Correo: contacto.demo@tiendawayuu.co</p>
              </div>
            </div>

          </div>

          <div className="pt-8 mt-8 border-t border-white/10 text-center text-[11px] text-[#EFE6DC]/60 flex flex-col sm:flex-row items-center justify-between gap-2">
            <p>© {new Date().getFullYear()} Tienda Artesanal Wayúu. Todos los derechos reservados.</p>
            <p className="text-[10px]">Sitio Público Independiente para Comercio Artesanal</p>
          </div>
        </div>
      </footer>

    </div>
  );
}