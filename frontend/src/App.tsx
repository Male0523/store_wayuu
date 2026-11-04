import { lazy, Suspense, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useUserSession } from './context/user-context'
import type { SessionUser } from './types'

const CustomerPanel = lazy(() => import('./CustomerPanel'))
const ConnectedShop = lazy(() => import('./ShopApp').then((module) => ({ default: module.ConnectedShop })))

type Role = SessionUser['role']

const roleRoutes: { path: string; label: string; role: Role }[] = [
	{ path: '/cliente', label: 'Cliente', role: 'customer' },
	{ path: '/tejedora', label: 'Tejedora', role: 'craftswoman' },
	{ path: '/admin', label: 'Administración', role: 'admin' },
	{ path: '/superadmin', label: 'Superadministración', role: 'superadmin' },
]

function DemoNotice() {
	return (
		<div className="demo-notice" role="note">
			Interfaz original · datos demostrativos temporales; los cambios no se guardan en Django.
		</div>
	)
}

function AccessGate({ user, onLogin }: {
	user: SessionUser | null
	onLogin: (event: FormEvent<HTMLFormElement>) => Promise<void>
}) {
	const [error, setError] = useState('')
	const [busy, setBusy] = useState(false)

	async function submit(event: FormEvent<HTMLFormElement>) {
		setBusy(true)
		setError('')
		try {
			await onLogin(event)
		} catch (reason) {
			setError(reason instanceof Error ? reason.message : 'No fue posible iniciar sesión.')
		} finally {
			setBusy(false)
		}
	}

	if (user) {
		const destination = roleRoutes.find((route) => route.role === user.role)
		return (
			<section className="access-page">
				<div className="access-story">
					<p className="access-kicker">WAYUUWAA · TEJIDO CON ORIGEN</p>
					<div className="access-weave" aria-hidden="true"><span /><span /><span /><span /><span /></div>
					<p className="access-story-note">Cada pieza guarda una historia. Cada acceso cuida el trabajo de quienes la hacen posible.</p>
				</div>
				<div className="access-card" aria-live="polite">
					<p className="access-card-kicker">ACCESO A LA PLATAFORMA</p>
					<h1>Esta vista no está disponible para tu cuenta.</h1>
					<p>Tu sesión está activa, pero corresponde a otro perfil. Los permisos se validan de forma segura en Django.</p>
					{destination && <a className="access-submit" href={destination.path}>Ir a {destination.label}</a>}
				</div>
			</section>
		)
	}

	return (
		<section className="access-page">
			<div className="access-story">
				<p className="access-kicker">WAYUUWAA · TEJIDO CON ORIGEN</p>
				<div className="access-weave" aria-hidden="true"><span /><span /><span /><span /><span /></div>
				<p className="access-story-note">Una tienda construida alrededor del oficio, la memoria y las manos de las tejedoras Wayúu.</p>
			</div>
			<div className="access-card">
				<a className="access-back" href="/">Volver a la tienda</a>
				<p className="access-card-kicker">BIENVENIDA DE NUEVO</p>
				<h1>Tu espacio en Wayúu.</h1>
				<p>Inicia sesión para continuar con tu cuenta y acceder a las funciones que corresponden a tu perfil.</p>
				<form className="access-form" onSubmit={submit}>
					<label>Usuario<input name="username" autoComplete="username" placeholder="Escribe tu usuario" required /></label>
					<label>Contraseña<input name="password" type="password" autoComplete="current-password" placeholder="Tu contraseña" required /></label>
					{error && <p className="form-error" role="alert">{error}</p>}
					<button className="access-submit" type="submit" disabled={busy}>{busy ? 'Validando acceso…' : 'Iniciar sesión'}</button>
				</form>
				<p className="access-security-note">Acceso protegido · La plataforma valida tu identidad y tus permisos.</p>
			</div>
		</section>
	)
}

function RolePage({ user, role, onLogin, children, connected = false }: {
	user: SessionUser | null
	role: Role
	onLogin: (event: FormEvent<HTMLFormElement>) => Promise<void>
	children: ReactNode
	connected?: boolean
}) {
	if (user?.role !== role) return <AccessGate user={user} onLogin={onLogin} />
	if (role === 'craftswoman' && user.profile?.active === false) {
		return <section className="access-panel"><h1>Cuenta pendiente de activación</h1><p>La administración debe activar el perfil antes de habilitar el panel de tejedora.</p></section>
	}
	return connected ? <>{children}</> : <><DemoNotice />{children}</>
}

export default function App() {
	const [path, setPath] = useState(window.location.pathname)
	const standaloneStorefront = path === '/' || path === '/tienda'
	const [logoutError, setLogoutError] = useState('')
	const { user, loaded: sessionLoaded, sessionError, login: loginUser, logout: logoutUser } = useUserSession()

	useEffect(() => {
		const syncPath = () => setPath(window.location.pathname)
		window.addEventListener('popstate', syncPath)
		return () => {
			window.removeEventListener('popstate', syncPath)
		}
	}, [])

	function navigate(event: React.MouseEvent<HTMLAnchorElement>, destination: string) {
		if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
		event.preventDefault()
		window.history.pushState(null, '', destination)
		setPath(destination)
	}

	async function login(event: FormEvent<HTMLFormElement>) {
		event.preventDefault()
		const values = new FormData(event.currentTarget)
		const account = await loginUser(String(values.get('username')), String(values.get('password')))
		const destination = roleRoutes.find((route) => route.role === account.role)?.path ?? '/tienda'
		window.history.pushState(null, '', destination)
		setPath(destination)
	}

	async function logout() {
		setLogoutError('')
		try {
			await logoutUser()
		} catch {
			setLogoutError('No se pudo cerrar la sesión con Django. Revisa la conexión e inténtalo de nuevo.')
			return
		}
		window.history.pushState(null, '', '/')
		setPath('/')
	}

	function protectedPage(role: Role, page: ReactNode, connected = false) {
		if (!sessionLoaded) return <div className="route-loading" role="status">Comprobando sesión…</div>
		return <RolePage user={user} role={role} onLogin={login} connected={connected}>{page}</RolePage>
	}

	let page: ReactNode
	switch (path.replace(/\/$/, '') || '/') {
		case '/': page = <ConnectedShop key="public" initialScreen="shop" />; break
		case '/cliente': page = protectedPage('customer', <CustomerPanel />, true); break
		case '/tienda': page = <ConnectedShop key="tienda" initialScreen="shop" />; break
		case '/tejedora': page = protectedPage('craftswoman', <ConnectedShop key="tejedora" initialScreen="craftswoman" />, true); break
		case '/admin': page = protectedPage('admin', <ConnectedShop key="admin" initialScreen="admin" />, true); break
		case '/superadmin': page = protectedPage('superadmin', <ConnectedShop key="superadmin" initialScreen="admin" />, true); break
		default: page = <section className="access-panel"><h1>Página no encontrada</h1><a className="primary-link" href="/" onClick={(event) => navigate(event, '/')}>Volver al inicio</a></section>
	}

	return (
		<>
			{!standaloneStorefront && <header className="unified-header">
				<a className="unified-brand" href="/" onClick={(event) => navigate(event, '/')}>STORE WAYUU</a>
				<nav aria-label="Navegación de la aplicación">
					<a href="/" onClick={(event) => navigate(event, '/')}>Sitio público</a>
					<a href="/tienda" onClick={(event) => navigate(event, '/tienda')}>Tienda conectada</a>
					{roleRoutes.filter((route) => route.role === user?.role).map((route) => (
						<a key={route.path} href={route.path} onClick={(event) => navigate(event, route.path)}>{route.label}</a>
					))}
				</nav>
				{user && <button className="session-button" type="button" onClick={logout}>Cerrar sesión</button>}
			</header>}
			{logoutError && <p className="form-error" role="alert">{logoutError}</p>}
			{sessionError && <p className="form-error" role="status">{sessionError}</p>}
			<main>
				<Suspense fallback={<div className="route-loading" role="status">Cargando interfaz…</div>}>
					{page}
				</Suspense>
			</main>
			{!standaloneStorefront && <footer className="authorization-note">
				La protección de rutas en el navegador es solo de navegación. Django debe autorizar cada operación y endpoint.
			</footer>}
		</>
	)
}
